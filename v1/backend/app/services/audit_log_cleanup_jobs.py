"""audit_log retention cleanup job — Phase 11 D-2.

Deletes audit_logs rows with created_at < now() - AUDIT_LOG_RETENTION_DAYS days.
Default: 365 days (1년).
Runs daily via the lifespan cron registered in app/main.py (24th worker).

Pattern follows draft_cleanup_jobs.py.
"""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal

log = logging.getLogger(__name__)

_RETENTION_DAYS = int(os.getenv("AUDIT_LOG_RETENTION_DAYS", "365"))


async def cleanup_old_audit_logs(db: AsyncSession) -> int:
    """AUDIT_LOG_RETENTION_DAYS 이전 audit_logs 행 삭제.

    Returns: 삭제된 행 수.
    """
    from app.models.audit_log import AuditLog  # 순환 import 방지

    cutoff = datetime.now(timezone.utc) - timedelta(days=_RETENTION_DAYS)
    result = await db.execute(
        delete(AuditLog).where(AuditLog.created_at < cutoff)
    )
    deleted = result.rowcount or 0
    if deleted:
        await db.commit()
        log.info(
            "audit_log_cleanup: deleted %d rows older than %d days",
            deleted,
            _RETENTION_DAYS,
        )
    return deleted


async def audit_log_cleanup_cron_loop(interval_seconds: int = 86400) -> None:
    """Background task — 일 1회 실행 (03:00 UTC 기준, interval=86400s)."""
    log.info(
        "audit_log_cleanup_cron_loop started (interval=%ss, retention=%dd)",
        interval_seconds,
        _RETENTION_DAYS,
    )
    while True:
        try:
            async with AsyncSessionLocal() as db:
                await cleanup_old_audit_logs(db)
        except Exception as e:  # noqa: BLE001
            log.exception("audit_log cleanup cron failed: %s", e)
        await asyncio.sleep(interval_seconds)
