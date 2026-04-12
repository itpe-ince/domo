"""Refresh token rotation service (Phase 4 M2).

Reference: phase4.design.md §2
"""
from __future__ import annotations

import hashlib
import logging
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import ApiError
from app.core.security import create_access_token
from app.models.auth_token import RefreshToken
from app.models.notification import Notification
from app.models.user import User

log = logging.getLogger(__name__)
settings = get_settings()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _hash(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _generate_raw_token() -> str:
    return secrets.token_urlsafe(48)


async def issue_initial_tokens(
    db: AsyncSession,
    user: User,
    *,
    user_agent: str | None = None,
    ip_address: str | None = None,
) -> tuple[str, str]:
    """Called on login — creates a new token family."""
    raw = _generate_raw_token()
    family_id = uuid.uuid4()
    expires = _now() + timedelta(days=settings.refresh_token_expire_days)

    record = RefreshToken(
        user_id=user.id,
        token_hash=_hash(raw),
        family_id=family_id,
        parent_id=None,
        expires_at=expires,
        user_agent=user_agent,
        ip_address=ip_address,
    )
    db.add(record)
    await db.flush()

    access = create_access_token(str(user.id), user.role, user.status)
    return access, raw


async def rotate_tokens(
    db: AsyncSession,
    raw_refresh_token: str,
    *,
    user_agent: str | None = None,
    ip_address: str | None = None,
) -> tuple[str, str]:
    """Rotate a refresh token. Detects reuse and revokes the whole family."""
    token_hash = _hash(raw_refresh_token)

    # Lock the row
    result = await db.execute(
        select(RefreshToken)
        .where(RefreshToken.token_hash == token_hash)
        .with_for_update()
    )
    record = result.scalar_one_or_none()
    if not record:
        raise ApiError("UNAUTHORIZED", "Invalid refresh token", http_status=401)

    if record.expires_at < _now():
        raise ApiError("UNAUTHORIZED", "Refresh token expired", http_status=401)

    # REUSE DETECTION: already rotated token re-submitted
    if record.revoked_at is not None and record.revoked_reason == "rotation":
        log.warning(
            "Refresh token reuse detected: user=%s family=%s",
            record.user_id,
            record.family_id,
        )
        # Revoke entire family
        await db.execute(
            update(RefreshToken)
            .where(
                RefreshToken.family_id == record.family_id,
                RefreshToken.revoked_at.is_(None),
            )
            .values(revoked_at=_now(), revoked_reason="family_compromised")
        )
        db.add(
            Notification(
                user_id=record.user_id,
                type="session_compromised",
                title="보안 경고: 세션 탈취 의심",
                body="이전 토큰 재사용이 탐지되어 모든 세션이 로그아웃되었습니다.",
                link="/auth/sessions",
            )
        )
        await db.commit()
        raise ApiError(
            "UNAUTHORIZED",
            "Token reuse detected, all sessions revoked",
            http_status=401,
        )

    if record.revoked_at is not None:
        raise ApiError("UNAUTHORIZED", "Token revoked", http_status=401)

    # Look up user (role may have changed)
    user_result = await db.execute(
        select(User).where(User.id == record.user_id)
    )
    user = user_result.scalar_one_or_none()
    if not user:
        raise ApiError("NOT_FOUND", "User not found", http_status=404)
    if user.status == "suspended":
        raise ApiError("ACCOUNT_SUSPENDED", "Account suspended", http_status=403)

    # Revoke current token
    record.revoked_at = _now()
    record.revoked_reason = "rotation"

    # Issue new token in same family
    new_raw = _generate_raw_token()
    new_record = RefreshToken(
        user_id=user.id,
        token_hash=_hash(new_raw),
        family_id=record.family_id,
        parent_id=record.id,
        expires_at=_now() + timedelta(days=settings.refresh_token_expire_days),
        user_agent=user_agent,
        ip_address=ip_address,
    )
    db.add(new_record)
    await db.commit()

    access = create_access_token(str(user.id), user.role, user.status)
    return access, new_raw


async def revoke_token(
    db: AsyncSession, raw_refresh_token: str, reason: str = "logout"
) -> None:
    """Revoke a specific refresh token (e.g. logout)."""
    token_hash = _hash(raw_refresh_token)
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    record = result.scalar_one_or_none()
    if record and record.revoked_at is None:
        record.revoked_at = _now()
        record.revoked_reason = reason
        await db.commit()


async def revoke_user_tokens(
    db: AsyncSession, user_id: uuid.UUID, *, reason: str
) -> int:
    """Revoke all active refresh tokens for a user."""
    result = await db.execute(
        update(RefreshToken)
        .where(
            RefreshToken.user_id == user_id,
            RefreshToken.revoked_at.is_(None),
        )
        .values(revoked_at=_now(), revoked_reason=reason)
    )
    return result.rowcount or 0


async def list_user_sessions(
    db: AsyncSession, user_id: uuid.UUID
) -> list[RefreshToken]:
    """Return active sessions for a user."""
    result = await db.execute(
        select(RefreshToken)
        .where(
            RefreshToken.user_id == user_id,
            RefreshToken.revoked_at.is_(None),
            RefreshToken.expires_at > _now(),
        )
        .order_by(RefreshToken.issued_at.desc())
    )
    return list(result.scalars().all())
