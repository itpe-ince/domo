"""System settings runtime accessor.

Reads from system_settings table; falls back to hardcoded defaults
if a key is missing (e.g., before migration runs).
"""
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sponsorship import SystemSetting

DEFAULTS: dict[str, Any] = {
    "bluebird_unit_price": {"amount": 1, "currency": "USD"},
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
}


async def get_setting(db: AsyncSession, key: str) -> Any:
    result = await db.execute(select(SystemSetting).where(SystemSetting.key == key))
    row = result.scalar_one_or_none()
    if row:
        return row.value
    return DEFAULTS.get(key)
