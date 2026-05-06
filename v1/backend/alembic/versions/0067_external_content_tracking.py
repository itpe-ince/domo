"""외부 콘텐츠 트래킹 — Phase 9 L-B.

external_feeds, external_articles (RSS auto-fetch L-2)
newsletter_events (open rate tracking L-4)

Revision ID: 0067_external_content_tracking
Revises: 0066_pgvector_embeddings
Create Date: 2026-05-05
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0067_external_content_tracking"
down_revision: Union[str, None] = "0066_pgvector_embeddings"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── L-2 RSS: external_feeds ────────────────────────────────────────────────
    op.create_table(
        "external_feeds",
        sa.Column(
            "id",
            sa.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("source_name", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("TRUE")),
        sa.Column("last_fetched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "fetch_interval_hours",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("1"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("source_url", name="uq_external_feeds_source_url"),
    )

    # ── L-2 RSS: external_articles ────────────────────────────────────────────
    op.create_table(
        "external_articles",
        sa.Column(
            "id",
            sa.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("feed_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("artist_id", sa.UUID(as_uuid=True), nullable=True),
        sa.Column("match_confidence", sa.Float(), nullable=True),
        sa.Column(
            "is_approved",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("FALSE"),
        ),
        sa.Column("og_image_url", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["feed_id"],
            ["external_feeds.id"],
            name="fk_external_articles_feed_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["artist_id"],
            ["users.id"],
            name="fk_external_articles_artist_id",
            ondelete="SET NULL",
        ),
        sa.UniqueConstraint("url", name="uq_external_articles_url"),
    )

    op.create_index(
        "ix_external_articles_feed_id",
        "external_articles",
        ["feed_id"],
    )
    op.create_index(
        "ix_external_articles_artist_id",
        "external_articles",
        ["artist_id"],
        postgresql_where=sa.text("artist_id IS NOT NULL"),
    )
    op.create_index(
        "ix_external_articles_published_at",
        "external_articles",
        [sa.text("published_at DESC")],
    )

    # ── L-4 Newsletter Events ──────────────────────────────────────────────────
    op.create_table(
        "newsletter_events",
        sa.Column(
            "id",
            sa.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("issue_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.UUID(as_uuid=True), nullable=True),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("ip_hash", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["issue_id"],
            ["newsletter_issues.id"],
            name="fk_newsletter_events_issue_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_newsletter_events_user_id",
            ondelete="SET NULL",
        ),
        sa.CheckConstraint(
            "event_type IN ('open', 'click')",
            name="ck_newsletter_events_event_type",
        ),
    )

    op.create_index(
        "ix_newsletter_events_issue_id",
        "newsletter_events",
        ["issue_id"],
    )
    op.create_index(
        "ix_newsletter_events_user_id",
        "newsletter_events",
        ["user_id"],
        postgresql_where=sa.text("user_id IS NOT NULL"),
    )
    op.create_index(
        "ix_newsletter_events_event_type",
        "newsletter_events",
        ["event_type", sa.text("created_at DESC")],
    )


def downgrade() -> None:
    # newsletter_events 인덱스 + 테이블
    op.drop_index("ix_newsletter_events_event_type", table_name="newsletter_events")
    op.drop_index("ix_newsletter_events_user_id", table_name="newsletter_events")
    op.drop_index("ix_newsletter_events_issue_id", table_name="newsletter_events")
    op.drop_table("newsletter_events")

    # external_articles 인덱스 + 테이블
    op.drop_index("ix_external_articles_published_at", table_name="external_articles")
    op.drop_index("ix_external_articles_artist_id", table_name="external_articles")
    op.drop_index("ix_external_articles_feed_id", table_name="external_articles")
    op.drop_table("external_articles")

    # external_feeds 테이블
    op.drop_table("external_feeds")
