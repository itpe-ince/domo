"""KYC (Identity Verification) service with adapter pattern.

Providers:
  - mock: Instant verification for development
  - toss: Toss 신분증 인증 (Korea)
  - stripe: Stripe Identity (Global)
"""
from __future__ import annotations

import logging
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone

from app.core.config import get_settings

log = logging.getLogger(__name__)


@dataclass
class KYCStartResult:
    session_id: str
    redirect_url: str | None  # None for mock (no redirect needed)
    provider: str


@dataclass
class KYCVerifyResult:
    verified: bool
    provider: str
    name: str | None = None
    birth_year: int | None = None
    error: str | None = None


class KYCProvider(ABC):
    @abstractmethod
    async def start_verification(self, user_id: str, redirect_url: str) -> KYCStartResult:
        ...

    @abstractmethod
    async def check_status(self, session_id: str) -> KYCVerifyResult:
        ...

    async def verify_immediate(self, name: str, birth_year: int) -> KYCVerifyResult:
        """Optional fast-path for providers that support immediate verification (e.g. mock).

        Default raises NotImplementedError — only MockKYCProvider implements this.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} does not support verify_immediate"
        )


class MockKYCProvider(KYCProvider):
    """Dev mock — instant verification with name/birth_year input."""

    async def start_verification(self, user_id: str, redirect_url: str) -> KYCStartResult:
        return KYCStartResult(
            session_id=f"mock_{uuid.uuid4().hex[:8]}",
            redirect_url=None,  # No redirect for mock
            provider="mock",
        )

    async def check_status(self, session_id: str) -> KYCVerifyResult:
        return KYCVerifyResult(verified=True, provider="mock")

    async def verify_immediate(self, name: str, birth_year: int) -> KYCVerifyResult:
        """Mock-only: instant verification with provided data."""
        if not name or not birth_year:
            return KYCVerifyResult(verified=False, provider="mock", error="Name and birth_year required")
        return KYCVerifyResult(
            verified=True,
            provider="mock",
            name=name,
            birth_year=birth_year,
        )


class TossKYCProvider(KYCProvider):
    """Toss 신분증 인증 — placeholder for future integration."""

    def __init__(self, client_id: str, client_secret: str):
        log.warning(
            "TossKYCProvider initialised but not implemented — "
            "set KYC_PROVIDER=mock for development"
        )
        raise RuntimeError(
            "TossKYCProvider is not implemented yet. "
            "Set KYC_PROVIDER=mock in your environment for development."
        )

    async def start_verification(self, user_id: str, redirect_url: str) -> KYCStartResult:
        raise NotImplementedError("Toss KYC integration pending")

    async def check_status(self, session_id: str) -> KYCVerifyResult:
        raise NotImplementedError("Toss KYC integration pending")


class StripeIdentityProvider(KYCProvider):
    """Stripe Identity — placeholder for future integration."""

    def __init__(self, api_key: str):
        log.warning(
            "StripeIdentityProvider initialised but not implemented — "
            "set KYC_PROVIDER=mock for development"
        )
        raise RuntimeError(
            "StripeIdentityProvider is not implemented yet. "
            "Set KYC_PROVIDER=mock in your environment for development."
        )

    async def start_verification(self, user_id: str, redirect_url: str) -> KYCStartResult:
        raise NotImplementedError("Stripe Identity integration pending")

    async def check_status(self, session_id: str) -> KYCVerifyResult:
        raise NotImplementedError("Stripe Identity integration pending")


def get_kyc_provider() -> KYCProvider:
    settings = get_settings()
    provider = getattr(settings, "kyc_provider", "mock")

    if provider == "mock":
        return MockKYCProvider()
    elif provider == "toss":
        return TossKYCProvider(
            client_id=getattr(settings, "toss_client_id", ""),
            client_secret=getattr(settings, "toss_client_secret", ""),
        )
    elif provider == "stripe":
        return StripeIdentityProvider(api_key=settings.stripe_secret_key)
    else:
        log.warning("Unknown KYC provider '%s', falling back to mock", provider)
        return MockKYCProvider()


# ─── KYC Gate Helper (C2 gap fix) ───────────────────────────────────────────


async def require_kyc_verified(user, db) -> None:
    """Enforce KYC gate at transaction endpoints.

    Parameters
    ----------
    user : app.models.user.User
    db   : sqlalchemy.ext.asyncio.AsyncSession

    Behaviour is controlled by the ``kyc_enforcement`` system setting:

    * ``"off"``     — no-op (default in dev / CI so existing tests pass)
    * ``"soft"``    — logs a warning and sends an in-app Notification,
                      but does **not** raise; the request continues
    * ``"enforce"`` — raises ``ApiError("KYC_REQUIRED", ..., 403)``
                      when ``user.identity_verified_at`` is ``None``
    """
    from app.core.errors import ApiError
    from app.models.notification import Notification
    from app.services.settings import get_setting

    mode = await get_setting(db, "kyc_enforcement")
    if not isinstance(mode, str):
        mode = "off"

    if mode == "off":
        return

    if user.identity_verified_at is not None:
        # Already verified — passes in all modes
        return

    if mode == "soft":
        log.warning(
            "KYC not verified (soft gate): user_id=%s email=%s",
            user.id,
            user.email,
        )
        db.add(
            Notification(
                user_id=user.id,
                type="kyc_required_soft",
                title="본인 인증이 필요합니다",
                body="거래를 계속하려면 본인 인증을 완료해 주세요.",
                link="/settings/identity",
            )
        )
        return

    # mode == "enforce"
    raise ApiError(
        "KYC_REQUIRED",
        "Identity verification required to proceed",
        http_status=403,
    )
