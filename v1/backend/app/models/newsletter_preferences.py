"""NewsletterPreferences model — C-5 newsletter-digest.

Per-user newsletter subscription preferences.
Opt-in design: is_subscribed defaults to False (GDPR compliant).
"""
from __future__ import annotations

import secrets
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
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
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
