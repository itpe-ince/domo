"""Pydantic schemas for audit_logs — Phase 12 B-1a."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

# ── 민감 필드 마스킹 ──────────────────────────────────────────────────────────

_SENSITIVE_KEYS = frozenset(
    {"password_hash", "password", "token", "secret", "recovery_code"}
)


def _mask_sensitive(data: dict | None) -> dict | None:
    """audit_metadata JSONB 내 민감 키를 '***' 로 치환 (1-depth only)."""
    if data is None:
        return None
    return {k: ("***" if k in _SENSITIVE_KEYS else v) for k, v in data.items()}


# ── Response schemas ──────────────────────────────────────────────────────────

class AuditLogItem(BaseModel):
    id: UUID
    actor_id: UUID | None
    actor_role: str | None
    action: str
    target_type: str | None
    target_id: UUID | None
    audit_metadata: dict | None
    ip_address: str | None
    user_agent: str | None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_masked(cls, row: object) -> "AuditLogItem":
        """ORM row → Pydantic model, audit_metadata 민감 필드 마스킹 적용."""
        obj = cls.model_validate(row)
        obj.audit_metadata = _mask_sensitive(obj.audit_metadata)
        return obj


class AuditLogPagination(BaseModel):
    next_cursor: str | None   # ISO-8601 created_at of the last item
    has_more: bool


class AuditLogListResponse(BaseModel):
    data: list[AuditLogItem]
    pagination: AuditLogPagination
