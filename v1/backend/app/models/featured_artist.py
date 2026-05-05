"""FeaturedArtist model — G'-7 admin-featured-artists.

Monthly curated featured artist selection by admin.
Supports history (one active entry per month).
"""
from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class FeaturedArtist(Base):
    """Monthly featured artist curated by admin."""

    __tablename__ = "featured_artists"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    artist_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    # Month stored as first day of month (e.g. 2026-05-01)
    month: Mapped[date] = mapped_column(Date, nullable=False)
    curation_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_by_admin_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )

    __table_args__ = (
        # Fast lookup by month + active status
        Index("ix_featured_artists_month_active", "month", "is_active"),
        # Partial unique index: only one ACTIVE entry per month allowed.
        # (implemented in alembic migration via raw DDL — SQLAlchemy Index
        #  doesn't support postgresql_where directly in all versions)
    )
