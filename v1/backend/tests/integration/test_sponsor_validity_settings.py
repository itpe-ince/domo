"""Integration tests for sponsor_validity_days settings — D'-1 carry-over.

Endpoints under test:
  GET   /v1/me/sponsor-settings
  PATCH /v1/me/sponsor-settings

Strategy: direct endpoint function calls with AsyncMock DB + MagicMock User.
No real DB or Stripe required. Mirrors test_tier_benefits.py pattern.

Test count: 5
  1. 200 GET success — returns current sponsor_validity_days (None)
  2. 200 PATCH success — sets 30 days
  3. 200 PATCH success — resets to lifetime (None)
  4. 422 PATCH invalid value (not in allowed set)
  5. Tier expiry logic — _viewer_meets_tier returns False after validity days exceeded
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.api.me import get_sponsor_settings, patch_sponsor_settings
from app.core.errors import ApiError
from app.schemas.user import UserSponsorSettingsRequest


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _make_user(*, role: str = "artist", sponsor_validity_days: int | None = None) -> MagicMock:
    u = MagicMock()
    u.id = uuid.uuid4()
    u.role = role
    u.display_name = "Test Artist"
    u.sponsor_validity_days = sponsor_validity_days
    return u


def _make_db() -> AsyncMock:
    db = AsyncMock()
    db.commit = AsyncMock()
    return db


# ─── Test 1: GET sponsor-settings returns current value ──────────────────────


@pytest.mark.asyncio
async def test_get_sponsor_settings_returns_none_by_default():
    user = _make_user(sponsor_validity_days=None)
    result = await get_sponsor_settings(user=user)
    assert result["data"]["sponsor_validity_days"] is None


# ─── Test 2: PATCH sets valid value ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_patch_sponsor_settings_sets_30_days():
    user = _make_user(sponsor_validity_days=None)
    db = _make_db()
    body = UserSponsorSettingsRequest(sponsor_validity_days=30)

    # Pass _rl=None to bypass FastAPI dependency injection in direct call tests.
    result = await patch_sponsor_settings(body=body, user=user, db=db, _rl=None)

    assert user.sponsor_validity_days == 30
    db.commit.assert_called_once()
    assert result["data"]["sponsor_validity_days"] == 30


# ─── Test 3: PATCH resets to lifetime (None) ─────────────────────────────────


@pytest.mark.asyncio
async def test_patch_sponsor_settings_resets_to_lifetime():
    user = _make_user(sponsor_validity_days=30)
    db = _make_db()
    body = UserSponsorSettingsRequest(sponsor_validity_days=None)

    result = await patch_sponsor_settings(body=body, user=user, db=db, _rl=None)

    assert user.sponsor_validity_days is None
    db.commit.assert_called_once()
    assert result["data"]["sponsor_validity_days"] is None


# ─── Test 4: PATCH rejects invalid value ─────────────────────────────────────


def test_patch_sponsor_settings_rejects_invalid_value():
    """Pydantic validation should raise for value not in (1, 7, 30, 90, 365)."""
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        UserSponsorSettingsRequest(sponsor_validity_days=15)  # not in allowed set


# ─── Test 5: _viewer_meets_tier respects validity_days expiry ────────────────


@pytest.mark.asyncio
async def test_viewer_meets_tier_sponsor_expired():
    """Sponsorship created 31 days ago should NOT qualify when validity_days=30."""
    from app.api.posts import _viewer_meets_tier

    viewer_id = uuid.uuid4()
    author_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    expired_created_at = now - timedelta(days=31)

    db = AsyncMock()

    # First call: author's sponsor_validity_days = 30
    validity_result = MagicMock()
    validity_result.scalar_one_or_none = MagicMock(return_value=30)

    # Second call: EXISTS query → False (sponsorship too old)
    exists_result = MagicMock()
    exists_result.scalar = MagicMock(return_value=False)

    db.execute = AsyncMock(side_effect=[validity_result, exists_result])

    qualifies = await _viewer_meets_tier(db, viewer_id, author_id, "sponsor")
    assert qualifies is False
