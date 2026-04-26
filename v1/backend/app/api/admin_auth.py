"""Admin-only credential authentication (email + password + TOTP 2FA).

Admin accounts MUST authenticate here. SNS login is blocked for the
`admin` role in `app/api/auth.py:google_login`.

Flow:
    1. POST /auth/admin/login           {email, password}
       → if TOTP enabled: returns {challenge_token, totp_required: true}
       → else (first-time admin):       returns full token pair
    2. POST /auth/admin/login/verify    {challenge_token, totp_code}
       → returns full token pair

TOTP enrollment (must be done while authenticated):
    GET  /auth/admin/totp/setup         → {secret, otpauth_uri}
    POST /auth/admin/totp/enable        {totp_code}
    POST /auth/admin/totp/disable       {password}    (re-prompt to disable)
"""
import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import delete, func as sql_func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.errors import ApiError
from app.core.rate_limit import rate_limit
from app.core.security import (
    create_admin_challenge_token,
    decode_admin_challenge_token,
    encrypt_totp_secret,
    generate_recovery_codes,
    generate_totp_secret,
    hash_password,
    hash_recovery_code,
    totp_provisioning_uri,
    verify_password,
    verify_recovery_code,
    verify_totp,
)
from app.db.session import get_db
from app.models.auth_token import AdminRecoveryCode, RefreshToken
from app.models.user import User
from app.schemas.auth import TokenPair, UserPublic
from app.services.auth_tokens import issue_initial_tokens
from app.services.email.factory import get_email_provider
from app.services.email.templates.admin_login_alert import render as render_admin_login_alert

log = logging.getLogger(__name__)

router = APIRouter(prefix="/auth/admin", tags=["admin-auth"])

# Lockout policy: 5 consecutive failures → lock for 15 minutes
_MAX_FAILED_ATTEMPTS = 5
_LOCKOUT_DURATION = timedelta(minutes=15)


def _client_info(request: Request) -> tuple[str | None, str | None]:
    ua = request.headers.get("user-agent")
    ip = request.client.host if request.client else None
    return ua, ip


# ─── Request / Response schemas ────────────────────────────────────────
class AdminLoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=200)


class AdminTotpVerifyRequest(BaseModel):
    """Either a 6-digit TOTP code OR a recovery code must be provided."""
    challenge_token: str
    totp_code: str | None = Field(
        default=None, min_length=6, max_length=6, pattern=r"^\d{6}$"
    )
    recovery_code: str | None = Field(
        default=None, min_length=12, max_length=20
    )


class AdminTotpEnableRequest(BaseModel):
    totp_code: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")


class AdminTotpDisableRequest(BaseModel):
    password: str = Field(min_length=1, max_length=200)


class AdminRecoveryCodeRegenerateRequest(BaseModel):
    """Re-prompts password to issue a fresh batch (and invalidate old)."""
    password: str = Field(min_length=1, max_length=200)


# ─── Helpers ──────────────────────────────────────────────────────────
async def _load_admin_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(
        select(User).where(User.email == email.lower(), User.role == "admin")
    )
    return result.scalar_one_or_none()


async def _record_failed_attempt(db: AsyncSession, user: User) -> None:
    user.failed_login_count = (user.failed_login_count or 0) + 1
    if user.failed_login_count >= _MAX_FAILED_ATTEMPTS:
        user.locked_until = datetime.now(timezone.utc) + _LOCKOUT_DURATION
    await db.commit()


async def _reset_failed_attempts(db: AsyncSession, user: User) -> None:
    user.failed_login_count = 0
    user.locked_until = None


def _check_lockout(user: User) -> None:
    if user.locked_until and user.locked_until > datetime.now(timezone.utc):
        remaining = int((user.locked_until - datetime.now(timezone.utc)).total_seconds())
        raise ApiError(
            "ADMIN_LOCKED",
            f"Account locked. Try again in {remaining}s.",
            http_status=423,
            details={"locked_until": user.locked_until.isoformat()},
        )


