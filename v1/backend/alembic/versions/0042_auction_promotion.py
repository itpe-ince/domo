"""Add auction promotion columns + partial index — auction-promotion-suite PDCA #11 PR1.

Adds to auctions:
- notified_24h_at  TIMESTAMP WITH TIME ZONE NULL
- notified_6h_at   TIMESTAMP WITH TIME ZONE NULL
- notified_1h_at   TIMESTAMP WITH TIME ZONE NULL
- share_card_url   TEXT NULL
- share_card_generated_at TIMESTAMP WITH TIME ZONE NULL

Partial index ix_auctions_pending_notif ON (end_at)
  WHERE status='active' AND (notified_24h_at IS NULL OR notified_6h_at IS NULL OR notified_1h_at IS NULL)

NOTE: PostgreSQL NOW() is not IMMUTABLE so it cannot appear in a partial index
WHERE clause. end_at column index + runtime WHERE handles this correctly.

Revision ID: 0042_auction_promotion
Revises: 0041_post_tier_release
Create Date: 2026-05-03
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0042_auction_promotion"
down_revision: Union[str, None] = "0041_post_tier_release"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Notification idempotent tracking columns (24h / 6h / 1h)
    op.add_column("auctions", sa.Column("notified_24h_at",
        sa.DateTime(timezone=True), nullable=True))
    op.add_column("auctions", sa.Column("notified_6h_at",
        sa.DateTime(timezone=True), nullable=True))
    op.add_column("auctions", sa.Column("notified_1h_at",
        sa.DateTime(timezone=True), nullable=True))

    # 2. Share-card cache columns
    op.add_column("auctions", sa.Column("share_card_url",
        sa.Text, nullable=True))
    op.add_column("auctions", sa.Column("share_card_generated_at",
        sa.DateTime(timezone=True), nullable=True))

    # 3. Partial index — accelerates cron sweep over active auctions with pending notifications
    op.create_index(
        "ix_auctions_pending_notif",
        "auctions",
        ["end_at"],
        postgresql_where=sa.text(
            "status = 'active' AND ("
            "notified_24h_at IS NULL OR notified_6h_at IS NULL OR notified_1h_at IS NULL)"
        ),
    )


def downgrade() -> None:
    op.drop_index("ix_auctions_pending_notif", table_name="auctions",
        postgresql_where=sa.text(
            "status = 'active' AND ("
            "notified_24h_at IS NULL OR notified_6h_at IS NULL OR notified_1h_at IS NULL)"
        ))
    op.drop_column("auctions", "share_card_generated_at")
    op.drop_column("auctions", "share_card_url")
    op.drop_column("auctions", "notified_1h_at")
    op.drop_column("auctions", "notified_6h_at")
    op.drop_column("auctions", "notified_24h_at")
