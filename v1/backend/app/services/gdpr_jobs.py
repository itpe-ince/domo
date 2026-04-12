"""GDPR hard delete cron (Phase 4 M3).

Reference: phase4.design.md §6.7

After 30-day grace period, anonymize expired users.
Posts/comments are retained but author info scrubbed.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.models.auth_token import RefreshToken
from app.models.user import User

log = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def hard_delete_pending_users(db: AsyncSession) -> int:
    """Anonymize users whose grace period has expired."""
    result = await db.execute(
        select(User).where(
            User.deletion_scheduled_for.is_not(None),
            User.deletion_scheduled_for < _now(),
        )
    )
    expired = list(result.scalars().all())
    count = 0

    for user in expired:
        # Anonymize (preserve FK integrity)
        user.email = f"anon_{user.id}@deleted.local"
        user.display_name = "Anonymous"
        user.avatar_url = None
        user.bio = None
        user.birth_date = None
        user.country_code = None
        user.sns_provider = None
        user.sns_id = None
        user.status = "deleted"

        # Delete all refresh tokens for this user
        from sqlalchemy import delete

        await db.execute(delete(RefreshToken).where(RefreshToken.user_id == user.id))
        count += 1

    if count:
        await db.commit()
        log.info("GDPR hard_delete_pending_users: anonymized %d users", count)

    return count


async def gdpr_cron_loop(interval_seconds: int = 3600) -> None:
    """Background task — runs every hour."""
    log.info("gdpr_cron_loop started (interval=%ss)", interval_seconds)
    while True:
        try:
            async with AsyncSessionLocal() as db:
                await hard_delete_pending_users(db)
        except Exception as e:  # noqa: BLE001
            log.exception("gdpr cron sweep failed: %s", e)
        await asyncio.sleep(interval_seconds)
