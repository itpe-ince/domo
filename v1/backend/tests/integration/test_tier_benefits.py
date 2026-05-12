"""Integration tests for tier benefits API — B-4 tier-benefits-customization.

Endpoints under test:
  GET    /v1/me/tier-benefits
  PUT    /v1/me/tier-benefits/{tier}
  DELETE /v1/me/tier-benefits/{tier}
  GET    /v1/users/{user_id}/tier-benefits

Strategy: direct endpoint function calls with AsyncMock DB + MagicMock User.
No real DB or Stripe required. Mirrors test_patronage_dashboard.py pattern.

Test count: 10
  1. GET /me/tier-benefits 200 artist — platform default fallback for undefined tiers
  2. GET /me/tier-benefits 403 non-artist
  3. PUT /me/tier-benefits/sponsor 200 create success
  4. PUT /me/tier-benefits/sponsor 200 update success (existing row)
  5. PUT /me/tier-benefits/invalid 422 invalid tier
  6. PUT /me/tier-benefits/sponsor 422 too many benefits (> 10)
  7. DELETE /me/tier-benefits/sponsor 204 success
  8. DELETE /me/tier-benefits/sponsor 204 idempotent (non-existent row)
  9. GET /users/{id}/tier-benefits 200 public — artist with overrides
  10. GET /users/{id}/tier-benefits 404 non-artist user
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.api.tier_benefits import (
    delete_my_tier_benefits,
    get_my_tier_benefits,
    get_user_tier_benefits,
    upsert_my_tier_benefits,
)
from app.core.errors import ApiError
from app.schemas.tier_benefits import TierBenefitsUpsert


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _make_artist() -> MagicMock:
    u = MagicMock()
    u.id = uuid.uuid4()
    u.role = "artist"
    u.display_name = "test_artist"
    return u


def _make_user() -> MagicMock:
    u = MagicMock()
    u.id = uuid.uuid4()
    u.role = "user"
    u.display_name = "regular_user"
    return u


def _make_benefits_row(
    artist_id: uuid.UUID, tier: str, benefits: list[str], welcome_message: str | None = None
) -> MagicMock:
    row = MagicMock()
    row.id = uuid.uuid4()
    row.artist_id = artist_id
    row.tier = tier
    row.benefits = benefits
    row.welcome_message = welcome_message
    row.created_at = datetime.now(timezone.utc)
    row.updated_at = datetime.now(timezone.utc)
    return row


def _make_db_empty() -> AsyncMock:
    """DB that returns no rows from all queries."""
    db = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = []
    result_mock.scalar_one_or_none.return_value = None
    db.execute.return_value = result_mock
    return db


def _make_db_with_rows(rows: list) -> AsyncMock:
    """DB that returns given rows from scalars().all()."""
    db = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = rows
    result_mock.scalar_one_or_none.return_value = rows[0] if rows else None
    db.execute.return_value = result_mock
    return db


# ─── Tests ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_my_tier_benefits_artist_platform_defaults():
    """GET /me/tier-benefits — artist with no overrides returns platform defaults."""
    artist = _make_artist()
    db = _make_db_empty()

    result = await get_my_tier_benefits(user=artist, db=db, _rl=None)

    data = result["data"]
    assert data["subscriber"]["is_platform_default"] is True
    assert data["sponsor"]["is_platform_default"] is True
    assert data["follower"]["is_platform_default"] is True
    assert "patronage.supporter.tier.benefits.subscriber" in (
        data["subscriber"]["platform_default_key"] or ""
    )


@pytest.mark.asyncio
async def test_get_my_tier_benefits_non_artist_403():
    """GET /me/tier-benefits — non-artist returns 403 ARTIST_ONLY."""
    user = _make_user()
    db = _make_db_empty()

    with pytest.raises(ApiError) as exc_info:
        await get_my_tier_benefits(user=user, db=db, _rl=None)

    assert exc_info.value.code == "ARTIST_ONLY"
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_upsert_my_tier_benefits_create_success():
    """PUT /me/tier-benefits/sponsor 200 — creates new row."""
    artist = _make_artist()
    db = _make_db_empty()

    body = TierBenefitsUpsert(
        benefits=["Early access to posts", "Direct message to artist"],
        welcome_message="Thank you for sponsoring!",
    )

    new_row = _make_benefits_row(
        artist.id, "sponsor", body.benefits, body.welcome_message
    )
    db.refresh = AsyncMock()

    # After commit, refresh returns the new row state
    async def mock_refresh(obj):
        obj.benefits = new_row.benefits
        obj.welcome_message = new_row.welcome_message
        obj.created_at = new_row.created_at
        obj.updated_at = new_row.updated_at

    db.refresh.side_effect = mock_refresh

    result = await upsert_my_tier_benefits(
        tier="sponsor", body=body, user=artist, db=db, _rl=None
    )

    data = result["data"]
    assert data["tier"] == "sponsor"
    assert data["is_platform_default"] is False
    assert "Early access to posts" in data["benefits"]
    assert data["welcome_message"] == "Thank you for sponsoring!"
    db.add.assert_called_once()
    db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_upsert_my_tier_benefits_update_existing():
    """PUT /me/tier-benefits/sponsor 200 — updates existing row."""
    artist = _make_artist()
    existing = _make_benefits_row(artist.id, "sponsor", ["Old benefit"])

    # DB returns existing row
    db = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = existing
    db.execute.return_value = result_mock

    async def mock_refresh(obj):
        obj.updated_at = datetime.now(timezone.utc)

    db.refresh = AsyncMock(side_effect=mock_refresh)

    body = TierBenefitsUpsert(benefits=["New benefit 1", "New benefit 2"])

    result = await upsert_my_tier_benefits(
        tier="sponsor", body=body, user=artist, db=db, _rl=None
    )

    data = result["data"]
    assert data["tier"] == "sponsor"
    assert "New benefit 1" in data["benefits"]
    # add should NOT be called for update (row already in session)
    db.add.assert_not_called()
    db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_upsert_my_tier_benefits_invalid_tier_422():
    """PUT /me/tier-benefits/invalid 422 — invalid tier name."""
    artist = _make_artist()
    db = _make_db_empty()
    body = TierBenefitsUpsert(benefits=["something"])

    with pytest.raises(ApiError) as exc_info:
        await upsert_my_tier_benefits(
            tier="vip", body=body, user=artist, db=db, _rl=None
        )

    assert exc_info.value.status_code == 422


@pytest.mark.asyncio
async def test_upsert_my_tier_benefits_too_many_benefits_422():
    """PUT /me/tier-benefits/sponsor 422 — benefits list exceeds 10 items."""
    from pydantic import ValidationError

    with pytest.raises(ValidationError) as exc_info:
        TierBenefitsUpsert(benefits=[f"Benefit {i}" for i in range(11)])

    assert "cannot exceed 10 items" in str(exc_info.value)


@pytest.mark.asyncio
async def test_delete_my_tier_benefits_success():
    """DELETE /me/tier-benefits/sponsor 204 — removes existing row."""
    artist = _make_artist()
    existing = _make_benefits_row(artist.id, "sponsor", ["Benefit"])

    db = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = existing
    db.execute.return_value = result_mock

    response = await delete_my_tier_benefits(
        tier="sponsor", user=artist, db=db, _rl=None
    )

    db.delete.assert_called_once_with(existing)
    db.commit.assert_called_once()
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_delete_my_tier_benefits_idempotent():
    """DELETE /me/tier-benefits/sponsor 204 — idempotent when row doesn't exist."""
    artist = _make_artist()
    db = _make_db_empty()

    response = await delete_my_tier_benefits(
        tier="sponsor", user=artist, db=db, _rl=None
    )

    # delete should not be called when row doesn't exist
    db.delete.assert_not_called()
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_get_user_tier_benefits_artist_with_override():
    """GET /users/{id}/tier-benefits 200 — artist with sponsor override."""
    artist = _make_artist()
    sponsor_row = _make_benefits_row(
        artist.id, "sponsor", ["Exclusive content"], "Welcome to my fanclub!"
    )

    db = AsyncMock()
    # First execute: user lookup → artist
    # Second execute: tier benefits fetch → rows
    call_count = 0

    async def execute_side_effect(stmt):
        nonlocal call_count
        call_count += 1
        result = MagicMock()
        if call_count == 1:
            # User lookup
            result.scalar_one_or_none.return_value = artist
        else:
            # Tier benefits
            result.scalars.return_value.all.return_value = [sponsor_row]
        return result

    db.execute.side_effect = execute_side_effect

    result = await get_user_tier_benefits(
        user_id=str(artist.id), db=db, _rl=None
    )

    data = result["data"]
    assert data["sponsor"]["is_platform_default"] is False
    assert "Exclusive content" in data["sponsor"]["benefits"]
    assert data["sponsor"]["welcome_message"] == "Welcome to my fanclub!"
    # subscriber and follower still platform default
    assert data["subscriber"]["is_platform_default"] is True
    assert data["follower"]["is_platform_default"] is True


@pytest.mark.asyncio
async def test_get_user_tier_benefits_non_artist_404():
    """GET /users/{id}/tier-benefits 404 — user exists but is not an artist."""
    regular_user = _make_user()

    db = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = regular_user
    db.execute.return_value = result_mock

    with pytest.raises(ApiError) as exc_info:
        await get_user_tier_benefits(
            user_id=str(regular_user.id), db=db, _rl=None
        )

    assert exc_info.value.status_code == 404
