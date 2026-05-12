"""MediaCoverage model — C-4 media-coverage-cms.

Admin-managed external media exposure records (articles, YouTube, radio, etc.)
Supports per-locale filtering and featured (hero) display.
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
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

COVERAGE_TYPES = ("article", "youtube", "radio", "podcast", "tv")
SUPPORTED_LOCALES = ("ko", "en", "ja", "zh", "es")


class MediaCoverage(Base):
    """External media coverage entry managed by admin."""

    __tablename__ = "media_coverage"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # Display title (HTML-sanitized before persist)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    # article | youtube | radio | podcast | tv
    coverage_type: Mapped[str] = mapped_column(String(20), nullable=False)
    # Source outlet name, e.g. "한겨레", "TBS"
    source_name: Mapped[str] = mapped_column(String(100), nullable=False)
    # External link
    external_url: Mapped[str] = mapped_column(Text, nullable=False)
    # OG image or admin-uploaded thumbnail
    thumbnail_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Publication date
    published_at: Mapped[date] = mapped_column(Date, nullable=False)
    # Optional related artist (nullable FK)
    artist_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    # Short description (HTML-sanitized)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Media locale (ko/en/ja/zh/es)
    locale: Mapped[str] = mapped_column(String(8), nullable=False, default="ko")
    # Draft / published
    is_published: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    # Featured for storyhub hero grid
    is_featured: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    created_by_admin_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        # Filter by type
        Index("ix_media_coverage_type", "coverage_type"),
        # Public list: locale + published + date desc
        Index(
            "ix_media_coverage_locale_published_at",
            "locale",
            "is_published",
            "published_at",
        ),
        # Partial index for featured items (small set, fast lookup)
        # Implemented via raw DDL in alembic migration
    )
