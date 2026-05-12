"""Coupon provider interface + implementations — D'-3.

Mirrors the PaymentProvider / MockStripeProvider / StripeProvider pattern
established in base.py, mock_stripe.py, and stripe_real.py.

Provides:
  CouponResult       — dataclass returned by create_coupon
  CouponProvider     — ABC (abstract)
  MockCouponProvider — in-memory stub for dev/test
  StripeCouponProvider — real Stripe API (requires STRIPE_SECRET_KEY)
"""
from __future__ import annotations

import asyncio
import secrets
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime


# ─── Domain types ────────────────────────────────────────────────────────────


@dataclass
class CouponResult:
    """Provider-agnostic coupon descriptor."""

    id: str                    # Stripe Coupon ID (or mock_coupon_... in mock mode)
    code: str | None           # Human-readable admin code, may be None
    discount_type: str         # 'percent' | 'amount'
    discount_value: int        # percent: 1-100, amount: cents
    duration: str              # 'once' | 'forever' | 'repeating'
    duration_in_months: int | None
    valid_until: datetime | None
    max_redemptions: int | None
    times_redeemed: int = 0
    active: bool = True
    metadata: dict = field(default_factory=dict)


# ─── Abstract provider ────────────────────────────────────────────────────────


class CouponProvider(ABC):
    """Abstract coupon provider — Stripe-compatible surface."""

    name: str

    @abstractmethod
    async def create_coupon(
        self,
        code: str,
        discount_type: str,            # 'percent' | 'amount'
        discount_value: int,
        duration: str,                 # 'once' | 'forever' | 'repeating'
        duration_in_months: int | None = None,
        valid_until: datetime | None = None,
        max_redemptions: int | None = None,
        idempotency_key: str | None = None,
    ) -> CouponResult: ...

    @abstractmethod
    async def get_coupon(self, coupon_id: str) -> CouponResult: ...

    @abstractmethod
    async def list_coupons(
        self, limit: int = 20, starting_after: str | None = None
    ) -> list[CouponResult]: ...

    @abstractmethod
    async def delete_coupon(self, coupon_id: str) -> bool:
        """Deactivate/delete the coupon. Returns True on success."""
        ...

    @abstractmethod
    async def attach_coupon_to_subscription(
        self,
        subscription_id: str,
        coupon_id: str,
        idempotency_key: str | None = None,
    ) -> bool:
        """Apply coupon to a Stripe subscription. Returns True on success."""
        ...


# ─── Mock implementation ──────────────────────────────────────────────────────

# In-memory store (dev/test only — ephemeral)
_mock_coupons: dict[str, CouponResult] = {}
_mock_sub_coupons: dict[str, list[str]] = {}  # subscription_id -> [coupon_id, ...]


def _mock_coupon_id(code: str) -> str:
    return f"mock_coupon_{code}_{secrets.token_hex(4)}"


