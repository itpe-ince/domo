"""Coupon Pydantic schemas — D'-3 stripe-coupon-foundation."""
from __future__ import annotations

import re
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

# Alphanumeric + dash + underscore only (prevent injection)
_COUPON_CODE_RE = re.compile(r"^[A-Za-z0-9_-]+$")


class AdminCreateCouponRequest(BaseModel):
    """POST /admin/coupons — admin creates a new coupon."""

    code: str = Field(..., min_length=4, max_length=50)
    discount_type: Literal["percent", "amount"]
    discount_value: int = Field(..., ge=1, le=10000)
    duration: Literal["once", "forever", "repeating"]
    duration_in_months: int | None = Field(default=None, ge=1, le=12)
    valid_until: datetime | None = None
    max_redemptions: int | None = Field(default=None, ge=1)

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        v = v.strip().upper()
        if not _COUPON_CODE_RE.match(v):
            raise ValueError(
                "Coupon code may only contain letters, digits, hyphens, and underscores."
            )
        return v

    @model_validator(mode="after")
    def validate_cross_fields(self) -> "AdminCreateCouponRequest":
        if self.discount_type == "percent" and self.discount_value > 100:
            raise ValueError("percent discount_value must be between 1 and 100")
        if self.duration == "repeating" and not self.duration_in_months:
            raise ValueError(
                "duration_in_months is required when duration='repeating'"
            )
        if self.duration != "repeating" and self.duration_in_months is not None:
            raise ValueError(
                "duration_in_months may only be set when duration='repeating'"
            )
        return self


class CouponOut(BaseModel):
    """Serialized coupon — returned by admin list/create."""

    id: str
    code: str | None
    discount_type: str
    discount_value: int
    duration: str
    duration_in_months: int | None
    valid_until: datetime | None
    max_redemptions: int | None
    times_redeemed: int
    active: bool


class ApplyCouponRequest(BaseModel):
    """POST /me/coupons/apply — user applies a coupon to their subscription."""

    coupon_code: str = Field(..., min_length=4, max_length=50)
    subscription_id: UUID | None = None  # None = most recent active subscription

    @field_validator("coupon_code")
    @classmethod
    def validate_coupon_code(cls, v: str) -> str:
        v = v.strip().upper()
        if not _COUPON_CODE_RE.match(v):
            raise ValueError(
                "Coupon code may only contain letters, digits, hyphens, and underscores."
            )
        return v


class AppliedCouponOut(BaseModel):
    """Serialized AppliedCoupon row."""

    id: UUID
    user_id: UUID
    subscription_id: UUID | None
    stripe_coupon_id: str
    coupon_code: str | None
    discount_type: str
    discount_value: int
    duration: str
    duration_in_months: int | None
    valid_until: datetime | None
    applied_at: datetime
    redeemed_at: datetime | None

    class Config:
        from_attributes = True


# ─── G'-2: winback coupon ─────────────────────────────────────────────────────

WINBACK_REASONS = Literal[
    "too_expensive", "changed_mind", "not_satisfied", "other"
]


class WinbackCouponRequest(BaseModel):
    """POST /v1/subscriptions/{id}/winback-coupon request body."""

    reason: WINBACK_REASONS
    feedback: str | None = Field(default=None, max_length=500)


class WinbackCouponResponse(BaseModel):
    """200 response from winback-coupon endpoint."""

    coupon_applied: bool
    cancel_reverted: bool
    dm_link: str | None = None
    applied_coupon: AppliedCouponOut
