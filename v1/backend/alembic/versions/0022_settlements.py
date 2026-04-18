"""Add settlements + settlement_items tables

Revision ID: 0022_settlements
Revises: 0021_kyc
Create Date: 2026-04-18
"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision: str = "0022_settlements"
down_revision: Union[str, None] = "0021_kyc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "settlements",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("artist_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("period_start", sa.Date, nullable=False),
        sa.Column("period_end", sa.Date, nullable=False),
        sa.Column("order_count", sa.Integer, server_default="0"),
        sa.Column("gross_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("platform_fee", sa.Numeric(12, 2), nullable=False),
        sa.Column("net_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(3), server_default="'USD'"),
        sa.Column("status", sa.String(20), server_default="'pending'"),
        sa.Column("approved_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("payout_reference", sa.String(200), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_settlements_artist", "settlements", ["artist_id", "period_end"])

    op.create_table(
        "settlement_items",
        sa.Column("settlement_id", UUID(as_uuid=True), sa.ForeignKey("settlements.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("order_id", UUID(as_uuid=True), sa.ForeignKey("orders.id"), primary_key=True),
    )


def downgrade() -> None:
    op.drop_table("settlement_items")
    op.drop_index("idx_settlements_artist", table_name="settlements")
    op.drop_table("settlements")
