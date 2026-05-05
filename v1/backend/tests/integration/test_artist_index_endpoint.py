"""Integration tests for artist-index-v1 endpoints (A-6).

Endpoints under test:
  GET /v1/artists/index              — global ranking list (public)
  GET /v1/artists/index?region=KR    — filtered by region
  GET /v1/artists/{user_id}/index    — individual artist ranking
  GET /v1/artists/{non_artist}/index — 404 for non-artist

Strategy: direct function calls with AsyncMock DB + MagicMock User.
Mirrors test_patronage_dashboard.py pattern. No real DB required.

Test count: 4
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.api.artists import get_artist_index, get_artist_ranking
from app.core.errors import ApiError


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _make_artist(
    *,
    uid: uuid.UUID | None = None,
    display_name: str = "test_artist",
    country_code: str | None = "KR",
    rank: int | None = 5,
    score: float | None = 72.5,
    role: str = "artist",
    status: str = "active",
) -> MagicMock:
    u = MagicMock()
    u.id = uid or uuid.uuid4()
    u.display_name = display_name
    u.avatar_url = None
    u.country_code = country_code
    u.role = role
    u.status = status
    u.deleted_at = None
    u.artist_index_score = score
    u.artist_index_rank = rank
    u.artist_index_rank_region = None
    u.artist_index_rank_genre = None
    u.artist_index_score_region = None
    u.artist_index_score_genre = None
    u.artist_index_primary_genre = None
    u.artist_index_calculated_at = datetime(2026, 5, 4, tzinfo=timezone.utc)
    u.created_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return u


def _make_profile(
    *,
    user_id: uuid.UUID,
    genre_tags: list[str] | None = None,
) -> MagicMock:
    p = MagicMock()
    p.user_id = user_id
    p.genre_tags = genre_tags
    return p


def _make_db_result(rows: list) -> MagicMock:
    """Mock AsyncSession.execute() result returning list of row tuples."""
    mock_result = MagicMock()
    mock_result.all.return_value = rows
    mock_result.scalar_one_or_none.return_value = rows[0] if rows else None
    return mock_result


# ─── Test 1: GET /artists/index 200 with sample data ─────────────────────────


@pytest.mark.asyncio
async def test_get_artist_index_200():
    """GET /v1/artists/index returns 200 with ranked artist entries."""
    artist1 = _make_artist(display_name="artist_one", rank=1, score=90.0)
    profile1 = _make_profile(user_id=artist1.id, genre_tags=["watercolor"])
    artist2 = _make_artist(display_name="artist_two", rank=2, score=75.0)
    profile2 = _make_profile(user_id=artist2.id, genre_tags=["oil"])

    rows = [(artist1, profile1), (artist2, profile2)]

    mock_db = AsyncMock()
    mock_db.execute.return_value = _make_db_result(rows)

    # Patch rate_limit dependency to no-op
    with patch("app.api.artists.rate_limit", return_value=lambda *a, **kw: None):
        result = await get_artist_index(
            region=None,
            genre=None,
            limit=50,
            cursor=None,
            db=mock_db,
            _rl=None,
        )

    # Double-wrapped: {"data": {"data": [...], "next_cursor": ..., "total": ...}}
    assert "data" in result
    payload = result["data"]
    assert "data" in payload
    data = payload["data"]
    assert len(data) == 2
    assert data[0]["username"] == "artist_one"
    assert data[0]["rank"] == 1
    assert data[0]["score"] == 90.0
    assert data[0]["tier_badge"] == "top_10"
    assert data[1]["username"] == "artist_two"
    assert data[1]["primary_genre"] == "oil"
    assert payload["next_cursor"] is None  # only 2 entries, no more


# ─── Test 2: GET /artists/index?region=KR 200 ────────────────────────────────


@pytest.mark.asyncio
async def test_get_artist_index_filter_by_region():
    """GET /v1/artists/index?region=KR returns only KR artists."""
    kr_artist = _make_artist(display_name="kr_artist", country_code="KR", rank=3, score=65.0)
    kr_profile = _make_profile(user_id=kr_artist.id, genre_tags=["digital"])
    # Only KR artist returned (DB filter applied)
    rows = [(kr_artist, kr_profile)]

    mock_db = AsyncMock()
    mock_db.execute.return_value = _make_db_result(rows)

    with patch("app.api.artists.rate_limit", return_value=lambda *a, **kw: None):
        result = await get_artist_index(
            region="KR",
            genre=None,
            limit=50,
            cursor=None,
            db=mock_db,
            _rl=None,
        )

    payload = result["data"]
    data = payload["data"]
    assert len(data) == 1
    assert data[0]["country"] == "KR"
    assert data[0]["username"] == "kr_artist"


# ─── Test 3: GET /artists/{user_id}/index 200 ────────────────────────────────


@pytest.mark.asyncio
async def test_get_artist_ranking_200():
    """GET /v1/artists/{user_id}/index returns score, rank, tier_badge for ranked artist."""
    artist = _make_artist(rank=42, score=55.0, country_code="PE")

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = artist
    mock_db.execute.return_value = mock_result

    with patch("app.api.artists.rate_limit", return_value=lambda *a, **kw: None):
        result = await get_artist_ranking(
            user_id=str(artist.id),
            db=mock_db,
            _rl=None,
        )

    data = result["data"]
    assert data["rank"] == 42
    assert data["score"] == 55.0
    assert data["tier_badge"] == "top_100"
    assert data["last_calculated_at"] is not None


# ─── Test 4: GET /artists/{non_artist_id}/index 404 ──────────────────────────


@pytest.mark.asyncio
async def test_get_artist_ranking_404_non_artist():
    """GET /v1/artists/{user_id}/index raises 404 when user is not an artist or not found."""
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None  # DB returns no artist
    mock_db.execute.return_value = mock_result

    with patch("app.api.artists.rate_limit", return_value=lambda *a, **kw: None):
        with pytest.raises(ApiError) as exc_info:
            await get_artist_ranking(
                user_id=str(uuid.uuid4()),
                db=mock_db,
                _rl=None,
            )

    assert exc_info.value.status_code == 404
    assert "NOT_FOUND" in exc_info.value.code
