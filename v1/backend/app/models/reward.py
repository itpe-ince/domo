import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SponsorReward(Base):
    """Reward tiers set by artists for sponsors."""

    __tablename__ = "sponsor_rewards"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    artist_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    tier: Mapped[str] = mapped_column(String(20), nullable=False)
    # 'bronze' | 'silver' | 'gold' | 'platinum'
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    min_bluebirds: Mapped[int] = mapped_column(Integer, nullable=False)
    # Cumulative bluebird count required
    reward_type: Mapped[str] = mapped_column(String(20), nullable=False)
    # 'badge' | 'poster' | 'card' | 'message' | 'custom'
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class RewardClaim(Base):
    """Sponsor claims for unlocked rewards."""

    __tablename__ = "reward_claims"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reward_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sponsor_rewards.id", ondelete="CASCADE"), nullable=False
    )
    sponsor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), default="pending")
    # 'pending' | 'fulfilled' | 'cancelled'
    claimed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    fulfilled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
