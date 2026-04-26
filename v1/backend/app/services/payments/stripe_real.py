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
import logging
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.services.payments.base import (
    PaymentIntent,
    PaymentProvider,
    SubscriptionResult,
)

log = logging.getLogger(__name__)


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
        db: AsyncSession | None = None,
    ) -> SubscriptionResult:
        """Create a recurring subscription with Stripe Customer/Price caching.

        On first call for a (artist_id, amount, currency) tuple, creates a
        Stripe Product + Price and persists to stripe_price_cache.
        On subsequent calls, reuses the cached stripe_price_id.

        Stripe Customer is cached on the User row (stripe_customer_id).
        ``db`` is optional for backwards compatibility — without it the caching
        is skipped and the old on-the-fly creation path is used.
        """
        stripe = self._stripe
        import uuid as _uuid

        # ── Load cached Customer and Price from DB ────────────────────────
        cached_customer_id: str | None = None
        cached_price_id: str | None = None

        if db is not None:
            from app.models.sponsorship import StripePriceCache
            from app.models.user import User

            try:
                sponsor_uuid = _uuid.UUID(sponsor_id)
                user_result = await db.execute(
                    select(User).where(User.id == sponsor_uuid)
                )
                sponsor_user = user_result.scalar_one_or_none()
                if sponsor_user and sponsor_user.stripe_customer_id:
                    cached_customer_id = sponsor_user.stripe_customer_id
            except Exception as exc:  # noqa: BLE001
                log.warning("stripe customer cache lookup failed: %s", exc)

            try:
                artist_uuid = _uuid.UUID(artist_id)
                price_result = await db.execute(
                    select(StripePriceCache).where(
                        StripePriceCache.artist_id == artist_uuid,
                        StripePriceCache.amount == monthly_amount,
                        StripePriceCache.currency == currency.upper(),
                    )
                )
                price_cache = price_result.scalar_one_or_none()
                if price_cache:
                    cached_price_id = price_cache.stripe_price_id
            except Exception as exc:  # noqa: BLE001
                log.warning("stripe price cache lookup failed: %s", exc)

        def _create(customer_id: str | None, price_id: str | None):
            # 1. Customer — find or create
            if customer_id:
                customer = stripe.Customer.retrieve(customer_id)
            else:
                customer = stripe.Customer.create(
                    metadata={"sponsor_id": sponsor_id},
                )

            # 2. Price — find or create
            if price_id:
                price = stripe.Price.retrieve(price_id)
            else:
                product = stripe.Product.create(
                    name=f"Domo Bluebird Subscription — Artist {artist_id}",
                    metadata={"artist_id": artist_id},
                )
                price = stripe.Price.create(
                    product=product.id,
                    unit_amount=int(monthly_amount),
                    currency=currency.lower(),
                    recurring={"interval": "month"},
                )

            # 3. Subscription
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
            return sub, customer.id, price.id, getattr(price, "product", None)

        sub, new_customer_id, new_price_id, product_id = await asyncio.to_thread(
            _create, cached_customer_id, cached_price_id
        )

        # ── Persist new Customer/Price to DB cache ────────────────────────
        if db is not None:
            try:
                from app.models.sponsorship import StripePriceCache
                from app.models.user import User

                if not cached_customer_id:
                    sponsor_uuid = _uuid.UUID(sponsor_id)
                    user_result = await db.execute(
                        select(User).where(User.id == sponsor_uuid)
                    )
                    sponsor_user = user_result.scalar_one_or_none()
                    if sponsor_user:
                        sponsor_user.stripe_customer_id = new_customer_id

                if not cached_price_id:
                    artist_uuid = _uuid.UUID(artist_id)
                    db.add(StripePriceCache(
                        artist_id=artist_uuid,
                        amount=monthly_amount,
                        currency=currency.upper(),
                        stripe_price_id=new_price_id,
                        stripe_product_id=str(product_id) if product_id else "",
                    ))

                await db.flush()
            except Exception as exc:  # noqa: BLE001
                log.warning("stripe cache persist failed: %s", exc)

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

    # ─── Refunds ────────────────────────────────────────────────────────

    async def refund(
        self,
        payment_intent_id: str,
        amount: Decimal | None = None,
        reason: str | None = None,
    ) -> dict:
        """Issue a Stripe refund for the given PaymentIntent.

        ``amount`` is in the smallest currency unit (e.g. cents / won).
        When ``None``, Stripe will refund the full charge.
        """
        stripe = self._stripe

        def _create():
            kwargs: dict = {"payment_intent": payment_intent_id}
            if amount is not None:
                kwargs["amount"] = int(amount)
            if reason is not None:
                # Stripe accepts: duplicate | fraudulent | requested_by_customer
                kwargs["reason"] = reason
            return stripe.Refund.create(**kwargs)

        refund_obj = await asyncio.to_thread(_create)
        return {
            "id": refund_obj.id,
            "payment_intent": refund_obj.payment_intent,
            "amount": str(refund_obj.amount),
            "reason": refund_obj.reason,
            "status": refund_obj.status,
        }

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
