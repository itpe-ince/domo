"""Shared moderation helpers (3-strike warning, suspension).

Used by:
- app/services/auction_jobs.py (auction_unpaid expiration)
- app/api/admin.py (resolve_report)
"""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.moderation import Warning
from app.models.notification import Notification
from app.models.user import User
from app.services.settings import get_setting


async def issue_warning(
    db: AsyncSession,
    user_id: UUID,
    reason: str,
    *,
    issued_by: UUID | None = None,
    report_id: UUID | None = None,
) -> Warning:
    """Issue a formal warning row, increment counter, suspend if threshold crossed.

    Caller is responsible for committing the transaction.
    Sends notification to the affected user.
    """
    warning = Warning(
        user_id=user_id,
        reason=reason,
        report_id=report_id,
        issued_by=issued_by,
        is_active=True,
        appealed=False,
    )
    db.add(warning)
    await db.flush()

    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if user:
        user.warning_count = (user.warning_count or 0) + 1

        threshold_setting = await get_setting(db, "warning_threshold")
        threshold = int(threshold_setting["count"]) if threshold_setting else 3

        if user.warning_count >= threshold and user.status != "suspended":
            user.status = "suspended"
            db.add(
                Notification(
                    user_id=user_id,
                    type="account_suspended",
                    title="계정이 정지되었습니다",
                    body=f"누적 경고 {user.warning_count}회로 계정이 정지되었습니다. 이의 제기가 가능합니다.",
                    link="/warnings",
                )
            )

    db.add(
        Notification(
            user_id=user_id,
            type="warning_issued",
            title="경고 발급",
            body=reason,
            link="/warnings",
        )
    )
    return warning


async def cancel_warning(
    db: AsyncSession,
    warning: Warning,
    *,
    cancelled_by: UUID,
) -> None:
    """Cancel an active warning (admin approves appeal).

    Decrements user.warning_count and reactivates if previously suspended.
    """
    if not warning.is_active:
        return
    warning.is_active = False
    warning.cancelled_at = datetime.now(timezone.utc)

    user_result = await db.execute(select(User).where(User.id == warning.user_id))
    user = user_result.scalar_one_or_none()
    if user:
        user.warning_count = max(0, (user.warning_count or 0) - 1)
        threshold_setting = await get_setting(db, "warning_threshold")
        threshold = int(threshold_setting["count"]) if threshold_setting else 3
        if user.status == "suspended" and user.warning_count < threshold:
            user.status = "active"
            db.add(
                Notification(
                    user_id=user.id,
                    type="account_reactivated",
                    title="계정 정지 해제",
                    body="이의 제기가 승인되어 계정이 다시 활성화되었습니다.",
                )
            )

    db.add(
        Notification(
            user_id=warning.user_id,
            type="warning_cancelled",
            title="경고 취소",
            body="이의 제기가 승인되어 경고가 취소되었습니다.",
            link="/warnings",
        )
    )
