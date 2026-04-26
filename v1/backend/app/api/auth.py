from uuid import UUID

from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.errors import ApiError
from app.core.rate_limit import rate_limit
from app.db.session import get_db
from app.models.auth_token import RefreshToken
from app.models.user import User
from app.schemas.auth import (
    GoogleLoginRequest,
    RefreshRequest,
    TokenPair,
    UserPublic,
)
from app.services.auth_tokens import (
    issue_initial_tokens,
    list_user_sessions,
    revoke_token,
    rotate_tokens,
)
from app.services.google_auth import verify_google_id_token

router = APIRouter(prefix="/auth", tags=["auth"])


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
    if not user:
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
    body: RefreshRequest | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Revoke the provided refresh token. If body is omitted, just return OK."""
    if body and body.refresh_token:
        await revoke_token(db, body.refresh_token, reason="logout")
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
        from datetime import datetime, timezone

        record.revoked_at = datetime.now(timezone.utc)
        record.revoked_reason = "admin_action"
        await db.commit()
    return {"data": {"ok": True}}
