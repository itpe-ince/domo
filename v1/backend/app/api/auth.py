from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.errors import ApiError
from app.core.rate_limit import rate_limit
from app.core.security import hash_password, verify_password
from app.db.session import get_db
from app.models.auth_token import RefreshToken
from app.models.user import User
from app.schemas.auth import (
    GoogleLoginRequest,
    LoginEmailRequest,
    RefreshRequest,
    RegisterRequest,
    TokenPair,
    UserPublic,
    VerifyEmailRequest,
)
from app.services.auth_tokens import (
    issue_initial_tokens,
    list_user_sessions,
    revoke_token,
    rotate_tokens,
)
from app.services.email_verification import (
    RESEND_COOLDOWN_MINUTES,
    generate_verification_token,
    send_verification_email,
    verification_expires_at,
)
from app.services.google_auth import verify_google_id_token
from app.services.analytics import capture_event
from app.services.audit_log import record_audit

# 로그인 실패 잠금 정책 (admin_auth.py 와 동일 기준)
_MAX_FAILED_ATTEMPTS = 5
_USER_LOCKOUT_DURATION = timedelta(minutes=15)

router = APIRouter(prefix="/auth", tags=["auth"])


# ─── 비밀번호 정책 검증 (NIST SP 800-63B) ──────────────────────────────────

def validate_password(pw: str) -> None:
    """비밀번호 강도 검증.

    규칙:
    - 최소 8자
    - 최대 72바이트 (bcrypt 한도, 초과 시 silent truncation 방지)
    - 대소문자 / 숫자 / 특수문자 중 3종 이상
    """
    if len(pw) < 8:
        raise ApiError(
            "PASSWORD_TOO_SHORT",
            "비밀번호는 8자 이상이어야 합니다",
            http_status=422,
        )
    if len(pw.encode("utf-8")) > 72:
        raise ApiError(
            "PASSWORD_TOO_LONG",
            "비밀번호는 72바이트를 초과할 수 없습니다",
            http_status=422,
        )
    classes = [
        any(c.isupper() for c in pw),   # 대문자
        any(c.islower() for c in pw),   # 소문자
        any(c.isdigit() for c in pw),   # 숫자
        any(not c.isalnum() for c in pw),  # 특수문자
    ]
    if sum(classes) < 3:
        raise ApiError(
            "PASSWORD_WEAK",
            "비밀번호는 대소문자/숫자/특수문자 중 3종 이상 포함해야 합니다",
            http_status=422,
        )


def _client_info(request: Request) -> tuple[str | None, str | None]:
    ua = request.headers.get("user-agent")
    ip = request.client.host if request.client else None
    return ua, ip


