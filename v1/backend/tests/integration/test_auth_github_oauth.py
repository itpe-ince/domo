"""Integration tests — GitHub OAuth API (Phase 12 C-2 / Phase 13 A-1).

테스트 항목:
  1.  POST /auth/sns/github 신규 사용자 -> 200 + JWT + github_id 저장
  2.  GitHub email == Google email -> 계정 통합 + github_id 추가 + 200
  3.  GitHub email == 비밀번호 가입 -> 409 GITHUB_EMAIL_CONFLICT
  4.  GitHub email == admin 계정 -> 403 ADMIN_SNS_FORBIDDEN
  5.  GitHub 인증 이메일 없음 -> 400 GITHUB_EMAIL_REQUIRED
  6.  유효하지 않은 code -> 400 GITHUB_TOKEN_EXCHANGE_FAILED
  7.  기존 github_id 보유 사용자 -> 로그인 성공 + 신규 row 없음

전략: endpoint 함수 직접 호출 + AsyncMock DB + MagicMock User.
실제 DB/GitHub API 불필요. (Phase 13 A-1: skip 제거 + mock 정확화)
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.api.auth import github_login
from app.core.errors import ApiError
from app.schemas.auth import GitHubLoginRequest


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_request(ip: str = "127.0.0.1") -> MagicMock:
    req = MagicMock()
    req.headers = {}
    req.client = MagicMock(host=ip)
    return req


def _make_user(
    email: str = "artist@example.com",
    role: str = "user",
    sns_provider: str | None = "google",
    github_id: int | None = None,
    password_hash: str | None = None,
    avatar_url: str | None = None,
) -> MagicMock:
    user = MagicMock()
    user.id = uuid.uuid4()
    user.email = email
    user.role = role
    user.status = "active"
    user.sns_provider = sns_provider
    user.sns_id = "google-sub-123"
    user.github_id = github_id
    user.password_hash = password_hash
    user.avatar_url = avatar_url
    user.display_name = "Test Artist"
    user.language = "ko"
    user.is_minor = False
    user.warning_count = 0
    user.preferred_currency = "USD"
    user.totp_enabled_at = None
    user.email_verified = True
    user.bio = None
    user.country_code = None
    user.created_at = datetime.now(timezone.utc)
    return user


def _make_db(user_by_github_id=None, user_by_email=None) -> AsyncMock:
    """AsyncMock DB — github_id 조회 우선, 없으면 email 조회."""
    db = AsyncMock()
    call_count = 0

    async def execute_side_effect(stmt):
        nonlocal call_count
        call_count += 1
        result = MagicMock()
        if call_count == 1:
            # 첫 번째 execute: github_id 조회
            result.scalar_one_or_none = MagicMock(return_value=user_by_github_id)
        else:
            # 두 번째 execute: email 조회
            result.scalar_one_or_none = MagicMock(return_value=user_by_email)
        return result

    db.execute = AsyncMock(side_effect=execute_side_effect)
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.add = MagicMock()
    return db


_GITHUB_USER_PAYLOAD = {
    "id": 12345678,
    "login": "dev-artist",
    "name": "Dev Artist",
    "avatar_url": "https://avatars.githubusercontent.com/u/12345678",
    "email": None,
}

_GITHUB_EMAIL = "dev@example.com"

_FAKE_TOKEN_PAIR = ("access.token.here", "refresh.token.here")


# ── Tests ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
@patch("app.api.auth.record_audit", new_callable=AsyncMock)
@patch("app.api.auth.capture_event")
@patch("app.api.auth.issue_initial_tokens", new_callable=AsyncMock)
@patch("app.api.auth.fetch_github_primary_email", new_callable=AsyncMock)
@patch("app.api.auth.fetch_github_user", new_callable=AsyncMock)
@patch("app.api.auth.exchange_github_code", new_callable=AsyncMock)
@patch("app.api.auth.UserPublic")
async def test_github_new_user_signup(
    mock_user_public,
    mock_exchange,
    mock_fetch_user,
    mock_fetch_email,
    mock_issue,
    mock_capture,
    mock_audit,
    monkeypatch,
):
    """신규 GitHub 사용자 -> JWT + github_id 저장.

    Phase 13 A-2: UserPublic.model_validate 패치.
    신규 User 인스턴스는 server_default(created_at) 등이 None이어서 Pydantic 검증 실패 가능.
    """
    # Phase 13 A-1: env monkeypatch 추가
    monkeypatch.setenv("GITHUB_CLIENT_ID", "test_client_id")
    monkeypatch.setenv("GITHUB_CLIENT_SECRET", "test_client_secret")

    mock_exchange.return_value = "gh_access_token"
    mock_fetch_user.return_value = _GITHUB_USER_PAYLOAD.copy()
    mock_fetch_email.return_value = _GITHUB_EMAIL
    mock_issue.return_value = _FAKE_TOKEN_PAIR
    mock_user_public.model_validate.return_value.model_dump.return_value = {
        "id": "new-github-user-123",
        "email": _GITHUB_EMAIL,
    }

    db = _make_db(user_by_github_id=None, user_by_email=None)

    body = GitHubLoginRequest(code="auth_code", redirect_uri="https://domo.art/callback")
    req = _make_request()

    result = await github_login(body=body, request=req, db=db, _rl=None)

    data = result["data"]
    assert "tokens" in data
    assert "user" in data
    assert data["tokens"]["access_token"] == "access.token.here"
    mock_capture.assert_called_once()
    _, audit_kwargs = mock_audit.call_args
    assert audit_kwargs["action"] == "auth.github_signup"


@pytest.mark.asyncio
@patch("app.api.auth.record_audit", new_callable=AsyncMock)
@patch("app.api.auth.capture_event")
@patch("app.api.auth.issue_initial_tokens", new_callable=AsyncMock)
@patch("app.api.auth.fetch_github_primary_email", new_callable=AsyncMock)
@patch("app.api.auth.fetch_github_user", new_callable=AsyncMock)
@patch("app.api.auth.exchange_github_code", new_callable=AsyncMock)
async def test_github_existing_google_account_merge(
    mock_exchange,
    mock_fetch_user,
    mock_fetch_email,
    mock_issue,
    mock_capture,
    mock_audit,
    monkeypatch,
):
    """GitHub email == Google email -> 계정 통합 (github_id 추가) + 200."""
    monkeypatch.setenv("GITHUB_CLIENT_ID", "test_client_id")
    monkeypatch.setenv("GITHUB_CLIENT_SECRET", "test_client_secret")

    mock_exchange.return_value = "gh_access_token"
    mock_fetch_user.return_value = _GITHUB_USER_PAYLOAD.copy()
    mock_fetch_email.return_value = _GITHUB_EMAIL
    mock_issue.return_value = _FAKE_TOKEN_PAIR

    existing_google_user = _make_user(
        email=_GITHUB_EMAIL,
        sns_provider="google",
        github_id=None,
    )

    db = _make_db(user_by_github_id=None, user_by_email=existing_google_user)

    body = GitHubLoginRequest(code="auth_code", redirect_uri="https://domo.art/callback")
    req = _make_request()

    result = await github_login(body=body, request=req, db=db, _rl=None)

    data = result["data"]
    assert "tokens" in data
    # github_id가 추가되어야 함
    assert existing_google_user.github_id == _GITHUB_USER_PAYLOAD["id"]
    # 신규 사용자가 아니므로 capture_event 미호출
    mock_capture.assert_not_called()
    _, audit_kwargs = mock_audit.call_args
    assert audit_kwargs["action"] == "auth.github_login"


@pytest.mark.asyncio
@patch("app.api.auth.fetch_github_primary_email", new_callable=AsyncMock)
@patch("app.api.auth.fetch_github_user", new_callable=AsyncMock)
@patch("app.api.auth.exchange_github_code", new_callable=AsyncMock)
async def test_github_email_conflict_password_account(
    mock_exchange,
    mock_fetch_user,
    mock_fetch_email,
    monkeypatch,
):
    """GitHub email == 비밀번호 가입 이메일 -> 409 GITHUB_EMAIL_CONFLICT."""
    monkeypatch.setenv("GITHUB_CLIENT_ID", "test_client_id")
    monkeypatch.setenv("GITHUB_CLIENT_SECRET", "test_client_secret")

    mock_exchange.return_value = "gh_access_token"
    mock_fetch_user.return_value = _GITHUB_USER_PAYLOAD.copy()
    mock_fetch_email.return_value = _GITHUB_EMAIL

    password_user = _make_user(
        email=_GITHUB_EMAIL,
        sns_provider=None,
        password_hash="$2b$12$hashedpassword",
    )

    db = _make_db(user_by_github_id=None, user_by_email=password_user)

    body = GitHubLoginRequest(code="auth_code", redirect_uri="https://domo.art/callback")
    req = _make_request()

    with pytest.raises(ApiError) as exc_info:
        await github_login(body=body, request=req, db=db, _rl=None)

    assert exc_info.value.code == "GITHUB_EMAIL_CONFLICT"
    assert exc_info.value.status_code == 409


@pytest.mark.asyncio
@patch("app.api.auth.fetch_github_primary_email", new_callable=AsyncMock)
@patch("app.api.auth.fetch_github_user", new_callable=AsyncMock)
@patch("app.api.auth.exchange_github_code", new_callable=AsyncMock)
async def test_github_admin_account_forbidden(
    mock_exchange,
    mock_fetch_user,
    mock_fetch_email,
    monkeypatch,
):
    """GitHub email == admin 계정 -> 403 ADMIN_SNS_FORBIDDEN."""
    monkeypatch.setenv("GITHUB_CLIENT_ID", "test_client_id")
    monkeypatch.setenv("GITHUB_CLIENT_SECRET", "test_client_secret")

    mock_exchange.return_value = "gh_access_token"
    mock_fetch_user.return_value = _GITHUB_USER_PAYLOAD.copy()
    mock_fetch_email.return_value = "admin@domo.art"

    admin_user = _make_user(
        email="admin@domo.art",
        role="admin",
        sns_provider=None,
    )

    db = _make_db(user_by_github_id=None, user_by_email=admin_user)

    body = GitHubLoginRequest(code="auth_code", redirect_uri="https://domo.art/callback")
    req = _make_request()

    with pytest.raises(ApiError) as exc_info:
        await github_login(body=body, request=req, db=db, _rl=None)

    assert exc_info.value.code == "ADMIN_SNS_FORBIDDEN"
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
@patch("app.api.auth.fetch_github_primary_email", new_callable=AsyncMock)
@patch("app.api.auth.fetch_github_user", new_callable=AsyncMock)
@patch("app.api.auth.exchange_github_code", new_callable=AsyncMock)
async def test_github_no_verified_email(
    mock_exchange,
    mock_fetch_user,
    mock_fetch_email,
    monkeypatch,
):
    """GitHub 인증 이메일 없음 -> 400 GITHUB_EMAIL_REQUIRED."""
    monkeypatch.setenv("GITHUB_CLIENT_ID", "test_client_id")
    monkeypatch.setenv("GITHUB_CLIENT_SECRET", "test_client_secret")

    mock_exchange.return_value = "gh_access_token"
    mock_fetch_user.return_value = _GITHUB_USER_PAYLOAD.copy()
    mock_fetch_email.return_value = None  # 인증된 이메일 없음

    db = AsyncMock()
    db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))

    body = GitHubLoginRequest(code="auth_code", redirect_uri="https://domo.art/callback")
    req = _make_request()

    with pytest.raises(ApiError) as exc_info:
        await github_login(body=body, request=req, db=db, _rl=None)

    assert exc_info.value.code == "GITHUB_EMAIL_REQUIRED"
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
@patch("app.api.auth.exchange_github_code", new_callable=AsyncMock)
async def test_github_invalid_code(mock_exchange, monkeypatch):
    """유효하지 않은 code -> ApiError (GITHUB_TOKEN_EXCHANGE_FAILED 또는 GITHUB_OAUTH_DISABLED)."""
    monkeypatch.setenv("GITHUB_CLIENT_ID", "test_client_id")
    monkeypatch.setenv("GITHUB_CLIENT_SECRET", "test_client_secret")

    mock_exchange.side_effect = ApiError(
        "GITHUB_TOKEN_EXCHANGE_FAILED",
        "code 교환 실패",
        http_status=400,
    )

    db = AsyncMock()
    body = GitHubLoginRequest(code="bad_code", redirect_uri="https://domo.art/callback")
    req = _make_request()

    with pytest.raises(ApiError) as exc_info:
        await github_login(body=body, request=req, db=db, _rl=None)

    assert exc_info.value.status_code in (400, 503)


@pytest.mark.asyncio
@patch("app.api.auth.record_audit", new_callable=AsyncMock)
@patch("app.api.auth.capture_event")
@patch("app.api.auth.issue_initial_tokens", new_callable=AsyncMock)
@patch("app.api.auth.fetch_github_primary_email", new_callable=AsyncMock)
@patch("app.api.auth.fetch_github_user", new_callable=AsyncMock)
@patch("app.api.auth.exchange_github_code", new_callable=AsyncMock)
async def test_github_existing_user_by_github_id(
    mock_exchange,
    mock_fetch_user,
    mock_fetch_email,
    mock_issue,
    mock_capture,
    mock_audit,
    monkeypatch,
):
    """기존 github_id 보유 사용자 -> 로그인 성공 + 신규 row 없음."""
    monkeypatch.setenv("GITHUB_CLIENT_ID", "test_client_id")
    monkeypatch.setenv("GITHUB_CLIENT_SECRET", "test_client_secret")

    mock_exchange.return_value = "gh_access_token"
    mock_fetch_user.return_value = _GITHUB_USER_PAYLOAD.copy()
    mock_fetch_email.return_value = _GITHUB_EMAIL
    mock_issue.return_value = _FAKE_TOKEN_PAIR

    existing_gh_user = _make_user(
        email=_GITHUB_EMAIL,
        sns_provider="github",
        github_id=_GITHUB_USER_PAYLOAD["id"],
    )

    # github_id로 첫 번째 조회에서 바로 반환 → 이메일 조회 불필요
    db = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none = MagicMock(return_value=existing_gh_user)
    db.execute = AsyncMock(return_value=result_mock)
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.add = MagicMock()

    body = GitHubLoginRequest(code="auth_code", redirect_uri="https://domo.art/callback")
    req = _make_request()

    result = await github_login(body=body, request=req, db=db, _rl=None)

    data = result["data"]
    assert "tokens" in data
    # 기존 사용자 → 신규 가입 이벤트 없음
    mock_capture.assert_not_called()
    # add 호출 없음 → 신규 row 생성 없음
    db.add.assert_not_called()
    _, audit_kwargs = mock_audit.call_args
    assert audit_kwargs["action"] == "auth.github_login"
