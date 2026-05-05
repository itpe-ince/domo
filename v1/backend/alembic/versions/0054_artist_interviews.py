"""Add artist_interviews table — C-1 ai-artist-interview-generation.

Stores LLM-generated artist interview articles.
Status flow: draft → admin_review → approved → published | rejected | archived

Revision ID: 0054_artist_interviews
Revises: 0053_post_engagement_cache
Create Date: 2026-05-04
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

revision: str = "0054_artist_interviews"
down_revision: Union[str, None] = "0053_post_engagement_cache"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "artist_interviews",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "artist_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("locale", sa.String(8), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("body_markdown", sa.Text, nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        # LLM metadata
        sa.Column("llm_model", sa.String(100), nullable=True),
        sa.Column("llm_input_summary", sa.Text, nullable=True),
        sa.Column("generation_prompt_hash", sa.String(64), nullable=True),
        # Admin review
        sa.Column(
            "reviewed_by_admin_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column(
            "reviewed_at", sa.DateTime(timezone=True), nullable=True
        ),
        sa.Column("review_note", sa.Text, nullable=True),
        # Artist GDPR consent
        sa.Column(
            "artist_consent_at", sa.DateTime(timezone=True), nullable=True
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    # Composite index: artist + locale lookups (most common query pattern)
    op.create_index(
        "ix_artist_interviews_artist_locale",
        "artist_interviews",
        ["artist_id", "locale"],
    )

    # Status index: admin review queue
    op.create_index(
        "ix_artist_interviews_status",
        "artist_interviews",
        ["status"],
    )

    # Partial unique index: only one published interview per artist+locale
    # Allows multiple drafts/admin_review/approved/rejected — only published is unique
    op.execute(
        "CREATE UNIQUE INDEX uq_artist_interviews_published "
        "ON artist_interviews (artist_id, locale) WHERE status = 'published'"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_artist_interviews_published")
    op.drop_index("ix_artist_interviews_status", table_name="artist_interviews")
    op.drop_index("ix_artist_interviews_artist_locale", table_name="artist_interviews")
    op.drop_table("artist_interviews")
