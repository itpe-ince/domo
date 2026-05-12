"""Integration tests for D'-3 stripe-coupon-foundation.

Endpoints under test:
  POST   /admin/coupons              — admin creates coupon
  GET    /admin/coupons              — admin lists coupons
  DELETE /admin/coupons/{id}         — admin deletes coupon
  POST   /me/coupons/apply           — user applies coupon
  GET    /me/coupons                 — user lists own coupons

Strategy: direct endpoint function calls with AsyncMock DB + MockCouponProvider.
No real DB or Stripe required. Mirrors test_subscription_cancel_tracking.py pattern.

Test count: 10
  admin_create_coupon:
    1. 201 admin creates percent coupon
    2. 403 non-admin is rejected
  admin_list_coupons:
    3. 200 admin lists coupons (pagination)
  admin_delete_coupon:
    4. 204 admin deletes coupon
    5. 404 deleting unknown coupon
  apply_coupon:
    6. 200 user applies own subscription coupon
    7. 403 user cannot apply to another's subscription
    8. 409 coupon already applied (duplicate)
  list_my_coupons:
    9. 200 user lists own coupons
  validation:
    10. 422 invalid coupon code format
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.api.admin_coupons import admin_create_coupon, admin_delete_coupon, admin_list_coupons
from app.api.me_coupons import apply_coupon, list_my_coupons
from app.core.errors import ApiError
from app.schemas.coupon import AdminCreateCouponRequest, ApplyCouponRequest
from app.services.payments.coupon import CouponResult


# ─── Helpers ─────────────────────────────────────────────────────────────────


def _make_admin() -> MagicMock:
    u = MagicMock()
    u.id = uuid.uuid4()
    u.role = "admin"
    u.totp_enabled_at = datetime.now(timezone.utc)
    return u


def _make_user() -> MagicMock:
    u = MagicMock()
    u.id = uuid.uuid4()
    u.role = "user"
    return u


def _make_subscription(sponsor_id: uuid.UUID) -> MagicMock:
    sub = MagicMock()
    sub.id = uuid.uuid4()
    sub.sponsor_id = sponsor_id
    sub.artist_id = uuid.uuid4()
    sub.status = "active"
    sub.monthly_amount = Decimal("9.99")
    sub.currency = "USD"
    sub.provider_subscription_id = "sub_mock_test123"
    sub.cancel_at_period_end = False
    sub.current_period_end = None
    sub.created_at = datetime.now(timezone.utc)
    return sub


def _make_coupon_result(code: str = "TEST50") -> CouponResult:
    return CouponResult(
        id=f"mock_coupon_{code}",
        code=code,
        discount_type="percent",
        discount_value=50,
        duration="once",
        duration_in_months=None,
        valid_until=None,
        max_redemptions=100,
        times_redeemed=0,
        active=True,
    )


def _make_applied_coupon_row(user_id: uuid.UUID, sub_id: uuid.UUID) -> MagicMock:
    row = MagicMock()
    row.id = uuid.uuid4()
    row.user_id = user_id
    row.subscription_id = sub_id
    row.stripe_coupon_id = "mock_coupon_TEST50"
    row.coupon_code = "TEST50"
    row.discount_type = "percent"
    row.discount_value = 50
    row.duration = "once"
    row.duration_in_months = None
    row.valid_until = None
    row.applied_at = datetime.now(timezone.utc)
    row.redeemed_at = None
    return row


def _make_empty_db() -> AsyncMock:
    db = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = None
    result_mock.scalars.return_value.all.return_value = []
    db.execute = AsyncMock(return_value=result_mock)
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.add = MagicMock()
    return db


def _make_mock_coupon_provider(coupon_result=None):
    provider = AsyncMock()
    coupon_result = coupon_result or _make_coupon_result()
    provider.create_coupon = AsyncMock(return_value=coupon_result)
    provider.get_coupon = AsyncMock(return_value=coupon_result)
    provider.list_coupons = AsyncMock(return_value=[coupon_result])
    provider.delete_coupon = AsyncMock(return_value=True)
    provider.attach_coupon_to_subscription = AsyncMock(return_value=True)
    return provider


# ─── Test 1: admin creates percent coupon ────────────────────────────────────


@pytest.mark.asyncio
async def test_admin_create_coupon_201():
    """201 — admin successfully creates a percent coupon."""
    admin = _make_admin()
    db = _make_empty_db()
    provider = _make_mock_coupon_provider()

    body = AdminCreateCouponRequest(
        code="WINBACK50",
        discount_type="percent",
        discount_value=50,
        duration="once",
    )

    with patch("app.api.admin_coupons.get_coupon_provider", return_value=provider):
        result = await admin_create_coupon(body=body, admin=admin, db=db, _rl=None)

    assert "data" in result
    assert result["data"]["discount_value"] == 50
    assert result["data"]["discount_type"] == "percent"
    provider.create_coupon.assert_called_once()


# ─── Test 2: non-admin is rejected ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_admin_create_coupon_403_non_admin():
    """403 — non-admin cannot create coupons (require_admin_with_2fa gate)."""
    from app.core.admin_deps import require_admin_with_2fa

    regular_user = _make_user()
    db = AsyncMock()
    # No WebauthnCredential rows
    credential_result = MagicMock()
    credential_result.scalar_one.return_value = 0
    db.execute = AsyncMock(return_value=credential_result)

    with pytest.raises(ApiError) as exc_info:
        await require_admin_with_2fa(user=regular_user, db=db)

    assert exc_info.value.status_code == 403


# ─── Test 3: admin lists coupons ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_admin_list_coupons_200():
    """200 — admin gets a list of coupons with pagination."""
    admin = _make_admin()
    db = _make_empty_db()
    provider = _make_mock_coupon_provider()

    with patch("app.api.admin_coupons.get_coupon_provider", return_value=provider):
        result = await admin_list_coupons(
            limit=20, starting_after=None, admin=admin, db=db
        )

    assert "data" in result
    assert isinstance(result["data"], list)
    assert len(result["data"]) == 1
    assert result["data"][0]["code"] == "TEST50"
    provider.list_coupons.assert_called_once_with(limit=20, starting_after=None)


# ─── Test 4: admin deletes coupon ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_admin_delete_coupon_204():
    """204 — admin successfully deletes a coupon."""
    admin = _make_admin()
    db = _make_empty_db()
    provider = _make_mock_coupon_provider()

    with patch("app.api.admin_coupons.get_coupon_provider", return_value=provider):
        result = await admin_delete_coupon(
            coupon_id="mock_coupon_TEST50", admin=admin, db=db, _rl=None
        )

    assert result is None
    provider.delete_coupon.assert_called_once_with("mock_coupon_TEST50")


# ─── Test 5: admin deletes unknown coupon ────────────────────────────────────


@pytest.mark.asyncio
async def test_admin_delete_coupon_404_unknown():
    """404 — deleting a non-existent coupon raises COUPON_NOT_FOUND."""
    admin = _make_admin()
    db = _make_empty_db()
    provider = _make_mock_coupon_provider()
    provider.delete_coupon = AsyncMock(side_effect=ValueError("Coupon not found: NOSUCHCOUPON"))

    with patch("app.api.admin_coupons.get_coupon_provider", return_value=provider):
        with pytest.raises(ApiError) as exc_info:
            await admin_delete_coupon(
                coupon_id="NOSUCHCOUPON", admin=admin, db=db, _rl=None
            )

    assert exc_info.value.code == "COUPON_NOT_FOUND"
    assert exc_info.value.status_code == 404


# ─── Test 6: user applies own subscription coupon ────────────────────────────


@pytest.mark.asyncio
async def test_apply_coupon_200_own_subscription():
    """200 — user applies a coupon to their own subscription."""
    user = _make_user()
    subscription = _make_subscription(sponsor_id=user.id)
    coupon_result = _make_coupon_result("TEST50")

    call_count = [0]

    db = AsyncMock()

    async def execute(query):
        call_count[0] += 1
        result = MagicMock()
        if call_count[0] == 1:
            # Subscription lookup
            result.scalar_one_or_none.return_value = subscription
        elif call_count[0] == 2:
            # Duplicate check — no existing row
            result.scalar_one_or_none.return_value = None
        return result

    db.execute = execute
    db.commit = AsyncMock()
    applied_row = _make_applied_coupon_row(user.id, subscription.id)
    db.refresh = AsyncMock(side_effect=lambda row: None)

    provider = _make_mock_coupon_provider(coupon_result)

    body = ApplyCouponRequest(coupon_code="TEST50", subscription_id=subscription.id)

    with patch("app.api.me_coupons.get_coupon_provider", return_value=provider):
        # Don't patch AppliedCoupon class — select(AppliedCoupon) on line 86 needs the real class.
        # Instead, allow constructor to create a real instance and mock only model_validate.
        with patch(
            "app.api.me_coupons.AppliedCouponOut.model_validate",
            return_value=_make_applied_coupon_schema(user.id, subscription.id),
        ):
            result = await apply_coupon(body=body, user=user, db=db, _rl=None)

    assert "data" in result
    provider.get_coupon.assert_called_once_with("TEST50")
    provider.attach_coupon_to_subscription.assert_called_once()
    db.commit.assert_called_once()


def _make_applied_coupon_schema(user_id, sub_id):
    from app.schemas.coupon import AppliedCouponOut

    return AppliedCouponOut(
        id=uuid.uuid4(),
        user_id=user_id,
        subscription_id=sub_id,
        stripe_coupon_id="mock_coupon_TEST50",
        coupon_code="TEST50",
        discount_type="percent",
        discount_value=50,
        duration="once",
        duration_in_months=None,
        valid_until=None,
        applied_at=datetime.now(timezone.utc),
        redeemed_at=None,
    )


# ─── Test 7: user cannot apply to another's subscription ─────────────────────


@pytest.mark.asyncio
async def test_apply_coupon_403_others_subscription():
    """403 — user cannot apply coupon to another user's subscription."""
    user = _make_user()
    other_user = _make_user()
    subscription = _make_subscription(sponsor_id=other_user.id)

    db = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = subscription
    db.execute = AsyncMock(return_value=result_mock)

    provider = _make_mock_coupon_provider()
    body = ApplyCouponRequest(coupon_code="TEST50", subscription_id=subscription.id)

    with patch("app.api.me_coupons.get_coupon_provider", return_value=provider):
        with pytest.raises(ApiError) as exc_info:
            await apply_coupon(body=body, user=user, db=db, _rl=None)

    assert exc_info.value.status_code == 403
    assert exc_info.value.code == "FORBIDDEN"


