"""Real Stripe payment provider (Phase 4 M1).

Reference: phase4.design.md §4

Uses the official Stripe Python SDK (sync) wrapped in asyncio.to_thread.
Requires:
- PAYMENT_PROVIDER=stripe
- STRIPE_SECRET_KEY (sk_test_... or sk_live_...)
- STRIPE_WEBHOOK_SECRET (whsec_...)

All Stripe API calls are offloaded to a thread pool so we don't block
the asyncio event loop.
"""
from __future__ import annotations

import asyncio
import json
from decimal import Decimal
from typing import Any

from app.core.config import get_settings
from app.services.payments.base import (
    PaymentIntent,
    PaymentProvider,
    SubscriptionResult,
)


class StripeProvider(PaymentProvider):
    """Real Stripe provider — production ready.

    Not imported at module load unless PAYMENT_PROVIDER=stripe,
    so development environments without the stripe SDK/API key
    still work fine with the mock provider.
    """

    name = "stripe"

    def __init__(self):
        import stripe  # Lazy import — only loaded when actually used

        settings = get_settings()
        self.secret_key = settings.stripe_secret_key
        self.webhook_secret = settings.stripe_webhook_secret

        if not self.secret_key:
            raise RuntimeError(
                "StripeProvider requires STRIPE_SECRET_KEY. "
                "Set PAYMENT_PROVIDER=mock_stripe for development."
            )

        stripe.api_key = self.secret_key
        # Hold a reference so test code can monkey-patch if needed
        self._stripe = stripe

    # ─── Payment Intents ────────────────────────────────────────────────

    async def create_payment_intent(
        self,
        amount: Decimal,
        currency: str,
        metadata: dict | None = None,
    ) -> PaymentIntent:
        stripe = self._stripe

        def _create():
            return stripe.PaymentIntent.create(
                amount=int(amount),  # Stripe expects smallest currency unit
                currency=currency.lower(),
                metadata=metadata or {},
                automatic_payment_methods={"enabled": True},
            )

        intent = await asyncio.to_thread(_create)
        return PaymentIntent(
            id=intent.id,
            client_secret=intent.client_secret or "",
            amount=Decimal(str(intent.amount)),
            currency=intent.currency.upper(),
            status=intent.status,
            metadata=dict(intent.metadata or {}),
        )

    async def confirm_payment_intent(self, intent_id: str) -> PaymentIntent:
        """For real Stripe, confirmation happens client-side.

        This method is mainly used by the mock provider. In production,
        we rely on webhook events instead. We still provide it for parity
        by retrieving the current state.
        """
        stripe = self._stripe

        def _retrieve():
            return stripe.PaymentIntent.retrieve(intent_id)

        intent = await asyncio.to_thread(_retrieve)
        return PaymentIntent(
            id=intent.id,
            client_secret=intent.client_secret or "",
            amount=Decimal(str(intent.amount)),
            currency=intent.currency.upper(),
            status=intent.status,
            metadata=dict(intent.metadata or {}),
        )

    # ─── Subscriptions ──────────────────────────────────────────────────

    async def create_subscription(
        self,
        sponsor_id: str,
        artist_id: str,
        monthly_amount: Decimal,
        currency: str,
        metadata: dict | None = None,
    ) -> SubscriptionResult:
        """Create a recurring subscription.

        Production implementation requires:
        1. A Stripe Customer for the sponsor (create on first use + store)
        2. A Price object for the monthly amount (dynamically created or cached)
        3. Subscription attached to the customer + price

        This implementation assumes the artist ID is used as a product key
        and creates Price objects on the fly. For real production you'd
        want to cache Customer/Price to avoid duplicate creations.
        """
        stripe = self._stripe

        def _create():
            # 1. Find or create product for this artist
            product = stripe.Product.create(
                name=f"Domo Bluebird Subscription — Artist {artist_id}",
                metadata={"artist_id": artist_id},
            )
            # 2. Create a recurring price
            price = stripe.Price.create(
                product=product.id,
                unit_amount=int(monthly_amount),
                currency=currency.lower(),
                recurring={"interval": "month"},
            )
            # 3. Create a customer for this sponsor (in production: cache/dedupe)
            customer = stripe.Customer.create(
                metadata={"sponsor_id": sponsor_id},
            )
            # 4. Create subscription
            sub = stripe.Subscription.create(
                customer=customer.id,
                items=[{"price": price.id}],
                metadata=metadata or {
                    "sponsor_id": sponsor_id,
                    "artist_id": artist_id,
                },
                payment_behavior="default_incomplete",
                payment_settings={"save_default_payment_method": "on_subscription"},
                expand=["latest_invoice.payment_intent"],
            )
            return sub

        sub = await asyncio.to_thread(_create)
        return SubscriptionResult(
            id=sub.id,
            status=sub.status,
            current_period_end_unix=sub.current_period_end,
            cancel_at_period_end=bool(sub.cancel_at_period_end),
        )

    async def cancel_subscription(
        self, subscription_id: str, at_period_end: bool = True
    ) -> SubscriptionResult:
        stripe = self._stripe

        def _cancel():
            if at_period_end:
                return stripe.Subscription.modify(
                    subscription_id,
                    cancel_at_period_end=True,
                )
            return stripe.Subscription.cancel(subscription_id)

        sub = await asyncio.to_thread(_cancel)
        return SubscriptionResult(
            id=sub.id,
            status=sub.status,
            current_period_end_unix=sub.current_period_end,
            cancel_at_period_end=bool(sub.cancel_at_period_end),
        )

    # ─── Webhooks ───────────────────────────────────────────────────────

    async def verify_webhook_signature(
        self, payload: bytes, signature: str | None
    ) -> dict[str, Any]:
        """Verify Stripe webhook signature using the configured secret.

        Raises ValueError on invalid signature.
        Returns the parsed event as a plain dict.
        """
        stripe = self._stripe

        if not signature:
            raise ValueError("Missing Stripe-Signature header")
        if not self.webhook_secret:
            raise ValueError("STRIPE_WEBHOOK_SECRET not configured")

        try:
            event = stripe.Webhook.construct_event(
                payload, signature, self.webhook_secret
            )
        except stripe.error.SignatureVerificationError as e:  # type: ignore
            raise ValueError(f"Invalid signature: {e}") from e
        except ValueError as e:
            raise ValueError(f"Invalid payload: {e}") from e

        # Convert Stripe's StripeObject to plain dict recursively
        # Easiest: to_dict_recursive (Stripe SDK) or JSON round-trip
        return json.loads(json.dumps(event, default=str))
