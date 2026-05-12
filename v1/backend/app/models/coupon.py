"""AppliedCoupon model — D'-3 stripe-coupon-foundation."""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AppliedCoupon(Base):
    """Records each coupon application for a user/subscription.

    stripe_coupon_id references the Stripe Coupon object ID (e.g. "WINBACK50").
    coupon_code is the human-readable admin code (optional, may differ from stripe_coupon_id).
    """

    __tablename__ = "applied_coupons"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    subscription_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("subscriptions.id", ondelete="SET NULL"),
        nullable=True,
    )
    stripe_coupon_id: Mapped[str] = mapped_column(String(100), nullable=False)
    coupon_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    discount_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # 'percent' | 'amount'
    discount_value: Mapped[int] = mapped_column(
        Integer, nullable=False
    )  # percent: 1-100, amount: cents
    duration: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # 'once' | 'forever' | 'repeating'
    duration_in_months: Mapped[int | None] = mapped_column(Integer, nullable=True)
    valid_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    applied_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    redeemed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