# ─── Test 8: duplicate coupon application ────────────────────────────────────


@pytest.mark.asyncio
async def test_apply_coupon_409_already_applied():
    """409 — coupon already applied to this subscription."""
    user = _make_user()
    subscription = _make_subscription(sponsor_id=user.id)
    existing_row = _make_applied_coupon_row(user.id, subscription.id)

    call_count = [0]

    db = AsyncMock()

    async def execute(query):
        call_count[0] += 1
        result = MagicMock()
        if call_count[0] == 1:
            result.scalar_one_or_none.return_value = subscription
        elif call_count[0] == 2:
            # Duplicate check — row exists
            result.scalar_one_or_none.return_value = existing_row
        return result

    db.execute = execute

    provider = _make_mock_coupon_provider()
    body = ApplyCouponRequest(coupon_code="TEST50", subscription_id=subscription.id)

    with patch("app.api.me_coupons.get_coupon_provider", return_value=provider):
        with pytest.raises(ApiError) as exc_info:
            await apply_coupon(body=body, user=user, db=db, _rl=None)

    assert exc_info.value.status_code == 409
    assert exc_info.value.code == "COUPON_ALREADY_APPLIED"


# ─── Test 9: user lists own coupons ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_my_coupons_200():
    """200 — user gets their list of applied coupons."""
    user = _make_user()
    sub_id = uuid.uuid4()
    rows = [_make_applied_coupon_row(user.id, sub_id)]

    db = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = rows
    db.execute = AsyncMock(return_value=result_mock)

    def _validate(row):
        return _make_applied_coupon_schema(row.user_id, row.subscription_id)

    with patch(
        "app.api.me_coupons.AppliedCouponOut.model_validate",
        side_effect=_validate,
    ):
        result = await list_my_coupons(limit=20, user=user, db=db, _rl=None)

    assert "data" in result
    assert len(result["data"]) == 1


