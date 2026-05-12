"""Add applied_coupons table — D'-3 stripe-coupon-foundation.

Stores coupon applications per user/subscription for audit + redemption tracking.

Revision ID: 0046_applied_coupons
Revises: 0045_user_sponsor_validity
Create Date: 2026-05-04
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "0046_applied_coupons"
down_revision: Union[str, None] = "0045_user_sponsor_validity"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "applied_coupons",
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
            "subscription_id",
            UUID(as_uuid=True),
            sa.ForeignKey("subscriptions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("stripe_coupon_id", sa.String(100), nullable=False),
        sa.Column("coupon_code", sa.String(50), nullable=True),
        sa.Column(
            "discount_type",
            sa.String(20),
            nullable=False,
            comment="'percent' | 'amount'",
        ),
        sa.Column(
            "discount_value",
            sa.Integer,
            nullable=False,
            comment="percent: 1-100, amount: cents",
        ),
        sa.Column(
            "duration",
            sa.String(20),
            nullable=False,
            comment="'once' | 'forever' | 'repeating'",
        ),
        sa.Column(
            "duration_in_months",
            sa.Integer,
            nullable=True,
            comment="Set only when duration='repeating'",
        ),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "applied_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("redeemed_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Indexes for common queries
    op.create_index(
        "ix_applied_coupons_user_id",
        "applied_coupons",
        ["user_id"],
    )
    op.create_index(
        "ix_applied_coupons_subscription_id",
        "applied_coupons",
        ["subscription_id"],
        postgresql_where=sa.text("subscription_id IS NOT NULL"),
    )
    op.create_index(
        "ix_applied_coupons_stripe_coupon_id",
        "applied_coupons",
        ["stripe_coupon_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_applied_coupons_stripe_coupon_id", table_name="applied_coupons")
    op.drop_index("ix_applied_coupons_subscription_id", table_name="applied_coupons")
    op.drop_index("ix_applied_coupons_user_id", table_name="applied_coupons")
    op.drop_table("applied_coupons")
