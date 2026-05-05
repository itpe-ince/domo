"""Add newsletter_preferences + newsletter_issues tables — C-5 newsletter-digest.

Revision ID: 0058_newsletter
Revises: 0057_media_coverage
Create Date: 2026-05-04
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID

revision: str = "0058_newsletter"
down_revision: Union[str, None] = "0057_media_coverage"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # newsletter_preferences — one row per user (opt-in, GDPR)
    op.create_table(
        "newsletter_preferences",
        sa.Column(
            "user_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "is_subscribed",
            sa.Boolean,
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "frequency",
            sa.String(20),
            nullable=False,
            server_default="monthly",
        ),
        sa.Column(
            "preferred_locale",
            sa.String(8),
            nullable=False,
            server_default="ko",
        ),
        sa.Column("last_sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("unsubscribe_token", sa.String(64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # Index for cron: subscribed users by locale (batch-send lookup)
    op.create_index(
        "ix_newsletter_prefs_locale_subscribed",
        "newsletter_preferences",
        ["preferred_locale", "is_subscribed"],
    )

    # newsletter_issues — admin-authored issues with content snapshot
    op.create_table(
        "newsletter_issues",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column("issue_date", sa.Date, nullable=False),
        sa.Column("subject", sa.String(200), nullable=False),
        sa.Column("body_markdown", sa.Text, nullable=False, server_default=""),
        sa.Column("body_html", sa.Text, nullable=False, server_default=""),
        sa.Column("locale", sa.String(8), nullable=False),
        sa.Column(
            "featured_artist_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "new_top_artists",
            JSONB,
            nullable=False,
            server_default="[]",
        ),
        sa.Column(
            "new_posts_highlight",
            JSONB,
            nullable=False,
            server_default="[]",
        ),
        sa.Column(
            "media_coverage_ids",
            JSONB,
            nullable=False,
            server_default="[]",
        ),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="draft",
        ),
        sa.Column("sent_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("failed_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_by_admin_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # Index: status + locale for cron worker lookup (find 'sending' issues)
    op.create_index(
        "ix_newsletter_issues_status_locale",
        "newsletter_issues",
        ["status", "locale"],
    )

    # Index: issue_date desc for admin list view
    op.create_index(
        "ix_newsletter_issues_date",
        "newsletter_issues",
        [sa.text("issue_date DESC")],
    )


def downgrade() -> None:
    op.drop_index("ix_newsletter_issues_date", table_name="newsletter_issues")
    op.drop_index("ix_newsletter_issues_status_locale", table_name="newsletter_issues")
    op.drop_table("newsletter_issues")
    op.drop_index(
        "ix_newsletter_prefs_locale_subscribed", table_name="newsletter_preferences"
    )
    op.drop_table("newsletter_preferences")
