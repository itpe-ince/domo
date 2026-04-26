"""Add stripe_customer_id to users and stripe_price_cache table

Revision ID: 0029_user_stripe_customer
Revises: 0028_community_comments
Create Date: 2026-04-24
"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision: str = "0029_user_stripe_customer"
down_revision: Union[str, None] = "0028_community_comments"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add stripe_customer_id to users
    op.add_column(
        "users",
        sa.Column("stripe_customer_id", sa.String(100), nullable=True),
    )
    op.create_index(
        "ix_users_stripe_customer_id",
        "users",
        ["stripe_customer_id"],
    )

    # Create stripe_price_cache table
    op.create_table(
        "stripe_price_cache",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "artist_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("stripe_price_id", sa.String(100), nullable=False),
        sa.Column("stripe_product_id", sa.String(100), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("artist_id", "amount", "currency", name="uq_stripe_price_cache"),
    )
    op.create_index(
        "ix_stripe_price_cache_artist_id",
        "stripe_price_cache",
        ["artist_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_stripe_price_cache_artist_id", table_name="stripe_price_cache")
    op.drop_table("stripe_price_cache")
    op.drop_index("ix_users_stripe_customer_id", table_name="users")
    op.drop_column("users", "stripe_customer_id")
