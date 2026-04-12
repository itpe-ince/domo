from datetime import datetime
from decimal import Decimal
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
    created_at: datetime

    class Config:
        from_attributes = True
