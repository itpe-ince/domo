"""Integration tests — Admin PATCH /users/{id} self-modify 차단.

테스트 항목:
  1. admin이 본인 role 변경 시도 → 400 SELF_MODIFY_FORBIDDEN
  2. admin이 본인 status="suspended" 시도 → 400 SELF_MODIFY_FORBIDDEN
  3. 다른 사용자의 role을 admin으로 변경 → 200 (정상) + 토큰 revoke 검증
  4. admin이 다른 user role 변경 → 200 + revoke_user_tokens 호출 확인

전략: endpoint 함수 직접 호출 + AsyncMock DB + MagicMock User.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest

from app.api.admin.users import UserUpdateRequest, update_user
from app.core.errors import ApiError


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_admin(user_id: uuid.UUID | None = None) -> MagicMock:
    u = MagicMock()
    u.id = user_id or uuid.uuid4()
    u.role = "admin"
    u.totp_enabled_at = datetime.now(timezone.utc)
    return u


def _make_user_row(
    user_id: uuid.UUID | None = None,
    role: str = "user",
    status: str = "active",
) -> MagicMock:
    row = MagicMock()
    row.id = user_id or uuid.uuid4()
    row.role = role
    row.status = status
    row.created_at = datetime.now(timezone.utc)
    return row


def _make_db_with_user(target_user: MagicMock) -> AsyncMock:
    """target_user를 DB에서 찾아주는 mock."""
    db = AsyncMock()
    scalar_one_or_none_mock = MagicMock(return_value=target_user)
    execute_result = MagicMock()
    execute_result.scalar_one_or_none = scalar_one_or_none_mock
    db.execute = AsyncMock(return_value=execute_result)
    db.commit = AsyncMock()
    db.add = MagicMock()
    return db


# ── Test 1: admin이 본인 role 변경 → 400 SELF_MODIFY_FORBIDDEN ───────────────


@pytest.mark.asyncio
async def test_admin_cannot_change_own_role():
    """admin이 자신의 role을 변경하려 하면 400 SELF_MODIFY_FORBIDDEN."""
    admin_id = uuid.uuid4()
    admin = _make_admin(user_id=admin_id)

    # target user가 admin 자신
    target = _make_user_row(user_id=admin_id, role="admin")
    db = _make_db_with_user(target)

    body = UserUpdateRequest(role="user")  # 자신의 role을 user로 낮추려 시도

    with pytest.raises(ApiError) as exc_info:
        await update_user(user_id=admin_id, body=body, admin=admin, db=db)

    assert exc_info.value.status_code == 400
    assert exc_info.value.code == "SELF_MODIFY_FORBIDDEN"


# ── Test 2: admin이 본인 status="suspended" → 400 ─────────────────────────────


@pytest.mark.asyncio
async def test_admin_cannot_suspend_self():
    """admin이 자신을 정지하려 하면 400 SELF_MODIFY_FORBIDDEN."""
    admin_id = uuid.uuid4()
    admin = _make_admin(user_id=admin_id)

    target = _make_user_row(user_id=admin_id, role="admin", status="active")
    db = _make_db_with_user(target)

    body = UserUpdateRequest(status="suspended")

    with pytest.raises(ApiError) as exc_info:
        await update_user(user_id=admin_id, body=body, admin=admin, db=db)

    assert exc_info.value.status_code == 400
    assert exc_info.value.code == "SELF_MODIFY_FORBIDDEN"


# ── Test 3: 다른 user의 role을 admin으로 변경 → 200 + revoke 검증 ───────────────


@pytest.mark.asyncio
async def test_admin_can_change_other_user_role_to_admin():
    """admin이 다른 user의 role을 admin으로 올리는 것은 허용. + revoke_user_tokens 호출."""
    admin_id = uuid.uuid4()
    target_id = uuid.uuid4()

    admin = _make_admin(user_id=admin_id)
    target = _make_user_row(user_id=target_id, role="user")
    db = _make_db_with_user(target)

    body = UserUpdateRequest(role="admin")

    with patch("app.api.admin.users.revoke_user_tokens", new=AsyncMock()) as mock_revoke:
        result = await update_user(user_id=target_id, body=body, admin=admin, db=db)
        mock_revoke.assert_awaited_once_with(db, target_id, reason="admin_role_change")

    assert result["data"]["role"] == "admin"


# ── Test 4: admin이 다른 user role 변경 → 200 + revoke_user_tokens 호출 ────────


@pytest.mark.asyncio
async def test_admin_can_change_other_user_role():
    """admin이 다른 user의 role 변경 → 200 정상 + audit log 확인 (revoke 호출)."""
    admin_id = uuid.uuid4()
    target_id = uuid.uuid4()

    admin = _make_admin(user_id=admin_id)
    target = _make_user_row(user_id=target_id, role="artist")
    db = _make_db_with_user(target)

    body = UserUpdateRequest(role="user")

    with patch("app.api.admin.users.revoke_user_tokens", new=AsyncMock()) as mock_revoke:
        result = await update_user(user_id=target_id, body=body, admin=admin, db=db)
        # 토큰 revoke 호출 확인
        mock_revoke.assert_awaited_once()

    assert "data" in result
    assert result["data"]["id"] == str(target_id)
