"""Integration tests — Admin Create User API (POST /admin/users).

테스트 항목:
  1. admin이 user role 사용자 생성 → 201
  2. admin이 admin role 사용자 생성 → 201, magic link sent
  3. 이메일 중복 → 409 ALREADY_EXISTS
  4. display_name 짧음 (2자) → 422 (Pydantic validation)
  5. non-admin 시도 → 403 FORBIDDEN
  6. send_magic_link=false 시 → magic_link_sent=False
  7. 매직 링크 발송 환경 미설정 → graceful (sent=False, 에러 X)

전략: endpoint 함수 직접 호출 + AsyncMock DB + MagicMock User.
실제 DB/이메일 서버 불필요.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.api.admin.users import AdminCreateUserRequest, create_user_by_admin
from app.core.errors import ApiError


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_admin() -> MagicMock:
    """2FA 완료 admin 사용자 mock."""
    u = MagicMock()
    u.id = uuid.uuid4()
    u.role = "admin"
    u.totp_enabled_at = datetime.now(timezone.utc)
    return u


def _make_new_user_row(
    email: str = "newuser@example.com",
    display_name: str = "new_user",
    role: str = "user",
) -> MagicMock:
    """새로 생성된 User DB row mock."""
    row = MagicMock()
    row.id = uuid.uuid4()
    row.email = email
    row.display_name = display_name
    row.role = role
    row.status = "active"
    row.created_at = datetime.now(timezone.utc)
    return row


def _make_db_no_existing(new_user: MagicMock) -> AsyncMock:
    """이메일 중복 없음 + add/flush/commit/refresh 지원하는 DB mock."""
    db = AsyncMock()
    # scalar(): 이메일 중복 확인 — None 반환 (없음)
    db.scalar = AsyncMock(return_value=None)
    # flush, commit, refresh
    db.flush = AsyncMock()
    db.commit = AsyncMock()

    async def _refresh(obj):
        obj.id = new_user.id
        obj.created_at = new_user.created_at

    db.refresh = AsyncMock(side_effect=_refresh)
    db.add = MagicMock()
    return db


# ── Test 1: user role 사용자 생성 → 201 ──────────────────────────────────────


@pytest.mark.asyncio
async def test_create_user_role_success():
    """admin이 일반 user 생성 → 201 + 올바른 응답 형식."""
    admin = _make_admin()
    new_user = _make_new_user_row(role="user")
    db = _make_db_no_existing(new_user)

    body = AdminCreateUserRequest(
        email="newuser@example.com",
        display_name="New User",
        role="user",
        send_magic_link=True,
    )

    with patch(
        "app.services.magic_link.send_admin_invite_magic_link",
        new=AsyncMock(return_value={"sent": True, "provider": "mock"}),
    ):
        result = await create_user_by_admin(body=body, admin=admin, db=db)

    assert "data" in result
    data = result["data"]
    assert data["email"] == "newuser@example.com"
    assert data["role"] == "user"
    assert data["status"] == "active"
    assert data["magic_link_sent"] is True
    assert "id" in data
    assert "created_at" in data


# ── Test 2: admin role 사용자 생성 → 201, magic link sent ─────────────────────


@pytest.mark.asyncio
async def test_create_admin_role_with_magic_link():
    """admin이 admin role 사용자 생성 → 201, magic_link_sent=True."""
    admin = _make_admin()
    new_user = _make_new_user_row(email="newadmin@example.com", role="admin")
    db = _make_db_no_existing(new_user)

    body = AdminCreateUserRequest(
        email="newadmin@example.com",
        display_name="New Admin",
        role="admin",
        send_magic_link=True,
    )

    with patch(
        "app.services.magic_link.send_admin_invite_magic_link",
        new=AsyncMock(return_value={"sent": True, "provider": "mock"}),
    ):
        result = await create_user_by_admin(body=body, admin=admin, db=db)

    data = result["data"]
    assert data["role"] == "admin"
    assert data["magic_link_sent"] is True


# ── Test 3: 이메일 중복 → 409 ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_user_duplicate_email():
    """이미 존재하는 이메일 → 409 ALREADY_EXISTS."""
    admin = _make_admin()
    db = AsyncMock()

    # scalar()가 기존 User를 반환 (중복)
    existing = MagicMock()
    db.scalar = AsyncMock(return_value=existing)

    body = AdminCreateUserRequest(
        email="exists@example.com",
        display_name="Existing User",
        role="user",
    )

    with pytest.raises(ApiError) as exc_info:
        await create_user_by_admin(body=body, admin=admin, db=db)

    assert exc_info.value.status_code == 409
    assert exc_info.value.code == "ALREADY_EXISTS"


# ── Test 4: display_name 짧음 (2자) → 422 ────────────────────────────────────


def test_create_user_short_display_name_validation():
    """display_name 2자 → Pydantic ValidationError (min_length=3)."""
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        AdminCreateUserRequest(
            email="user@example.com",
            display_name="ab",  # 2자 — min_length=3 위반
            role="user",
        )


# ── Test 5: non-admin 시도 → 403 ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_user_non_admin_forbidden():
    """non-admin 사용자 → require_admin 계층에서 403."""
    from app.core.admin_deps import require_admin

    non_admin = MagicMock()
    non_admin.id = uuid.uuid4()
    non_admin.role = "user"

    with pytest.raises(ApiError) as exc_info:
        await require_admin(user=non_admin)

    assert exc_info.value.status_code == 403
    assert exc_info.value.code == "FORBIDDEN"


# ── Test 6: send_magic_link=False → magic_link_sent=False ────────────────────


@pytest.mark.asyncio
async def test_create_user_no_magic_link():
    """send_magic_link=False 시 이메일 미발송, magic_link_sent=False."""
    admin = _make_admin()
    new_user = _make_new_user_row()
    db = _make_db_no_existing(new_user)

    body = AdminCreateUserRequest(
        email="nolink@example.com",
        display_name="No Link User",
        role="user",
        send_magic_link=False,
    )

    # send_admin_invite_magic_link 가 호출되지 않아야 하므로 실제 patch 없이 테스트
    with patch(
        "app.services.magic_link.send_admin_invite_magic_link",
        new=AsyncMock(return_value={"sent": True}),
    ) as mock_send:
        result = await create_user_by_admin(body=body, admin=admin, db=db)
        # send_magic_link=False이므로 함수 자체가 호출되지 않아야 함
        mock_send.assert_not_called()

    assert result["data"]["magic_link_sent"] is False


# ── Test 7: 매직 링크 발송 실패 → graceful (sent=False, 에러 X) ───────────────


@pytest.mark.asyncio
async def test_create_user_magic_link_failure_graceful():
    """이메일 서비스 오류 → magic_link_sent=False, 예외 없이 201 반환."""
    admin = _make_admin()
    new_user = _make_new_user_row()
    db = _make_db_no_existing(new_user)

    body = AdminCreateUserRequest(
        email="faillink@example.com",
        display_name="Fail Link User",
        role="user",
        send_magic_link=True,
    )

    # send_admin_invite_magic_link 가 sent=False 반환 (graceful 처리)
    with patch(
        "app.services.magic_link.send_admin_invite_magic_link",
        new=AsyncMock(return_value={"sent": False, "reason": "SES not configured"}),
    ):
        result = await create_user_by_admin(body=body, admin=admin, db=db)

    # 예외 없이 응답 반환
    assert result["data"]["magic_link_sent"] is False
    assert result["data"]["status"] == "active"