class MockCouponProvider(CouponProvider):
    """In-memory mock — mirrors Stripe API surface for dev/test."""

    name = "mock_coupon"

    async def create_coupon(
        self,
        code: str,
        discount_type: str,
        discount_value: int,
        duration: str,
        duration_in_months: int | None = None,
        valid_until: datetime | None = None,
        max_redemptions: int | None = None,
        idempotency_key: str | None = None,
    ) -> CouponResult:
        # Idempotency: if a coupon with same code already exists, return it
        for c in _mock_coupons.values():
            if c.code == code and c.active:
                return c

        coupon_id = _mock_coupon_id(code)
        result = CouponResult(
            id=coupon_id,
            code=code,
            discount_type=discount_type,
            discount_value=discount_value,
            duration=duration,
            duration_in_months=duration_in_months,
            valid_until=valid_until,
            max_redemptions=max_redemptions,
        )
        _mock_coupons[coupon_id] = result
        return result

    async def get_coupon(self, coupon_id: str) -> CouponResult:
        coupon = _mock_coupons.get(coupon_id)
        if not coupon:
            raise ValueError(f"Coupon not found: {coupon_id}")
        return coupon

    async def list_coupons(
        self, limit: int = 20, starting_after: str | None = None
    ) -> list[CouponResult]:
        all_coupons = list(_mock_coupons.values())
        if starting_after:
            idx = next(
                (i for i, c in enumerate(all_coupons) if c.id == starting_after), -1
            )
            all_coupons = all_coupons[idx + 1 :] if idx >= 0 else all_coupons
        return all_coupons[:limit]

    async def delete_coupon(self, coupon_id: str) -> bool:
        coupon = _mock_coupons.get(coupon_id)
        if not coupon:
            raise ValueError(f"Coupon not found: {coupon_id}")
        coupon.active = False
        return True

    async def attach_coupon_to_subscription(
        self,
        subscription_id: str,
        coupon_id: str,
        idempotency_key: str | None = None,
    ) -> bool:
        if coupon_id not in _mock_coupons:
            raise ValueError(f"Coupon not found: {coupon_id}")
        if subscription_id not in _mock_sub_coupons:
            _mock_sub_coupons[subscription_id] = []
        if coupon_id not in _mock_sub_coupons[subscription_id]:
            _mock_sub_coupons[subscription_id].append(coupon_id)
        return True


# ─── Real Stripe implementation ───────────────────────────────────────────────


class StripeCouponProvider(CouponProvider):
    """Real Stripe coupon provider.

    Requires STRIPE_SECRET_KEY in settings (same as StripeProvider).
    All Stripe API calls are offloaded to asyncio.to_thread.
    """

    name = "stripe_coupon"

    def __init__(self):
        import stripe  # Lazy import

        from app.core.config import get_settings

        settings = get_settings()
        secret_key = settings.stripe_secret_key
        if not secret_key:
            raise RuntimeError(
                "StripeCouponProvider requires STRIPE_SECRET_KEY. "
                "Set PAYMENT_PROVIDER=mock_stripe for development."
            )
        stripe.api_key = secret_key
        self._stripe = stripe

    async def create_coupon(
        self,
        code: str,
        discount_type: str,
        discount_value: int,
        duration: str,
        duration_in_months: int | None = None,
        valid_until: datetime | None = None,
        max_redemptions: int | None = None,
        idempotency_key: str | None = None,
    ) -> CouponResult:
        stripe = self._stripe

        def _create():
            params: dict = {
                "id": code,  # Use code as Stripe Coupon ID for readability
                "duration": duration,
                "metadata": {"created_by": "domo_admin"},
            }
            if discount_type == "percent":
                params["percent_off"] = discount_value
            else:
                params["amount_off"] = discount_value
                # Stripe requires currency for amount_off coupons
                params["currency"] = "usd"
            if duration == "repeating" and duration_in_months:
                params["duration_in_months"] = duration_in_months
            if max_redemptions:
                params["max_redemptions"] = max_redemptions
            if valid_until:
                import time as _time

                params["redeem_by"] = int(valid_until.timestamp())

            create_kwargs: dict = {}
            if idempotency_key:
                create_kwargs["idempotency_key"] = idempotency_key

            return stripe.Coupon.create(**params, **create_kwargs)

        coupon = await asyncio.to_thread(_create)
        return _stripe_coupon_to_result(coupon, code)

    async def get_coupon(self, coupon_id: str) -> CouponResult:
        stripe = self._stripe

        def _retrieve():
            return stripe.Coupon.retrieve(coupon_id)

        coupon = await asyncio.to_thread(_retrieve)
        return _stripe_coupon_to_result(coupon)

    async def list_coupons(
        self, limit: int = 20, starting_after: str | None = None
    ) -> list[CouponResult]:
        stripe = self._stripe

        def _list():
            params: dict = {"limit": min(limit, 100)}
            if starting_after:
                params["starting_after"] = starting_after
            return stripe.Coupon.list(**params)

        response = await asyncio.to_thread(_list)
        return [_stripe_coupon_to_result(c) for c in response.data]

    async def delete_coupon(self, coupon_id: str) -> bool:
        stripe = self._stripe

        def _delete():
            return stripe.Coupon.delete(coupon_id)

        await asyncio.to_thread(_delete)
        return True

    async def attach_coupon_to_subscription(
        self,
        subscription_id: str,
        coupon_id: str,
        idempotency_key: str | None = None,
    ) -> bool:
        stripe = self._stripe

        def _modify():
            modify_kwargs: dict = {}
            if idempotency_key:
                modify_kwargs["idempotency_key"] = idempotency_key
            return stripe.Subscription.modify(
                subscription_id,
                coupon=coupon_id,
                **modify_kwargs,
            )

        await asyncio.to_thread(_modify)
        return True


