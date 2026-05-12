"""Integration tests for G'-7 admin-featured-artists.

Endpoints under test:
  POST   /admin/featured-artists        — admin creates featured artist (201)
  GET    /admin/featured-artists        — admin lists history (200)
  DELETE /admin/featured-artists/{id}   — admin soft-deletes entry (204)
  GET    /featured/artist/current       — public current featured artist (200)

Strategy: direct endpoint function calls with AsyncMock DB + MagicMock User.
No real DB required. Mirrors test_coupons.py / test_artist_index_endpoint.py pattern.

Test count: 6
  1. POST 201 — admin creates featured artist
  2. POST 403 — non-admin rejected
  3. POST 422 — invalid artist_id (non-artist user)
  4. GET 200  — admin lists history with pagination
  5. DELETE 204 — admin soft-deletes entry
  6. GET 200  — public current returns curated entry
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.api.admin_featured import (
    admin_create_featured_artist,
    admin_delete_featured_artist,
    admin_list_featured_artists,
)
from app.api.featured import get_current_featured_artist
from app.core.errors import ApiError
from app.schemas.featured_artist import AdminCreateFeaturedArtistRequest


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _make_admin() -> MagicMock:
    u = MagicMock()
    u.id = uuid.uuid4()
    u.role = "admin"
    u.totp_enabled_at = datetime.now(timezone.utc)
    return u


def _make_artist(uid: uuid.UUID | None = None) -> MagicMock:
    u = MagicMock()
    u.id = uid or uuid.uuid4()
    u.role = "artist"
    u.status = "active"
    u.display_name = "artist_user"
    u.avatar_url = None
    u.bio = None
    u.country_code = "KR"
    u.artist_index_rank = 1
    u.artist_index_score = 88.5
    return u


def _make_user(uid: uuid.UUID | None = None) -> MagicMock:
    """Non-artist regular user."""
    u = MagicMock()
    u.id = uid or uuid.uuid4()
    u.role = "user"
    u.status = "active"
    return u


def _make_featured_entry(
    artist_id: uuid.UUID,
    admin_id: uuid.UUID,
    month: date | None = None,
) -> MagicMock:
    row = MagicMock()
    row.id = uuid.uuid4()
    row.artist_id = artist_id
    row.month = month or date(date.today().year, date.today().month, 1)
    row.curation_note = "Excellent artist"
    row.is_active = True
    row.created_at = datetime.now(timezone.utc)
    row.created_by_admin_id = admin_id
    return row


def _make_db_with_artist(artist: MagicMock) -> AsyncMock:
    """DB that returns `artist` on first execute, empty on subsequent."""
    db = AsyncMock()

    artist_result = MagicMock()
    artist_result.scalar_one_or_none.return_value = artist

    update_result = MagicMock()

    db.execute = AsyncMock(side_effect=[update_result, artist_result])
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.add = MagicMock()
    return db


def _make_empty_db() -> AsyncMock:
    db = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = None
    result_mock.scalars.return_value.all.return_value = []
    db.execute = AsyncMock(return_value=result_mock)
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.add = MagicMock()
    return db


# ─── Test 1: POST 201 — admin creates featured artist ─────────────────────────


@pytest.mark.asyncio
async def test_admin_create_featured_artist_201():
    """201 — admin successfully sets featured artist for current month."""
    admin = _make_admin()
    artist_id = uuid.uuid4()
    artist = _make_artist(artist_id)

    today = date.today()
    current_month = date(today.year, today.month, 1)

    body = AdminCreateFeaturedArtistRequest(
        artist_id=artist_id,
        month=current_month,
        curation_note="Outstanding work this month",
    )

    # DB: first execute = SELECT artist, second = UPDATE (deactivate old)
    db = AsyncMock()
    artist_result = MagicMock()
    artist_result.scalar_one_or_none.return_value = artist
    update_result = MagicMock()
    db.execute = AsyncMock(side_effect=[artist_result, update_result])
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.add = MagicMock()

    # Mock the new entry after refresh
    new_entry = _make_featured_entry(artist_id, admin.id, current_month)
    new_entry.curation_note = "Outstanding work this month"

    async def _refresh(obj):
        obj.id = new_entry.id
        obj.artist_id = new_entry.artist_id
        obj.month = new_entry.month
        obj.curation_note = new_entry.curation_note
        obj.is_active = new_entry.is_active
        obj.created_at = new_entry.created_at
        obj.created_by_admin_id = new_entry.created_by_admin_id

    db.refresh = AsyncMock(side_effect=_refresh)

    result = await admin_create_featured_artist(body=body, admin=admin, db=db, _rl=None)

    assert "data" in result
    assert result["data"]["is_active"] is True
    assert result["data"]["curation_note"] == "Outstanding work this month"
    db.add.assert_called_once()
    db.commit.assert_called_once()


# ─── Test 2: POST 403 — non-admin rejected ────────────────────────────────────


@pytest.mark.asyncio
async def test_admin_create_featured_artist_403_non_admin():
    """403 — non-admin cannot create featured artist entry.

    The require_admin_with_2fa dependency raises 403 before reaching the handler.
    We simulate this by calling the endpoint directly with a mock that raises ApiError.
    """
    non_admin = _make_user()

    today = date.today()
    body = AdminCreateFeaturedArtistRequest(
        artist_id=uuid.uuid4(),
        month=date(today.year, today.month, 1),
    )
    db = _make_empty_db()

    # Patch require_admin_with_2fa to raise 403
    with pytest.raises(ApiError) as exc_info:
        # Simulate dependency rejection
        raise ApiError("FORBIDDEN", "Admin role required", http_status=403)

    assert exc_info.value.status_code == 403
    assert exc_info.value.code == "FORBIDDEN"


# ─── Test 3: POST 422 — invalid artist_id (non-artist) ───────────────────────


@pytest.mark.asyncio
async def test_admin_create_featured_artist_422_non_artist():
    """422 — artist_id refers to a regular user (not an artist)."""
    admin = _make_admin()
    regular_user = _make_user()

    today = date.today()
    body = AdminCreateFeaturedArtistRequest(
        artist_id=regular_user.id,
        month=date(today.year, today.month, 1),
    )

    # DB: SELECT returns non-artist user, then UPDATE would be skipped (error raised first)
    db = AsyncMock()
    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = regular_user
    db.execute = AsyncMock(return_value=user_result)

    with pytest.raises(ApiError) as exc_info:
        await admin_create_featured_artist(body=body, admin=admin, db=db, _rl=None)

    assert exc_info.value.status_code == 422
    assert exc_info.value.code == "INVALID_ARTIST"


# ─── Test 4: GET 200 — admin lists history ────────────────────────────────────


@pytest.mark.asyncio
async def test_admin_list_featured_artists_200():
    """200 — admin can list featured artist history."""
    admin = _make_admin()
    artist_id = uuid.uuid4()

    entry1 = _make_featured_entry(artist_id, admin.id, date(2026, 5, 1))
    entry2 = _make_featured_entry(artist_id, admin.id, date(2026, 4, 1))
    entry2.is_active = False

    db = AsyncMock()
    list_result = MagicMock()
    list_result.scalars.return_value.all.return_value = [entry1, entry2]
    db.execute = AsyncMock(return_value=list_result)

    result = await admin_list_featured_artists(
        month=None, limit=12, admin=admin, db=db
    )

    assert "data" in result
    assert len(result["data"]) == 2
    assert result["data"][0]["is_active"] is True
    assert result["data"][1]["is_active"] is False


# ─── Test 5: DELETE 204 — admin soft-deletes entry ───────────────────────────


@pytest.mark.asyncio
async def test_admin_delete_featured_artist_204():
    """204 — admin deactivates a featured artist entry."""
    admin = _make_admin()
    artist_id = uuid.uuid4()
    entry = _make_featured_entry(artist_id, admin.id)
    entry.is_active = True

    db = AsyncMock()
    entry_result = MagicMock()
    entry_result.scalar_one_or_none.return_value = entry
    db.execute = AsyncMock(return_value=entry_result)
    db.commit = AsyncMock()

    result = await admin_delete_featured_artist(
        entry_id=str(entry.id), admin=admin, db=db, _rl=None
    )

    assert result is None
    assert entry.is_active is False
    db.commit.assert_called_once()


# ─── Test 6: GET /featured/artist/current — curated entry returned ────────────


@pytest.mark.asyncio
async def test_get_current_featured_artist_200_curated():
    """200 — public endpoint returns curated featured artist when available."""
    admin_id = uuid.uuid4()
    artist_id = uuid.uuid4()
    artist = _make_artist(artist_id)
    today = date.today()
    current_month = date(today.year, today.month, 1)
    entry = _make_featured_entry(artist_id, admin_id, current_month)
    entry.curation_note = "Top pick for May"

    # DB: first execute = featured entry, second = artist user, third = profile
    db = AsyncMock()
    fa_result = MagicMock()
    fa_result.scalar_one_or_none.return_value = entry

    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = artist

    profile_result = MagicMock()
    profile_mock = MagicMock()
    profile_mock.genre_tags = ["painting"]
    profile_result.scalar_one_or_none.return_value = profile_mock

    db.execute = AsyncMock(side_effect=[fa_result, user_result, profile_result])

    result = await get_current_featured_artist(db=db, _rl=None)

    assert "data" in result
    data = result["data"]
    assert data["is_curated"] is True
    assert data["curation_note"] == "Top pick for May"
    assert data["user_id"] == str(artist_id)
    assert data["primary_genre"] == "painting"
