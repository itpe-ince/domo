"""Unit tests for app/services/currency.py — B'-1 multi-currency-foundation.

Tests: get_rate, convert_amount, format_currency, get_all_rates, convertAndFormat logic.
"""
from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.currency import (
    FALLBACK_RATES,
    SUPPORTED_CURRENCIES,
    convert_amount,
    format_currency,
    get_all_rates,
    get_rate,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_db_with_rate(target: str, rate: float) -> AsyncMock:
    """Return an AsyncSession mock that yields an ExchangeRate row for `target`."""
    from datetime import datetime, timedelta, timezone

    db = AsyncMock()
    row = MagicMock()
    row.rate = Decimal(str(rate))
    row.target_currency = target
    row.base_currency = "USD"
    row.expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = row
    db.execute = AsyncMock(return_value=mock_result)
    return db


def _make_db_no_row() -> AsyncMock:
    """Return an AsyncSession mock that yields no ExchangeRate row (fallback path)."""
    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=mock_result)
    return db


# ---------------------------------------------------------------------------
# get_rate
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_rate_usd_is_one():
    """get_rate("USD") returns Decimal(1.0) immediately (no DB call)."""
    db = AsyncMock()
    rate = await get_rate("USD", db)
    assert rate == Decimal("1.0")
    db.execute.assert_not_called()


@pytest.mark.asyncio
async def test_get_rate_krw_from_db():
    """get_rate("KRW") reads from DB when row exists."""
    db = _make_db_with_rate("KRW", 1300.0)
    rate = await get_rate("KRW", db)
    assert rate == Decimal("1300.0")


@pytest.mark.asyncio
async def test_get_rate_eur_from_db():
    """get_rate("EUR") reads from DB when row exists."""
    db = _make_db_with_rate("EUR", 0.92)
    rate = await get_rate("EUR", db)
    assert rate == Decimal("0.92")


@pytest.mark.asyncio
async def test_get_rate_fallback_when_no_db_row():
    """get_rate falls back to FALLBACK_RATES when no DB row found."""
    db = _make_db_no_row()
    rate = await get_rate("KRW", db)
    assert rate == FALLBACK_RATES["KRW"]


@pytest.mark.asyncio
async def test_get_rate_unsupported_currency_returns_one():
    """get_rate with unsupported currency returns Decimal(1.0) (safe fallback)."""
    db = _make_db_no_row()
    rate = await get_rate("BTC", db)
    assert rate == Decimal("1.0")


# ---------------------------------------------------------------------------
# convert_amount
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_convert_amount_same_currency():
    """convert_amount with same from/to returns unchanged."""
    db = AsyncMock()
    result = await convert_amount(5000, "USD", "USD", db)
    assert result == 5000
    db.execute.assert_not_called()


@pytest.mark.asyncio
async def test_convert_amount_usd_to_krw():
    """100 USD-cents = $1.00 → 130000 KRW-cents = 1300 won at rate 1300."""
    db = _make_db_with_rate("KRW", 1300.0)
    result = await convert_amount(100, "USD", "KRW", db)
    assert result == 130000


@pytest.mark.asyncio
async def test_convert_amount_krw_to_usd():
    """130000 KRW-cents = 1300 won → ~100 USD-cents = $1.00 at rate 1300."""
    db = AsyncMock()
    krw_row = MagicMock()
    krw_row.rate = Decimal("1300.0")
    krw_row.expires_at = MagicMock()
    krw_row.expires_at.__gt__ = lambda self, other: True

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = krw_row
    db.execute = AsyncMock(return_value=mock_result)

    result = await convert_amount(130000, "KRW", "USD", db)
    assert result == 100  # 130000 / 1300 = 100 USD-cents


@pytest.mark.asyncio
async def test_convert_amount_usd_to_eur():
    """100 USD-cents = $1.00 → 92 EUR-cents at rate 0.92."""
    db = _make_db_with_rate("EUR", 0.92)
    result = await convert_amount(100, "USD", "EUR", db)
    assert result == 92


@pytest.mark.asyncio
async def test_convert_amount_usd_to_jpy():
    """100 USD-cents = $1.00 → 15000 JPY-cents = ¥150 at rate 150."""
    db = _make_db_with_rate("JPY", 150.0)
    result = await convert_amount(100, "USD", "JPY", db)
    assert result == 15000


# ---------------------------------------------------------------------------
# format_currency
# ---------------------------------------------------------------------------


def test_format_currency_usd():
    """format_currency 500 USD-cents = $5.00."""
    result = format_currency(500, "USD")
    assert "$5.00" in result


def test_format_currency_krw():
    """format_currency 130000 KRW-cents = ₩1,300 (whole number, no decimal)."""
    result = format_currency(130000, "KRW")
    assert "₩" in result
    assert "1,300" in result
    assert "." not in result  # KRW has no fractional display


def test_format_currency_jpy():
    """format_currency 15000 JPY-cents = ¥150."""
    result = format_currency(15000, "JPY")
    assert "¥" in result
    assert "150" in result


def test_format_currency_eur():
    """format_currency 92 EUR-cents = €0.92."""
    result = format_currency(92, "EUR")
    assert "€" in result
    assert "0.92" in result


# ---------------------------------------------------------------------------
# get_all_rates
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_all_rates_returns_all_supported():
    """get_all_rates returns all SUPPORTED_CURRENCIES as float dict."""
    db = AsyncMock()

    # Return fallback for every currency (no DB row)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=mock_result)

    rates = await get_all_rates(db)

    assert isinstance(rates, dict)
    for currency in SUPPORTED_CURRENCIES:
        assert currency in rates
        assert isinstance(rates[currency], float)
    assert rates["USD"] == 1.0


@pytest.mark.asyncio
async def test_get_all_rates_usd_always_one():
    """get_all_rates always has USD=1.0."""
    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=mock_result)

    rates = await get_all_rates(db)
    assert rates["USD"] == 1.0
