"""Add cancellation tracking columns to subscriptions.

Revision ID: 0044_subscription_cancellation
Revises: 0043_artist_tier_benefits
Create Date: 2026-05-04

D'-2: subscription-cancellation-tracking
  - cancellation_reason  String(50) nullable
  - cancellation_feedback Text nullable
  (cancelled_at already exists from initial migration — skip)
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision = "0044_subscription_cancellation"
down_revision = "0043_artist_tier_benefits"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "subscriptions",
        sa.Column("cancellation_reason", sa.String(50), nullable=True),
    )
    op.add_column(
        "subscriptions",
        sa.Column("cancellation_feedback", sa.Text, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("subscriptions", "cancellation_feedback")
    op.drop_column("subscriptions", "cancellation_reason")
