"""Guardian consent service (Phase 4 M5).

Reference: phase4.design.md §7
"""
from __future__ import annotations

import logging
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.guardian import GuardianConsent
from app.models.notification import Notification
from app.models.user import User
from app.services.email import EmailMessage, get_email_provider
from app.services.settings import get_setting

log = logging.getLogger(__name__)

MAGIC_LINK_TTL_HOURS = 24

# Fallback if system_settings missing
DEFAULT_MINOR_AGE = {
    "KR": 14,
    "US": 13,
    "EU": 16,
    "JP": 18,
    "default": 16,
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def minor_age_threshold(db: AsyncSession, country_code: str | None) -> int:
    setting = await get_setting(db, "minor_age_by_country")
    if not isinstance(setting, dict):
        setting = DEFAULT_MINOR_AGE
    code = (country_code or "").upper()
    return int(setting.get(code, setting.get("default", 16)))


def calculate_age(birth_year: int) -> int:
    return _now().year - birth_year


async def is_minor(
    db: AsyncSession, birth_year: int | None, country_code: str | None
) -> bool:
    if birth_year is None:
        return False
    threshold = await minor_age_threshold(db, country_code)
    return calculate_age(birth_year) < threshold


async def get_active_consent(
    db: AsyncSession, minor_user_id
) -> GuardianConsent | None:
    result = await db.execute(
        select(GuardianConsent)
        .where(
            GuardianConsent.minor_user_id == minor_user_id,
            GuardianConsent.consented_at.is_not(None),
            GuardianConsent.withdrawn_at.is_(None),
        )
        .order_by(GuardianConsent.consented_at.desc())
    )
    return result.scalar_one_or_none()


async def request_guardian_consent(
    db: AsyncSession,
    minor: User,
    guardian_email: str,
    guardian_name: str | None = None,
) -> GuardianConsent:
    """Create a pending consent row and send the magic link email."""
    token = secrets.token_urlsafe(48)
    expires = _now() + timedelta(hours=MAGIC_LINK_TTL_HOURS)

    consent = GuardianConsent(
        minor_user_id=minor.id,
        guardian_email=guardian_email,
        guardian_name=guardian_name,
        consent_token=token,
        expires_at=expires,
    )
    db.add(consent)
    await db.flush()

    settings = get_settings()
    link = f"{settings.frontend_url}/guardian/consent/{token}"
    subject = f"[Domo] {minor.display_name}님의 보호자 동의 요청"
    text = (
        f"안녕하세요,\n\n"
        f"{minor.display_name}({minor.email})님이 Domo 플랫폼 사용을 위해 "
        f"보호자 동의를 요청했습니다.\n\n"
        f"다음 링크에서 동의해주세요 (24시간 내 만료):\n"
        f"{link}\n\n"
        f"링크를 클릭하시면 동의 또는 거절을 선택할 수 있습니다.\n"
    )
    html = f"""
        <div style="font-family: sans-serif; max-width: 600px;">
          <h2>Domo 보호자 동의 요청</h2>
          <p><strong>{minor.display_name}</strong> ({minor.email})님이
          Domo 플랫폼 사용을 위해 보호자 동의를 요청했습니다.</p>
          <p>아래 버튼을 눌러 동의 여부를 선택해주세요.</p>
          <p><a href="{link}" style="display:inline-block;padding:12px 24px;
          background:#A8D76E;color:#1A1410;text-decoration:none;
          border-radius:999px;font-weight:bold;">동의 링크 열기</a></p>
          <p style="color:#888;font-size:12px;">
            링크는 24시간 후 만료됩니다.<br>
            본인이 요청한 것이 아니라면 이 이메일을 무시해주세요.
          </p>
        </div>
    """.strip()

    provider = get_email_provider()
    try:
        await provider.send(
            EmailMessage(
                to=guardian_email,
                subject=subject,
                html=html,
                text=text,
                tags=["guardian_consent"],
            )
        )
    except Exception as e:  # noqa: BLE001
        log.exception("Failed to send guardian email: %s", e)
        # We still return the consent row — operator can re-trigger send

    return consent


async def approve_consent(
    db: AsyncSession, token: str
) -> GuardianConsent:
    """Guardian clicks magic link → approve."""
    result = await db.execute(
        select(GuardianConsent).where(GuardianConsent.consent_token == token)
    )
    consent = result.scalar_one_or_none()
    if not consent:
        raise ValueError("Invalid token")
    if consent.withdrawn_at is not None:
        raise ValueError("Consent already withdrawn")
    if consent.consented_at is not None:
        return consent
    if consent.expires_at < _now():
        raise ValueError("Magic link expired")

    consent.consented_at = _now()

    # Reactivate minor user if they were pending
    user_result = await db.execute(
        select(User).where(User.id == consent.minor_user_id)
    )
    minor = user_result.scalar_one_or_none()
    if minor:
        if minor.status == "pending_guardian":
            minor.status = "active"
        db.add(
            Notification(
                user_id=minor.id,
                type="guardian_consent_approved",
                title="보호자 동의 완료",
                body=f"{consent.guardian_email}님이 동의했습니다. 계정이 활성화되었습니다.",
                link="/",
            )
        )

    return consent


async def withdraw_consent(
    db: AsyncSession, token: str
) -> GuardianConsent:
    """Guardian withdraws previously given consent."""
    result = await db.execute(
        select(GuardianConsent).where(GuardianConsent.consent_token == token)
    )
    consent = result.scalar_one_or_none()
    if not consent:
        raise ValueError("Invalid token")
    if consent.consented_at is None:
        raise ValueError("Consent was never approved")
    if consent.withdrawn_at is not None:
        return consent

    consent.withdrawn_at = _now()

    user_result = await db.execute(
        select(User).where(User.id == consent.minor_user_id)
    )
    minor = user_result.scalar_one_or_none()
    if minor:
        minor.status = "guardian_revoked"
        db.add(
            Notification(
                user_id=minor.id,
                type="guardian_consent_withdrawn",
                title="보호자 동의 철회",
                body="보호자가 동의를 철회하여 계정이 비활성화되었습니다.",
            )
        )

    return consent
