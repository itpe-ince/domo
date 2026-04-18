from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


ALLOWED_DURATION_DAYS = [3, 7, 14]


class AuctionCreate(BaseModel):
    product_post_id: UUID
    start_price: Decimal = Field(..., gt=0)
    min_increment: Decimal = Field(Decimal("1"), gt=0)
    duration_days: int = Field(7)  # 3, 7, 14일 중 선택 (기본 7일 추천)
    start_at: datetime | None = None

    @field_validator("duration_days")
    @classmethod
    def validate_duration(cls, v: int) -> int:
        if v not in ALLOWED_DURATION_DAYS:
            raise ValueError(f"경매 기간은 {ALLOWED_DURATION_DAYS}일 중 선택해야 합니다.")
        return v


class AuctionOut(BaseModel):
    id: UUID
    product_post_id: UUID
    seller_id: UUID
    start_price: Decimal
    min_increment: Decimal
    current_price: Decimal
    current_winner: UUID | None
    currency: str
    start_at: datetime
    end_at: datetime
    status: str
    bid_count: int
    payment_deadline: datetime | None
    created_at: datetime

    class Config:
        from_attributes = True


class BidCreate(BaseModel):
    amount: Decimal = Field(..., gt=0)


class BidOut(BaseModel):
    id: UUID
    auction_id: UUID
    bidder_id: UUID
    amount: Decimal
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class OrderOut(BaseModel):
    id: UUID
    buyer_id: UUID
    seller_id: UUID
    product_post_id: UUID
    source: str
    auction_id: UUID | None
    amount: Decimal
    currency: str
    status: str
    payment_due_at: datetime | None
    paid_at: datetime | None
    created_at: datetime

    class Config:
        from_attributes = True
