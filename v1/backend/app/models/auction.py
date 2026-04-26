import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Auction(Base):
    """Auction (design.md §2.2)."""

    __tablename__ = "auctions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    product_post_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("product_posts.post_id"),
        nullable=False,
    )
    seller_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    start_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    min_increment: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, server_default="1000"
    )
    current_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    current_winner: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    currency: Mapped[str] = mapped_column(String(3), default="KRW")
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="scheduled")
    # 'scheduled' | 'active' | 'ended' | 'cancelled' | 'settled'
    bid_count: Mapped[int] = mapped_column(Integer, default=0)
    payment_deadline: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Bid(Base):
    """Auction bid (design.md §2.2)."""

    __tablename__ = "bids"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    auction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("auctions.id"), nullable=False
    )
    bidder_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active")
    # 'active' | 'outbid' | 'won' | 'cancelled'
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Order(Base):
    """Order (design.md §2.2)."""

    __tablename__ = "orders"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    buyer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    seller_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    product_post_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("product_posts.post_id"),
        nullable=False,
    )
    source: Mapped[str] = mapped_column(String(20), nullable=False)
    # 'auction' | 'buy_now'
    auction_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("auctions.id"), nullable=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="KRW")
    platform_fee: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0")
    )
    buyer_fee: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0")
    )
    # buyer_fee = amount * 10% (콜렉터 추가 수수료)
    status: Mapped[str] = mapped_column(String(30), default="pending_payment")
    # 'pending_payment' | 'paid' | 'shipped' | 'inspection' | 'inspection_complete' | 'settled' | 'paid_out' | 'cancelled' | 'expired' | 'refunded'
    tracking_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    shipping_carrier: Mapped[str | None] = mapped_column(String(50), nullable=True)
    shipping_status: Mapped[str] = mapped_column(String(20), default="pending")
    # 'pending' | 'shipped' | 'delivered'
    inspection_status: Mapped[str] = mapped_column(String(20), default="pending")
    # 'pending' | 'approved' | 'disputed'
    payment_intent_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    payment_due_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    paid_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    inspection_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    settled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    refunded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