# ─── Step 1: password ─────────────────────────────────────────────────
@router.post("/login")
async def admin_login(
    body: AdminLoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _rl=rate_limit("auth_login"),
):
    """Verify password. If TOTP enabled, return a challenge_token to be
    exchanged for tokens via /auth/admin/login/verify. If TOTP not yet
    enabled (first-run admin), return full tokens immediately AND signal
    that TOTP setup is required."""
    user = await _load_admin_by_email(db, body.email)
    # Constant-ish error to avoid leaking which step failed
    invalid = ApiError(
        "INVALID_CREDENTIALS", "Invalid email or password.", http_status=401
    )
    if not user or user.status != "active":
        raise invalid
    _check_lockout(user)
    if not user.password_hash:
        # Admin exists but never set a password — refuse rather than fall
        # back to insecure default. Operator must seed a password first.
        raise ApiError(
            "ADMIN_NO_PASSWORD",
            "Admin password not configured. Run the seed script or contact ops.",
            http_status=403,
        )
    if not verify_password(body.password, user.password_hash):
        await _record_failed_attempt(db, user)
        raise invalid

    await _reset_failed_attempts(db, user)

    if user.totp_enabled_at and user.totp_secret:
        challenge = create_admin_challenge_token(str(user.id))
        await db.commit()
        return {
            "data": {
                "totp_required": True,
                "challenge_token": challenge,
            }
        }

    # First-time admin: issue full tokens, but the client should redirect
    # to TOTP setup before letting the user do anything else.
    ua, ip = _client_info(request)
    # Check device BEFORE issuing tokens (so the new token doesn't itself
    # mark the device as known)
    await _maybe_send_login_alert(db, user, ua, ip, auth_method="password_only")
    access, refresh = await issue_initial_tokens(db, user, user_agent=ua, ip_address=ip)
    await db.commit()
    return {
        "data": {
            "totp_required": False,
            "totp_setup_required": True,
            "tokens": TokenPair(access_token=access, refresh_token=refresh).model_dump(),
            "user": UserPublic.model_validate(user).model_dump(mode="json"),
        }
    }


# ─── Step 2: TOTP ─────────────────────────────────────────────────────
@router.post("/login/verify")
async def admin_login_verify(
    body: AdminTotpVerifyRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _rl=rate_limit("auth_login"),
):
    try:
        payload = decode_admin_challenge_token(body.challenge_token)
    except ValueError as e:
        raise ApiError(
            "INVALID_CHALLENGE", "Challenge token invalid or expired.", http_status=401
        ) from e

    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == user_id, User.role == "admin"))
    user = result.scalar_one_or_none()
    if not user or user.status != "active":
        raise ApiError("INVALID_CREDENTIALS", "Account not available.", http_status=401)
    _check_lockout(user)
    if not (user.totp_secret and user.totp_enabled_at):
        raise ApiError(
            "TOTP_NOT_ENABLED",
            "TOTP is not enabled for this account.",
            http_status=400,
        )

    # Accept either TOTP code or one-time recovery code
    if not body.totp_code and not body.recovery_code:
        raise ApiError(
            "MISSING_CODE",
            "Provide totp_code or recovery_code.",
            http_status=400,
        )

    used_recovery: AdminRecoveryCode | None = None
    if body.totp_code:
        if not verify_totp(user.totp_secret, body.totp_code):
            await _record_failed_attempt(db, user)
            raise ApiError(
                "INVALID_TOTP", "Invalid authentication code.", http_status=401
            )
    else:
        # Recovery code path — find an unused code whose hash matches
        result = await db.execute(
            select(AdminRecoveryCode).where(
                AdminRecoveryCode.user_id == user.id,
                AdminRecoveryCode.used_at.is_(None),
            )
        )
        candidates = result.scalars().all()
        used_recovery = next(
            (c for c in candidates if verify_recovery_code(body.recovery_code or "", c.code_hash)),
            None,
        )
        if used_recovery is None:
            await _record_failed_attempt(db, user)
            raise ApiError(
                "INVALID_RECOVERY_CODE",
                "Invalid or already-used recovery code.",
                http_status=401,
            )

    await _reset_failed_attempts(db, user)
    ua, ip = _client_info(request)
    if used_recovery is not None:
        used_recovery.used_at = datetime.now(timezone.utc)
        used_recovery.used_user_agent = ua
        used_recovery.used_ip = ip
    # Detect new device BEFORE issuing the new refresh token
    await _maybe_send_login_alert(
        db, user, ua, ip,
        auth_method="recovery_code" if used_recovery else "totp",
    )
    access, refresh = await issue_initial_tokens(db, user, user_agent=ua, ip_address=ip)
    await db.commit()

    # Surface remaining recovery codes count so frontend can warn when low
    remaining_count = await _count_remaining_recovery_codes(db, user.id)
    return {
        "data": {
            "tokens": TokenPair(access_token=access, refresh_token=refresh).model_dump(),
            "user": UserPublic.model_validate(user).model_dump(mode="json"),
            "auth_method": "recovery_code" if used_recovery else "totp",
            "recovery_codes_remaining": remaining_count,
        }
    }


