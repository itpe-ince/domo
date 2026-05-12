"""Payment provider factory.

Selects implementation based on PAYMENT_PROVIDER env var.
- 'mock_stripe' (default) → MockStripeProvider (in-memory, for dev)
- 'stripe' → StripeProvider (real Stripe API, Phase 4 M1)

Also provides get_coupon_provider() for D'-3 coupon infrastructure.
"""
from functools import lru_cache

from app.core.config import get_settings
from app.services.payments.base import PaymentProvider
from app.services.payments.coupon import CouponProvider
from app.services.payments.mock_stripe import MockStripeProvider


@lru_cache
def get_payment_provider() -> PaymentProvider:
    settings = get_settings()
    provider = getattr(settings, "payment_provider", "mock_stripe")

    if provider == "stripe":
        # Lazy import so dev environments without Stripe keys don't error
        from app.services.payments.stripe_real import StripeProvider

        return StripeProvider()

    if provider == "mock_stripe":
        return MockStripeProvider()

    raise ValueError(f"Unknown payment provider: {provider}")


@lru_cache
def get_coupon_provider() -> CouponProvider:
    """Return the appropriate CouponProvider based on PAYMENT_PROVIDER setting.

    - 'mock_stripe' (default) → MockCouponProvider
    - 'stripe' → StripeCouponProvider
    """
    settings = get_settings()
    provider = getattr(settings, "payment_provider", "mock_stripe")

    if provider == "stripe":
        from app.services.payments.coupon import StripeCouponProvider

        return StripeCouponProvider()

    from app.services.payments.coupon import MockCouponProvider

    return MockCouponProvider()
