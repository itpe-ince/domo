"""Integration-style endpoint tests for editor-image-studio PDCA #6-image — Backend Step 4.

Strategy: direct endpoint function calls with MagicMock stand-ins for SQLAlchemy
model instances, AsyncMock for DB session, and MagicMock for storage provider.
No real DB, no real network. Catches contract regressions: ApiError codes, HTTP
statuses, permission flow, Pydantic validation, and storage interactions.

SQLAlchemy mapped classes cannot be instantiated with __new__ outside of a session
context, so all model "instances" are MagicMock objects with the required attributes
set explicitly. This is the standard approach for endpoint-function unit testing.

Design ref: §B-5 (transform endpoint), §B-10 (error codes), §B-14 (signature endpoints).

10 required test cases:
  Transform (7): 404, 403, 409, 415×2, 413, 200 (seed+second-call), 400 sig-missing
  Signature (3): 415 unsupported, GET null, DELETE idempotent
"""
from __future__ import annotations

import io
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from PIL import Image

from app.core.errors import ApiError
from app.schemas.media_transform import (
    MediaTransformRequest,
    RotateOp,
    WatermarkOp,
    WatermarkPosition,
)

# ---------------------------------------------------------------------------
# Fixture helpers — MagicMock model instances
# ---------------------------------------------------------------------------


def _make_user(
    *,
    user_id: uuid.UUID | None = None,
    signature_storage_key: str | None = None,
    status: str = "active",
    warning_count: int = 0,
) -> MagicMock:
    u = MagicMock()
    u.id = user_id or uuid.uuid4()
    u.email = "test@example.com"
    u.role = "artist"
    u.status = status
    u.warning_count = warning_count
    u.display_name = "Test Artist"
    u.signature_storage_key = signature_storage_key
    return u


def _make_post(
    *,
    post_id: uuid.UUID | None = None,
    author_id: uuid.UUID | None = None,
    type_: str = "general",
) -> MagicMock:
    p = MagicMock()
    p.id = post_id or uuid.uuid4()
    p.author_id = author_id or uuid.uuid4()
    p.type = type_
    return p


def _make_media(
    *,
    media_id: uuid.UUID | None = None,
    post_id: uuid.UUID | None = None,
    type_: str = "image",
    storage_key: str = "uploads/test/img.jpg",
    original_storage_key: str | None = None,
    size_bytes: int | None = 1024 * 1024,
) -> MagicMock:
    m = MagicMock()
    m.id = media_id or uuid.uuid4()
    m.post_id = post_id or uuid.uuid4()
    m.type = type_
    m.url = f"http://localhost/uploads/{m.id}.jpg"
    m.storage_key = storage_key
    m.original_storage_key = original_storage_key
    m.size_bytes = size_bytes
    m.thumbnail_url = None
    m.thumb_small_url = None
    m.thumb_medium_url = None
    m.thumb_large_url = None
    m.width = 200
    m.height = 100
    m.crop_meta = None
    m.storage_provider = "local"
    return m


def _make_jpeg_bytes(width: int = 200, height: int = 100) -> bytes:
    img = Image.new("RGB", (width, height), color=(100, 150, 200))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return buf.getvalue()


def _make_db_mock(
    media: MagicMock | None,
    post: MagicMock | None,
    *,
    active_auction: MagicMock | None = None,
) -> AsyncMock:
    """AsyncSession mock: returns media, then post, then auction result on successive execute()."""
    db = AsyncMock()

    media_scalar = MagicMock()
    media_scalar.scalar_one_or_none.return_value = media

    post_scalar = MagicMock()
    post_scalar.scalar_one_or_none.return_value = post

    auction_scalar = MagicMock()
    auction_scalar.scalar_one_or_none.return_value = active_auction

    db.execute = AsyncMock(side_effect=[media_scalar, post_scalar, auction_scalar])
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.flush = AsyncMock()
    return db


def _make_provider_mock(image_bytes: bytes | None = None) -> MagicMock:
    provider = MagicMock()
    provider.get = AsyncMock(return_value=image_bytes or _make_jpeg_bytes())

    stored = MagicMock()
    stored.url = "http://localhost/transformed/result.jpg"
    stored.key = "transformed/abc/result.jpg"
    stored.provider = "local"
    stored.size_bytes = 50000
    provider.put = AsyncMock(return_value=stored)
    provider.delete = AsyncMock()
    provider.public_url = MagicMock(return_value="http://localhost/sig.png")
    return provider


_ROTATE_90 = MediaTransformRequest(ops=[RotateOp(type="rotate", degrees=90)])

