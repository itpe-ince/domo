"""Integration-style endpoint tests for publish-controls PDCA #8 — Backend Step 2.

Strategy: direct endpoint function calls with MagicMock stand-ins for SQLAlchemy
model instances, AsyncMock for DB session. No real DB, no real network.

Design ref: §B-7 (publish endpoint), §B-8 (Series CRUD), §B-11 (error codes),
            §B-13 (test strategy).

12 test cases:
  publish_post (7):
    - 404 POST_NOT_FOUND
    - 403 POST_NOT_OWNER
    - 409 POST_INVALID_STATE (already published)
    - 409 AUCTION_ACTIVE_VISIBILITY_LOCKED (product + active auction + vis change)
    - 200 immediate (draft → pending_review or published)
    - 200 scheduled (publish_at set → scheduled)
    - 200 with series (series_ids → memberships replaced)
  Series CRUD (5):
    - 201 create_series
    - 404 get_series not found
    - 403 patch_series not owner
    - 204 delete_series (owner)
    - 403 update_post_series cross-ownership
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.errors import ApiError
from app.schemas.series import PostPublishRequest, PostSeriesUpdateIn, SeriesCreate, SeriesPatch

# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def _make_user(
    *,
    user_id: uuid.UUID | None = None,
    role: str = "artist",
) -> MagicMock:
    u = MagicMock()
    u.id = user_id or uuid.uuid4()
    u.email = "test@example.com"
    u.role = role
    u.display_name = "Test Artist"
    return u


def _make_post(
    *,
    post_id: uuid.UUID | None = None,
    author_id: uuid.UUID | None = None,
    status: str = "draft",
    type_: str = "general",
    has_media: bool = False,
    visibility: str = "public",
    comments_enabled: bool = True,
) -> MagicMock:
    p = MagicMock()
    p.id = post_id or uuid.uuid4()
    p.author_id = author_id or uuid.uuid4()
    p.status = status
    p.type = type_
    p.visibility = visibility
    p.comments_enabled = comments_enabled
    p.scheduled_at = None
    p.updated_at = datetime.now(timezone.utc)
    # media list: empty or one image asset
    if has_media:
        media = MagicMock()
        media.type = "image"
        p.media = [media]
    else:
        p.media = []
    return p


def _make_series(
    *,
    series_id: uuid.UUID | None = None,
    author_id: uuid.UUID | None = None,
    title: str = "Test Series",
) -> MagicMock:
    s = MagicMock()
    s.id = series_id or uuid.uuid4()
    s.author_id = author_id or uuid.uuid4()
    s.title = title
    s.description = None
    s.cover_url = None
    s.created_at = datetime.now(timezone.utc)
    s.updated_at = datetime.now(timezone.utc)
    return s


def _make_db_for_load_post(post: MagicMock | None) -> AsyncMock:
    """DB mock returning post from _load_post_full (selectinload pattern)."""
    db = AsyncMock()
    scalar_result = MagicMock()
    scalar_result.scalar_one_or_none.return_value = post
    db.execute = AsyncMock(return_value=scalar_result)
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.flush = AsyncMock()
    db.delete = AsyncMock()
    db.add = MagicMock()
    return db


# ---------------------------------------------------------------------------
# Import endpoint functions
# ---------------------------------------------------------------------------

from app.api.posts import publish_post  # noqa: E402
from app.api.series import (  # noqa: E402
    create_series,
    delete_series,
    get_series,
    patch_series,
    update_post_series,
)

# ---------------------------------------------------------------------------
# publish_post — Test 1: 404 POST_NOT_FOUND
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_publish_404_post_not_found():
    user = _make_user()
    db = _make_db_for_load_post(post=None)
    body = PostPublishRequest()

    with pytest.raises(ApiError) as exc_info:
        await publish_post(uuid.uuid4(), body, user, db, _rl=None)

    err = exc_info.value
    assert err.code == "POST_NOT_FOUND"
    assert err.status_code == 404


# ---------------------------------------------------------------------------
# publish_post — Test 2: 403 POST_NOT_OWNER
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_publish_403_not_owner():
    user = _make_user()
    other_author = uuid.uuid4()
    post = _make_post(author_id=other_author, status="draft")
    db = _make_db_for_load_post(post)
    body = PostPublishRequest()

    with pytest.raises(ApiError) as exc_info:
        await publish_post(post.id, body, user, db, _rl=None)

    err = exc_info.value
    assert err.code == "POST_NOT_OWNER"
    assert err.status_code == 403


# ---------------------------------------------------------------------------
# publish_post — Test 3: 409 POST_INVALID_STATE (already published)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_publish_409_invalid_state():
    user = _make_user()
    post = _make_post(author_id=user.id, status="published")
    db = _make_db_for_load_post(post)
    body = PostPublishRequest()

    with pytest.raises(ApiError) as exc_info:
        await publish_post(post.id, body, user, db, _rl=None)

    err = exc_info.value
    assert err.code == "POST_INVALID_STATE"
    assert err.status_code == 409


# ---------------------------------------------------------------------------
# publish_post — Test 4: 409 AUCTION_ACTIVE_VISIBILITY_LOCKED
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_publish_409_auction_lock():
    user = _make_user()
    post = _make_post(author_id=user.id, status="draft", type_="product", visibility="public")
    db = AsyncMock()

    # _load_post_full → post
    load_result = MagicMock()
    load_result.scalar_one_or_none.return_value = post

    # _check_auction_visibility_lock → active auction
    active_auction = MagicMock()
    active_auction.status = "active"
    auction_result = MagicMock()
    auction_result.scalar_one_or_none.return_value = active_auction

    db.execute = AsyncMock(side_effect=[load_result, auction_result])
    db.commit = AsyncMock()
    db.flush = AsyncMock()
    db.delete = AsyncMock()
    db.add = MagicMock()

    # Change visibility to trigger auction lock check
    body = PostPublishRequest(visibility="followers_only")

    with pytest.raises(ApiError) as exc_info:
        await publish_post(post.id, body, user, db, _rl=None)

    err = exc_info.value
    assert err.code == "AUCTION_ACTIVE_VISIBILITY_LOCKED"
    assert err.status_code == 409


# ---------------------------------------------------------------------------
# publish_post — Test 5: 200 immediate (no media → published)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_publish_200_immediate():
    user = _make_user()
    post = _make_post(author_id=user.id, status="draft", has_media=False)
    db = AsyncMock()

    # _load_post_full → post; _replace_post_series: existing memberships → none
    load_result = MagicMock()
    load_result.scalar_one_or_none.return_value = post
    empty_memberships = MagicMock()
    empty_memberships.scalars.return_value.all.return_value = []
    db.execute = AsyncMock(side_effect=[load_result, empty_memberships])
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.flush = AsyncMock()
    db.delete = AsyncMock()
    db.add = MagicMock()

    body = PostPublishRequest(visibility="public", comments_enabled=True)

    result = await publish_post(post.id, body, user, db, _rl=None)

    assert "data" in result
    # No media → should be 'published'
    assert post.status == "published"
    assert post.scheduled_at is None
    db.commit.assert_awaited_once()


# ---------------------------------------------------------------------------
# publish_post — Test 6: 200 scheduled
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_publish_200_scheduled():
    user = _make_user()
    post = _make_post(author_id=user.id, status="draft")
    db = AsyncMock()

    load_result = MagicMock()
    load_result.scalar_one_or_none.return_value = post
    empty_memberships = MagicMock()
    empty_memberships.scalars.return_value.all.return_value = []
    db.execute = AsyncMock(side_effect=[load_result, empty_memberships])
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.flush = AsyncMock()
    db.delete = AsyncMock()
    db.add = MagicMock()

    publish_at = datetime.now(timezone.utc) + timedelta(minutes=30)
    body = PostPublishRequest(publish_at=publish_at, visibility="public")

    result = await publish_post(post.id, body, user, db, _rl=None)

    assert "data" in result
    assert post.status == "scheduled"
    assert post.scheduled_at == publish_at
    db.commit.assert_awaited_once()


# ---------------------------------------------------------------------------
# publish_post — Test 7: 200 with series_ids
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_publish_with_series():
    user = _make_user()
    post = _make_post(author_id=user.id, status="draft")
    series_id = uuid.uuid4()
    series = _make_series(series_id=series_id, author_id=user.id)

    db = AsyncMock()
    load_result = MagicMock()
    load_result.scalar_one_or_none.return_value = post

    # _replace_post_series: existing memberships
    empty_memberships = MagicMock()
    empty_memberships.scalars.return_value.all.return_value = []

    # series lookup
    series_lookup = MagicMock()
    series_lookup.scalars.return_value.all.return_value = [series]

    db.execute = AsyncMock(side_effect=[load_result, empty_memberships, series_lookup])
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.flush = AsyncMock()
    db.delete = AsyncMock()
    db.add = MagicMock()

    body = PostPublishRequest(series_ids=[series_id])

    result = await publish_post(post.id, body, user, db, _rl=None)

    assert "data" in result
    assert result["data"]["series_count"] == 1
    # db.add should have been called for the new membership
    db.add.assert_called()


# ---------------------------------------------------------------------------
# Series CRUD — Test 8: 201 create_series
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_series_create_201():
    user = _make_user()
    series = _make_series(author_id=user.id)

    db = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock(side_effect=lambda s: setattr(s, "id", series.id) or
                           setattr(s, "created_at", series.created_at) or
                           setattr(s, "updated_at", series.updated_at))
    db.add = MagicMock()

    body = SeriesCreate(title="My Series")

    result = await create_series(body, user, db, _rl=None)

    assert "data" in result
    assert result["data"]["title"] == "My Series"
    db.add.assert_called_once()
    db.commit.assert_awaited_once()


# ---------------------------------------------------------------------------
# Series CRUD — Test 9: 404 get_series not found
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_series_get_404():
    db = AsyncMock()
    not_found = MagicMock()
    not_found.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=not_found)

    with pytest.raises(ApiError) as exc_info:
        await get_series(uuid.uuid4(), db, _rl=None)

    err = exc_info.value
    assert err.code == "SERIES_NOT_FOUND"
    assert err.status_code == 404


# ---------------------------------------------------------------------------
# Series CRUD — Test 10: 403 patch_series not owner
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_series_patch_403_not_owner():
    user = _make_user()
    other_owner_id = uuid.uuid4()
    series = _make_series(author_id=other_owner_id)

    db = AsyncMock()
    found_result = MagicMock()
    found_result.scalar_one_or_none.return_value = series
    db.execute = AsyncMock(return_value=found_result)

    body = SeriesPatch(title="New Title")

    with pytest.raises(ApiError) as exc_info:
        await patch_series(series.id, body, user, db, _rl=None)

    err = exc_info.value
    assert err.code == "SERIES_NOT_OWNER"
    assert err.status_code == 403


# ---------------------------------------------------------------------------
# Series CRUD — Test 11: 204 delete_series (owner)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_series_delete_204():
    user = _make_user()
    series = _make_series(author_id=user.id)

    db = AsyncMock()
    found_result = MagicMock()
    found_result.scalar_one_or_none.return_value = series
    db.execute = AsyncMock(return_value=found_result)
    db.delete = AsyncMock()
    db.commit = AsyncMock()

    # delete_series returns None (204 no content)
    result = await delete_series(series.id, user, db, _rl=None)

    assert result is None
    db.delete.assert_awaited_once_with(series)
    db.commit.assert_awaited_once()


# ---------------------------------------------------------------------------
# Series CRUD — Test 12: 403 update_post_series cross-ownership
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_post_series_update_cross_ownership():
    user = _make_user()
    other_owner_id = uuid.uuid4()
    series_id = uuid.uuid4()
    series = _make_series(series_id=series_id, author_id=other_owner_id)
    post = _make_post(author_id=user.id)

    db = AsyncMock()
    post_result = MagicMock()
    post_result.scalar_one_or_none.return_value = post

    # existing memberships (none)
    empty_memberships = MagicMock()
    empty_memberships.scalars.return_value.all.return_value = []

    # series lookup returns series owned by other user
    series_lookup = MagicMock()
    series_lookup.scalars.return_value.all.return_value = [series]

    db.execute = AsyncMock(side_effect=[post_result, empty_memberships, series_lookup])
    db.delete = AsyncMock()
    db.commit = AsyncMock()
    db.add = MagicMock()

    body = PostSeriesUpdateIn(series_ids=[series_id])

    with pytest.raises(ApiError) as exc_info:
        await update_post_series(post.id, body, user, db, _rl=None)

    err = exc_info.value
    assert err.code == "SERIES_NOT_OWNER"
    assert err.status_code == 403
