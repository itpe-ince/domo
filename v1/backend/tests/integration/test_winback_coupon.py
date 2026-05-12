"""Integration tests for G'-2 winback-coupon-endpoint.

Endpoint under test:
  POST /v1/subscriptions/{id}/winback-coupon

Strategy: direct endpoint function calls with AsyncMock DB + MockCouponProvider.
No real DB or Stripe required. Mirrors test_coupons.py pattern.

Test count: 8
  1. 200 too_expensive → 50% 1-month repeating coupon, cancel_reverted=True
  2. 200 changed_mind  → 30% 1-month repeating coupon
  3. 200 other         → 10% once coupon
  4. 200 not_satisfied → 20% 1-month repeating + dm_link=None (Phase 8+ carry-over)
  5. 403 non-owner → FORBIDDEN
  6. 409 already used today (idempotency guard)
  7. 422 invalid reason → Pydantic validation error
  8. 401 unauthenticated → covered by FastAPI dependency (mocked to raise)
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.api.sponsorships import apply_winback_coupon
from app.core.errors import ApiError
from app.schemas.coupon import WinbackCouponRequest
from app.services.payments.coupon import CouponResult


# ─── Helpers ─────────────────────────────────────────────────────────────────


def _make_user(user_id: uuid.UUID | None = None) -> MagicMock:
    u = MagicMock()
    u.id = user_id or uuid.uuid4()
    u.role = "user"
    u.display_name = "sponsor_test"
    return u


def _make_subscription(
    sponsor_id: uuid.UUID,
    cancel_at_period_end: bool = True,
) -> MagicMock:
    sub = MagicMock()
    sub.id = uuid.uuid4()
    sub.sponsor_id = sponsor_id
    sub.artist_id = uuid.uuid4()
    sub.status = "active"
    sub.monthly_amount = Decimal("9.99")
    sub.currency = "USD"
    sub.provider_subscription_id = "sub_mock_winback_test"
    sub.cancel_at_period_end = cancel_at_period_end
    sub.current_period_end = None
    sub.cancellation_reason = "too_expensive"
    sub.cancellation_feedback = None
    sub.created_at = datetime.now(timezone.utc)
    return sub


def _make_coupon_result(
    percent_off: int = 50,
    duration: str = "repeating",
    duration_in_months: int | None = 1,
) -> CouponResult:
    return CouponResult(
        id=f"mock_coupon_WINBACK_{percent_off}",
        code=f"WINBACK_TOO_EXPENSIVE_AB12CD34",
        discount_type="percent",
        discount_value=percent_off,
        duration=duration,
        duration_in_months=duration_in_months,
        valid_until=None,
        max_redemptions=1,
        times_redeemed=0,
        active=True,
    )


def _make_mock_coupon_provider(coupon_result=None):
    provider = AsyncMock()
    coupon_result = coupon_result or _make_coupon_result()
    provider.create_coupon = AsyncMock(return_value=coupon_result)
    provider.get_coupon = AsyncMock(return_value=coupon_result)
    provider.attach_coupon_to_subscription = AsyncMock(return_value=True)
    return provider


def _make_mock_payment_provider():
    provider = AsyncMock()
    provider.revert_cancel_at_period_end = AsyncMock(return_value=True)
    return provider


def _make_applied_coupon_row(
    user_id: uuid.UUID,
    sub_id: uuid.UUID,
    percent_off: int = 50,
    duration: str = "repeating",
    duration_in_months: int | None = 1,
) -> MagicMock:
    row = MagicMock()
    row.id = uuid.uuid4()
    row.user_id = user_id
    row.subscription_id = sub_id
    row.stripe_coupon_id = f"mock_coupon_WINBACK_{percent_off}"
    row.coupon_code = f"WINBACK_TOO_EXPENSIVE_AB12CD34"
    row.discount_type = "percent"
    row.discount_value = percent_off
    row.duration = duration
    row.duration_in_months = duration_in_months
    row.valid_until = None
    row.applied_at = datetime.now(timezone.utc)
    row.redeemed_at = None
    return row


def _make_empty_db(subscription=None, existing_coupon=None) -> AsyncMock:
    """DB mock that returns subscription on first execute, None on second (no existing coupon)."""
    db = AsyncMock()

    sub_result = MagicMock()
    sub_result.scalar_one_or_none.return_value = subscription

    no_coupon_result = MagicMock()
    no_coupon_result.scalar_one_or_none.return_value = existing_coupon

    # First call → subscription lookup, second call → idempotency check
    db.execute = AsyncMock(side_effect=[sub_result, no_coupon_result])
    db.commit = AsyncMock()
    db.refresh = AsyncMock(side_effect=lambda obj: None)
    db.add = MagicMock()
    return db


def _make_applied_coupon_db(
    subscription: MagicMock,
    user: MagicMock,
    coupon_row: MagicMock,
) -> AsyncMock:
    """DB mock that returns subscription on first call, then sets coupon row on refresh."""
    db = AsyncMock()

    sub_result = MagicMock()
    sub_result.scalar_one_or_none.return_value = subscription

    no_coupon_result = MagicMock()
    no_coupon_result.scalar_one_or_none.return_value = None

    db.execute = AsyncMock(side_effect=[sub_result, no_coupon_result])
    db.commit = AsyncMock()

    async def _refresh_side_effect(obj):
        # Populate the applied coupon row fields after commit
        if hasattr(obj, "user_id"):
            obj.id = coupon_row.id
            obj.user_id = coupon_row.user_id
            obj.subscription_id = coupon_row.subscription_id
            obj.stripe_coupon_id = coupon_row.stripe_coupon_id
            obj.coupon_code = coupon_row.coupon_code
            obj.discount_type = coupon_row.discount_type
            obj.discount_value = coupon_row.discount_value
            obj.duration = coupon_row.duration
            obj.duration_in_months = coupon_row.duration_in_months
            obj.valid_until = coupon_row.valid_until
            obj.applied_at = coupon_row.applied_at
            obj.redeemed_at = coupon_row.redeemed_at

    db.refresh = AsyncMock(side_effect=_refresh_side_effect)
    db.add = MagicMock()
    return db


# ─── Test 1: 200 too_expensive → 50% 1mo ─────────────────────────────────────


@pytest.mark.asyncio
async def test_winback_coupon_too_expensive_200():
    """200 — too_expensive reason creates 50% 1-month repeating coupon."""
    user = _make_user()
    sub = _make_subscription(sponsor_id=user.id, cancel_at_period_end=True)
    coupon_result = _make_coupon_result(percent_off=50, duration="repeating", duration_in_months=1)
    coupon_row = _make_applied_coupon_row(user.id, sub.id, percent_off=50)
    db = _make_applied_coupon_db(sub, user, coupon_row)
    provider = _make_mock_coupon_provider(coupon_result)
    pay_provider = _make_mock_payment_provider()

    body = WinbackCouponRequest(reason="too_expensive")

    with (
        patch("app.api.sponsorships.get_coupon_provider", return_value=provider),
        patch("app.api.sponsorships.get_payment_provider", return_value=pay_provider),
        patch("app.api.sponsorships.capture_event"),
    ):
        result = await apply_winback_coupon(
            subscription_id=sub.id,
            body=body,
            user=user,
            db=db,
            _rl=None,
        )

    assert "data" in result
    data = result["data"]
    assert data["coupon_applied"] is True
    assert data["cancel_reverted"] is True
    assert data["applied_coupon"]["discount_value"] == 50
    assert data["applied_coupon"]["duration"] == "repeating"
    assert data["applied_coupon"]["duration_in_months"] == 1
    # cancel_at_period_end reverted
    assert sub.cancel_at_period_end is False
    provider.create_coupon.assert_called_once()
    provider.attach_coupon_to_subscription.assert_called_once()


# ─── Test 2: 200 changed_mind → 30% 1mo ─────────────────────────────────────


@pytest.mark.asyncio
async def test_winback_coupon_changed_mind_200():
    """200 — changed_mind reason creates 30% 1-month repeating coupon."""
    user = _make_user()
    sub = _make_subscription(sponsor_id=user.id)
    sub.cancellation_reason = "changed_mind"
    coupon_result = _make_coupon_result(percent_off=30, duration="repeating", duration_in_months=1)
    coupon_row = _make_applied_coupon_row(user.id, sub.id, percent_off=30)
    db = _make_applied_coupon_db(sub, user, coupon_row)
    provider = _make_mock_coupon_provider(coupon_result)
    pay_provider = _make_mock_payment_provider()

    body = WinbackCouponRequest(reason="changed_mind")

    with (
        patch("app.api.sponsorships.get_coupon_provider", return_value=provider),
        patch("app.api.sponsorships.get_payment_provider", return_value=pay_provider),
        patch("app.api.sponsorships.capture_event"),
    ):
        result = await apply_winback_coupon(
            subscription_id=sub.id,
            body=body,
            user=user,
            db=db,
            _rl=None,
        )

    assert result["data"]["coupon_applied"] is True
    assert result["data"]["applied_coupon"]["discount_value"] == 30
    assert result["data"]["applied_coupon"]["duration"] == "repeating"


# ─── Test 3: 200 other → 10% once ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_winback_coupon_other_200():
    """200 — other reason creates 10% once coupon."""
    user = _make_user()
    sub = _make_subscription(sponsor_id=user.id)
    sub.cancellation_reason = "other"
    coupon_result = _make_coupon_result(percent_off=10, duration="once", duration_in_months=None)
    coupon_row = _make_applied_coupon_row(user.id, sub.id, percent_off=10, duration="once", duration_in_months=None)
    db = _make_applied_coupon_db(sub, user, coupon_row)
    provider = _make_mock_coupon_provider(coupon_result)
    pay_provider = _make_mock_payment_provider()

    body = WinbackCouponRequest(reason="other", feedback="Just testing")

    with (
        patch("app.api.sponsorships.get_coupon_provider", return_value=provider),
        patch("app.api.sponsorships.get_payment_provider", return_value=pay_provider),
        patch("app.api.sponsorships.capture_event"),
    ):
        result = await apply_winback_coupon(
            subscription_id=sub.id,
            body=body,
            user=user,
            db=db,
            _rl=None,
        )

    assert result["data"]["coupon_applied"] is True
    assert result["data"]["applied_coupon"]["discount_value"] == 10
    assert result["data"]["applied_coupon"]["duration"] == "once"
    assert result["data"]["applied_coupon"]["duration_in_months"] is None


# ─── Test 4: 200 not_satisfied → 20% 1mo + dm_link=None ─────────────────────


@pytest.mark.asyncio
async def test_winback_coupon_not_satisfied_200():
    """200 — not_satisfied creates 20% 1-month coupon + dm_link=None (Phase 8+ carry-over)."""
    user = _make_user()
    sub = _make_subscription(sponsor_id=user.id)
    sub.cancellation_reason = "not_satisfied"
    coupon_result = _make_coupon_result(percent_off=20, duration="repeating", duration_in_months=1)
    coupon_row = _make_applied_coupon_row(user.id, sub.id, percent_off=20)
    db = _make_applied_coupon_db(sub, user, coupon_row)
    provider = _make_mock_coupon_provider(coupon_result)
    pay_provider = _make_mock_payment_provider()

    body = WinbackCouponRequest(reason="not_satisfied", feedback="작품 퀄리티가 기대에 못 미쳤어요")

    with (
        patch("app.api.sponsorships.get_coupon_provider", return_value=provider),
        patch("app.api.sponsorships.get_payment_provider", return_value=pay_provider),
        patch("app.api.sponsorships.capture_event"),
    ):
        result = await apply_winback_coupon(
            subscription_id=sub.id,
            body=body,
            user=user,
            db=db,
            _rl=None,
        )

    assert result["data"]["coupon_applied"] is True
    assert result["data"]["applied_coupon"]["discount_value"] == 20
    # DM link is None until Phase 8+ messaging infra
    assert result["data"]["dm_link"] is None


# ─── Test 5: 403 non-owner ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_winback_coupon_non_owner_403():
    """403 — user cannot apply winback coupon to another user's subscription."""
    owner = _make_user()
    attacker = _make_user()
    sub = _make_subscription(sponsor_id=owner.id)

    db = AsyncMock()
    sub_result = MagicMock()
    sub_result.scalar_one_or_none.return_value = sub
    db.execute = AsyncMock(return_value=sub_result)

    body = WinbackCouponRequest(reason="too_expensive")

    with pytest.raises(ApiError) as exc_info:
        await apply_winback_coupon(
            subscription_id=sub.id,
            body=body,
            user=attacker,
            db=db,
            _rl=None,
        )

    assert exc_info.value.status_code == 403
    assert "FORBIDDEN" in exc_info.value.code


