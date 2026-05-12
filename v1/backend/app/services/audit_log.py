"""Audit log service — Phase 11 D-2.

record_audit(): admin endpoint 전체 + user sensitive action 감사 기록.
실패해도 main flow를 차단하지 않는다 (graceful).
"""
from __future__ import annotations

import logging
from uuid import UUID

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

log = logging.getLogger(__name__)


async def record_audit(
    db: AsyncSession,
    *,
    actor,  # User | None — 순환 import 방지를 위해 타입 미지정
    action: str,
    target_type: str | None = None,
    target_id: UUID | None = None,
    metadata: dict | None = None,
    request: Request | None = None,
    status: str = "success",
) -> None:
    """비동기 audit log 기록.

    실패해도 main flow를 차단하지 않는다 (graceful).
    Request 객체가 전달되면 IP / User-Agent를 자동 추출한다.

    Args:
        db: AsyncSession — 전용 세션 또는 기존 세션 사용 가능.
        actor: User 또는 None (system/anonymous 행위 시).
        action: 'domain.verb' 형식 (예: 'admin.create_user', 'user.login').
        target_type: 영향받은 객체 유형 (예: 'user', 'ai_collection').
        target_id: 영향받은 객체 UUID.
        metadata: 추가 컨텍스트 dict (개인정보 최소화).
        request: FastAPI Request (IP / UA 자동 추출).
        status: 'success' | 'failure' | 'error'.
    """
    try:
        ip_address: str | None = None
        user_agent: str | None = None

        if request is not None:
            forwarded_for = request.headers.get("x-forwarded-for")
            ip_address = (
                forwarded_for.split(",")[0].strip()
                if forwarded_for
                else (request.client.host if request.client else None)
            )
            user_agent = request.headers.get("user-agent")

        # 순환 import 방지 — 함수 내부에서 lazy import
        from app.models.audit_log import AuditLog

        actor_id = getattr(actor, "id", None)
        actor_role = getattr(actor, "role", None) if actor is not None else "system"

        row = AuditLog(
            actor_id=actor_id,
            actor_role=actor_role,
            action=action,
            target_type=target_type,
            target_id=target_id,
            audit_metadata=metadata,
            ip_address=ip_address,
            user_agent=user_agent,
            status=status,
        )
        db.add(row)
        await db.commit()

    except Exception as exc:  # noqa: BLE001
        log.warning("record_audit failed (action=%s): %s", action, exc)
