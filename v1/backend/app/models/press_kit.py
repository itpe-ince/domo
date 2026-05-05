"""PressKit model — C-2 press-kit-auto-export.

Cache + history for artist press kit PDFs.
Keyed by (artist_id, locale); 30-day cache via expires_at.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PressKit(Base):
    """Generated press kit PDF record."""

    __tablename__ = "press_kits"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    artist_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    locale: Mapped[str] = mapped_column(
        String(8), nullable=False
    )  # ko / en / ja / zh / es
    storage_key: Mapped[str] = mapped_column(
        String(500), nullable=False
    )  # S3/local storage key
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    page_count: Mapped[int] = mapped_column(Integer, nullable=False)

    # Optional: linked published interview (C-1 integration — page 4)
    interview_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("artist_interviews.id"),
        nullable=True,
    )

    # Snapshot of data used at generation time (ranking, sponsor stats, etc.)
    generation_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Artist consent to make the PDF publicly downloadable
    is_public: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # 30-day cache: same (artist_id, locale) reuses this row until expires_at
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        # Fast lookup for cache check: artist + locale, filter active cache
        Index("ix_press_kits_artist_locale", "artist_id", "locale"),
        # Admin history list by artist (newest first)
        Index("ix_press_kits_artist_created", "artist_id", "created_at"),
    )
