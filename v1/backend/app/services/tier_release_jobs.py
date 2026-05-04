"""Background job: clear expired early_access tier release rows.

Runs every 60 seconds. Bulk UPDATE posts where early_access_until <= NOW()
→ sets both early_access_until and early_access_tier to NULL (DB cleanup).

NOTE: This worker is NOT on the critical path. The real-time visibility filter
in app/api/posts.py handles expiry instantly via `early_access_until > now()`
check. This worker maintains index efficiency by pruning NULL-able rows.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import update

from app.db.session import AsyncSessionLocal
from app.models.post import Post

log = logging.getLogger(__name__)


async def clear_expired_tier_release_once(db) -> int:
    """Clear expired early_access rows — single bulk UPDATE.

    Returns the number of rows cleared.
    """
    now = datetime.now(timezone.utc)
    result = await db.execute(
        update(Post)
        .where(
            Post.early_access_until.is_not(None),
            Post.early_access_until <= now,
        )
        .values(early_access_until=None, early_access_tier=None)
        .execution_options(synchronize_session=False)
    )
    await db.commit()
    return result.rowcount


async def tier_release_cron_loop(interval_seconds: int = 60) -> None:
    """OQ-5=A: 60s cron loop — schedule_jobs pattern."""
    log.info("tier_release_cron_loop started (interval=%ss)", interval_seconds)
    while True:
        try:
            async with AsyncSessionLocal() as db:
                count = await clear_expired_tier_release_once(db)
                if count:
                    log.info("tier_release: cleared %d post(s)", count)
        except Exception:
            log.exception("tier_release cron sweep failed")
        await asyncio.sleep(interval_seconds)
