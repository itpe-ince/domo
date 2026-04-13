"""Background job: publish scheduled posts.

Runs every 60 seconds. Promotes posts with status='scheduled'
and scheduled_at <= NOW() to 'published' or 'pending_review'.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.session import AsyncSessionLocal
from app.models.post import Post

log = logging.getLogger(__name__)


async def publish_scheduled_posts_once(db) -> int:
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(Post)
        .where(Post.status == "scheduled", Post.scheduled_at <= now)
        .options(selectinload(Post.media))
    )
    posts = list(result.scalars().all())
    if not posts:
        return 0

    for post in posts:
        has_visual = any(m.type in ("image", "video") for m in (post.media or []))
        post.status = "pending_review" if has_visual else "published"
        post.scheduled_at = None
        log.info("Published scheduled post %s (status=%s)", post.id, post.status)

    await db.commit()
    return len(posts)


async def schedule_cron_loop(interval_seconds: int = 60) -> None:
    log.info("schedule_cron_loop started (interval=%ss)", interval_seconds)
    while True:
        try:
            async with AsyncSessionLocal() as db:
                count = await publish_scheduled_posts_once(db)
                if count:
                    log.info("Published %d scheduled posts", count)
        except Exception as e:
            log.exception("schedule cron sweep failed: %s", e)
        await asyncio.sleep(interval_seconds)
