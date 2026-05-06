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

from app.core.metrics import cron_rows_processed_total, record_cron_run, tier_release_cleared_rows_total
from app.db.session import AsyncSessionLocal
from app.models.post import Post
from app.services.analytics import capture_event
from app.services.otel_setup import get_tracer

log = logging.getLogger(__name__)

tracer = get_tracer(__name__)


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
            with tracer.start_as_current_span("cron.tier_release") as span:
                with record_cron_run("tier_release"):
                    async with AsyncSessionLocal() as db:
                        count = await clear_expired_tier_release_once(db)
                    span.set_attribute("rows_processed", count)
                    if count:
                        log.info("tier_release: cleared %d post(s)", count)
                        tier_release_cleared_rows_total.inc(count)
                        cron_rows_processed_total.labels(worker="tier_release").inc(count)
                        # G'-4: cron outcome event (system-level, distinct_id="system")
                        capture_event(
                            "system",
                            "cron_run_completed_server",
                            {"worker": "tier_release", "rows_processed": count},
                        )
        except Exception:
            log.exception("tier_release cron sweep failed")
        await asyncio.sleep(interval_seconds)
