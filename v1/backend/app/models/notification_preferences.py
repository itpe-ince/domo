"""NotificationPreferences model — B'-3 push-email-digest-foundation.

Per-user push/email opt-in settings.
GDPR-compliant: all toggles default to False (explicit opt-in required).

push_per_type / email_per_type JSONB keys:
  auction | sponsorship | engagement | system | digest
Missing keys inherit the master push_enabled / email_enabled value.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class NotificationPreferences(Base):
    __tablename__ = "notification_preferences"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    # ── Master toggles (GDPR opt-in, default False) ───────────────────────────
    push_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    email_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    # ── Per-type overrides (JSONB) ─────────────────────────────────────────────
    # If a key is absent, the master toggle applies.
    # {"auction": true, "system": false, ...}
    push_per_type: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default="{}"
    )
    email_per_type: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default="{}"
    )
    # ── Digest frequency ──────────────────────────────────────────────────────
    # weekly | biweekly | monthly | never
    digest_frequency: Mapped[str] = mapped_column(
        String(20), nullable=False, default="weekly", server_default="'weekly'"
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
