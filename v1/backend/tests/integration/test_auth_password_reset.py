"""Integration tests — 비밀번호 재설정 API (Phase 12 C-1).

테스트 항목:
  5.  POST /auth/password/reset-request 정상 이메일 → 200 + sent=True
  6.  POST /auth/password/reset-request 미존재 이메일 → 200 (enumeration 방지)
  7.  POST /auth/password/reset-request Google 계정 → 200 + sent=False
  8.  POST /auth/password/reset-request cooldown (5분 내 재요청) → 429 RESET_TOO_SOON
  9.  POST /auth/password/reset 유효 토큰 + 새 비밀번호 → 200 + 비밀번호 변경 확인
  10. POST /auth/password/reset 만료 토큰 → 400 TOKEN_EXPIRED
  11. POST /auth/password/reset 이미 사용된 토큰 → 400 TOKEN_ALREADY_USED
  12. POST /auth/password/reset 잠금 계정 → 비밀번호 재설정 후 잠금 해제 확인
  13. POST /auth/password/reset 비밀번호 변경 후 refresh token revoke 확인

전략: endpoint 함수 직접 호출 + AsyncMock DB + MagicMock 객체.
실제 DB/이메일 서버 불필요.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.api.auth import request_password_reset, reset_password
from app.core.errors import ApiError
from app.core.security import hash_password, verify_password
from app.schemas.auth import PasswordResetBody, PasswordResetRequestBody


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_request(ip: str = "127.0.0.1") -> MagicMock:
    req = MagicMock()
    req.headers = {}
    req.client = MagicMock(host=ip)
    return req


def _make_user(
    email: str = "artist@example.com",
    password_hash: str | None = "$2b$12$fakehash",
    sns_provider: str | None = None,
    failed_login_count: int = 0,
    failed_login_locked_until: datetime | None = None,
    language: str = "ko",
) -> MagicMock:
    u = MagicMock()
    u.id = uuid.uuid4()
    u.email = email
    u.role = "user"
    u.status = "active"
    u.display_name = "Test Artist"
    u.sns_provider = sns_provider
    u.password_hash = password_hash
    u.failed_login_count = failed_login_count
    u.failed_login_locked_until = failed_login_locked_until
    u.language = language
    u.email_verified = True
    u.created_at = datetime.now(timezone.utc)
    u.preferred_currency = "USD"
    u.is_minor = False
    u.warning_count = 0
    u.totp_enabled_at = None
    return u


def _make_reset_token(
    user_id: uuid.UUID,
    token_str: str = "validtoken" * 4,
    used_at: datetime | None = None,
    expires_at: datetime | None = None,
    created_at: datetime | None = None,
) -> MagicMock:
    now = datetime.now(timezone.utc)
    t = MagicMock()
    t.id = 1
    t.user_id = user_id
    t.token = token_str
    t.used_at = used_at
    t.expires_at = expires_at or (now + timedelta(hours=1))
    t.created_at = created_at or now
    return t


def _make_db_user_found(user: MagicMock) -> AsyncMock:
    """user 조회 시 user를 반환하고, 이후 조회는 None을 반환하는 DB mock."""
    db = AsyncMock()

    call_count = {"n": 0}

    async def execute_side_effect(stmt):
        call_count["n"] += 1
        result = MagicMock()
        if call_count["n"] == 1:
            # 첫 번째 execute: User 조회
            result.scalar_one_or_none = MagicMock(return_value=user)
        else:
            # 이후 execute: cooldown 검사, update 등
            result.scalar_one_or_none = MagicMock(return_value=None)
        return result

    db.execute = AsyncMock(side_effect=execute_side_effect)
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    return db


def _make_db_none() -> AsyncMock:
    """항상 None을 반환하는 DB mock."""
    db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none = MagicMock(return_value=None)
    db.execute = AsyncMock(return_value=result)
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    return db


def _make_db_with_reset_token(user: MagicMock, reset_token: MagicMock) -> AsyncMock:
    """reset_token과 user를 순서대로 반환하는 DB mock."""
    db = AsyncMock()
    call_count = {"n": 0}

    async def execute_side_effect(stmt):
        call_count["n"] += 1
        result = MagicMock()
        if call_count["n"] == 1:
            # 첫 번째: PasswordResetToken 조회
            result.scalar_one_or_none = MagicMock(return_value=reset_token)
        elif call_count["n"] == 2:
            # 두 번째: User 조회
            result.scalar_one = MagicMock(return_value=user)
        else:
            # 이후: refresh token revoke update
            result.scalar_one = MagicMock(return_value=None)
        return result

    db.execute = AsyncMock(side_effect=execute_side_effect)
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    return db


# ── Test 5: reset-request 정상 이메일 → 200 + sent=True ─────────────────────

@pytest.mark.asyncio
async def test_reset_request_valid_email():
    """정상 이메일 → 200 + sent=True."""
    user = _make_user()
    db = _make_db_user_found(user)
    body = PasswordResetRequestBody(email="artist@example.com")

    with (
        patch("app.api.auth.send_password_reset_email",
              new=AsyncMock(return_value={"sent": True, "provider": "mock"})),
        patch("app.api.auth.record_audit", new=AsyncMock()),
    ):
        result = await request_password_reset(
            body=body,
            request=_make_request(),
            db=db,
        )

    assert result["data"]["sent"] is True


# ── Test 6: reset-request 미존재 이메일 → 200 (enumeration 방지) ─────────────

@pytest.mark.asyncio
async def test_reset_request_nonexistent_email():
    """존재하지 않는 이메일 → 200 반환 (enumeration 방지)."""
    db = _make_db_none()
    body = PasswordResetRequestBody(email="nobody@example.com")

    result = await request_password_reset(
        body=body,
        request=_make_request(),
        db=db,
    )

    assert result["data"]["sent"] is False
    # HTTP 200 (예외 미발생)


# ── Test 7: reset-request Google 계정 → 200 + sent=False ────────────────────

@pytest.mark.asyncio
async def test_reset_request_google_account():
    """Google OAuth 전용 계정 (password_hash=None) → 200 + sent=False."""
    google_user = _make_user(password_hash=None, sns_provider="google")
    db = _make_db_user_found(google_user)
    body = PasswordResetRequestBody(email="google@example.com")

    result = await request_password_reset(
        body=body,
        request=_make_request(),
        db=db,
    )

    assert result["data"]["sent"] is False


# ── Test 8: reset-request cooldown → 429 RESET_TOO_SOON ─────────────────────

@pytest.mark.asyncio
async def test_reset_request_cooldown():
    """5분 내 재요청 → 429 RESET_TOO_SOON."""
    user = _make_user()

    # cooldown 토큰이 2분 전에 발급된 상황
    recent_token = _make_reset_token(
        user_id=user.id,
        used_at=None,  # 미사용
        created_at=datetime.now(timezone.utc) - timedelta(minutes=2),
    )

    db = AsyncMock()
    call_count = {"n": 0}

    async def execute_side_effect(stmt):
        call_count["n"] += 1
        result = MagicMock()
        if call_count["n"] == 1:
            result.scalar_one_or_none = MagicMock(return_value=user)
        elif call_count["n"] == 2:
            # cooldown 검사 — 최근 토큰 존재
            result.scalar_one_or_none = MagicMock(return_value=recent_token)
        else:
            result.scalar_one_or_none = MagicMock(return_value=None)
        return result

    db.execute = AsyncMock(side_effect=execute_side_effect)
    db.add = MagicMock()
    db.commit = AsyncMock()

    body = PasswordResetRequestBody(email="artist@example.com")

    with pytest.raises(ApiError) as exc_info:
        await request_password_reset(
            body=body,
            request=_make_request(),
            db=db,
        )

    assert exc_info.value.code == "RESET_TOO_SOON"
    assert exc_info.value.status_code == 429
    assert "retry_after_seconds" in exc_info.value.details


# ── Test 9: reset 유효 토큰 + 새 비밀번호 → 200 ─────────────────────────────

@pytest.mark.asyncio
async def test_reset_complete_valid_token():
    """유효 토큰 + 비밀번호 정책 통과 → 200 + 비밀번호 변경."""
    user = _make_user()
    old_hash = hash_password("OldPass1!")
    user.password_hash = old_hash

    reset_token = _make_reset_token(user_id=user.id)
    db = _make_db_with_reset_token(user, reset_token)

    body = PasswordResetBody(token=reset_token.token, new_password="NewPass1!")

    with patch("app.api.auth.record_audit", new=AsyncMock()):
        result = await reset_password(body=body, request=_make_request(), db=db)

    assert result["data"]["success"] is True
    # 비밀번호 해시가 변경됐는지 확인
    assert user.password_hash != old_hash
    # 새 비밀번호로 verify 가능
    assert verify_password("NewPass1!", user.password_hash)
    # 토큰 무효화 확인
    assert reset_token.used_at is not None


# ── Test 10: reset 만료 토큰 → 400 TOKEN_EXPIRED ─────────────────────────────

@pytest.mark.asyncio
async def test_reset_complete_expired_token():
    """만료된 토큰 → 400 TOKEN_EXPIRED."""
    user = _make_user()
    # 61분 전에 만료된 토큰
    expired_token = _make_reset_token(
        user_id=user.id,
        used_at=None,
        expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
    )

    db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none = MagicMock(return_value=expired_token)
    db.execute = AsyncMock(return_value=result)

    body = PasswordResetBody(token=expired_token.token, new_password="NewPass1!")

    with pytest.raises(ApiError) as exc_info:
        await reset_password(body=body, request=_make_request(), db=db)

    assert exc_info.value.code == "TOKEN_EXPIRED"
    assert exc_info.value.status_code == 400


# ── Test 11: reset 이미 사용된 토큰 → 400 TOKEN_ALREADY_USED ────────────────

@pytest.mark.asyncio
async def test_reset_complete_used_token():
    """이미 사용된 토큰 → 400 TOKEN_ALREADY_USED."""
    user = _make_user()
    used_token = _make_reset_token(
        user_id=user.id,
        used_at=datetime.now(timezone.utc) - timedelta(minutes=10),  # 이미 사용됨
    )

    db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none = MagicMock(return_value=used_token)
    db.execute = AsyncMock(return_value=result)

    body = PasswordResetBody(token=used_token.token, new_password="NewPass1!")

    with pytest.raises(ApiError) as exc_info:
        await reset_password(body=body, request=_make_request(), db=db)

    assert exc_info.value.code == "TOKEN_ALREADY_USED"
    assert exc_info.value.status_code == 400


# ── Test 12: reset 잠금 계정 → 잠금 해제 확인 ──────────────────────────────

@pytest.mark.asyncio
async def test_reset_unlocks_locked_account():
    """failed_login_count=5 잠금 계정 → 비밀번호 재설정 후 잠금 해제."""
    user = _make_user(
        failed_login_count=5,
        failed_login_locked_until=datetime.now(timezone.utc) + timedelta(minutes=10),
    )
    reset_token = _make_reset_token(user_id=user.id)
    db = _make_db_with_reset_token(user, reset_token)

    body = PasswordResetBody(token=reset_token.token, new_password="NewPass1!")

    with patch("app.api.auth.record_audit", new=AsyncMock()):
        result = await reset_password(body=body, request=_make_request(), db=db)

    assert result["data"]["success"] is True
    assert user.failed_login_count == 0
    assert user.failed_login_locked_until is None


# ── Test 13: reset 후 refresh token revoke 확인 ──────────────────────────────

@pytest.mark.asyncio
async def test_reset_revokes_refresh_tokens():
    """비밀번호 변경 후 refresh token revoke update 호출 확인."""
    user = _make_user()
    reset_token = _make_reset_token(user_id=user.id)

    db = AsyncMock()
    call_count = {"n": 0}
    executed_stmts = []

    async def execute_side_effect(stmt):
        call_count["n"] += 1
        executed_stmts.append(stmt)
        result = MagicMock()
        if call_count["n"] == 1:
            # PasswordResetToken 조회
            result.scalar_one_or_none = MagicMock(return_value=reset_token)
        elif call_count["n"] == 2:
            # User 조회
            result.scalar_one = MagicMock(return_value=user)
        else:
            # RefreshToken revoke update
            result.scalar_one = MagicMock(return_value=None)
        return result

    db.execute = AsyncMock(side_effect=execute_side_effect)
    db.add = MagicMock()
    db.commit = AsyncMock()

    body = PasswordResetBody(token=reset_token.token, new_password="NewPass1!")

    with patch("app.api.auth.record_audit", new=AsyncMock()):
        result = await reset_password(body=body, request=_make_request(), db=db)

    assert result["data"]["success"] is True
    # execute가 3번 이상 호출됨 (token 조회 + user 조회 + refresh token revoke)
    assert call_count["n"] >= 3
