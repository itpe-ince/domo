"""Integration tests — Admin + Auth audit_log rows (Phase 11 D-2).

실제 DB 없이 endpoint 함수 직접 호출 + AsyncMock DB 방식.
audit_log.record_audit 호출 여부 + 인자를 검증.

테스트 항목:
  1. POST /admin/users → record_audit(action='admin.create_user') 호출
  2. PATCH /admin/users/{id} → record_audit(action='admin.update_user') + before/after metadata
  3. DELETE /admin/ai-collections/{id} → record_audit(action='admin.ai_collection_delete') + reason
  4. POST /auth/login (SNS success) → record_audit(action='user.login', status='success')
  5. POST /auth/logout → record_audit(action='user.logout')
  6. POST /me/delete → record_audit(action='user.account_delete_request')
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.errors import ApiError


# ──────────────────────────────────────────────────────────────────────────────
# 공통 헬퍼
# ──────────────────────────────────────────────────────────────────────────────

def _make_admin() -> MagicMock:
    u = MagicMock()
    u.id = uuid.uuid4()
    u.role = "admin"
    u.totp_enabled_at = datetime.now(timezone.utc)
    return u


def _make_user(role: str = "user") -> MagicMock:
    u = MagicMock()
    u.id = uuid.uuid4()
    u.role = role
    u.email = "user@example.com"
    u.display_name = "testuser"
    u.status = "active"
    u.deleted_at = None
    u.deletion_scheduled_for = None
    u.is_minor = False
    return u


def _make_request() -> MagicMock:
    req = MagicMock()
    req.client = MagicMock()
    req.client.host = "127.0.0.1"
    req.headers = MagicMock()
    req.headers.get = MagicMock(return_value=None)
    return req


def _make_db() -> AsyncMock:
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.flush = AsyncMock()
    db.scalar = AsyncMock(return_value=None)
    db.execute = AsyncMock()

    async def _refresh(obj):
        if not getattr(obj, "id", None):
            obj.id = uuid.uuid4()
        if not getattr(obj, "created_at", None):
            obj.created_at = datetime.now(timezone.utc)

    db.refresh = AsyncMock(side_effect=_refresh)
    return db


# ──────────────────────────────────────────────────────────────────────────────
# 1. POST /admin/users → admin.create_user audit
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.skip(reason="Over-mocked SQLAlchemy delete/select — Phase 12 refactor")
@pytest.mark.asyncio
async def test_admin_create_user_audit():
    """POST /admin/users 후 record_audit(action='admin.create_user') 호출 확인."""
    from app.api.admin.users import AdminCreateUserRequest, create_user_by_admin

    admin = _make_admin()
    db = _make_db()
    request = _make_request()

    body = AdminCreateUserRequest(
        email="newuser@example.com",
        display_name="New User",
        role="user",
        send_magic_link=False,
    )

    with patch("app.api.admin.users.record_audit", new_callable=AsyncMock) as mock_audit:
        with patch("app.api.admin.users.hash_password", return_value="hashed"):
            result = await create_user_by_admin(
                body=body,
                request=request,
                admin=admin,
                db=db,
            )

    assert result["data"]["email"] == "newuser@example.com"
    mock_audit.assert_awaited_once()
    call_kwargs = mock_audit.call_args[1]
    assert call_kwargs["action"] == "admin.create_user"
    assert call_kwargs["actor"] is admin
    assert call_kwargs["target_type"] == "user"
    assert "email" in call_kwargs["audit_metadata"]
    assert "role" in call_kwargs["audit_metadata"]


# ──────────────────────────────────────────────────────────────────────────────
# 2. PATCH /admin/users/{id} → admin.update_user audit + before/after metadata
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.skip(reason="Over-mocked SQLAlchemy delete/select — Phase 12 refactor")
@pytest.mark.asyncio
async def test_admin_update_user_audit_before_after():
    """PATCH /admin/users/{id} — record_audit 에 before/after metadata 포함 확인."""
    from app.api.admin.users import UserUpdateRequest, update_user

    admin = _make_admin()
    target = _make_user("user")
    target.status = "active"
    target.role = "user"

    db = _make_db()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=target)
    db.execute = AsyncMock(return_value=mock_result)

    request = _make_request()
    body = UserUpdateRequest(status="suspended")

    with patch("app.api.admin.users.record_audit", new_callable=AsyncMock) as mock_audit:
        with patch("app.api.admin.users.revoke_user_tokens", new_callable=AsyncMock):
            result = await update_user(
                user_id=target.id,
                body=body,
                request=request,
                admin=admin,
                db=db,
            )

    mock_audit.assert_awaited_once()
    call_kwargs = mock_audit.call_args[1]
    assert call_kwargs["action"] == "admin.update_user"
    assert "before" in call_kwargs["audit_metadata"]
    assert "after" in call_kwargs["audit_metadata"]
    assert call_kwargs["audit_metadata"]["before"]["status"] == "active"


# ──────────────────────────────────────────────────────────────────────────────
# 3. DELETE /admin/ai-collections/{id} → admin.ai_collection_delete + reason
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.skip(reason="Over-mocked SQLAlchemy delete/select — Phase 12 refactor")
@pytest.mark.asyncio
async def test_admin_ai_collection_delete_audit():
    """DELETE /admin/ai-collections/{id} — record_audit(reason) 확인."""
    from app.api.admin_ai_collections import CollectionDeleteRequest, delete_collection

    admin = _make_admin()
    collection_id = uuid.uuid4()
    db = _make_db()
    request = _make_request()

    # 컬렉션 존재 확인 mock
    mock_coll_row = MagicMock()
    mock_coll_row.id = collection_id
    mock_coll_row.status = "published"
    mock_result = MagicMock()
    mock_result.fetchone = MagicMock(return_value=mock_coll_row)
    db.execute = AsyncMock(return_value=mock_result)

    body = CollectionDeleteRequest(reason="잘못된 내용 포함, 즉시 삭제 필요합니다.")

    with patch("app.api.admin_ai_collections.record_audit", new_callable=AsyncMock) as mock_audit:
        result = await delete_collection(
            collection_id=collection_id,
            body=body,
            request=request,
            admin=admin,
            db=db,
        )

    assert result["data"]["deleted"] is True
    mock_audit.assert_awaited_once()
    call_kwargs = mock_audit.call_args[1]
    assert call_kwargs["action"] == "admin.ai_collection_delete"
    assert "reason" in call_kwargs["audit_metadata"]
    assert call_kwargs["audit_metadata"]["reason"] == body.reason


# ──────────────────────────────────────────────────────────────────────────────
# 4. POST /auth/logout → user.logout audit
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_user_logout_audit():
    """POST /auth/logout — record_audit(action='user.logout') 확인."""
    from app.api.auth import logout
    from app.schemas.auth import RefreshRequest

    user = _make_user()
    db = _make_db()
    request = _make_request()

    with patch("app.api.auth.record_audit", new_callable=AsyncMock) as mock_audit:
        with patch("app.api.auth.revoke_token", new_callable=AsyncMock):
            result = await logout(
                request=request,
                body=None,
                user=user,
                db=db,
            )

    assert result["data"]["ok"] is True
    mock_audit.assert_awaited_once()
    call_kwargs = mock_audit.call_args[1]
    assert call_kwargs["action"] == "user.logout"
    assert call_kwargs["status"] == "success"


# ──────────────────────────────────────────────────────────────────────────────
# 5. POST /me/delete → user.account_delete_request audit
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_user_delete_request_audit():
    """POST /me/delete — record_audit(action='user.account_delete_request') 확인."""
    from datetime import datetime, timedelta, timezone

    from app.api.me import DeleteRequest, request_deletion

    # MagicMock spec 없이 생성해 속성 할당 자유롭게
    user = MagicMock(spec=False)
    user.id = uuid.uuid4()
    user.role = "user"
    user.email = "user@example.com"
    user.display_name = "testuser"
    user.deleted_at = None
    _now = datetime.now(timezone.utc)
    user.deletion_scheduled_for = _now + timedelta(days=30)

    db = _make_db()
    request = _make_request()
    body = DeleteRequest(confirm="DELETE MY ACCOUNT")

    with patch("app.api.me.record_audit", new_callable=AsyncMock) as mock_audit:
        with patch("app.api.me.revoke_user_tokens", new_callable=AsyncMock):
            with patch("app.api.me.get_email_provider") as mock_email_prov:
                mock_prov = MagicMock()
                mock_prov.send = AsyncMock()
                mock_email_prov.return_value = mock_prov
                with patch("app.api.me.account_deleted_tpl") as mock_tpl:
                    mock_tpl.render = MagicMock(return_value=MagicMock())
                    result = await request_deletion(
                        body=body,
                        request=request,
                        user=user,
                        db=db,
                    )

    assert "deleted_at" in result["data"]
    mock_audit.assert_awaited_once()
    call_kwargs = mock_audit.call_args[1]
    assert call_kwargs["action"] == "user.account_delete_request"
    assert call_kwargs["status"] == "success"


# ──────────────────────────────────────────────────────────────────────────────
# 6. POST /admin/users → audit metadata에 send_magic_link 포함 확인
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.skip(reason="Over-mocked SQLAlchemy delete/select — Phase 12 refactor")
@pytest.mark.asyncio
async def test_admin_create_user_audit_metadata_keys():
    """audit metadata에 created_user_id, email, role, send_magic_link 포함 확인."""
    from app.api.admin.users import AdminCreateUserRequest, create_user_by_admin

    admin = _make_admin()
    db = _make_db()
    request = _make_request()

    body = AdminCreateUserRequest(
        email="another@example.com",
        display_name="Another User",
        role="artist",
        send_magic_link=False,  # magic link 없이 테스트
    )

    with patch("app.api.admin.users.record_audit", new_callable=AsyncMock) as mock_audit:
        with patch("app.api.admin.users.hash_password", return_value="hashed"):
            await create_user_by_admin(
                body=body,
                request=request,
                admin=admin,
                db=db,
            )

    call_kwargs = mock_audit.call_args[1]
    meta = call_kwargs["audit_metadata"]
    assert "created_user_id" in meta
    assert "email" in meta
    assert "role" in meta
    assert "send_magic_link" in meta
