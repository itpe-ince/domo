from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class AuctionCreate(BaseModel):
    product_post_id: UUID
    start_price: Decimal = Field(..., gt=0)
    min_increment: Decimal = Field(Decimal("1000"), gt=0)
    duration_hours: int = Field(..., ge=1, le=720)
    # Phase 2: 작가가 시작 시점도 선택할 수 있게
    start_at: datetime | None = None


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
