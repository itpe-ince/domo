"""Add expiry_notified_at to subscriptions — A-8 retention-loop-enhancement.

Adds a nullable column `expiry_notified_at` to the subscriptions table
so the subscription_expiry_jobs cron can track per-row notification
state (idempotent: only notify once per billing cycle).

A partial index on (id) WHERE expiry_notified_at IS NULL AND status='active'
speeds up the cron sweep without scanning cancelled rows.

Revision ID: 0048_subscription_expiry_notif
Revises:     0047_artist_index
Create Date: 2026-05-04
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0048_subscription_expiry_notif"
down_revision: Union[str, None] = "0047_artist_index"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "subscriptions",
        sa.Column("expiry_notified_at", sa.DateTime(timezone=True), nullable=True),
    )
    # Partial index — only covers rows the cron actually needs to check
    op.execute(
        """
        CREATE INDEX ix_subscriptions_expiry_notif_pending
        ON subscriptions (id)
        WHERE expiry_notified_at IS NULL AND status = 'active'
        """
    )


def downgrade() -> None:
    op.execute(
        "DROP INDEX IF EXISTS ix_subscriptions_expiry_notif_pending"
    )
    op.drop_column("subscriptions", "expiry_notified_at")
