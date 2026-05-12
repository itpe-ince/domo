"""Admin: GET /admin/audit-logs — Phase 12 B-1a."""
from __future__ import annotations

from datetime import date, datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.admin_deps import require_admin_with_2fa
from app.db.session import get_db
from app.models.audit_log import AuditLog
from app.models.user import User
from app.schemas.audit_log import AuditLogItem, AuditLogListResponse, AuditLogPagination

router = APIRouter(tags=["admin"])

_MAX_LIMIT = 200


@router.get("/audit-logs", response_model=AuditLogListResponse)
async def list_audit_logs(
    actor_id: UUID | None = None,
    action: str | None = None,
    target_type: str | None = None,
    target_id: UUID | None = None,
    period_start: date | None = None,
    period_end: date | None = None,
    cursor: str | None = None,   # created_at ISO-8601 (DESC keyset)
    limit: int = Query(default=50, ge=1, le=_MAX_LIMIT),
    admin: User = Depends(require_admin_with_2fa),
    db: AsyncSession = Depends(get_db),
) -> AuditLogListResponse:
    """Audit logs 페이지네이션 조회 (cursor-based, DESC).

    - cursor: created_at ISO-8601. 지정 시 해당 시각 이전 행만 반환 (keyset pagination).
    - limit: 1~200, 기본 50.
    - 필터: actor_id / action / target_type / target_id / period_start~period_end.
    - 인덱스: ix_audit_logs_created / ix_audit_logs_actor / ix_audit_logs_action / ix_audit_logs_target 활용.
    """
    # 조건 목록 조합
    filters = []

    if cursor:
        try:
            cursor_dt = datetime.fromisoformat(cursor)
            if cursor_dt.tzinfo is None:
                cursor_dt = cursor_dt.replace(tzinfo=timezone.utc)
        except ValueError:
            # 잘못된 cursor → 첫 페이지 반환
            cursor_dt = None
        if cursor_dt is not None:
            filters.append(AuditLog.created_at < cursor_dt)

    if actor_id is not None:
        filters.append(AuditLog.actor_id == actor_id)

    if action is not None:
        filters.append(AuditLog.action == action)

    if target_type is not None:
        filters.append(AuditLog.target_type == target_type)

    if target_id is not None:
        filters.append(AuditLog.target_id == target_id)

    if period_start is not None:
        start_dt = datetime(period_start.year, period_start.month, period_start.day, tzinfo=timezone.utc)
        filters.append(AuditLog.created_at >= start_dt)

    if period_end is not None:
        # period_end 포함 (하루 끝까지)
        end_dt = datetime(period_end.year, period_end.month, period_end.day, 23, 59, 59, tzinfo=timezone.utc)
        filters.append(AuditLog.created_at <= end_dt)

    # limit+1 조회 → has_more 판별
    fetch_limit = limit + 1

    stmt = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(fetch_limit)
    if filters:
        stmt = stmt.where(and_(*filters))

    result = await db.execute(stmt)
    rows = list(result.scalars().all())

    has_more = len(rows) == fetch_limit
    if has_more:
        rows = rows[:limit]

    items = [AuditLogItem.from_orm_masked(row) for row in rows]

    next_cursor: str | None = None
    if has_more and items:
        # cursor = 마지막 반환 항목의 created_at ISO
        next_cursor = items[-1].created_at.isoformat()

    return AuditLogListResponse(
        data=items,
        pagination=AuditLogPagination(next_cursor=next_cursor, has_more=has_more),
    )