# ---------------------------------------------------------------------------
# Import endpoint functions after fixture defs (avoids circular import issues)
# ---------------------------------------------------------------------------

from app.api.me import delete_signature, get_signature, upload_signature  # noqa: E402
from app.api.media import transform_media  # noqa: E402

# ---------------------------------------------------------------------------
# Test 1 — 404 MEDIA_NOT_FOUND
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_transform_404_media_not_found():
    user = _make_user()
    db = AsyncMock()
    not_found_result = MagicMock()
    not_found_result.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=not_found_result)

    with pytest.raises(ApiError) as exc_info:
        await transform_media(uuid.uuid4(), _ROTATE_90, user, db, _rl=None)

    err = exc_info.value
    assert err.code == "MEDIA_NOT_FOUND"
    assert err.status_code == 404


# ---------------------------------------------------------------------------
# Test 2 — 403 MEDIA_NOT_OWNER
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_transform_403_not_owner():
    user = _make_user()
    other_user_id = uuid.uuid4()  # different from user.id
    post = _make_post(author_id=other_user_id)
    media = _make_media(post_id=post.id)
    db = _make_db_mock(media, post)

    with pytest.raises(ApiError) as exc_info:
        await transform_media(media.id, _ROTATE_90, user, db, _rl=None)

    err = exc_info.value
    assert err.code == "MEDIA_NOT_OWNER"
    assert err.status_code == 403


# ---------------------------------------------------------------------------
# Test 3 — 409 AUCTION_ACTIVE_MEDIA_LOCKED
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_transform_409_auction_active_lock():
    user = _make_user()
    post = _make_post(author_id=user.id, type_="product")
    media = _make_media(post_id=post.id)

    active_auction = MagicMock()
    active_auction.id = uuid.uuid4()
    active_auction.status = "active"

    db = _make_db_mock(media, post, active_auction=active_auction)

    with pytest.raises(ApiError) as exc_info:
        await transform_media(media.id, _ROTATE_90, user, db, _rl=None)

    err = exc_info.value
    assert err.code == "AUCTION_ACTIVE_MEDIA_LOCKED"
    assert err.status_code == 409


# ---------------------------------------------------------------------------
# Test 4 — 415 MEDIA_TRANSFORM_UNSUPPORTED_TYPE (video AND gif)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_transform_415_video_or_gif():
    user = _make_user()

    # Sub-case A: video type
    post_v = _make_post(author_id=user.id)
    media_v = _make_media(post_id=post_v.id, type_="video", storage_key="uploads/vid.mp4")
    db_v = _make_db_mock(media_v, post_v)

    with pytest.raises(ApiError) as exc_info:
        await transform_media(media_v.id, _ROTATE_90, user, db_v, _rl=None)
    assert exc_info.value.code == "MEDIA_TRANSFORM_UNSUPPORTED_TYPE"
    assert exc_info.value.status_code == 415

    # Sub-case B: image type but .gif extension
    post_g = _make_post(author_id=user.id)
    media_g = _make_media(post_id=post_g.id, type_="image", storage_key="uploads/anim.gif")
    db_g = _make_db_mock(media_g, post_g)

    with pytest.raises(ApiError) as exc_info:
        await transform_media(media_g.id, _ROTATE_90, user, db_g, _rl=None)
    assert exc_info.value.code == "MEDIA_TRANSFORM_UNSUPPORTED_TYPE"
    assert exc_info.value.status_code == 415


# ---------------------------------------------------------------------------
# Test 5 — 413 MEDIA_TRANSFORM_TOO_LARGE (DB-recorded size_bytes > 20MB)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_transform_413_too_large():
    user = _make_user()
    post = _make_post(author_id=user.id)
    media = _make_media(post_id=post.id, size_bytes=21 * 1024 * 1024)
    db = _make_db_mock(media, post)

    with pytest.raises(ApiError) as exc_info:
        await transform_media(media.id, _ROTATE_90, user, db, _rl=None)

    err = exc_info.value
    assert err.code == "MEDIA_TRANSFORM_TOO_LARGE"
    assert err.status_code == 413