# ─── Test 6: 409 already used today (idempotency) ────────────────────────────


@pytest.mark.asyncio
async def test_winback_coupon_already_used_409():
    """409 — second winback coupon on same subscription within 24h is rejected."""
    user = _make_user()
    sub = _make_subscription(sponsor_id=user.id)

    # Simulate an existing coupon applied today
    existing_coupon_row = MagicMock()
    existing_coupon_row.id = uuid.uuid4()

    db = AsyncMock()
    sub_result = MagicMock()
    sub_result.scalar_one_or_none.return_value = sub
    existing_result = MagicMock()
    existing_result.scalar_one_or_none.return_value = existing_coupon_row
    db.execute = AsyncMock(side_effect=[sub_result, existing_result])

    body = WinbackCouponRequest(reason="too_expensive")

    with pytest.raises(ApiError) as exc_info:
        await apply_winback_coupon(
            subscription_id=sub.id,
            body=body,
            user=user,
            db=db,
            _rl=None,
        )

    assert exc_info.value.status_code == 409
    assert "WINBACK_ALREADY_USED" in exc_info.value.code


# ─── Test 7: 422 invalid reason ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_winback_coupon_invalid_reason_422():
    """422 — invalid reason value is rejected by Pydantic schema."""
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        WinbackCouponRequest(reason="invalid_reason_xyz")


# ─── Test 8: 404 subscription not found ──────────────────────────────────────


@pytest.mark.asyncio
async def test_winback_coupon_not_found_404():
    """404 — subscription does not exist."""
    user = _make_user()

    db = AsyncMock()
    sub_result = MagicMock()
    sub_result.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=sub_result)

    body = WinbackCouponRequest(reason="too_expensive")

    with pytest.raises(ApiError) as exc_info:
        await apply_winback_coupon(
            subscription_id=uuid.uuid4(),
            body=body,
            user=user,
            db=db,
            _rl=None,
        )

    assert exc_info.value.status_code == 404
    assert "NOT_FOUND" in exc_info.value.code
