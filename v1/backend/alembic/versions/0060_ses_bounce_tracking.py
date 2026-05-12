"""Add SES bounce tracking fields — H'-5 newsletter-bounce-handling.

Adds bounce/complaint tracking fields to newsletter_preferences.
Adds delivery counters to newsletter_issues.

Revision ID: 0060_ses_bounce_tracking
Revises: 0059_perf_indexes
Create Date: 2026-05-04
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0060_ses_bounce_tracking"
down_revision: Union[str, None] = "0059_perf_indexes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── newsletter_preferences: bounce/complaint tracking ──────────────────────
    op.add_column(
        "newsletter_preferences",
        sa.Column("bounce_count", sa.Integer, nullable=False, server_default="0"),
    )
    op.add_column(
        "newsletter_preferences",
        sa.Column("last_bounce_at", sa.DateTime(timezone=True), nullable=True),
    )
    # Soft bounce suspension: NULL = not suspended; future timestamp = suspended until
    op.add_column(
        "newsletter_preferences",
        sa.Column("suspended_until", sa.DateTime(timezone=True), nullable=True),
    )
    # bounce_type: 'permanent' | 'transient' | 'complaint' | None
    op.add_column(
        "newsletter_preferences",
        sa.Column("last_bounce_type", sa.String(20), nullable=True),
    )

    # ── newsletter_issues: delivery counters ───────────────────────────────────
    op.add_column(
        "newsletter_issues",
        sa.Column("delivered_count", sa.Integer, nullable=False, server_default="0"),
    )
    op.add_column(
        "newsletter_issues",
        sa.Column("bounced_count", sa.Integer, nullable=False, server_default="0"),
    )
    op.add_column(
        "newsletter_issues",
        sa.Column("complained_count", sa.Integer, nullable=False, server_default="0"),
    )
    # SES Configuration Set name for this issue (if any)
    op.add_column(
        "newsletter_issues",
        sa.Column("ses_configuration_set", sa.String(64), nullable=True),
    )

    # Index for fast lookup of suspended users (cron skip check)
    op.create_index(
        "ix_newsletter_prefs_suspended_until",
        "newsletter_preferences",
        ["suspended_until"],
    )


def downgrade() -> None:
    op.drop_index("ix_newsletter_prefs_suspended_until", table_name="newsletter_preferences")

    # newsletter_issues columns
    op.drop_column("newsletter_issues", "ses_configuration_set")
    op.drop_column("newsletter_issues", "complained_count")
    op.drop_column("newsletter_issues", "bounced_count")
    op.drop_column("newsletter_issues", "delivered_count")

    # newsletter_preferences columns
    op.drop_column("newsletter_preferences", "last_bounce_type")
    op.drop_column("newsletter_preferences", "suspended_until")
    op.drop_column("newsletter_preferences", "last_bounce_at")
    op.drop_column("newsletter_preferences", "bounce_count")