# ─── G'-2 winback coupon helper ──────────────────────────────────────────────

# Maps cancellation reason to coupon specification.
_WINBACK_SPEC: dict[str, dict] = {
    "too_expensive": {
        "percent_off": 50,
        "duration": "repeating",
        "duration_in_months": 1,
    },
    "changed_mind": {
        "percent_off": 30,
        "duration": "repeating",
        "duration_in_months": 1,
    },
    "not_satisfied": {
        "percent_off": 20,
        "duration": "repeating",
        "duration_in_months": 1,
        # DM link returned by endpoint (Phase 8+ messaging infra carry-over)
        "dm_link_placeholder": True,
    },
    "other": {
        "percent_off": 10,
        "duration": "once",
        "duration_in_months": None,
    },
}


async def create_winback_coupon(
    provider: "CouponProvider",
    reason: str,
    subscription_id: str,
    idempotency_key: str | None = None,
) -> "CouponResult":
    """Create a winback coupon via provider based on cancellation reason.

    Maps reason → coupon spec (G'-2 §1.1).
    Raises ValueError for unknown reason.
    """
    spec = _WINBACK_SPEC.get(reason)
    if spec is None:
        raise ValueError(f"Unknown winback reason: {reason!r}")

    import secrets as _secrets

    # Coupon code: WINBACK_{REASON_UPPER}_{hex8} — readable + unique
    code = f"WINBACK_{reason.upper()}_{_secrets.token_hex(4).upper()}"

    return await provider.create_coupon(
        code=code,
        discount_type="percent",
        discount_value=spec["percent_off"],
        duration=spec["duration"],
        duration_in_months=spec.get("duration_in_months"),
        idempotency_key=idempotency_key,
    )


def winback_dm_link(reason: str) -> str | None:
    """Return DM placeholder link for not_satisfied reason (Phase 8+ carry-over)."""
    spec = _WINBACK_SPEC.get(reason, {})
    if spec.get("dm_link_placeholder"):
        # Phase 8+ DM infra: return None until messaging PDCA implemented
        return None
    return None


def _stripe_coupon_to_result(
    coupon, code: str | None = None
) -> CouponResult:
    """Convert a Stripe Coupon object to CouponResult."""
    discount_type = "percent" if coupon.percent_off is not None else "amount"
    discount_value = (
        int(coupon.percent_off)
        if discount_type == "percent"
        else int(coupon.amount_off or 0)
    )
    valid_until: datetime | None = None
    if getattr(coupon, "redeem_by", None):
        valid_until = datetime.fromtimestamp(coupon.redeem_by)

    return CouponResult(
        id=coupon.id,
        code=code or coupon.id,
        discount_type=discount_type,
        discount_value=discount_value,
        duration=coupon.duration,
        duration_in_months=getattr(coupon, "duration_in_months", None),
        valid_until=valid_until,
        max_redemptions=getattr(coupon, "max_redemptions", None),
        times_redeemed=getattr(coupon, "times_redeemed", 0),
        active=bool(getattr(coupon, "valid", True)),
        metadata=dict(getattr(coupon, "metadata", {}) or {}),
    )
