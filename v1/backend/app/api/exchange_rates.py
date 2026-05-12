"""GET /v1/exchange-rates — B'-1 multi-currency-foundation.

Public endpoint. Returns USD-based rates for all supported currencies.
5-minute Redis cache (G''-2) keyed by "exchange_rates:USD".

Rate limit: 60/min by IP (exchange_rates_read).
"""
from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rate_limit import rate_limit
from app.db.session import get_db
from app.services.currency import get_all_rates

log = logging.getLogger(__name__)

router = APIRouter(prefix="/exchange-rates", tags=["exchange-rates"])

# Redis cache key and TTL (5 min — shorter than 1h DB TTL for endpoint freshness)
_CACHE_KEY = "exchange_rates:USD"
_CACHE_TTL = 300  # 5 minutes


@router.get("")
async def get_exchange_rates(
    base: str = "USD",
    db: AsyncSession = Depends(get_db),
    _rl=rate_limit("exchange_rates_read"),
):
    """Return current exchange rates for all supported currencies.

    Base is always USD (Open Exchange Rates free tier limitation).
    Response is cached in Redis for 5 minutes.

    Supported: USD, KRW, EUR, JPY.
    """
    # 1. Try Redis cache first
    try:
        from app.services.cache import cache  # type: ignore[import]

        if cache.is_enabled:
            cached = await cache.get(_CACHE_KEY)
            if cached:
                rates = json.loads(cached)
                return {
                    "data": {
                        "base": "USD",
                        "rates": rates,
                        "cached": True,
                    }
                }
    except Exception as exc:  # noqa: BLE001
        log.debug("exchange_rates cache read failed: %s", exc)

    # 2. Fetch from DB (populated by exchange_rate_cron_loop)
    rates = await get_all_rates(db)

    # 3. Cache in Redis
    try:
        from app.services.cache import cache  # type: ignore[import]

        if cache.is_enabled:
            await cache.set(_CACHE_KEY, json.dumps(rates), _CACHE_TTL)
    except Exception as exc:  # noqa: BLE001
        log.debug("exchange_rates cache write failed: %s", exc)

    return {
        "data": {
            "base": "USD",
            "rates": rates,
            "cached": False,
        }
    }
