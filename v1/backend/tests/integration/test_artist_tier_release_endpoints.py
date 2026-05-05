"""Integration-style endpoint tests for artist-tier-release — Phase 4 #10 §B-12.

Strategy: direct endpoint function calls with MagicMock stand-ins for SQLAlchemy
model instances, AsyncMock for DB session. No real DB, no real network.
Mirrors test_publish_controls_endpoints.py pattern.

8 test cases:
  publish_post tier integration (3):
    - 200 publish with tier (duration=24, tier='sponsor') → early_access_until ≈ now+24h
    - 200 publish without tier → early_access columns NULL
    - 422 inconsistent tier fields (duration set, tier null)
  get_post tier visibility (4):
    - 200 as author viewing own active tier_only → is_tier_locked=False
    - 200 as qualifying viewer → is_tier_locked=False
    - 403 POST_TIER_RESTRICTED as non-qualifying viewer
    - 200 expired tier fallback → original visibility returned
  subscription cancellation real-time check (1):
    - 403 after subscription cancelled (OQ-4=B real-time check)
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from app.core.errors import ApiError
from app.schemas.series import PostPublishRequest


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def _make_user(*, user_id: uuid.UUID | None = None, role: str = "artist") -> MagicMock:
    u = MagicMock()
    u.id = user_id or uuid.uuid4()
    u.email = "test@example.com"
    u.role = role
    u.display_name = "Test Artist"
    u.avatar_url = None
    return u


def _make_post(
    *,
    post_id: uuid.UUID | None = None,
    author_id: uuid.UUID | None = None,
    status: str = "draft",
    visibility: str = "public",
    early_access_until: datetime | None = None,
    early_access_tier: str | None = None,
) -> MagicMock:
    p = MagicMock(spec=[])  # spec=[] prevents auto-attribute creation
    p.id = post_id or uuid.uuid4()
    p.author_id = author_id or uuid.uuid4()
    p.status = status
    p.type = "general"
    p.visibility = visibility
    p.comments_enabled = True
    p.scheduled_at = None
    p.updated_at = datetime.now(timezone.utc)
    p.early_access_until = early_access_until
    p.early_access_tier = early_access_tier
    p.media = []
    p.product = None
    # Required PostOut fields (None where optional)
    p.title = None
    p.content = None
    p.genre = None
    p.tags = None
    p.language = "ko"
    p.like_count = 0
    p.comment_count = 0
    p.view_count = 0
    p.bluebird_count = 0
    p.digital_art_check = "not_required"
    p.location_name = None
    p.location_lat = None
    p.location_lng = None
    p.created_at = datetime.now(timezone.utc)
    p.author = None
    return p


def _make_db_for_load_post(post: MagicMock | None) -> AsyncMock:
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
from app.api.posts import get_post, publish_post  # noqa: E402


# ---------------------------------------------------------------------------
# Test 1 — publish with tier: duration=24, tier='sponsor' → 200 + early_access_until set
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_publish_with_tier_immediate():
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

    before = datetime.now(timezone.utc)
    body = PostPublishRequest(
        early_access_duration=24,
        early_access_tier="sponsor",
    )

    result = await publish_post(post.id, body, user, db, _rl=None)

    assert "data" in result
    # post.early_access_until should be set (mocked attribute assigned)
    # verify the attribute was written to the mock
    assert post.early_access_until is not None
    assert post.early_access_tier == "sponsor"
    # early_access_until should be approximately now + 24h
    delta = post.early_access_until - before
    assert timedelta(hours=23, minutes=58) < delta < timedelta(hours=24, minutes=2)
    db.commit.assert_awaited_once()


# ---------------------------------------------------------------------------
# Test 2 — publish without tier → early_access columns cleared to None
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_publish_without_tier():
    user = _make_user()
    # post with pre-existing tier values (should be cleared)
    post = _make_post(
        author_id=user.id,
        status="draft",
        early_access_until=datetime.now(timezone.utc) + timedelta(hours=10),
        early_access_tier="follower",
    )
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

    body = PostPublishRequest()  # no early_access fields

    result = await publish_post(post.id, body, user, db, _rl=None)

    assert "data" in result
    assert post.early_access_until is None
    assert post.early_access_tier is None


# ---------------------------------------------------------------------------
# Test 3 — inconsistent tier fields → 422 ValidationError (Pydantic, not endpoint)
# ---------------------------------------------------------------------------


def test_publish_inconsistent_422():
    with pytest.raises(ValidationError) as exc_info:
        PostPublishRequest(early_access_duration=24, early_access_tier=None)
    assert "TIER_FIELDS_INCONSISTENT" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Test 4 — get_post as author of active tier_only → 200, is_tier_locked=False
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_post_active_tier_as_author():
    author = _make_user()
    active_until = datetime.now(timezone.utc) + timedelta(hours=10)
    post = _make_post(
        author_id=author.id,
        status="published",
        visibility="public",
        early_access_until=active_until,
        early_access_tier="follower",
    )

    db = AsyncMock()
    post_result = MagicMock()
    post_result.scalar_one_or_none.return_value = post
    # _author_for query
    author_result = MagicMock()
    author_result.scalar_one_or_none.return_value = author
    db.execute = AsyncMock(side_effect=[post_result, author_result])

    # Build a JWT-like authorization for the author
    token = f"Bearer fake-token-{author.id}"

    with patch("app.api.posts._optional_viewer_id", new=AsyncMock(return_value=(author.id, "artist"))):
        result = await get_post(post.id, authorization=token, db=db)

    assert "data" in result
    assert result["data"]["is_tier_locked"] is False


# ---------------------------------------------------------------------------
# Test 5 — get_post as qualifying viewer → 200, is_tier_locked=False
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_post_active_tier_qualifying_viewer():
    author_id = uuid.uuid4()
    viewer_id = uuid.uuid4()
    active_until = datetime.now(timezone.utc) + timedelta(hours=5)
    post = _make_post(
        author_id=author_id,
        status="published",
        visibility="public",
        early_access_until=active_until,
        early_access_tier="subscriber",
    )

    db = AsyncMock()
    post_result = MagicMock()
    post_result.scalar_one_or_none.return_value = post
    # _viewer_meets_tier EXISTS query
    tier_result = MagicMock()
    tier_result.scalar.return_value = True
    # _author_for query
    author_user = _make_user(user_id=author_id)
    author_result = MagicMock()
    author_result.scalar_one_or_none.return_value = author_user
    db.execute = AsyncMock(side_effect=[post_result, tier_result, author_result])

    with patch("app.api.posts._optional_viewer_id", new=AsyncMock(return_value=(viewer_id, "user"))):
        result = await get_post(post.id, authorization="Bearer token", db=db)

    assert "data" in result
    assert result["data"]["is_tier_locked"] is False


# ---------------------------------------------------------------------------
# Test 6 — get_post as non-qualifying viewer → 403 POST_TIER_RESTRICTED
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_post_active_tier_non_qualifying_viewer():
    author_id = uuid.uuid4()
    viewer_id = uuid.uuid4()
    active_until = datetime.now(timezone.utc) + timedelta(hours=5)
    post = _make_post(
        author_id=author_id,
        status="published",
        visibility="public",
        early_access_until=active_until,
        early_access_tier="sponsor",
    )

    db = AsyncMock()
    post_result = MagicMock()
    post_result.scalar_one_or_none.return_value = post
    # D'-1: sponsor_validity_days fetch → None (lifetime)
    validity_result = MagicMock()
    validity_result.scalar_one_or_none.return_value = None
    # _viewer_meets_tier EXISTS query → False
    tier_result = MagicMock()
    tier_result.scalar.return_value = False
    db.execute = AsyncMock(side_effect=[post_result, validity_result, tier_result])

    with patch("app.api.posts._optional_viewer_id", new=AsyncMock(return_value=(viewer_id, "user"))):
        with pytest.raises(ApiError) as exc_info:
            await get_post(post.id, authorization="Bearer token", db=db)

    err = exc_info.value
    assert err.code == "POST_TIER_RESTRICTED"
    assert err.status_code == 403


# ---------------------------------------------------------------------------
# Test 7 — get_post expired tier → 200 with original visibility (fallback)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_post_expired_tier_fallback():
    author_id = uuid.uuid4()
    viewer_id = uuid.uuid4()
    expired_until = datetime.now(timezone.utc) - timedelta(hours=1)
    post = _make_post(
        author_id=author_id,
        status="published",
        visibility="public",
        early_access_until=expired_until,
        early_access_tier="follower",
    )

    db = AsyncMock()
    post_result = MagicMock()
    post_result.scalar_one_or_none.return_value = post
    author_user = _make_user(user_id=author_id)
    author_result = MagicMock()
    author_result.scalar_one_or_none.return_value = author_user
    db.execute = AsyncMock(side_effect=[post_result, author_result])

    with patch("app.api.posts._optional_viewer_id", new=AsyncMock(return_value=(viewer_id, "user"))):
        result = await get_post(post.id, authorization="Bearer token", db=db)

    assert "data" in result
    # No 403, tier check skipped because expired
    assert result["data"]["is_tier_locked"] is False


# ---------------------------------------------------------------------------
# Test 8 — subscription cancelled → 403 (real-time OQ-4=B)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_subscription_cancelled_immediate_block():
    """After subscription is cancelled, viewer loses access immediately (OQ-4=B)."""
    author_id = uuid.uuid4()
    viewer_id = uuid.uuid4()
    active_until = datetime.now(timezone.utc) + timedelta(hours=10)
    post = _make_post(
        author_id=author_id,
        status="published",
        visibility="public",
        early_access_until=active_until,
        early_access_tier="subscriber",
    )

    db = AsyncMock()
    post_result = MagicMock()
    post_result.scalar_one_or_none.return_value = post
    # subscription check returns False (cancelled)
    tier_result = MagicMock()
    tier_result.scalar.return_value = False
    db.execute = AsyncMock(side_effect=[post_result, tier_result])

    with patch("app.api.posts._optional_viewer_id", new=AsyncMock(return_value=(viewer_id, "user"))):
        with pytest.raises(ApiError) as exc_info:
            await get_post(post.id, authorization="Bearer token", db=db)

    err = exc_info.value
    assert err.code == "POST_TIER_RESTRICTED"
    assert err.status_code == 403
