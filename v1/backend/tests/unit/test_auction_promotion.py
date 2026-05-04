"""Unit tests for auction-promotion-suite — Phase 4 #11 §B-13.

6 test cases:
  _make_notifs (3):
    1. current_winner=None → seller only
    2. seller_id == current_winner (R-4) → seller only (no duplicate)
    3. winner != seller → 2 notifications
  dispatch_pending_notifications_once idempotent (1):
    4. same auction swept twice → first sweep inserts, second sweep skips
  _generate_share_card (2):
    5. httpx OK + valid image → non-empty bytes, valid PNG
    6. httpx raises Exception → fallback bytes, valid PNG, no exception propagated
"""
from __future__ import annotations

import io
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from PIL import Image

from app.services.auction_promotion_jobs import (
    _generate_share_card,
    _make_notifs,
    dispatch_pending_notifications_once,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_auction(
    *,
    seller_id: uuid.UUID | None = None,
    current_winner: uuid.UUID | None = None,
) -> MagicMock:
    a = MagicMock()
    a.id = uuid.uuid4()
    a.seller_id = seller_id or uuid.uuid4()
    a.current_winner = current_winner
    return a


def _now() -> datetime:
    return datetime.now(UTC)


# ---------------------------------------------------------------------------
# Test 1 — current_winner=None → seller 1건만
# ---------------------------------------------------------------------------


def test_make_notifs_winner_none():
    auction = _make_auction(current_winner=None)
    notifs = _make_notifs(auction, "auction_ending_1h")
    assert len(notifs) == 1
    assert notifs[0].user_id == auction.seller_id


# ---------------------------------------------------------------------------
# Test 2 — seller_id == current_winner (R-4 edge) → seller 1건만
# ---------------------------------------------------------------------------


def test_make_notifs_seller_equals_winner():
    seller_id = uuid.uuid4()
    auction = _make_auction(seller_id=seller_id, current_winner=seller_id)
    notifs = _make_notifs(auction, "auction_ending_6h")
    assert len(notifs) == 1
    assert notifs[0].user_id == seller_id


# ---------------------------------------------------------------------------
# Test 3 — winner != seller → 2건 (작가 + winner)
# ---------------------------------------------------------------------------


def test_make_notifs_winner_not_seller():
    seller_id = uuid.uuid4()
    winner_id = uuid.uuid4()
    auction = _make_auction(seller_id=seller_id, current_winner=winner_id)
    notifs = _make_notifs(auction, "auction_ending_24h")
    assert len(notifs) == 2
    user_ids = {n.user_id for n in notifs}
    assert seller_id in user_ids
    assert winner_id in user_ids


# ---------------------------------------------------------------------------
# Test 4 — dispatch idempotent: same auction 2회 sweep → 첫 sweep만 발송
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dispatch_idempotent():
    """Two sweeps of same auction: first fires notifications, second skips (IS NULL filter)."""
    seller_id = uuid.uuid4()

    auction = MagicMock()
    auction.id = uuid.uuid4()
    auction.seller_id = seller_id
    auction.current_winner = None

    # First sweep: col IS NULL → returns the auction
    scalars_first = MagicMock()
    scalars_first.all.return_value = [auction]
    result_first = MagicMock()
    result_first.scalars.return_value = scalars_first

    # Second sweep: col no longer NULL → returns empty
    scalars_second = MagicMock()
    scalars_second.all.return_value = []
    result_second = MagicMock()
    result_second.scalars.return_value = scalars_second

    # Alternate per slot (3 slots × 2 sweeps = 6 select calls + 3 update calls first sweep)
    # We test 24h slot only; mock execute to return first/second alternately for select,
    # and a generic mock for update (execute_options returns self)
    execute_results = [
        result_first,   # slot 24h sweep 1
        MagicMock(),    # update for slot 24h sweep 1
        result_second,  # slot 6h sweep 1
        result_second,  # slot 1h sweep 1
        result_second,  # slot 24h sweep 2
        result_second,  # slot 6h sweep 2
        result_second,  # slot 1h sweep 2
    ]

    db = AsyncMock()
    execute_iter = iter(execute_results)

    async def _execute(stmt, *args, **kwargs):
        return next(execute_iter)

    db.execute = _execute
    db.add = MagicMock()
    db.commit = AsyncMock()

    # Sweep 1
    summary1 = await dispatch_pending_notifications_once(db)
    # Sweep 2
    summary2 = await dispatch_pending_notifications_once(db)

    # First sweep dispatched 1 for 24h slot
    assert summary1["auction_ending_24h"] == 1
    # Second sweep dispatched 0 for all slots
    assert summary2["auction_ending_24h"] == 0
    assert summary2["auction_ending_6h"] == 0
    assert summary2["auction_ending_1h"] == 0


# ---------------------------------------------------------------------------
# Test 5 — _generate_share_card success: httpx OK + Image bytes → valid PNG
# ---------------------------------------------------------------------------


def test_generate_share_card_success():
    # Create a small fake PNG image in memory
    fake_img = Image.new("RGB", (100, 100), (200, 100, 50))
    buf = io.BytesIO()
    fake_img.save(buf, format="PNG")
    fake_png_bytes = buf.getvalue()

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.content = fake_png_bytes

    with patch("app.services.auction_promotion_jobs.httpx.get", return_value=mock_response):
        result = _generate_share_card(
            thumbnail_url="https://example.com/thumb.png",
            artist_name="TestArtist",
            current_price=50000,
            currency="KRW",
            end_at=datetime.now(UTC) + timedelta(hours=2),
        )

    assert isinstance(result, bytes)
    assert len(result) > 0
    # Validate PNG
    img = Image.open(io.BytesIO(result))
    img.load()
    assert img.size == (1200, 630)


# ---------------------------------------------------------------------------
# Test 6 — _generate_share_card fallback: httpx raises → fallback path, valid PNG
# ---------------------------------------------------------------------------


def test_generate_share_card_fallback():
    with patch(
        "app.services.auction_promotion_jobs.httpx.get",
        side_effect=Exception("network error"),
    ):
        result = _generate_share_card(
            thumbnail_url="https://example.com/thumb.png",
            artist_name="FallbackArtist",
            current_price=10000,
            currency="KRW",
            end_at=datetime.now(UTC) + timedelta(minutes=30),
        )

    # Must not raise; must return valid PNG bytes
    assert isinstance(result, bytes)
    assert len(result) > 0
    img = Image.open(io.BytesIO(result))
    img.load()
    assert img.size == (1200, 630)
