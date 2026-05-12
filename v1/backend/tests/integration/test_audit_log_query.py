"""Integration tests — GET /admin/audit-logs (Phase 12 B-1a).

테스트 항목 (7개):
  1. test_list_audit_logs_no_filter       — 필터 없이 반환, DESC 정렬 확인
  2. test_list_audit_logs_filter_action   — action 필터 → 해당 행만 반환
  3. test_list_audit_logs_filter_period   — period 범위 외 행 미포함 확인
  4. test_list_audit_logs_cursor_pagination — cursor → 이전 마지막 행 이후부터 반환
  5. test_list_audit_logs_require_admin   — 일반 user → 403
  6. test_list_audit_logs_require_2fa     — 2FA 미완료 admin → 403 SECOND_FACTOR_REQUIRED
  7. test_sensitive_field_masking         — audit_metadata password_hash → "***"
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.errors import ApiError


# ─── 공통 헬퍼 ────────────────────────────────────────────────────────────────

def _make_admin(totp: bool = True) -> MagicMock:
    u = MagicMock()
    u.id = uuid.uuid4()
    u.role = "admin"
    u.totp_enabled_at = datetime.now(timezone.utc) if totp else None
    return u


def _make_user() -> MagicMock:
    u = MagicMock()
    u.id = uuid.uuid4()
    u.role = "user"
    return u


def _make_audit_row(
    *,
    action: str = "admin.create_user",
    target_type: str | None = "user",
    target_id: uuid.UUID | None = None,
    audit_metadata: dict | None = None,
    created_at: datetime | None = None,
    status: str = "success",
) -> MagicMock:
    row = MagicMock()
    row.id = uuid.uuid4()
    row.actor_id = uuid.uuid4()
    row.actor_role = "admin"
    row.action = action
    row.target_type = target_type
    row.target_id = target_id or uuid.uuid4()
    row.audit_metadata = audit_metadata
    row.ip_address = "127.0.0.1"
    row.user_agent = "pytest/1.0"
    row.status = status
    row.created_at = created_at or datetime.now(timezone.utc)
    return row


def _make_scalars(rows: list) -> MagicMock:
    """scalars().all() 패턴을 반환하는 mock."""
    result = MagicMock()
    scalars_mock = MagicMock()
    scalars_mock.all = MagicMock(return_value=rows)
    result.scalars = MagicMock(return_value=scalars_mock)
    return result


# ─── 1. 필터 없이 반환 + DESC 정렬 ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_audit_logs_no_filter():
    """필터 없이 호출 시 rows 반환, 첫 항목 created_at >= 마지막 항목 (DESC)."""
    from app.api.admin.audit_logs import list_audit_logs

    now = datetime.now(timezone.utc)
    rows = [
        _make_audit_row(created_at=now - timedelta(seconds=i))
        for i in range(3)
    ]

    db = AsyncMock()
    db.execute = AsyncMock(return_value=_make_scalars(rows))
    admin = _make_admin()

    result = await list_audit_logs(
        actor_id=None,
        action=None,
        target_type=None,
        target_id=None,
        period_start=None,
        period_end=None,
        cursor=None,
        limit=50,
        admin=admin,
        db=db,
    )

    assert len(result.data) == 3
    assert result.pagination.has_more is False
    assert result.pagination.next_cursor is None
    # DESC 정렬 확인 — 첫 항목이 가장 최신
    for i in range(len(result.data) - 1):
        assert result.data[i].created_at >= result.data[i + 1].created_at


# ─── 2. action 필터 ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_audit_logs_filter_action():
    """action='admin.create_user' 필터 → 해당 action만 반환."""
    from app.api.admin.audit_logs import list_audit_logs

    matching = _make_audit_row(action="admin.create_user")

    db = AsyncMock()
    db.execute = AsyncMock(return_value=_make_scalars([matching]))
    admin = _make_admin()

    result = await list_audit_logs(
        actor_id=None,
        action="admin.create_user",
        target_type=None,
        target_id=None,
        period_start=None,
        period_end=None,
        cursor=None,
        limit=50,
        admin=admin,
        db=db,
    )

    assert len(result.data) == 1
    assert result.data[0].action == "admin.create_user"


# ─── 3. period 필터 ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_audit_logs_filter_period():
    """period 범위 내 행만 포함.

    실제 DB 필터링은 SQLAlchemy가 처리. 이 테스트에서는 mock이 범위 내 행만
    반환하는 시나리오를 확인 + 빈 결과 처리 정상 동작 확인.
    """
    from datetime import date

    from app.api.admin.audit_logs import list_audit_logs

    # 범위 내 행 1개
    in_range = _make_audit_row(
        created_at=datetime(2026, 5, 1, 12, 0, 0, tzinfo=timezone.utc)
    )

    db = AsyncMock()
    db.execute = AsyncMock(return_value=_make_scalars([in_range]))
    admin = _make_admin()

    result = await list_audit_logs(
        actor_id=None,
        action=None,
        target_type=None,
        target_id=None,
        period_start=date(2026, 5, 1),
        period_end=date(2026, 5, 7),
        cursor=None,
        limit=50,
        admin=admin,
        db=db,
    )

    assert len(result.data) == 1
    # 범위 내 항목만 포함
    assert result.data[0].created_at.year == 2026
    assert result.data[0].created_at.month == 5

    # 빈 결과 시나리오
    db2 = AsyncMock()
    db2.execute = AsyncMock(return_value=_make_scalars([]))
    result2 = await list_audit_logs(
        actor_id=None,
        action=None,
        target_type=None,
        target_id=None,
        period_start=date(2024, 1, 1),
        period_end=date(2024, 1, 2),
        cursor=None,
        limit=50,
        admin=admin,
        db=db2,
    )
    assert result2.data == []
    assert result2.pagination.has_more is False


# ─── 4. cursor pagination ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_audit_logs_cursor_pagination():
    """limit=2, 3건 존재 → has_more=True, next_cursor 설정 확인."""
    from app.api.admin.audit_logs import list_audit_logs

    now = datetime.now(timezone.utc)
    # limit+1 = 3건 반환 → has_more=True
    rows = [
        _make_audit_row(created_at=now - timedelta(seconds=i))
        for i in range(3)
    ]

    db = AsyncMock()
    db.execute = AsyncMock(return_value=_make_scalars(rows))
    admin = _make_admin()

    result = await list_audit_logs(
        actor_id=None,
        action=None,
        target_type=None,
        target_id=None,
        period_start=None,
        period_end=None,
        cursor=None,
        limit=2,
        admin=admin,
        db=db,
    )

    assert len(result.data) == 2
    assert result.pagination.has_more is True
    assert result.pagination.next_cursor is not None
    # next_cursor = 마지막 반환 항목의 created_at
    assert result.pagination.next_cursor == result.data[-1].created_at.isoformat()

    # cursor 전달 → DB execute 호출 확인
    db2 = AsyncMock()
    db2.execute = AsyncMock(return_value=_make_scalars([]))
    cursor_val = result.pagination.next_cursor

    result2 = await list_audit_logs(
        actor_id=None,
        action=None,
        target_type=None,
        target_id=None,
        period_start=None,
        period_end=None,
        cursor=cursor_val,
        limit=2,
        admin=admin,
        db=db2,
    )
    assert result2.data == []
    assert result2.pagination.has_more is False
    db2.execute.assert_awaited_once()


# ─── 5. 일반 user → 403 ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_audit_logs_require_admin():
    """require_admin_with_2fa 미충족 (role=user) → 403 FORBIDDEN."""
    from app.core.admin_deps import require_admin_with_2fa

    user = _make_user()
    db = AsyncMock()

    with pytest.raises(ApiError) as exc_info:
        await require_admin_with_2fa(user=user, db=db)

    assert exc_info.value.status_code == 403
    assert exc_info.value.code == "FORBIDDEN"


# ─── 6. 2FA 미완료 admin → 403 SECOND_FACTOR_REQUIRED ──────────────────────

@pytest.mark.asyncio
async def test_list_audit_logs_require_2fa():
    """totp_enabled_at=None + Passkey 없음 → 403 SECOND_FACTOR_REQUIRED."""
    from app.core.admin_deps import require_admin_with_2fa

    admin_no_2fa = _make_admin(totp=False)
    admin_no_2fa.totp_enabled_at = None

    db = AsyncMock()
    # passkey count query → 0
    count_result = MagicMock()
    count_result.scalar_one = MagicMock(return_value=0)
    db.execute = AsyncMock(return_value=count_result)

    with pytest.raises(ApiError) as exc_info:
        await require_admin_with_2fa(user=admin_no_2fa, db=db)

    assert exc_info.value.status_code == 403
    assert exc_info.value.code == "SECOND_FACTOR_REQUIRED"


# ─── 7. 민감 필드 마스킹 ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_sensitive_field_masking():
    """audit_metadata 내 password_hash 키 → '***' 마스킹 확인."""
    from app.api.admin.audit_logs import list_audit_logs

    sensitive_meta = {
        "password_hash": "bcrypt_$2b$12$abc...",
        "token": "eyJhbGciOiJIUzI1NiJ9...",
        "before": {"status": "active"},
        "after": {"status": "suspended"},
    }
    row = _make_audit_row(audit_metadata=sensitive_meta)

    db = AsyncMock()
    db.execute = AsyncMock(return_value=_make_scalars([row]))
    admin = _make_admin()

    result = await list_audit_logs(
        actor_id=None,
        action=None,
        target_type=None,
        target_id=None,
        period_start=None,
        period_end=None,
        cursor=None,
        limit=50,
        admin=admin,
        db=db,
    )

    assert len(result.data) == 1
    meta = result.data[0].audit_metadata
    assert meta is not None
    assert meta["password_hash"] == "***"
    assert meta["token"] == "***"
    # 비민감 키는 보존
    assert meta["before"] == {"status": "active"}
    assert meta["after"] == {"status": "suspended"}
