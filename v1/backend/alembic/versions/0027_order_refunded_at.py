"""Add refunded_at column to orders table

Revision ID: 0027_order_refunded_at
Revises: 0026_live_flag
Create Date: 2026-04-24
"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0027_order_refunded_at"
down_revision: Union[str, None] = "0026_live_flag"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "orders",
        sa.Column("refunded_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("orders", "refunded_at")
