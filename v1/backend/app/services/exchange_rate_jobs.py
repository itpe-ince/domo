"""Exchange rate fetch cron — B'-1 multi-currency-foundation.

9th cron worker (R-5 isolated): runs every 3600 seconds.
Fetches USD-based rates for USD/KRW/EUR/JPY from Open Exchange Rates API.

Configuration:
  EXCHANGE_RATE_API_KEY — Open Exchange Rates APP_ID (1000 req/month free).
  If unset, Mock mode: hardcoded fallback rates (no external API call).

Prometheus metric: exchange_rate_fetch_total (counter, labels: status=ok|error|mock).
"""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import httpx
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.db.session import AsyncSessionLocal
from app.models.exchange_rate import ExchangeRate
from app.services.cron_monitor import record_cron_run as _push_cron_status

log = logging.getLogger(__name__)

# ── Supported currencies ──────────────────────────────────────────────────────
SUPPORTED_CURRENCIES = ["USD", "KRW", "EUR", "JPY"]

# ── Mock rates (API key absent) ───────────────────────────────────────────────
MOCK_RATES: dict[str, float] = {
    "USD": 1.0,
    "KRW": 1300.0,
    "EUR": 0.92,
    "JPY": 150.0,
}

# ── Cache TTL ─────────────────────────────────────────────────────────────────
CACHE_TTL_SECONDS = 3600  # 1 hour

# ── Open Exchange Rates API ───────────────────────────────────────────────────
OXR_BASE_URL = "https://openexchangerates.org/api/latest.json"


def _get_api_key() -> str | None:
    return os.environ.get("EXCHANGE_RATE_API_KEY") or None


async def _fetch_rates_from_api(api_key: str) -> dict[str, float]:
    """Fetch latest USD-based rates from Open Exchange Rates."""
    params = {
        "app_id": api_key,
        "base": "USD",
        "symbols": ",".join(c for c in SUPPORTED_CURRENCIES if c != "USD"),
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(OXR_BASE_URL, params=params)
        resp.raise_for_status()
        data = resp.json()
        rates: dict[str, float] = data.get("rates", {})
        rates["USD"] = 1.0
        return rates


async def _upsert_rates(rates: dict[str, float]) -> None:
    """Upsert exchange rates into DB and optionally Redis cache."""
    now = datetime.now(timezone.utc)
    expires = now + timedelta(seconds=CACHE_TTL_SECONDS)

    async with AsyncSessionLocal() as db:
        for currency, rate in rates.items():
            if currency not in SUPPORTED_CURRENCIES:
                continue
            stmt = (
                pg_insert(ExchangeRate)
                .values(
                    base_currency="USD",
                    target_currency=currency,
                    rate=Decimal(str(rate)),
                    fetched_at=now,
                    expires_at=expires,
                )
                .on_conflict_do_update(
                    index_elements=["base_currency", "target_currency"],
                    set_={
                        "rate": Decimal(str(rate)),
                        "fetched_at": now,
                        "expires_at": expires,
                    },
                )
            )
            await db.execute(stmt)
        await db.commit()

    # Also update Redis cache if available (G''-2)
    try:
        from app.services.cache import cache  # type: ignore[import]
        import json

        if cache.is_enabled:
            cache_key = "exchange_rates:USD"
            payload = json.dumps({k: v for k, v in rates.items() if k in SUPPORTED_CURRENCIES})
            await cache.set(cache_key, payload, CACHE_TTL_SECONDS)
    except Exception as exc:  # noqa: BLE001
        log.debug("Redis exchange rate cache update skipped: %s", exc)


async def run_exchange_rate_fetch() -> str:
    """Run one exchange rate fetch cycle. Returns status: 'ok' | 'mock' | 'error'."""
    # ── Prometheus counter ─────────────────────────────────────────────────────
    try:
        from app.core.metrics import EXCHANGE_RATE_FETCH_TOTAL  # type: ignore[import]
        _counter = EXCHANGE_RATE_FETCH_TOTAL
    except (ImportError, AttributeError):
        _counter = None

    api_key = _get_api_key()

    if not api_key:
        log.info("EXCHANGE_RATE_API_KEY not set — using mock rates (B'-1 Mock mode)")
        await _upsert_rates(MOCK_RATES)
        if _counter:
            try:
                _counter.labels(status="mock").inc()
            except Exception:  # noqa: BLE001
                pass
        return "mock"

    try:
        rates = await _fetch_rates_from_api(api_key)
        await _upsert_rates(rates)
        log.info(
            "exchange_rate_fetch ok: %s",
            {k: rates[k] for k in SUPPORTED_CURRENCIES if k in rates},
        )
        if _counter:
            try:
                _counter.labels(status="ok").inc()
            except Exception:  # noqa: BLE001
                pass
        return "ok"
    except Exception as exc:  # noqa: BLE001
        log.warning("exchange_rate_fetch failed: %s — falling back to mock rates", exc)
        await _upsert_rates(MOCK_RATES)
        if _counter:
            try:
                _counter.labels(status="error").inc()
            except Exception:  # noqa: BLE001
                pass
        return "error"


async def exchange_rate_cron_loop(interval_seconds: int = 3600) -> None:
    """Background cron loop — 9th worker (R-5 isolated).

    Fetches on startup, then every interval_seconds.
    Designed to run as an asyncio.Task in lifespan (main.py).
    """
    log.info("exchange_rate_cron_loop started (interval=%ds)", interval_seconds)
    while True:
        await _push_cron_status("exchange_rate", "running")
        try:
            status = await run_exchange_rate_fetch()
            log.debug("exchange_rate_cron: status=%s", status)
            await _push_cron_status("exchange_rate", "success")
        except asyncio.CancelledError:
            log.info("exchange_rate_cron_loop cancelled — shutting down")
            return
        except Exception as exc:  # noqa: BLE001
            log.error("exchange_rate_cron_loop unhandled: %s", exc, exc_info=True)
            await _push_cron_status("exchange_rate", "failed", error=str(exc)[:500])
        try:
            await asyncio.sleep(interval_seconds)
        except asyncio.CancelledError:
            log.info("exchange_rate_cron_loop sleep cancelled — shutting down")
            return
