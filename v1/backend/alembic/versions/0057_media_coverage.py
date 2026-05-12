"""Add media_coverage table — C-4 media-coverage-cms.

Stores admin-managed external media exposure records.
Supports per-locale filtering and featured (hero) display.

Revision ID: 0057_media_coverage
Revises: 0056_user_bio_translations
Create Date: 2026-05-04
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

revision: str = "0057_media_coverage"
down_revision: Union[str, None] = "0056_user_bio_translations"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "media_coverage",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("coverage_type", sa.String(20), nullable=False),
        sa.Column("source_name", sa.String(100), nullable=False),
        sa.Column("external_url", sa.Text, nullable=False),
        sa.Column("thumbnail_url", sa.Text, nullable=True),
        sa.Column("published_at", sa.Date, nullable=False),
        sa.Column(
            "artist_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("locale", sa.String(8), nullable=False, server_default="ko"),
        sa.Column(
            "is_published",
            sa.Boolean,
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "is_featured",
            sa.Boolean,
            nullable=False,
            server_default=sa.false(),
        ),
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

    # Index on coverage_type for type-filtered queries
    op.create_index(
        "ix_media_coverage_type",
        "media_coverage",
        ["coverage_type"],
    )

    # Composite index: locale + is_published + published_at DESC for public list
    op.create_index(
        "ix_media_coverage_locale_published_at",
        "media_coverage",
        ["locale", "is_published", sa.text("published_at DESC")],
    )

    # Partial index for featured+published items (storyhub hero grid fast path)
    op.execute(
        """
        CREATE INDEX ix_media_coverage_featured
        ON media_coverage (published_at DESC)
        WHERE is_featured = TRUE AND is_published = TRUE
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_media_coverage_featured")
    op.drop_index("ix_media_coverage_locale_published_at", table_name="media_coverage")
    op.drop_index("ix_media_coverage_type", table_name="media_coverage")
    op.drop_table("media_coverage")
