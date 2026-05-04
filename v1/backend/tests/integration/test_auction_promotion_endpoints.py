"""Integration-style endpoint tests for auction-promotion-suite — Phase 4 #11 §B-13.

Strategy: direct endpoint function calls with MagicMock for SQLAlchemy model instances,
AsyncMock for DB session. No real DB, no real network.
Mirrors test_artist_tier_release_endpoints.py pattern.

6 test cases (share-card endpoint):
  1. test_share_card_200_first_time    — seller calls, no cache → 200 + cached=False
  2. test_share_card_200_cache_hit     — share_card_generated_at < 1h ago → 200 + cached=True
  3. test_share_card_403_not_owner     — different user → 403 FORBIDDEN
  4. test_share_card_404_not_found     — random UUID → 404 AUCTION_NOT_FOUND
  5. test_share_card_409_not_active    — status='ended' → 409 AUCTION_NOT_ACTIVE
  6. test_share_card_500_storage_fail  — storage.put raises → 500 SHARE_CARD_GENERATION_FAILED
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.errors import ApiError

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now() -> datetime:
    return datetime.now(UTC)


def _make_user(
    *,
    user_id: uuid.UUID | None = None,
    role: str = "artist",
    display_name: str = "Test Artist",
) -> MagicMock:
    u = MagicMock()
    u.id = user_id or uuid.uuid4()
    u.role = role
    u.display_name = display_name
    return u


def _make_auction(
    *,
    auction_id: uuid.UUID | None = None,
    seller_id: uuid.UUID | None = None,
    status: str = "active",
    current_price: int = 50000,
    currency: str = "KRW",
    share_card_url: str | None = None,
    share_card_generated_at: datetime | None = None,
) -> MagicMock:
    a = MagicMock(spec=[
        "id", "seller_id", "status", "current_price", "currency",
        "end_at", "product_post_id", "share_card_url", "share_card_generated_at",
    ])
    a.id = auction_id or uuid.uuid4()
    a.seller_id = seller_id or uuid.uuid4()
    a.status = status
    a.current_price = current_price
    a.currency = currency
    a.end_at = _now() + timedelta(hours=3)
    a.product_post_id = uuid.uuid4()
    a.share_card_url = share_card_url
    a.share_card_generated_at = share_card_generated_at
    return a


def _make_db_returning(auction: MagicMock | None) -> AsyncMock:
    """DB mock that returns auction on first scalar(), then a user mock on second."""
    db = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.add = MagicMock()

    artist_mock = MagicMock()
    artist_mock.display_name = "Test Artist"

    # db.scalar() side_effect: auction → artist → None (media)
    db.scalar = AsyncMock(side_effect=[auction, artist_mock, None])
    return db


# ---------------------------------------------------------------------------
# Import endpoint under test
# ---------------------------------------------------------------------------
from app.api.auctions import create_share_card  # noqa: E402

# ---------------------------------------------------------------------------
# Test 1 — seller calls, no cache → 200 + cached=False
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_share_card_200_first_time():
    seller = _make_user()
    auction = _make_auction(seller_id=seller.id)

    db = _make_db_returning(auction)

    fake_stored = MagicMock()
    fake_stored.url = "https://cdn.example.com/share-cards/test.png"

    mock_provider = AsyncMock()
    mock_provider.put = AsyncMock(return_value=fake_stored)

    with (
        patch("app.api.auctions._generate_share_card", return_value=b"<fake png>"),
        patch("app.api.auctions.get_storage_provider", return_value=mock_provider),
    ):
        result = await create_share_card(auction.id, user=seller, db=db, _rl=None)

    assert "data" in result
    data = result["data"]
    assert data["cached"] is False
    assert "share_card_url" in data
    assert data["share_card_url"] == "https://cdn.example.com/share-cards/test.png"
    db.commit.assert_awaited_once()


# ---------------------------------------------------------------------------
# Test 2 — share_card_generated_at < 1h ago → 200 + cached=True
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_share_card_200_cache_hit():
    seller = _make_user()
    recent_time = _now() - timedelta(minutes=30)
    auction = _make_auction(
        seller_id=seller.id,
        share_card_url="https://cdn.example.com/cached.png",
        share_card_generated_at=recent_time,
    )

    db = AsyncMock()
    db.scalar = AsyncMock(return_value=auction)
    db.commit = AsyncMock()

    result = await create_share_card(auction.id, user=seller, db=db, _rl=None)

    assert "data" in result
    data = result["data"]
    assert data["cached"] is True
    assert data["share_card_url"] == "https://cdn.example.com/cached.png"
    # No commit for cache hit
    db.commit.assert_not_awaited()


# ---------------------------------------------------------------------------
# Test 3 — different user → 403 FORBIDDEN
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_share_card_403_not_owner():
    seller = _make_user()
    other_user = _make_user(role="user")
    auction = _make_auction(seller_id=seller.id)

    db = AsyncMock()
    db.scalar = AsyncMock(return_value=auction)

    with pytest.raises(ApiError) as exc_info:
        await create_share_card(auction.id, user=other_user, db=db, _rl=None)

    err = exc_info.value
    assert err.code == "FORBIDDEN"
    assert err.status_code == 403


# ---------------------------------------------------------------------------
# Test 4 — random UUID → 404 AUCTION_NOT_FOUND
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_share_card_404_not_found():
    user = _make_user()
    db = AsyncMock()
    db.scalar = AsyncMock(return_value=None)

    with pytest.raises(ApiError) as exc_info:
        await create_share_card(uuid.uuid4(), user=user, db=db, _rl=None)

    err = exc_info.value
    assert err.code == "AUCTION_NOT_FOUND"
    assert err.status_code == 404


# ---------------------------------------------------------------------------
# Test 5 — status='ended' → 409 AUCTION_NOT_ACTIVE
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_share_card_409_not_active():
    seller = _make_user()
    auction = _make_auction(seller_id=seller.id, status="ended")

    db = AsyncMock()
    db.scalar = AsyncMock(return_value=auction)

    with pytest.raises(ApiError) as exc_info:
        await create_share_card(auction.id, user=seller, db=db, _rl=None)

    err = exc_info.value
    assert err.code == "AUCTION_NOT_ACTIVE"
    assert err.status_code == 409


# ---------------------------------------------------------------------------
# Test 6 — storage.put raises → 500 SHARE_CARD_GENERATION_FAILED
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_share_card_500_storage_failure():
    seller = _make_user()
    auction = _make_auction(seller_id=seller.id)

    db = _make_db_returning(auction)

    mock_provider = AsyncMock()
    mock_provider.put = AsyncMock(side_effect=Exception("S3 unavailable"))

    with (
        patch("app.api.auctions._generate_share_card", return_value=b"<fake png>"),
        patch("app.api.auctions.get_storage_provider", return_value=mock_provider),
    ):
        with pytest.raises(ApiError) as exc_info:
            await create_share_card(auction.id, user=seller, db=db, _rl=None)

    err = exc_info.value
    assert err.code == "SHARE_CARD_GENERATION_FAILED"
    assert err.status_code == 500
