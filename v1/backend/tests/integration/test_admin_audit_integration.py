"""Integration tests — Admin + Auth audit_log rows (Phase 11 D-2).

Phase 12 A-1 refactor:
  - 카테고리 2: AsyncMock DB → real_db_session (testcontainers)
  - record_audit mock 유지 (commit 충돌 방지) + 실제 User INSERT/SELECT 검증
  - @pytest.mark.skip 제거

테스트 항목:
  1. POST /admin/users → record_audit(action='admin.create_user') 호출
  2. PATCH /admin/users/{id} → record_audit(action='admin.update_user') + before/after metadata
  3. DELETE /admin/ai-collections/{id} → record_audit(action='admin.ai_collection_delete') + reason
  4. POST /auth/logout → record_audit(action='user.logout')
  5. POST /me/delete → record_audit(action='user.account_delete_request')
  6. POST /admin/users → audit metadata에 created_user_id, email, role, send_magic_link 포함
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

def _make_admin_mock() -> MagicMock:
    """MagicMock admin user (DB row 불필요한 상황에서 사용)."""
    u = MagicMock()
    u.id = uuid.uuid4()
    u.role = "admin"
    u.totp_enabled_at = datetime.now(timezone.utc)
    return u


def _make_user_mock(role: str = "user") -> MagicMock:
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


# ──────────────────────────────────────────────────────────────────────────────
# 1. POST /admin/users → admin.create_user audit
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_admin_create_user_audit(real_db_session):
    """POST /admin/users 후 record_audit(action='admin.create_user') 호출 확인.

    real_db_session: 실제 DB에서 User INSERT + SELECT 수행 (email 중복 검사 포함).
    record_audit: mock — commit() 충돌 없이 호출 인자만 검증.
    """
    from app.api.admin.users import AdminCreateUserRequest, create_user_by_admin

    # admin은 mock (DB row 불필요)
    admin = _make_admin_mock()
    request = _make_request()

    body = AdminCreateUserRequest(
        email="newuser_audit_test@example.com",
        display_name="New User",
        role="user",
        send_magic_link=False,
    )

    with patch("app.api.admin.users.record_audit", new_callable=AsyncMock) as mock_audit:
        with patch("app.api.admin.users.hash_password", return_value="hashed_pw_123"):
            # real_db_session은 BEGIN 상태이므로 내부 commit/refresh 패치
            with patch.object(real_db_session, "commit", new_callable=AsyncMock):
                with patch.object(real_db_session, "refresh", new_callable=AsyncMock) as mock_refresh:
                    # refresh 시 id 및 created_at 자동 설정
                    import uuid as _uuid
                    from datetime import datetime, timezone as _tz
                    async def _side_refresh(obj):
                        if not getattr(obj, "id", None):
                            obj.id = _uuid.uuid4()
                        if not getattr(obj, "created_at", None):
                            obj.created_at = datetime.now(_tz.utc)
                    mock_refresh.side_effect = _side_refresh
                    result = await create_user_by_admin(
                        body=body,
                        request=request,
                        admin=admin,
                        db=real_db_session,
                    )

    assert result["data"]["email"] == "newuser_audit_test@example.com"
    mock_audit.assert_awaited_once()
    call_kwargs = mock_audit.call_args[1]
    assert call_kwargs["action"] == "admin.create_user"
    assert call_kwargs["actor"] is admin
    assert call_kwargs["target_type"] == "user"
    assert "email" in call_kwargs["metadata"]
    assert "role" in call_kwargs["metadata"]


# ──────────────────────────────────────────────────────────────────────────────
# 2. PATCH /admin/users/{id} → admin.update_user audit + before/after metadata
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_admin_update_user_audit_before_after(real_db_session):
    """PATCH /admin/users/{id} — record_audit 에 before/after metadata 포함 확인.

    real_db_session: 실제 User row INSERT 후 update_user 호출.
    """
    from app.api.admin.users import UserUpdateRequest, update_user
    from tests.factories import UserFactory

    # 실제 User row INSERT
    target_user = UserFactory(
        email="target_user_update@example.com",
        role="user",
        status="active",
        display_name="target_user_update",
    )
    real_db_session.add(target_user)
    await real_db_session.flush()

    admin = _make_admin_mock()
    request = _make_request()
    body = UserUpdateRequest(status="suspended")

    with patch("app.api.admin.users.record_audit", new_callable=AsyncMock) as mock_audit:
        with patch("app.api.admin.users.revoke_user_tokens", new_callable=AsyncMock):
            with patch.object(real_db_session, "commit", new_callable=AsyncMock):
                result = await update_user(
                    user_id=target_user.id,
                    body=body,
                    request=request,
                    admin=admin,
                    db=real_db_session,
                )

    mock_audit.assert_awaited_once()
    call_kwargs = mock_audit.call_args[1]
    assert call_kwargs["action"] == "admin.update_user"
    assert "before" in call_kwargs["metadata"]
    assert "after" in call_kwargs["metadata"]
    assert call_kwargs["metadata"]["before"]["status"] == "active"


# ──────────────────────────────────────────────────────────────────────────────
# 3. DELETE /admin/ai-collections/{id} → admin.ai_collection_delete + reason
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_admin_ai_collection_delete_audit(real_db_session):
    """DELETE /admin/ai-collections/{id} — record_audit(reason) 확인.

    ai_collections 테이블은 복잡하므로 db.execute mock 유지.
    record_audit 인자 검증이 핵심.
    """
    from app.api.admin_ai_collections import CollectionDeleteRequest, delete_collection

    admin = _make_admin_mock()
    collection_id = uuid.uuid4()
    request = _make_request()

    # ai_collections 행 존재 확인 mock (테이블 구조 복잡 — 별도 setup 필요)
    mock_coll_row = MagicMock()
    mock_coll_row.id = collection_id
    mock_coll_row.status = "generating"

    # real_db_session의 execute를 부분 mock (ai_collections SELECT/DELETE만)
    original_execute = real_db_session.execute

    async def _mock_execute(stmt, *args, **kwargs):
        sql_text = str(stmt)
        if "ai_collections" in sql_text or "SELECT id, status" in sql_text:
            result = MagicMock()
            if "DELETE" in sql_text:
                result.fetchone = lambda: None
            else:
                result.fetchone = lambda: mock_coll_row
            return result
        return await original_execute(stmt, *args, **kwargs)

    with patch.object(real_db_session, "execute", side_effect=_mock_execute):
        with patch.object(real_db_session, "commit", new_callable=AsyncMock):
            with patch("app.api.admin_ai_collections.record_audit", new_callable=AsyncMock) as mock_audit:
                body = CollectionDeleteRequest(reason="잘못된 내용 포함, 즉시 삭제 필요합니다.")
                result = await delete_collection(
                    collection_id=collection_id,
                    body=body,
                    request=request,
                    admin=admin,
                    db=real_db_session,
                )

    assert result["data"]["deleted"] is True
    mock_audit.assert_awaited_once()
    call_kwargs = mock_audit.call_args[1]
    assert call_kwargs["action"] == "admin.ai_collection_delete"
    # record_audit 호출 시 metadata= 키워드 사용
    assert "reason" in call_kwargs["metadata"]
    assert call_kwargs["metadata"]["reason"] == body.reason


# ──────────────────────────────────────────────────────────────────────────────
# 4. POST /auth/logout → user.logout audit
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_user_logout_audit():
    """POST /auth/logout — record_audit(action='user.logout') 확인.

    이 테스트는 real_db_session 불필요 (logout은 DB read 없이 token revoke만).
    """
    from app.api.auth import logout
    from unittest.mock import AsyncMock as AM

    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AM()
    db.execute = AM()

    user = _make_user_mock()
    request = _make_request()

    with patch("app.api.auth.record_audit", new_callable=AM) as mock_audit:
        with patch("app.api.auth.revoke_token", new_callable=AM):
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

    user = MagicMock(spec=False)
    user.id = uuid.uuid4()
    user.role = "user"
    user.email = "user@example.com"
    user.display_name = "testuser"
    user.deleted_at = None
    _now = datetime.now(timezone.utc)
    user.deletion_scheduled_for = _now + timedelta(days=30)

    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.flush = AsyncMock()
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
# 6. POST /admin/users → audit metadata에 created_user_id, email, role, send_magic_link 포함
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_admin_create_user_audit_metadata_keys(real_db_session):
    """audit metadata에 created_user_id, email, role, send_magic_link 포함 확인.

    real_db_session: 실제 DB에서 User INSERT + 이메일 중복 검사.
    """
    from app.api.admin.users import AdminCreateUserRequest, create_user_by_admin

    admin = _make_admin_mock()
    request = _make_request()

    body = AdminCreateUserRequest(
        email="another_meta_test@example.com",
        display_name="Another User",
        role="artist",
        send_magic_link=False,
    )

    with patch("app.api.admin.users.record_audit", new_callable=AsyncMock) as mock_audit:
        with patch("app.api.admin.users.hash_password", return_value="hashed_pw_456"):
            with patch.object(real_db_session, "commit", new_callable=AsyncMock):
                with patch.object(real_db_session, "refresh", new_callable=AsyncMock) as mock_refresh2:
                    import uuid as _uuid2
                    from datetime import datetime as _dt2, timezone as _tz2
                    async def _side_refresh2(obj):
                        if not getattr(obj, "id", None):
                            obj.id = _uuid2.uuid4()
                        if not getattr(obj, "created_at", None):
                            obj.created_at = _dt2.now(_tz2.utc)
                    mock_refresh2.side_effect = _side_refresh2
                    await create_user_by_admin(
                        body=body,
                        request=request,
                        admin=admin,
                        db=real_db_session,
                    )

    call_kwargs = mock_audit.call_args[1]
    meta = call_kwargs["metadata"]
    assert "created_user_id" in meta
    assert "email" in meta
    assert "role" in meta
    assert "send_magic_link" in meta