# ---------------------------------------------------------------------------
# Test 6 — 200: first call seeds original_storage_key; second call reuses it
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_transform_200_first_call_seeds_original_storage_key():
    user = _make_user()
    post = _make_post(author_id=user.id)
    initial_key = "uploads/original/img.jpg"
    media = _make_media(post_id=post.id, storage_key=initial_key, original_storage_key=None)

    db = _make_db_mock(media, post)
    provider = _make_provider_mock(_make_jpeg_bytes())

    with patch("app.api.media.get_storage_provider", return_value=provider):
        result = await transform_media(media.id, _ROTATE_90, user, db, _rl=None)

    # original_storage_key must be seeded from initial storage_key on first call
    assert media.original_storage_key == initial_key

    # Response envelope must have 'data' key
    assert "data" in result

    # provider.get called with the original key
    provider.get.assert_awaited_once_with(initial_key)

    # Second call simulation: original_storage_key already set; storage_key updated
    second_key = "transformed/new/result.jpg"
    media.storage_key = second_key  # simulate DB update from first transform
    # original_storage_key remains initial_key (already set above)

    db2 = _make_db_mock(media, post)
    provider2 = _make_provider_mock(_make_jpeg_bytes())

    with patch("app.api.media.get_storage_provider", return_value=provider2):
        await transform_media(media.id, _ROTATE_90, user, db2, _rl=None)

    # Second call must use original_storage_key, NOT the updated storage_key
    provider2.get.assert_awaited_once_with(initial_key)


# ---------------------------------------------------------------------------
# Test 7 — 400 WATERMARK_SIGNATURE_NOT_SET
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_transform_400_signature_missing():
    user = _make_user(signature_storage_key=None)
    post = _make_post(author_id=user.id)
    media = _make_media(post_id=post.id)
    db = _make_db_mock(media, post)

    # provider.get returns valid image bytes so the image-load step passes;
    # the WATERMARK_SIGNATURE_NOT_SET check fires after that.
    provider = _make_provider_mock(_make_jpeg_bytes())

    body = MediaTransformRequest(
        ops=[
            WatermarkOp(
                type="watermark",
                source="signature",
                text=None,
                position=WatermarkPosition(x=10, y=10),
                opacity=0.7,
            )
        ]
    )

    with patch("app.api.media.get_storage_provider", return_value=provider):
        with pytest.raises(ApiError) as exc_info:
            await transform_media(media.id, body, user, db, _rl=None)

    err = exc_info.value
    assert err.code == "WATERMARK_SIGNATURE_NOT_SET"
    assert err.status_code == 400


# ---------------------------------------------------------------------------
# Test 8 — POST /v1/me/signature 415 SIGNATURE_UNSUPPORTED_TYPE (image/jpeg)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_signature_upload_415_unsupported_mime():
    user = _make_user()
    db = AsyncMock()
    db.commit = AsyncMock()

    bad_file = MagicMock()
    bad_file.content_type = "image/jpeg"  # JPEG not in SIGNATURE_ALLOWED_MIME
    bad_file.read = AsyncMock(return_value=b"\xff\xd8\xff" + b"\x00" * 100)

    with pytest.raises(ApiError) as exc_info:
        await upload_signature(file=bad_file, user=user, db=db, _rl=None)

    err = exc_info.value
    assert err.code == "SIGNATURE_UNSUPPORTED_TYPE"
    assert err.status_code == 415


# ---------------------------------------------------------------------------
# Test 9 — GET /v1/me/signature returns {"data": {"signature_url": null}}
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_signature_get_returns_null_when_unset():
    user = _make_user(signature_storage_key=None)

    result = await get_signature(user=user)

    assert result == {"data": {"signature_url": None}}


# ---------------------------------------------------------------------------
# Test 10 — DELETE /v1/me/signature is idempotent (204 with and without sig)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_signature_delete_idempotent():
    # Case A: no signature — 204 without DB commit
    user_no_sig = _make_user(signature_storage_key=None)
    db_a = AsyncMock()
    db_a.commit = AsyncMock()

    resp_a = await delete_signature(user=user_no_sig, db=db_a)
    assert resp_a.status_code == 204
    db_a.commit.assert_not_awaited()

    # Case B: has signature — 204, key cleared, provider.delete called
    prev_key = "signatures/abc/sig.png"
    user_with_sig = _make_user(signature_storage_key=prev_key)
    db_b = AsyncMock()
    db_b.commit = AsyncMock()

    provider = MagicMock()
    provider.delete = AsyncMock()

    # get_storage_provider is imported inside the function body in me.py:
    #   from app.services.storage import get_storage_provider
    # so the effective patch target is the module-level symbol.
    with patch("app.services.storage.get_storage_provider", return_value=provider):
        resp_b = await delete_signature(user=user_with_sig, db=db_b)

    assert resp_b.status_code == 204
    assert user_with_sig.signature_storage_key is None
    db_b.commit.assert_awaited_once()
    provider.delete.assert_awaited_once_with(prev_key)
