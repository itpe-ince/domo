"""Currency conversion service — B'-1 multi-currency-foundation.

Provides:
  - get_rate(target, db)          → Decimal rate (USD → target)
  - convert_amount(cents, from_, to_, db) → int cents in target currency
  - convert_and_format(cents, native, target) → display string (frontend helper)

Layered cache:
  1. Redis (G''-2) — 5min TTL for endpoint responses
  2. DB (exchange_rates table) — 1h TTL
  3. In-memory fallback (MOCK_RATES) — if DB is empty / unreachable
"""
from __future__ import annotations

import logging
from decimal import ROUND_HALF_UP, Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

log = logging.getLogger(__name__)

SUPPORTED_CURRENCIES = ["USD", "KRW", "EUR", "JPY"]

# Fallback rates — used when DB is empty and cron hasn't run yet
FALLBACK_RATES: dict[str, Decimal] = {
    "USD": Decimal("1.0"),
    "KRW": Decimal("1300.0"),
    "EUR": Decimal("0.92"),
    "JPY": Decimal("150.0"),
}

# Zero-decimal currencies (like KRW, JPY — no fractional subunit)
ZERO_DECIMAL_CURRENCIES = {"KRW", "JPY"}


async def get_rate(target: str, db: "AsyncSession") -> Decimal:
    """Return USD → target currency rate.

    Reads from exchange_rates DB table (populated by exchange_rate_cron_loop).
    Falls back to FALLBACK_RATES if no valid DB entry found.
    """
    if target == "USD":
        return Decimal("1.0")

    if target not in SUPPORTED_CURRENCIES:
        log.warning("Unsupported currency requested: %s — using fallback 1.0", target)
        return Decimal("1.0")

    try:
        from datetime import datetime, timezone

        from sqlalchemy import select

        from app.models.exchange_rate import ExchangeRate

        now = datetime.now(timezone.utc)
        result = await db.execute(
            select(ExchangeRate).where(
                ExchangeRate.base_currency == "USD",
                ExchangeRate.target_currency == target,
                ExchangeRate.expires_at > now,
            )
        )
        row = result.scalar_one_or_none()
        if row is not None:
            return Decimal(str(row.rate))
    except Exception as exc:  # noqa: BLE001
        log.warning("get_rate DB lookup failed: %s — using fallback", exc)

    return FALLBACK_RATES.get(target, Decimal("1.0"))


async def convert_amount(
    cents: int,
    from_currency: str,
    to_currency: str,
    db: "AsyncSession",
) -> int:
    """Convert cents from one currency to another.

    Both ``cents`` values are in the smallest subunit (e.g. US cents, KRW won).
    For zero-decimal currencies (KRW/JPY), 100 cents = 100 units = 1 major unit
    but Domo convention stores everything as cents (×100 even for KRW).

    Returns an integer (cents in target currency).
    """
    if from_currency == to_currency:
        return cents

    # Get both rates vs USD
    if from_currency == "USD":
        from_rate = Decimal("1.0")
    else:
        from_rate = await get_rate(from_currency, db)

    if to_currency == "USD":
        to_rate = Decimal("1.0")
    else:
        to_rate = await get_rate(to_currency, db)

    # Convert: cents_from → USD cents → target cents
    # Domo stores all amounts as minor units ×100 — rate conversion is straightforward
    usd_cents = Decimal(str(cents)) / from_rate
    target_cents = usd_cents * to_rate
    return int(target_cents.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def format_currency(cents: int, currency: str) -> str:
    """Format cents into a locale-aware currency string (backend-side only).

    Frontend uses lib/format.ts formatPriceCents() for the same purpose.
    This is for API responses or email templates that need formatted amounts.
    """
    amount = Decimal(str(cents)) / Decimal("100")

    if currency in ZERO_DECIMAL_CURRENCIES:
        # KRW/JPY: display as whole number (100 cents = 100 won)
        whole = int(amount)
        if currency == "KRW":
            return f"₩{whole:,}"
        return f"¥{whole:,}"

    symbols = {"USD": "$", "EUR": "€"}
    sym = symbols.get(currency, f"{currency} ")
    return f"{sym}{amount:,.2f}"


async def get_all_rates(db: "AsyncSession") -> dict[str, float]:
    """Return all supported USD-based rates as a plain dict.

    Used by GET /v1/exchange-rates endpoint.
    """
    rates: dict[str, float] = {"USD": 1.0}
    for currency in SUPPORTED_CURRENCIES:
        if currency == "USD":
            continue
        rate = await get_rate(currency, db)
        rates[currency] = float(rate)
    return rates
