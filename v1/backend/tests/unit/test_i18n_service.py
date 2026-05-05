"""Unit tests for D-5: app/services/i18n.py translation helper.

5 test cases:
  1. ko (default) — title + body returned for all 4 keys
  2. en translation — correct English strings returned
  3. ja translation
  4. zh translation
  5. es translation
  6. fallback to ko on unknown language
  7. fallback to ko when lang=None
"""
from __future__ import annotations

import pytest

from app.services.i18n import t


# ---------------------------------------------------------------------------
# Test 1 — ko translation (default locale)
# ---------------------------------------------------------------------------


def test_ko_auction_ending_24h():
    assert t("auction_ending_24h", "title", "ko") == "경매 종료 24시간 전"
    assert "24시간" in t("auction_ending_24h", "body", "ko")


def test_ko_auction_ending_6h():
    assert t("auction_ending_6h", "title", "ko") == "경매 종료 6시간 전"
    assert "6시간" in t("auction_ending_6h", "body", "ko")


def test_ko_auction_ending_1h():
    assert t("auction_ending_1h", "title", "ko") == "경매 종료 1시간 전"
    assert "1시간" in t("auction_ending_1h", "body", "ko")


def test_ko_auction_ended():
    assert t("auction_ended", "title", "ko") == "경매가 종료되었습니다"
    assert "종료" in t("auction_ended", "body", "ko")


# ---------------------------------------------------------------------------
# Test 2 — en translation
# ---------------------------------------------------------------------------


def test_en_translation():
    assert t("auction_ending_24h", "title", "en") == "Auction ending in 24h"
    assert "24 hours" in t("auction_ending_24h", "body", "en")
    assert t("auction_ending_6h", "title", "en") == "Auction ending in 6h"
    assert t("auction_ending_1h", "title", "en") == "Auction ending in 1h"
    assert t("auction_ended", "title", "en") == "Auction has ended"


# ---------------------------------------------------------------------------
# Test 3 — ja translation
# ---------------------------------------------------------------------------


def test_ja_translation():
    assert "24時間" in t("auction_ending_24h", "title", "ja")
    assert "24時間" in t("auction_ending_24h", "body", "ja")
    assert "6時間" in t("auction_ending_6h", "title", "ja")
    assert "1時間" in t("auction_ending_1h", "title", "ja")
    assert "終了" in t("auction_ended", "title", "ja")


# ---------------------------------------------------------------------------
# Test 4 — zh translation
# ---------------------------------------------------------------------------


def test_zh_translation():
    assert "24小时" in t("auction_ending_24h", "title", "zh")
    assert "24小时" in t("auction_ending_24h", "body", "zh")
    assert "6小时" in t("auction_ending_6h", "title", "zh")
    assert "1小时" in t("auction_ending_1h", "title", "zh")
    assert "结束" in t("auction_ended", "title", "zh")


# ---------------------------------------------------------------------------
# Test 5 — es translation
# ---------------------------------------------------------------------------


def test_es_translation():
    assert "24h" in t("auction_ending_24h", "title", "es")
    assert "24 horas" in t("auction_ending_24h", "body", "es")
    assert "6h" in t("auction_ending_6h", "title", "es")
    assert "1h" in t("auction_ending_1h", "title", "es")
    assert "finalizado" in t("auction_ended", "title", "es")


# ---------------------------------------------------------------------------
# Test 6 — fallback to ko on unknown language
# ---------------------------------------------------------------------------


def test_fallback_unknown_lang():
    result = t("auction_ending_24h", "title", "fr")  # French not supported
    # Should fall back to Korean
    assert result == "경매 종료 24시간 전"


# ---------------------------------------------------------------------------
# Test 7 — fallback to ko when lang=None
# ---------------------------------------------------------------------------


def test_fallback_none_lang():
    result = t("auction_ending_1h", "title", None)
    assert result == "경매 종료 1시간 전"