async def _count_remaining_recovery_codes(db: AsyncSession, user_id) -> int:
    from sqlalchemy import func as _func
    result = await db.execute(
        select(_func.count(AdminRecoveryCode.id)).where(
            AdminRecoveryCode.user_id == user_id,
            AdminRecoveryCode.used_at.is_(None),
        )
    )
    return int(result.scalar_one() or 0)


async def _issue_recovery_codes(db: AsyncSession, user: User) -> list[str]:
    """Wipe existing codes for user and issue 10 fresh plaintext codes
    (returned once for the admin to save). Caller must commit."""
    await db.execute(
        delete(AdminRecoveryCode).where(AdminRecoveryCode.user_id == user.id)
    )
    plain_codes = generate_recovery_codes(10)
    for code in plain_codes:
        db.add(
            AdminRecoveryCode(user_id=user.id, code_hash=hash_recovery_code(code))
        )
    return plain_codes


async def _is_known_device(
    db: AsyncSession, user_id, user_agent: str | None, ip: str | None
) -> bool:
    """Check whether (user_agent, ip) has been seen on any prior refresh
    token for this user. The CURRENT login's refresh token is excluded by
    calling this BEFORE issue_initial_tokens.

    UA matching: we use the first 80 chars (browser/OS prefix) to avoid
    false positives from minor version bumps. IP matching: exact (IPv4/v6)
    — too lenient (subnet) and we'd miss legitimate alerts; too strict
    (per-request) and mobile users get spammed."""
    if not user_agent and not ip:
        return True  # nothing to alert on
    ua_prefix = (user_agent or "")[:80]
    stmt = select(sql_func.count(RefreshToken.id)).where(
        RefreshToken.user_id == user_id,
    )
    if ua_prefix:
        # SQL `LIKE` with prefix match — index-friendly
        stmt = stmt.where(RefreshToken.user_agent.like(f"{ua_prefix}%"))
    if ip:
        stmt = stmt.where(RefreshToken.ip_address == ip)
    result = await db.execute(stmt)
    return int(result.scalar_one() or 0) > 0


async def _maybe_send_login_alert(
    db: AsyncSession,
    user: User,
    user_agent: str | None,
    ip: str | None,
    auth_method: str,
) -> None:
    """Fire-and-forget alert for new device login. Failures are logged
    only — never block the login flow."""
    try:
        if await _is_known_device(db, user.id, user_agent, ip):
            return
        provider = get_email_provider()
        msg = render_admin_login_alert(
            admin_email=user.email,
            admin_name=user.display_name or user.email,
            user_agent=user_agent,
            ip_address=ip,
            when=datetime.now(timezone.utc),
            auth_method=auth_method,
        )
        await provider.send(msg)
    except Exception as e:  # noqa: BLE001
        log.warning("admin_login_alert delivery failed: %s", e)


