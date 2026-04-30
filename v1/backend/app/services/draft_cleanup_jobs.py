"""Draft retention cleanup job — editor-draft-autosave PDCA.

Deletes posts with status='draft' that have been untouched for >= 90 days.
Runs daily via the lifespan cron registered in app/main.py.

Pattern follows webhook_cleanup_jobs.py (Q-D3 = A).
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.models.post import Post

log = logging.getLogger(__name__)

_RETENTION_DAYS = 90


async def cleanup_stale_drafts(db: AsyncSession) -> int:
    """Delete drafts older than 90 days (by updated_at).

    MediaAsset rows cascade-delete via the Post.media relationship
    (post.py: cascade="all, delete-orphan").

    Returns the number of draft rows deleted.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=_RETENTION_DAYS)
    result = await db.execute(
        delete(Post).where(
            Post.status == "draft",
            Post.updated_at < cutoff,
        )
    )
    deleted = result.rowcount or 0
    if deleted:
        await db.commit()
        log.info(
            "draft_cleanup: deleted %d drafts untouched >= %d days",
            deleted,
            _RETENTION_DAYS,
        )
    return deleted


async def draft_cleanup_cron_loop(interval_seconds: int = 86400) -> None:
    """Background task — runs once per day."""
    log.info("draft_cleanup_cron_loop started (interval=%ss)", interval_seconds)
    while True:
        try:
            async with AsyncSessionLocal() as db:
                await cleanup_stale_drafts(db)
        except Exception as e:  # noqa: BLE001
            log.exception("draft cleanup cron failed: %s", e)
        await asyncio.sleep(interval_seconds)
