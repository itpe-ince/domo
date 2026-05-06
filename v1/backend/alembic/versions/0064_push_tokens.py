"""Create device_tokens and notification_preferences tables — B'-3 push-email-digest-foundation.

DeviceToken: per-device FCM/APNs push token storage.
NotificationPreferences: per-user push/email opt-in settings with GDPR-compliant defaults.

Revision ID: 0064_push_tokens
Revises: 0062_exchange_rates
Create Date: 2026-05-04
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "0064_push_tokens"
down_revision: Union[str, None] = "0063_dm_messaging"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── device_tokens ────────────────────────────────────────────────────────
    op.create_table(
        "device_tokens",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "token",
            sa.String(500),
            nullable=False,
        ),
        sa.Column(
            "platform",
            sa.Enum("fcm", "apns", name="push_platform"),
            nullable=False,
        ),
        sa.Column(
            "device_id",
            sa.String(255),
            nullable=True,
        ),
        sa.Column(
            "last_active_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "deleted_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    op.create_index(
        "ix_device_tokens_user_id",
        "device_tokens",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_device_tokens_token",
        "device_tokens",
        ["token"],
        unique=False,
    )
    # Partial unique: only one active row per (user_id, device_id) pair
    op.create_index(
        "ix_device_tokens_user_device_active",
        "device_tokens",
        ["user_id", "device_id"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL AND device_id IS NOT NULL"),
    )

    # ── notification_preferences ─────────────────────────────────────────────
    op.create_table(
        "notification_preferences",
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "push_enabled",
            sa.Boolean,
            nullable=False,
            default=False,
            server_default="false",
        ),
        sa.Column(
            "email_enabled",
            sa.Boolean,
            nullable=False,
            default=False,
            server_default="false",
        ),
        sa.Column(
            "push_per_type",
            JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
            comment=(
                "Per-type push opt-in overrides. "
                "Keys: auction | sponsorship | engagement | system | digest. "
                "Values: true | false. Missing keys inherit push_enabled."
            ),
        ),
        sa.Column(
            "email_per_type",
            JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
            comment=(
                "Per-type email opt-in overrides. "
                "Keys: auction | sponsorship | engagement | system | digest. "
                "Values: true | false. Missing keys inherit email_enabled."
            ),
        ),
        sa.Column(
            "digest_frequency",
            sa.String(20),
            nullable=False,
            default="weekly",
            server_default="'weekly'",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )


def downgrade() -> None:
    op.drop_table("notification_preferences")
    op.drop_index("ix_device_tokens_user_device_active", table_name="device_tokens")
    op.drop_index("ix_device_tokens_token", table_name="device_tokens")
    op.drop_index("ix_device_tokens_user_id", table_name="device_tokens")
    op.drop_table("device_tokens")
    op.execute("DROP TYPE IF EXISTS push_platform")
