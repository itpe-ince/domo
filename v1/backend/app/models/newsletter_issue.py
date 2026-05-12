"""NewsletterIssue model — C-5 newsletter-digest.

Admin-managed newsletter issues — content is compiled at compose time
and immutable after status transitions to 'sending'.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class NewsletterIssue(Base):
    """Newsletter issue (one per locale per period)."""

    __tablename__ = "newsletter_issues"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # Scheduled send date (e.g. 2026-05-01)
    issue_date: Mapped[date] = mapped_column(Date, nullable=False)
    # Email subject line
    subject: Mapped[str] = mapped_column(String(200), nullable=False)
    # Markdown source (editable before sending)
    body_markdown: Mapped[str] = mapped_column(Text, nullable=False, default="")
    # Rendered HTML (compiled from markdown at compose time or before send)
    body_html: Mapped[str] = mapped_column(Text, nullable=False, default="")
    # Locale: ko | en | ja | zh | es
    locale: Mapped[str] = mapped_column(String(8), nullable=False)

    # Content snapshot — UUIDs stored as strings in JSONB arrays
    # Featured artist (G'-7)
    featured_artist_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    # Ranking top artists (A-6): list of user UUID strings
    new_top_artists: Mapped[list] = mapped_column(
        JSONB, nullable=False, default=list, server_default="[]"
    )
    # New posts highlight (A-3 engagement): list of post UUID strings
    new_posts_highlight: Mapped[list] = mapped_column(
        JSONB, nullable=False, default=list, server_default="[]"
    )
    # Media coverage entries (C-4): list of media_coverage UUID strings
    media_coverage_ids: Mapped[list] = mapped_column(
        JSONB, nullable=False, default=list, server_default="[]"
    )

    # Lifecycle: draft | sending | sent | failed
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="draft"
    )
    sent_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # ── H'-5 delivery tracking (incremented via SES SNS events) ──────────────
    # SES Delivery event → delivered_count++
    delivered_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # SES Bounce event (any type) → bounced_count++
    bounced_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # SES Complaint event → complained_count++
    complained_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # SES Configuration Set name used for this issue (optional, for tracking)
    ses_configuration_set: Mapped[str | None] = mapped_column(
        String(64), nullable=True
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
