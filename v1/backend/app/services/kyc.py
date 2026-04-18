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
    birth_date: str | None = None
    error: str | None = None


class KYCProvider(ABC):
    @abstractmethod
    async def start_verification(self, user_id: str, redirect_url: str) -> KYCStartResult:
        ...

    @abstractmethod
    async def check_status(self, session_id: str) -> KYCVerifyResult:
        ...


class MockKYCProvider(KYCProvider):
    """Dev mock — instant verification with name/birth input."""

    async def start_verification(self, user_id: str, redirect_url: str) -> KYCStartResult:
        return KYCStartResult(
            session_id=f"mock_{uuid.uuid4().hex[:8]}",
            redirect_url=None,  # No redirect for mock
            provider="mock",
        )

    async def check_status(self, session_id: str) -> KYCVerifyResult:
        return KYCVerifyResult(verified=True, provider="mock")

    async def mock_verify(self, name: str, birth_date: str) -> KYCVerifyResult:
        """Mock-only: instant verification with provided data."""
        if not name or not birth_date:
            return KYCVerifyResult(verified=False, provider="mock", error="Name and birth_date required")
        return KYCVerifyResult(
            verified=True,
            provider="mock",
            name=name,
            birth_date=birth_date,
        )


class TossKYCProvider(KYCProvider):
    """Toss 신분증 인증 — placeholder for future integration."""

    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret

    async def start_verification(self, user_id: str, redirect_url: str) -> KYCStartResult:
        # TODO: Call Toss API to create verification session
        raise NotImplementedError("Toss KYC integration pending — use mock provider")

    async def check_status(self, session_id: str) -> KYCVerifyResult:
        raise NotImplementedError("Toss KYC integration pending")


class StripeIdentityProvider(KYCProvider):
    """Stripe Identity — placeholder for future integration."""

    def __init__(self, api_key: str):
        self.api_key = api_key

    async def start_verification(self, user_id: str, redirect_url: str) -> KYCStartResult:
        raise NotImplementedError("Stripe Identity integration pending — use mock provider")

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
