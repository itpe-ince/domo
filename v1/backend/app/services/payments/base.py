"""Payment provider interface (Stripe-compatible).

Phase 2 prototype uses MockStripeProvider.
Real Stripe integration can be enabled later by setting PAYMENT_PROVIDER=stripe.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal


@dataclass
class PaymentIntent:
    id: str
    client_secret: str
    amount: Decimal
    currency: str
    status: str  # 'requires_payment_method' | 'succeeded' | 'failed'
    metadata: dict


@dataclass
class SubscriptionResult:
    id: str
    status: str  # 'active' | 'cancelled' | 'past_due'
    current_period_end_unix: int | None
    cancel_at_period_end: bool


class PaymentProvider(ABC):
    """Abstract payment provider — Stripe-compatible surface."""

    name: str

    @abstractmethod
    async def create_payment_intent(
        self,
        amount: Decimal,
        currency: str,
        metadata: dict | None = None,
    ) -> PaymentIntent: ...

    @abstractmethod
    async def confirm_payment_intent(self, intent_id: str) -> PaymentIntent:
        """Simulate user-side confirmation (mock only)."""

    @abstractmethod
    async def create_subscription(
        self,
        sponsor_id: str,
        artist_id: str,
        monthly_amount: Decimal,
        currency: str,
        metadata: dict | None = None,
    ) -> SubscriptionResult: ...

    @abstractmethod
    async def cancel_subscription(
        self, subscription_id: str, at_period_end: bool = True
    ) -> SubscriptionResult: ...

    @abstractmethod
    async def verify_webhook_signature(
        self, payload: bytes, signature: str | None
    ) -> dict:
        """Returns parsed event {type, data} or raises ValueError."""
