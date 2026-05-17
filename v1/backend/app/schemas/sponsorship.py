from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class SponsorshipCreate(BaseModel):
    artist_id: UUID
    post_id: UUID | None = None
    bluebird_count: int = Field(..., ge=1, le=10000)
    is_anonymous: bool = False
    visibility: str = Field("public", pattern="^(public|artist_only|private)$")
    message: str | None = None


class SponsorshipOut(BaseModel):
    id: UUID
    sponsor_id: UUID | None
    artist_id: UUID
    post_id: UUID | None
    bluebird_count: int
    amount: Decimal
    currency: str
    is_anonymous: bool
    visibility: str
    message: str | None
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class SponsorshipCreateResponse(BaseModel):
    sponsorship: SponsorshipOut
    payment_intent: dict


class SubscriptionCreate(BaseModel):
    artist_id: UUID
    monthly_bluebird: int = Field(..., ge=1, le=10000)


class SubscriptionCancelRequest(BaseModel):
    """Optional body for DELETE /subscriptions/{id}.

    All fields are optional for backward compatibility — existing callers
    that send no body continue to work.
    """

    reason: (
        Literal["too_expensive", "changed_mind", "not_satisfied", "other"] | None
    ) = None
    feedback: str | None = Field(default=None, max_length=500)
    immediate: bool = False


class SubscriptionOut(BaseModel):
    id: UUID
    sponsor_id: UUID
    artist_id: UUID
    monthly_bluebird: int
    monthly_amount: Decimal
    currency: str
    status: str
    cancel_at_period_end: bool
    current_period_end: datetime | None
    cancelled_at: datetime | None
    cancellation_reason: str | None = None
    cancellation_feedback: str | None = None
    # B'-4: auto-renewal toggle
    auto_renew_enabled: bool = True
    created_at: datetime
    # Subscriptions-UX: artist denormalization (joined in /mine to avoid the
    # frontend rendering "428c98b4..." UUID slices). Optional everywhere so
    # endpoints that don't join (POST create, PATCH auto-renew, DELETE) can
    # keep returning the bare Subscription row unchanged.
    artist_username: str | None = None
    artist_avatar_url: str | None = None

    class Config:
        from_attributes = True


class SubscriptionRenewResponse(BaseModel):
    """Response for POST /subscriptions/{id}/renew (B'-4)."""

    id: UUID
    sponsor_id: UUID
    artist_id: UUID
    monthly_bluebird: int
    monthly_amount: Decimal
    currency: str
    status: str
    cancel_at_period_end: bool
    current_period_end: datetime | None
    cancelled_at: datetime | None
    auto_renew_enabled: bool = True
    renewed_at: datetime
    message: str

    class Config:
        from_attributes = True


class AutoRenewToggleRequest(BaseModel):
    """Request body for PATCH /subscriptions/{id}/auto-renew (B'-4)."""

    auto_renew_enabled: bool
