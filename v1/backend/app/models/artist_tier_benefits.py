"""ArtistTierBenefits model — B-4 tier-benefits-customization.

Stores per-artist override for tier benefit text (subscriber | sponsor | follower).
When no row exists for a given (artist_id, tier) pair, the platform default
i18n key is returned by the API.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ArtistTierBenefits(Base):
    __tablename__ = "artist_tier_benefits"
    __table_args__ = (
        UniqueConstraint("artist_id", "tier", name="uq_atb_artist_tier"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    artist_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # 'subscriber' | 'sponsor' | 'follower'
    tier: Mapped[str] = mapped_column(String(20), nullable=False)
    # list of benefit strings, max 10 items, each max 200 chars
    benefits: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    # optional welcome message shown on sponsorship success, max 500 chars
    welcome_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