# ─── Test 10: invalid coupon code format ─────────────────────────────────────


def test_apply_coupon_request_invalid_code():
    """422 — pydantic rejects coupon codes with invalid characters."""
    import pydantic

    with pytest.raises(pydantic.ValidationError):
        ApplyCouponRequest(coupon_code="BAD CODE!")  # space + exclamation = invalid


def test_apply_coupon_request_too_short():
    """422 — pydantic rejects coupon codes shorter than 4 chars."""
    import pydantic

    with pytest.raises(pydantic.ValidationError):
        ApplyCouponRequest(coupon_code="AB")


def test_admin_create_coupon_percent_over_100():
    """422 — percent discount_value > 100 is rejected by model_validator."""
    import pydantic

    with pytest.raises(pydantic.ValidationError):
        AdminCreateCouponRequest(
            code="BIGDISCOUNT",
            discount_type="percent",
            discount_value=150,
            duration="once",
        )


def test_admin_create_coupon_repeating_without_months():
    """422 — duration=repeating without duration_in_months raises ValidationError."""
    import pydantic

    with pytest.raises(pydantic.ValidationError):
        AdminCreateCouponRequest(
            code="REPEAT50",
            discount_type="percent",
            discount_value=50,
            duration="repeating",
            # duration_in_months missing
        )
