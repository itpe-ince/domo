"""Phase 4 M3: GDPR fields on users + webhook_events table

Revision ID: 0007_gdpr
Revises: 0006_auth_refresh_tokens
Create Date: 2026-04-11

Adds:
- users.deleted_at, deletion_scheduled_for (30-day grace soft delete)
- users.gdpr_export_count (rate limit export)
- users.privacy_policy_version, users.terms_version (consent tracking)
- webhook_events (idempotency for Stripe webhooks — M1 prep)
"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0007_gdpr"
down_revision: Union[str, None] = "0006_auth_refresh_tokens"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # users: GDPR fields
    op.add_column("users", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "users",
        sa.Column("deletion_scheduled_for", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("gdpr_export_count", sa.Integer, server_default="0", nullable=False),
    )
    op.add_column(
        "users",
        sa.Column("privacy_policy_version", sa.String(20), nullable=True),
    )
    op.add_column(
        "users", sa.Column("terms_version", sa.String(20), nullable=True)
    )
    op.create_index(
        "idx_users_deletion_scheduled",
        "users",
        ["deletion_scheduled_for"],
        postgresql_where=sa.text("deletion_scheduled_for IS NOT NULL"),
    )

    # webhook_events (idempotency for Stripe webhooks, will be used by M1)
    op.create_table(
        "webhook_events",
        sa.Column("id", sa.String(100), primary_key=True),
        sa.Column("type", sa.String(100), nullable=False),
        sa.Column("payload", postgresql.JSONB, nullable=False),
        sa.Column(
            "processed_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # Seed default policy versions
    op.execute(
        """
        INSERT INTO system_settings(key, value) VALUES
            ('privacy_policy_version', '{"version": "v1-draft", "effective_date": "2026-04-11"}'),
            ('terms_version', '{"version": "v1-draft", "effective_date": "2026-04-11"}')
        ON CONFLICT (key) DO NOTHING
        """
    )


def downgrade() -> None:
    op.execute(
        "DELETE FROM system_settings WHERE key IN ('privacy_policy_version', 'terms_version')"
    )
    op.drop_table("webhook_events")
    op.drop_index("idx_users_deletion_scheduled", table_name="users")
    op.drop_column("users", "terms_version")
    op.drop_column("users", "privacy_policy_version")
    op.drop_column("users", "gdpr_export_count")
    op.drop_column("users", "deletion_scheduled_for")
    op.drop_column("users", "deleted_at")
