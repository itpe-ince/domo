"""Admin coupon management endpoints — D'-3.

POST   /admin/coupons           — create coupon (admin only)
GET    /admin/coupons           — list coupons (admin only)
DELETE /admin/coupons/{id}      — deactivate coupon (admin only)
"""
from __future__ import annotations

import logging
import secrets

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.admin_deps import require_admin_with_2fa
from app.core.errors import ApiError
from app.core.rate_limit import rate_limit
from app.db.session import get_db
from app.models.user import User
from app.schemas.coupon import AdminCreateCouponRequest, CouponOut
from app.services.payments import get_coupon_provider

log = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/coupons", tags=["admin-coupons"])


def _coupon_result_to_out(result) -> CouponOut:
    return CouponOut(
        id=result.id,
        code=result.code,
        discount_type=result.discount_type,
        discount_value=result.discount_value,
        duration=result.duration,
        duration_in_months=result.duration_in_months,
        valid_until=result.valid_until,
        max_redemptions=result.max_redemptions,
        times_redeemed=result.times_redeemed,
        active=result.active,
    )


@router.post("", status_code=201)
async def admin_create_coupon(
    body: AdminCreateCouponRequest,
    admin: User = Depends(require_admin_with_2fa),
    db: AsyncSession = Depends(get_db),
    _rl=rate_limit("admin_coupons_write"),
):
    """Create a Stripe coupon and return its descriptor.

    Idempotency: if a coupon with the same code already exists in Stripe,
    the provider returns the existing one (Stripe Coupon.create is idempotent
    when the same ID is used).
    """
    provider = get_coupon_provider()
    idempotency_key = f"admin_coupon_{body.code}_{secrets.token_hex(8)}"

    try:
        result = await provider.create_coupon(
            code=body.code,
            discount_type=body.discount_type,
            discount_value=body.discount_value,
            duration=body.duration,
            duration_in_months=body.duration_in_months,
            valid_until=body.valid_until,
            max_redemptions=body.max_redemptions,
            idempotency_key=idempotency_key,
        )
    except Exception as exc:
        log.error("admin_create_coupon failed: %s", exc)
        raise ApiError(
            "COUPON_CREATE_FAILED",
            "Failed to create coupon. Please try again.",
            http_status=502,
        ) from exc

    log.info("AUDIT action=admin_create_coupon admin=%s code=%s", admin.id, body.code)
    return {"data": _coupon_result_to_out(result).model_dump()}


@router.get("")
async def admin_list_coupons(
    limit: int = Query(20, ge=1, le=100),
    starting_after: str | None = Query(None),
    admin: User = Depends(require_admin_with_2fa),
    db: AsyncSession = Depends(get_db),
):
    """List all Stripe coupons (from Stripe API, not DB)."""
    provider = get_coupon_provider()

    try:
        results = await provider.list_coupons(
            limit=limit, starting_after=starting_after
        )
    except Exception as exc:
        log.error("admin_list_coupons failed: %s", exc)
        raise ApiError(
            "COUPON_LIST_FAILED",
            "Failed to fetch coupons.",
            http_status=502,
        ) from exc

    return {"data": [_coupon_result_to_out(r).model_dump() for r in results]}


@router.delete("/{coupon_id}", status_code=204)
async def admin_delete_coupon(
    coupon_id: str,
    admin: User = Depends(require_admin_with_2fa),
    db: AsyncSession = Depends(get_db),
    _rl=rate_limit("admin_coupons_write"),
):
    """Deactivate/delete a Stripe coupon.

    Note: Stripe does not retroactively remove discounts from active subscriptions
    that already have this coupon applied. Only future applications are blocked.
    """
    provider = get_coupon_provider()

    try:
        await provider.delete_coupon(coupon_id)
    except ValueError as exc:
        raise ApiError("COUPON_NOT_FOUND", str(exc), http_status=404) from exc
    except Exception as exc:
        log.error("admin_delete_coupon failed coupon=%s: %s", coupon_id, exc)
        raise ApiError(
            "COUPON_DELETE_FAILED",
            "Failed to delete coupon.",
            http_status=502,
        ) from exc

    log.info(
        "AUDIT action=admin_delete_coupon admin=%s coupon=%s", admin.id, coupon_id
    )
    # 204 No Content
    return None
