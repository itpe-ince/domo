"""Add auto_renew_enabled to subscriptions — B'-4 stripe-billing-auto-renewal.

Adds a boolean flag so sponsors can opt out of automatic renewal.
Default: True (Stripe handles billing natively; backend monitors only).

Revision ID: 0065_auto_renew_enabled
Revises: 0062_exchange_rates
Create Date: 2026-05-04
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0065_auto_renew_enabled"
down_revision: Union[str, None] = "0064_push_tokens"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "subscriptions",
        sa.Column(
            "auto_renew_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )
    op.create_index(
        "ix_subscriptions_auto_renew_period_end",
        "subscriptions",
        ["auto_renew_enabled", "current_period_end"],
        postgresql_where=sa.text("status = 'active'"),
    )


def downgrade() -> None:
    op.drop_index(
        "ix_subscriptions_auto_renew_period_end",
        table_name="subscriptions",
    )
    op.drop_column("subscriptions", "auto_renew_enabled")
