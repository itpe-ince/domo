"""Webhook event retention cleanup job.

Deletes webhook_events rows older than 90 days (Stripe's retention window).
Runs daily via the lifespan cron registered in app/main.py.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.models.webhook_event import WebhookEvent

log = logging.getLogger(__name__)

_RETENTION_DAYS = 90


async def cleanup_old_webhook_events(db: AsyncSession) -> int:
    """Delete webhook_events rows older than 90 days.

    Returns the number of rows deleted.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=_RETENTION_DAYS)
    result = await db.execute(
        delete(WebhookEvent).where(WebhookEvent.processed_at < cutoff)
    )
    deleted = result.rowcount
    if deleted:
        await db.commit()
        log.info("webhook_cleanup: deleted %d rows older than %d days", deleted, _RETENTION_DAYS)
    return deleted


async def webhook_cleanup_cron_loop(interval_seconds: int = 86400) -> None:
    """Background task — runs once per day."""
    log.info("webhook_cleanup_cron_loop started (interval=%ss)", interval_seconds)
    while True:
        try:
            async with AsyncSessionLocal() as db:
                await cleanup_old_webhook_events(db)
        except Exception as e:  # noqa: BLE001
            log.exception("webhook cleanup cron failed: %s", e)
        await asyncio.sleep(interval_seconds)
