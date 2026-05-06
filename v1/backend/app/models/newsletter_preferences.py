"""NewsletterPreferences model — C-5 newsletter-digest.

Per-user newsletter subscription preferences.
Opt-in design: is_subscribed defaults to False (GDPR compliant).

H'-5 bounce fields:
  bounce_count      — cumulative soft bounce counter (resets to 0 on successful delivery)
  last_bounce_at    — timestamp of most recent bounce event
  suspended_until   — NULL = active; future datetime = soft-bounce suspended until date
  last_bounce_type  — most recent bounce type: 'permanent' | 'transient' | 'complaint'
"""
from __future__ import annotations

import secrets
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _gen_token() -> str:
    return secrets.token_urlsafe(48)


class NewsletterPreferences(Base):
    """Per-user newsletter preferences — one row per user."""

    __tablename__ = "newsletter_preferences"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    # GDPR: opt-in required — default False
    is_subscribed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    # weekly | biweekly | monthly | never
    frequency: Mapped[str] = mapped_column(
        String(20), nullable=False, default="monthly"
    )
    # Preferred locale for newsletters: ko | en | ja | zh | es
    preferred_locale: Mapped[str] = mapped_column(
        String(8), nullable=False, default="ko"
    )
    # Timestamp of last newsletter sent to this user
    last_sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # 1-click unsubscribe token embedded in email links
    unsubscribe_token: Mapped[str] = mapped_column(
        String(64), nullable=False, default=_gen_token
    )

    # ── H'-5 bounce tracking ──────────────────────────────────────────────────
    # Cumulative soft bounce counter; resets to 0 on successful delivery
    bounce_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    # Timestamp of most recent bounce event (any type)
    last_bounce_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # NULL = not suspended; future datetime = suspended until that point
    # After suspension window passes, cron will re-attempt and reset counter
    suspended_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Most recent bounce type: 'permanent' | 'transient' | 'complaint'
    last_bounce_type: Mapped[str | None] = mapped_column(
        String(20), nullable=True
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
