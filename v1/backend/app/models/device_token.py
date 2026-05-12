"""DeviceToken model — B'-3 push-email-digest-foundation.

Stores per-device FCM/APNs push tokens for authenticated users.
Soft-deleted on token revocation (logout / explicit unregister).
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DeviceToken(Base):
    __tablename__ = "device_tokens"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    # FCM registration token (Android/Web) or APNs device token (iOS)
    token: Mapped[str] = mapped_column(String(500), nullable=False)
    # Push platform
    platform: Mapped[str] = mapped_column(
        Enum("fcm", "apns", name="push_platform"), nullable=False
    )
    # Caller-provided device identifier for deduplication (optional)
    device_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Updated on successful push delivery (for token staleness detection)
    last_active_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    # Soft-delete: NULL = active, set = revoked
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
