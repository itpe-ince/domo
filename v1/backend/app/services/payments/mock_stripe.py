"""Mock Stripe provider for prototype.

Stores in-memory state — sufficient for prototype demos.
Mirrors Stripe API surface so swapping to real Stripe later is just a factory swap.
"""
from __future__ import annotations

import json
import secrets
import time
from decimal import Decimal

from app.services.payments.base import (
    PaymentIntent,
    PaymentProvider,
    SubscriptionResult,
)

# Module-level in-memory stores (prototype only)
_intents: dict[str, PaymentIntent] = {}
_subscriptions: dict[str, SubscriptionResult] = {}


def _new_id(prefix: str) -> str:
    return f"{prefix}_mock_{secrets.token_hex(12)}"


class MockStripeProvider(PaymentProvider):
    name = "mock_stripe"

    async def create_payment_intent(
        self,
        amount: Decimal,
        currency: str,
        metadata: dict | None = None,
    ) -> PaymentIntent:
        intent_id = _new_id("pi")
        intent = PaymentIntent(
            id=intent_id,
            client_secret=f"{intent_id}_secret_{secrets.token_hex(8)}",
            amount=amount,
            currency=currency,
            status="requires_payment_method",
            metadata=metadata or {},
        )
        _intents[intent_id] = intent
        return intent

    async def confirm_payment_intent(self, intent_id: str) -> PaymentIntent:
        intent = _intents.get(intent_id)
        if not intent:
            raise ValueError(f"Unknown intent: {intent_id}")
        intent.status = "succeeded"
        _intents[intent_id] = intent
        return intent

    async def create_subscription(
        self,
        sponsor_id: str,
        artist_id: str,
        monthly_amount: Decimal,
        currency: str,
        metadata: dict | None = None,
    ) -> SubscriptionResult:
        sub_id = _new_id("sub")
        # Period: 30 days from now
        period_end = int(time.time()) + 30 * 24 * 3600
        result = SubscriptionResult(
            id=sub_id,
            status="active",
            current_period_end_unix=period_end,
            cancel_at_period_end=False,
        )
        _subscriptions[sub_id] = result
        return result

    async def cancel_subscription(
        self, subscription_id: str, at_period_end: bool = True
    ) -> SubscriptionResult:
        sub = _subscriptions.get(subscription_id)
        if not sub:
            raise ValueError(f"Unknown subscription: {subscription_id}")
        if at_period_end:
            sub.cancel_at_period_end = True
            # status stays 'active' until period_end
        else:
            sub.status = "cancelled"
            sub.cancel_at_period_end = False
        _subscriptions[subscription_id] = sub
        return sub

    async def verify_webhook_signature(
        self, payload: bytes, signature: str | None
    ) -> dict:
        # Mock: accept any payload, parse JSON directly
        try:
            event = json.loads(payload.decode("utf-8"))
        except Exception as e:
            raise ValueError(f"Invalid mock webhook payload: {e}") from e
        if "type" not in event:
            raise ValueError("Webhook event missing 'type'")
        return event
