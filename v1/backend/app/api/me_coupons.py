"""User coupon endpoints — D'-3.

POST /me/coupons/apply   — apply a coupon to own subscription
GET  /me/coupons         — list own applied coupons
"""
from __future__ import annotations

import logging
import secrets
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.errors import ApiError
from app.core.rate_limit import rate_limit
from app.db.session import get_db
from app.models.coupon import AppliedCoupon
from app.models.sponsorship import Subscription
from app.models.user import User
from app.schemas.coupon import AppliedCouponOut, ApplyCouponRequest
from app.services.payments import get_coupon_provider

log = logging.getLogger(__name__)

router = APIRouter(prefix="/me/coupons", tags=["me-coupons"])


@router.post("/apply")
async def apply_coupon(
    body: ApplyCouponRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _rl=rate_limit("me_coupons_apply"),
):
    """Apply a coupon code to the user's own active subscription.

    If subscription_id is not provided, the most recently created active
    subscription is used. Returns 403 if the subscription belongs to another user.
    """
    # ── Resolve subscription ────────────────────────────────────────────────
    if body.subscription_id is not None:
        sub_result = await db.execute(
            select(Subscription).where(Subscription.id == body.subscription_id)
        )
        subscription = sub_result.scalar_one_or_none()
        if not subscription:
            raise ApiError("SUBSCRIPTION_NOT_FOUND", "Subscription not found.", http_status=404)
        if subscription.sponsor_id != user.id:
            raise ApiError(
                "FORBIDDEN",
                "You can only apply coupons to your own subscriptions.",
                http_status=403,
            )
    else:
        # Most recent active subscription
        sub_result = await db.execute(
            select(Subscription)
            .where(
                Subscription.sponsor_id == user.id,
                Subscription.status.in_(["active", "past_due"]),
            )
            .order_by(Subscription.created_at.desc())
            .limit(1)
        )
        subscription = sub_result.scalar_one_or_none()
        if not subscription:
            raise ApiError(
                "NO_ACTIVE_SUBSCRIPTION",
                "No active subscription found to apply coupon to.",
                http_status=404,
            )

    if subscription.status not in ("active", "past_due"):
        raise ApiError(
            "SUBSCRIPTION_NOT_ACTIVE",
            "Coupon can only be applied to an active subscription.",
            http_status=422,
        )

    # ── Check if already applied ─────────────────────────────────────────────
    existing = await db.execute(
        select(AppliedCoupon).where(
            AppliedCoupon.user_id == user.id,
            AppliedCoupon.subscription_id == subscription.id,
            AppliedCoupon.coupon_code == body.coupon_code,
        )
    )
    if existing.scalar_one_or_none():
        raise ApiError(
            "COUPON_ALREADY_APPLIED",
            "This coupon has already been applied to this subscription.",
            http_status=409,
        )

    # ── Validate coupon with Stripe ───────────────────────────────────────────
    provider = get_coupon_provider()
    try:
        coupon = await provider.get_coupon(body.coupon_code)
    except ValueError:
        raise ApiError("COUPON_NOT_FOUND", "Coupon code not found or expired.", http_status=404)
    except Exception as exc:
        log.error("apply_coupon get_coupon failed: %s", exc)
        raise ApiError("COUPON_LOOKUP_FAILED", "Failed to validate coupon.", http_status=502) from exc

    if not coupon.active:
        raise ApiError("COUPON_EXPIRED", "This coupon is no longer active.", http_status=422)

    if coupon.valid_until:
        # Normalize to UTC-aware for comparison (valid_until may be naive from mock)
        vu = coupon.valid_until
        if vu.tzinfo is None:
            vu = vu.replace(tzinfo=timezone.utc)
        if vu < datetime.now(timezone.utc):
            raise ApiError("COUPON_EXPIRED", "This coupon has expired.", http_status=422)

    # ── Attach coupon to Stripe subscription ─────────────────────────────────
    if subscription.provider_subscription_id:
        idempotency_key = f"apply_coupon_{user.id}_{subscription.id}_{body.coupon_code}_{secrets.token_hex(4)}"
        try:
            await provider.attach_coupon_to_subscription(
                subscription_id=subscription.provider_subscription_id,
                coupon_id=body.coupon_code,
                idempotency_key=idempotency_key,
            )
        except Exception as exc:
            log.error("attach_coupon_to_subscription failed: %s", exc)
            raise ApiError(
                "COUPON_ATTACH_FAILED",
                "Failed to apply coupon to subscription.",
                http_status=502,
            ) from exc

    # ── Persist AppliedCoupon row ─────────────────────────────────────────────
    applied = AppliedCoupon(
        user_id=user.id,
        subscription_id=subscription.id,
        stripe_coupon_id=coupon.id,
        coupon_code=body.coupon_code,
        discount_type=coupon.discount_type,
        discount_value=coupon.discount_value,
        duration=coupon.duration,
        duration_in_months=coupon.duration_in_months,
        valid_until=coupon.valid_until,
    )
    db.add(applied)
    await db.commit()
    await db.refresh(applied)

    log.info(
        "AUDIT action=apply_coupon user=%s subscription=%s coupon=%s",
        user.id,
        subscription.id,
        body.coupon_code,
    )
    return {"data": AppliedCouponOut.model_validate(applied).model_dump()}


@router.get("")
async def list_my_coupons(
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _rl=rate_limit("me_coupons_read"),
):
    """Return all coupons the current user has applied."""
    result = await db.execute(
        select(AppliedCoupon)
        .where(AppliedCoupon.user_id == user.id)
        .order_by(AppliedCoupon.applied_at.desc())
        .limit(limit)
    )
    coupons = result.scalars().all()
    return {"data": [AppliedCouponOut.model_validate(c).model_dump() for c in coupons]}