# ─── TOTP enrollment ──────────────────────────────────────────────────
@router.get("/totp/setup")
async def admin_totp_setup(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate (or regenerate while not yet enabled) a TOTP secret.
    Authenticated session required. Returns the otpauth:// URI which the
    client renders as a QR code, plus the raw secret as fallback.

    Re-running this endpoint while TOTP is already enabled is rejected;
    the admin must call /totp/disable first."""
    if user.role != "admin":
        raise ApiError("FORBIDDEN", "Admin only.", http_status=403)
    if user.totp_enabled_at:
        raise ApiError(
            "TOTP_ALREADY_ENABLED",
            "TOTP already enabled. Disable it first to re-enroll.",
            http_status=409,
        )
    secret = generate_totp_secret()
    # Store encrypted (auto-noop if no key) — but return plaintext to client
    # for QR / manual entry. verify_totp auto-decrypts on read.
    user.totp_secret = encrypt_totp_secret(secret)
    await db.commit()
    return {
        "data": {
            "secret": secret,
            "otpauth_uri": totp_provisioning_uri(secret, account_name=user.email),
            "issuer": "Domo Admin",
        }
    }


@router.post("/totp/enable")
async def admin_totp_enable(
    body: AdminTotpEnableRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if user.role != "admin":
        raise ApiError("FORBIDDEN", "Admin only.", http_status=403)
    if user.totp_enabled_at:
        raise ApiError(
            "TOTP_ALREADY_ENABLED", "TOTP already enabled.", http_status=409
        )
    if not user.totp_secret:
        raise ApiError(
            "TOTP_SETUP_MISSING",
            "Call /auth/admin/totp/setup first.",
            http_status=400,
        )
    if not verify_totp(user.totp_secret, body.totp_code):
        raise ApiError("INVALID_TOTP", "Invalid code.", http_status=401)
    user.totp_enabled_at = datetime.now(timezone.utc)
    # Issue 10 one-time recovery codes (shown ONCE here; only hashes stored)
    plain_codes = await _issue_recovery_codes(db, user)
    await db.commit()
    return {
        "data": {
            "enabled": True,
            "enabled_at": user.totp_enabled_at.isoformat(),
            "recovery_codes": plain_codes,
            "recovery_codes_warning": (
                "Save these codes offline. They will not be shown again. "
                "Each code works once if you lose access to your authenticator."
            ),
        }
    }


@router.post("/totp/disable")
async def admin_totp_disable(
    body: AdminTotpDisableRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Disable TOTP. Re-prompts password to prevent session-hijack abuse.
    All unused recovery codes are revoked at the same time."""
    if user.role != "admin":
        raise ApiError("FORBIDDEN", "Admin only.", http_status=403)
    if not user.password_hash or not verify_password(body.password, user.password_hash):
        raise ApiError(
            "INVALID_CREDENTIALS", "Password verification failed.", http_status=401
        )
    user.totp_secret = None
    user.totp_enabled_at = None
    await db.execute(
        delete(AdminRecoveryCode).where(AdminRecoveryCode.user_id == user.id)
    )
    await db.commit()
    return {"data": {"enabled": False}}


# ─── Recovery codes ────────────────────────────────────────────────────
@router.get("/recovery-codes/status")
async def admin_recovery_codes_status(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return remaining/used counts. Plaintext codes are NEVER returned
    here — only at generation/regeneration time."""
    if user.role != "admin":
        raise ApiError("FORBIDDEN", "Admin only.", http_status=403)
    from sqlalchemy import func as _func
    result = await db.execute(
        select(
            _func.count(AdminRecoveryCode.id).label("total"),
            _func.count(AdminRecoveryCode.used_at).label("used"),
        ).where(AdminRecoveryCode.user_id == user.id)
    )
    row = result.one()
    total = int(row.total or 0)
    used = int(row.used or 0)
    return {
        "data": {
            "total": total,
            "used": used,
            "remaining": total - used,
            "warning_low": (total - used) <= 2,
        }
    }


@router.post("/recovery-codes/regenerate")
async def admin_recovery_codes_regenerate(
    body: AdminRecoveryCodeRegenerateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Issue a fresh batch of 10 codes and invalidate the old set.
    Re-prompts password to prevent session-hijack abuse."""
    if user.role != "admin":
        raise ApiError("FORBIDDEN", "Admin only.", http_status=403)
    if not user.totp_enabled_at:
        raise ApiError(
            "TOTP_NOT_ENABLED",
            "Recovery codes require TOTP to be enabled first.",
            http_status=400,
        )
    if not user.password_hash or not verify_password(body.password, user.password_hash):
        raise ApiError(
            "INVALID_CREDENTIALS", "Password verification failed.", http_status=401
        )
    plain_codes = await _issue_recovery_codes(db, user)
    await db.commit()
    return {
        "data": {
            "recovery_codes": plain_codes,
            "recovery_codes_warning": (
                "Save these codes offline. They will not be shown again. "
                "All previously-issued codes have been invalidated."
            ),
        }
    }
