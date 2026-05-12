"""Add sponsor_validity_days to users — D'-1 tech-debt-cleanup.

Allows artists to configure how long a completed Sponsorship grants
tier access (NULL = lifetime, 1/7/30/90/365 days).

Revision ID: 0045_user_sponsor_validity
Revises: 0044_subscription_cancellation
Create Date: 2026-05-04
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0045_user_sponsor_validity"
down_revision: Union[str, None] = "0044_subscription_cancellation"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "sponsor_validity_days",
            sa.Integer,
            nullable=True,
            comment=(
                "NULL = lifetime; 1/7/30/90/365 = completed sponsorship "
                "expires after N days. Artist-only setting."
            ),
        ),
    )
    op.create_index(
        "ix_users_sponsor_validity_days",
        "users",
        ["sponsor_validity_days"],
        postgresql_where=sa.text("sponsor_validity_days IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_users_sponsor_validity_days", table_name="users")
    op.drop_column("users", "sponsor_validity_days")
