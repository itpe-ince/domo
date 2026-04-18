"""Add is_live flag to posts + shipping tracking fields

Revision ID: 0026_live_flag
Revises: 0025_shipping_tracking
Create Date: 2026-04-18
"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0026_live_flag"
down_revision: Union[str, None] = "0025_shipping_tracking"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("posts", sa.Column("is_live", sa.Boolean, server_default="false"))
    op.add_column("posts", sa.Column("live_url", sa.Text, nullable=True))


def downgrade() -> None:
    op.drop_column("posts", "live_url")
    op.drop_column("posts", "is_live")
