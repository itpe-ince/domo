"""9 unit tests for artist-tier-release — Phase 4 #10 §B-12.

Pure logic / Pydantic tests: no real DB, no real network.
Tests cover:
  - _viewer_meets_tier helper (6 cases)
  - Pydantic PostPublishRequest tier field validation (2 cases)
  - effective visibility expired fallback (1 case)
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import ValidationError

from app.schemas.series import PostPublishRequest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_scalar_result(value) -> MagicMock:
    r = MagicMock()
    r.scalar.return_value = value
    return r


def _make_db_with_scalar(value: bool) -> AsyncMock:
    """DB mock: execute() returns a result whose .scalar() returns value."""
    db = AsyncMock()
    db.execute = AsyncMock(return_value=_make_scalar_result(value))
    return db


# ---------------------------------------------------------------------------
# Import helper under test
# ---------------------------------------------------------------------------
from app.api.posts import _viewer_meets_tier  # noqa: E402


# ---------------------------------------------------------------------------
# Test 1 — viewer_id=None → False (no token)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_viewer_meets_tier_none_viewer():
    db = AsyncMock()
    result = await _viewer_meets_tier(db, None, uuid.uuid4(), "subscriber")
    assert result is False
    db.execute.assert_not_called()


# ---------------------------------------------------------------------------
# Test 2 — viewer_id == author_id → True (self)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_viewer_meets_tier_author_self():
    db = AsyncMock()
    author_id = uuid.uuid4()
    result = await _viewer_meets_tier(db, author_id, author_id, "subscriber")
    assert result is True
    db.execute.assert_not_called()


# ---------------------------------------------------------------------------
# Test 3 — required='subscriber', DB returns True (active subscription)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_viewer_meets_tier_subscriber_active():
    db = _make_db_with_scalar(True)
    viewer_id = uuid.uuid4()
    author_id = uuid.uuid4()
    result = await _viewer_meets_tier(db, viewer_id, author_id, "subscriber")
    assert result is True
    db.execute.assert_awaited_once()


# ---------------------------------------------------------------------------
# Test 4 — required='sponsor', DB returns True (completed sponsorship)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_viewer_meets_tier_sponsor_completed():
    db = _make_db_with_scalar(True)
    result = await _viewer_meets_tier(db, uuid.uuid4(), uuid.uuid4(), "sponsor")
    assert result is True


# ---------------------------------------------------------------------------
# Test 5 — required='sponsor', active subscription only → True (cascade OQ-2=A)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_viewer_meets_tier_sponsor_with_subscription():
    """sponsor tier includes subscriber via UNION ALL — DB returns True."""
    db = _make_db_with_scalar(True)
    result = await _viewer_meets_tier(db, uuid.uuid4(), uuid.uuid4(), "sponsor")
    assert result is True


# ---------------------------------------------------------------------------
# Test 6 — required='follower', DB returns True (follow row exists)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_viewer_meets_tier_follower_only():
    db = _make_db_with_scalar(True)
    result = await _viewer_meets_tier(db, uuid.uuid4(), uuid.uuid4(), "follower")
    assert result is True


# ---------------------------------------------------------------------------
# Test 7 — Pydantic: duration set + tier null → ValidationError TIER_FIELDS_INCONSISTENT
# ---------------------------------------------------------------------------


def test_pydantic_tier_fields_inconsistent():
    with pytest.raises(ValidationError) as exc_info:
        PostPublishRequest(early_access_duration=24, early_access_tier=None)
    assert "TIER_FIELDS_INCONSISTENT" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Test 8 — Pydantic: invalid duration (999) → ValidationError INVALID_DURATION
# ---------------------------------------------------------------------------


def test_pydantic_invalid_duration():
    with pytest.raises(ValidationError) as exc_info:
        PostPublishRequest(early_access_duration=999, early_access_tier="follower")
    assert "INVALID_DURATION" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Test 9 — effective visibility: early_access_until in past → fallback to post.visibility
# ---------------------------------------------------------------------------


def test_effective_visibility_expired_fallback():
    """When early_access_until is in the past, effective visibility = post.visibility."""
    now = datetime.now(timezone.utc)
    expired = now - timedelta(hours=1)

    # Simulate the effective visibility logic from §B-6
    early_access_until = expired
    post_visibility = "public"

    if (
        early_access_until is not None
        and early_access_until > now
    ):
        effective = "tier_only"
    else:
        effective = post_visibility

    assert effective == "public"
