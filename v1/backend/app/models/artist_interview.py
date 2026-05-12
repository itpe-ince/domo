"""ArtistInterview model — C-1 ai-artist-interview-generation.

LLM-generated interview articles for artists. Admin review workflow + artist consent.
Status flow: draft → admin_review → approved → published | rejected
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ArtistInterview(Base):
    """LLM-generated artist interview article."""

    __tablename__ = "artist_interviews"

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
    )  # ko/en/ja/zh/es
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body_markdown: Mapped[str] = mapped_column(
        Text, nullable=False
    )  # LLM output in markdown (no raw HTML — XSS defense)

    # Status flow: draft → admin_review → approved → published | rejected
    # 'archived' for previously published interviews superseded by a new one
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="draft"
    )

    # LLM metadata
    llm_model: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )  # e.g. "gemma4-e4b"
    llm_input_summary: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # artist portfolio + milestones summary sent to LLM
    generation_prompt_hash: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )  # SHA-256 hex of the prompt (idempotency)

    # Admin review
    reviewed_by_admin_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Artist GDPR opt-in / consent before publish
    artist_consent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
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
        # Fast lookup by artist + locale
        Index("ix_artist_interviews_artist_locale", "artist_id", "locale"),
        # Status filter (admin_review queue)
        Index("ix_artist_interviews_status", "status"),
        # Only one published interview per artist+locale allowed
        # (enforced via partial unique index in alembic DDL)
    )
