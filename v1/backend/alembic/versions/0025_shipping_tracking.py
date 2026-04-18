"""Add tracking fields to orders

Revision ID: 0025_shipping_tracking
Revises: 0024_rewards
Create Date: 2026-04-18
"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0025_shipping_tracking"
down_revision: Union[str, None] = "0024_rewards"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("orders", sa.Column("tracking_number", sa.String(100), nullable=True))
    op.add_column("orders", sa.Column("shipping_carrier", sa.String(50), nullable=True))


def downgrade() -> None:
    op.drop_column("orders", "shipping_carrier")
    op.drop_column("orders", "tracking_number")
