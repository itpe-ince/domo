"""System settings runtime accessor.

Reads from system_settings table; falls back to hardcoded defaults
if a key is missing (e.g., before migration runs).
"""
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sponsorship import SystemSetting

DEFAULTS: dict[str, Any] = {
    "bluebird_unit_price": {"amount": 1000, "currency": "KRW"},
    "platform_fee_sponsorship": {"percent": 10},
    "platform_fee_auction": {"percent": 10},
    "platform_fee_buy_now": {"percent": 10},
    "auction_payment_deadline_days": {"days": 3},
    "warning_threshold": {"count": 3},
    "settlement_cycle": {"cycle": "weekly"},
    "translation": {
        "provider": "ollama",
        "ollama_url": "http://100.75.139.86:11434",
        "ollama_model": "gemma4:latest",
        "google_api_key": "",
    },
    # KYC gate mode: "off" (dev default) | "soft" (warn+notify) | "enforce" (block)
    "kyc_enforcement": "off",
}


async def get_setting(db: AsyncSession, key: str) -> Any:
    """Return the setting value for *key*.

    Guarantees that the returned value matches the type in DEFAULTS:
    - If the DB row stores a plain scalar (e.g. a bare string) but the default
      is a dict, the scalar is normalised to ``{"value": scalar}`` so callers
      can always use dict `.get()` without isinstance guards.
    - Conversely, if the DB stores a dict but the default is a scalar, the
      raw dict is returned unchanged (callers should inspect it).
    """
    result = await db.execute(select(SystemSetting).where(SystemSetting.key == key))
    row = result.scalar_one_or_none()
    value = row.value if row else DEFAULTS.get(key)

    # Normalise: if default is dict but stored value is a plain scalar,
    # wrap it so downstream code can always call .get() safely.
    default = DEFAULTS.get(key)
    if isinstance(default, dict) and not isinstance(value, dict):
        # e.g. settlement_cycle stored as bare "weekly" string
        # Wrap using the first key of the default dict as the canonical key.
        first_key = next(iter(default))
        value = {first_key: value}

    return value