@router.post("/sns/google")
async def google_login(
    body: GoogleLoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _rl=rate_limit("auth_login"),
):
    """SNS login via Google ID token. Creates user if first time."""
    info = await verify_google_id_token(body.id_token)
    sns_id = info.get("sub")
    email = info.get("email")
    name = info.get("name") or (email.split("@")[0] if email else "user")
    avatar = info.get("picture")

    if not email or not sns_id:
        raise ApiError(
            "INVALID_REQUEST", "Missing email or sub from Google", http_status=400
        )

    # 1) Match by (sns_provider, sns_id)
    result = await db.execute(
        select(User).where(User.sns_provider == "google", User.sns_id == sns_id)
    )
    user = result.scalar_one_or_none()

    # 2) Fallback: existing email (e.g. seeded user) — adopt SNS identity
    if not user:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if user:
            # Security: admin accounts MUST NOT authenticate via SNS.
            # They use the dedicated /auth/admin/login flow with password + TOTP.
            if user.role == "admin":
                raise ApiError(
                    "ADMIN_SNS_FORBIDDEN",
                    "Administrator accounts must sign in via /auth/admin/login.",
                    http_status=403,
                )
            user.sns_provider = "google"
            user.sns_id = sns_id
            if not user.avatar_url and avatar:
                user.avatar_url = avatar
            await db.commit()
            await db.refresh(user)

    # 3) Create brand new user
    is_new_user = not user
    if is_new_user:
        user = User(
            email=email,
            sns_provider="google",
            sns_id=sns_id,
            display_name=name,
            avatar_url=avatar,
            role="user",
            status="active",
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    ua, ip = _client_info(request)
    access, refresh = await issue_initial_tokens(
        db, user, user_agent=ua, ip_address=ip
    )
    await db.commit()

    # G'-4: server-side signup event (new users only)
    if is_new_user:
        capture_event(
            str(user.id),
            "user_signup_confirmed",
            {"method": "google", "language": getattr(user, "language", None)},
        )

    # Audit: user login (SNS)
    await record_audit(
        db,
        actor=user,
        action="user.login",
        metadata={"method": "google", "ip": ip},
        request=request,
        status="success",
    )

    return {
        "data": {
            "tokens": TokenPair(
                access_token=access, refresh_token=refresh
            ).model_dump(),
            "user": UserPublic.model_validate(user).model_dump(mode="json"),
        }
    }


@router.post("/refresh")
async def refresh_token(
    body: RefreshRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _rl=rate_limit("auth_refresh"),
):
    ua, ip = _client_info(request)
    access, new_refresh = await rotate_tokens(
        db, body.refresh_token, user_agent=ua, ip_address=ip
    )
    return {
        "data": TokenPair(
            access_token=access, refresh_token=new_refresh
        ).model_dump()
    }


@router.get("/me")
async def get_me(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    payload = UserPublic.model_validate(user).model_dump(mode="json")
    # For admin users, include 2FA enrollment counters so the frontend
    # can decide whether to force the user into the setup flow.
    if user.role == "admin":
        from sqlalchemy import func as _func

        from app.models.webauthn import WebauthnCredential

        result = await db.execute(
            select(_func.count(WebauthnCredential.id)).where(
                WebauthnCredential.user_id == user.id
            )
        )
        passkey_count = int(result.scalar_one() or 0)
        payload["passkey_count"] = passkey_count
        payload["second_factor_enrolled"] = (
            user.totp_enabled_at is not None or passkey_count > 0
        )
    return {"data": payload}


@router.post("/logout")
async def logout(
    request: Request,
    body: RefreshRequest | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Revoke the provided refresh token. If body is omitted, just return OK."""
    if body and body.refresh_token:
        await revoke_token(db, body.refresh_token, reason="logout")
    await record_audit(
        db,
        actor=user,
        action="user.logout",
        request=request,
        status="success",
    )
    return {"data": {"ok": True}}


@router.get("/sessions")
async def list_my_sessions(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    sessions = await list_user_sessions(db, user.id)
    return {
        "data": [
            {
                "id": str(s.id),
                "issued_at": s.issued_at.isoformat(),
                "expires_at": s.expires_at.isoformat(),
                "user_agent": s.user_agent,
                "ip_address": str(s.ip_address) if s.ip_address else None,
            }
            for s in sessions
        ]
    }


@router.delete("/sessions/{session_id}")
async def revoke_session(
    session_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.id == session_id)
    )
    record = result.scalar_one_or_none()
    if not record:
        raise ApiError("NOT_FOUND", "Session not found", http_status=404)
    if record.user_id != user.id:
        raise ApiError("FORBIDDEN", "Not your session", http_status=403)
    if record.revoked_at is None:
        record.revoked_at = datetime.now(timezone.utc)
        record.revoked_reason = "admin_action"
        await db.commit()
    return {"data": {"ok": True}}


# ─── D-3: 이메일+비밀번호 인증 엔드포인트 ─────────────────────────────────

@router.post("/register", status_code=201)
async def register_with_password(
    body: RegisterRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _rl=rate_limit("auth_login"),
):
    """이메일+비밀번호 회원가입.

    - 비밀번호 정책 검증 (8자+, 3종 이상)
    - Google 계정 중복 시 409 + setup_password_url 반환
    - bcrypt hash 저장 (cost=12)
    - 이메일 인증 토큰 생성 + 발송 (이메일 미설정 시 graceful)
    - 미인증 상태로도 로그인 가능, 단 게시·후원 기능 제한
    """
    validate_password(body.password)

    email = body.email.lower()

    # 이메일 중복 확인
    result = await db.execute(select(User).where(User.email == email))
    existing = result.scalar_one_or_none()
    if existing:
        if existing.sns_provider == "google":
            # Google 계정이 존재하는 경우 — 통합 안내
            raise ApiError(
                "GOOGLE_ACCOUNT_EXISTS",
                "이미 Google 계정으로 가입된 이메일입니다. Google로 로그인하거나 비밀번호를 설정하세요.",
                http_status=409,
                details={
                    "setup_password_url": f"https://domo.art/auth/setup-password?email={email}"
                },
            )
        raise ApiError(
            "EMAIL_ALREADY_EXISTS",
            "이미 사용 중인 이메일입니다.",
            http_status=409,
        )

    # bcrypt hash 생성
    pw_hash = hash_password(body.password)

    # 인증 토큰 생성
    token = generate_verification_token()
    expires = verification_expires_at()
    now = datetime.now(timezone.utc)

    # 사용자 생성
    user = User(
        email=email,
        password_hash=pw_hash,
        display_name=body.display_name,
        role="user",
        status="active",
        email_verified=False,
        email_verification_token=token,
        email_verification_sent_at=now,
        email_verification_expires_at=expires,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # 이메일 발송 (graceful — 실패해도 가입 자체는 완료)
    send_result = await send_verification_email(
        email=user.email,
        display_name=user.display_name,
        token=token,
    )

    ua, ip = _client_info(request)
    access, refresh = await issue_initial_tokens(db, user, user_agent=ua, ip_address=ip)
    await db.commit()

    # analytics + audit
    capture_event(
        str(user.id),
        "user_signup_confirmed",
        {"method": "email_password", "language": getattr(user, "language", None)},
    )
    await record_audit(
        db,
        actor=user,
        action="user.register",
        metadata={"method": "email_password", "ip": ip},
        request=request,
        status="success",
    )

    return {
        "data": {
            "tokens": TokenPair(
                access_token=access, refresh_token=refresh
            ).model_dump(),
            "user": UserPublic.model_validate(user).model_dump(mode="json"),
            "email_verification_sent": send_result.get("sent", False),
        }
    }


@router.post("/login/email")
async def login_with_password(
    body: LoginEmailRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _rl=rate_limit("auth_login"),
):
    """이메일+비밀번호 로그인.

    - bcrypt 검증
    - 5회 실패 시 15분 잠금 (failed_login_count + failed_login_locked_until)
    - 성공 시 access + refresh 토큰 반환
    - audit_log 기록
    """
    email = body.email.lower()

    result = await db.execute(
        select(User).where(User.email == email)
    )
    user = result.scalar_one_or_none()

    # 상수 시간 에러로 계정 존재 여부 노출 방지
    invalid_creds = ApiError(
        "INVALID_CREDENTIALS",
        "이메일 또는 비밀번호가 올바르지 않습니다.",
        http_status=401,
    )

    if not user or user.status != "active":
        raise invalid_creds

    # admin 계정은 /auth/admin/login 전용
    if user.role == "admin":
        raise invalid_creds

    # password_hash 없음 → Google 전용 계정
    if not user.password_hash:
        raise ApiError(
            "GOOGLE_ACCOUNT_EXISTS",
            "이 계정은 Google 로그인 전용입니다.",
            http_status=409,
            details={
                "setup_password_url": f"https://domo.art/auth/setup-password?email={email}"
            },
        )

    # 잠금 확인
    now = datetime.now(timezone.utc)
    if user.failed_login_locked_until and user.failed_login_locked_until > now:
        remaining = int((user.failed_login_locked_until - now).total_seconds())
        raise ApiError(
            "ACCOUNT_LOCKED",
            f"로그인 시도 횟수 초과로 잠금되었습니다. {remaining}초 후 다시 시도하세요.",
            http_status=423,
            details={"locked_until": user.failed_login_locked_until.isoformat()},
        )

    # 비밀번호 검증
    if not verify_password(body.password, user.password_hash):
        user.failed_login_count = (user.failed_login_count or 0) + 1
        if user.failed_login_count >= _MAX_FAILED_ATTEMPTS:
            user.failed_login_locked_until = now + _USER_LOCKOUT_DURATION
        await db.commit()

        await record_audit(
            db,
            actor=user,
            action="user.login",
            metadata={"method": "email_password", "status": "failed"},
            request=request,
            status="failure",
        )
        raise invalid_creds

    # 로그인 성공 — 카운터 초기화
    user.failed_login_count = 0
    user.failed_login_locked_until = None

    ua, ip = _client_info(request)
    access, refresh = await issue_initial_tokens(db, user, user_agent=ua, ip_address=ip)
    await db.commit()

    await record_audit(
        db,
        actor=user,
        action="user.login",
        metadata={"method": "email_password", "ip": ip},
        request=request,
        status="success",
    )

    return {
        "data": {
            "tokens": TokenPair(
                access_token=access, refresh_token=refresh
            ).model_dump(),
            "user": UserPublic.model_validate(user).model_dump(mode="json"),
            "email_verified": user.email_verified,
        }
    }


@router.post("/email/verify")
async def verify_email(
    body: VerifyEmailRequest,
    db: AsyncSession = Depends(get_db),
):
    """이메일 인증 토큰 검증.

    - token으로 사용자 조회
    - 만료 여부 확인 (410 GONE)
    - email_verified=True 갱신 + 토큰 필드 초기화
    - audit_log 기록
    """
    result = await db.execute(
        select(User).where(User.email_verification_token == body.token)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise ApiError(
            "INVALID_VERIFICATION_TOKEN",
            "유효하지 않은 인증 토큰입니다.",
            http_status=400,
        )

    if user.email_verified:
        return {"data": {"verified": True, "already_verified": True}}

    # 만료 확인
    now = datetime.now(timezone.utc)
    expires = user.email_verification_expires_at
    if expires is None or (expires.tzinfo is None and expires < now.replace(tzinfo=None)):
        raise ApiError(
            "VERIFICATION_TOKEN_EXPIRED",
            "인증 링크가 만료되었습니다. 인증 메일을 다시 요청해주세요.",
            http_status=410,
        )
    if expires.tzinfo is not None and expires < now:
        raise ApiError(
            "VERIFICATION_TOKEN_EXPIRED",
            "인증 링크가 만료되었습니다. 인증 메일을 다시 요청해주세요.",
            http_status=410,
        )

    # 인증 완료 처리
    user.email_verified = True
    user.email_verification_token = None
    user.email_verification_expires_at = None
    await db.commit()

    await record_audit(
        db,
        actor=user,
        action="user.email_verified",
        metadata={"email": user.email},
        status="success",
    )

    return {"data": {"verified": True, "already_verified": False}}


@router.post("/email/verify/resend")
async def resend_verification_email(
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """이메일 인증 메일 재발송.

    - 이미 인증된 사용자 → 400 ALREADY_VERIFIED
    - 5분 cooldown 미충족 → 429 RESEND_TOO_SOON
    - 새 토큰 생성 후 발송
    """
    if user.email_verified:
        raise ApiError(
            "ALREADY_VERIFIED",
            "이미 이메일 인증이 완료된 계정입니다.",
            http_status=400,
        )

    # 5분 cooldown 확인
    now = datetime.now(timezone.utc)
    if user.email_verification_sent_at:
        sent_at = user.email_verification_sent_at
        # timezone-aware 처리
        if sent_at.tzinfo is None:
            sent_at = sent_at.replace(tzinfo=timezone.utc)
        elapsed_minutes = (now - sent_at).total_seconds() / 60
        if elapsed_minutes < RESEND_COOLDOWN_MINUTES:
            wait_seconds = int((RESEND_COOLDOWN_MINUTES * 60) - (now - sent_at).total_seconds())
            raise ApiError(
                "RESEND_TOO_SOON",
                f"인증 메일은 5분 후에 다시 요청할 수 있습니다. {wait_seconds}초 남았습니다.",
                http_status=429,
                details={"retry_after_seconds": wait_seconds},
            )

    # 새 토큰 생성
    token = generate_verification_token()
    expires = verification_expires_at()

    user.email_verification_token = token
    user.email_verification_sent_at = now
    user.email_verification_expires_at = expires
    await db.commit()

    send_result = await send_verification_email(
        email=user.email,
        display_name=user.display_name,
        token=token,
    )

    return {"data": {"sent": send_result.get("sent", False)}}
