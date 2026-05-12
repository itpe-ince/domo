"""Unit tests for D-5: auction_promotion_jobs i18n integration.

Verifies that _make_notifs respects user language via seller_lang/winner_lang args.

3 test cases:
  1. seller_lang='en' → English title/body in seller notification
  2. seller_lang=None → ko fallback
  3. winner_lang='ja' → Japanese title/body in winner notification
"""
from __future__ import annotations

import uuid
from unittest.mock import MagicMock

from app.services.auction_promotion_jobs import _make_notifs


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_auction(
    seller_id: uuid.UUID | None = None,
    current_winner: uuid.UUID | None = None,
) -> MagicMock:
    a = MagicMock()
    a.id = uuid.uuid4()
    a.seller_id = seller_id or uuid.uuid4()
    a.current_winner = current_winner
    return a


# ---------------------------------------------------------------------------
# Test 1 — seller_lang='en' → English notification
# ---------------------------------------------------------------------------


def test_make_notifs_english_seller():
    auction = _make_auction(current_winner=None)
    notifs = _make_notifs(auction, "auction_ending_24h", seller_lang="en")
    assert len(notifs) == 1
    notif = notifs[0]
    assert notif.title == "Auction ending in 24h"
    assert "24 hours" in notif.body


# ---------------------------------------------------------------------------
# Test 2 — seller_lang=None → ko fallback
# ---------------------------------------------------------------------------


def test_make_notifs_none_lang_ko_fallback():
    auction = _make_auction(current_winner=None)
    notifs = _make_notifs(auction, "auction_ending_1h", seller_lang=None)
    assert len(notifs) == 1
    notif = notifs[0]
    assert notif.title == "경매 종료 1시간 전"
    assert "1시간" in notif.body


# ---------------------------------------------------------------------------
# Test 3 — winner with different language from seller
# ---------------------------------------------------------------------------


def test_make_notifs_winner_different_lang():
    seller_id = uuid.uuid4()
    winner_id = uuid.uuid4()
    auction = _make_auction(seller_id=seller_id, current_winner=winner_id)

    notifs = _make_notifs(
        auction,
        "auction_ending_6h",
        seller_lang="ko",
        winner_lang="ja",
    )
    assert len(notifs) == 2

    notif_map = {n.user_id: n for n in notifs}
    seller_notif = notif_map[seller_id]
    winner_notif = notif_map[winner_id]

    # Seller gets Korean
    assert seller_notif.title == "경매 종료 6시간 전"
    # Winner gets Japanese
    assert "6時間" in winner_notif.title
