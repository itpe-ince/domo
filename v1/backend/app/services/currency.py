"""Currency conversion with exchange rate caching.

Uses free exchangerate-api.com (no key needed for limited use).
Falls back to hardcoded rates if API unavailable.
"""
import logging
import time

import httpx

log = logging.getLogger(__name__)

# Cache: {target_currency: (rate_from_usd, timestamp)}
_rate_cache: dict[str, tuple[float, float]] = {}
CACHE_TTL = 3600  # 1 hour

FALLBACK_RATES: dict[str, float] = {
    "USD": 1.0,
    "KRW": 1350.0,
    "JPY": 155.0,
    "EUR": 0.92,
    "GBP": 0.79,
    "CNY": 7.25,
    "TWD": 32.0,
    "HKD": 7.82,
    "VND": 25400.0,
    "THB": 35.5,
    "PHP": 56.0,
    "MYR": 4.7,
}


async def get_exchange_rate(target: str) -> float:
    """Get USD → target currency rate. Cached for 1h."""
    if target == "USD":
        return 1.0

    now = time.time()
    cached = _rate_cache.get(target)
    if cached and (now - cached[1]) < CACHE_TTL:
        return cached[0]

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                f"https://open.er-api.com/v6/latest/USD"
            )
            resp.raise_for_status()
            data = resp.json()
            rates = data.get("rates", {})
            rate = rates.get(target, FALLBACK_RATES.get(target, 1.0))
            # Cache all rates
            for currency, r in rates.items():
                _rate_cache[currency] = (r, now)
            return rate
    except Exception as e:
        log.warning("Exchange rate API failed: %s, using fallback", e)
        return FALLBACK_RATES.get(target, 1.0)


async def convert_usd(amount: float, target: str) -> dict:
    """Convert USD amount to target currency."""
    rate = await get_exchange_rate(target)
    return {
        "original": {"amount": amount, "currency": "USD"},
        "converted": {"amount": round(amount * rate, 2), "currency": target},
        "rate": rate,
    }
