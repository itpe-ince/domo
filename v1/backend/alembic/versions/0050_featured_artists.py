"""Add featured_artists table — G'-7 admin-featured-artists.

Stores monthly curated featured artist selections by admin.
Supports history with soft deactivation.

Revision ID: 0050_featured_artists
Revises: 0049_search_history
Create Date: 2026-05-04
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

revision: str = "0050_featured_artists"
down_revision: Union[str, None] = "0049_search_history"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "featured_artists",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "artist_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("month", sa.Date, nullable=False),
        sa.Column("curation_note", sa.Text, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "created_by_admin_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_featured_artists_month_active",
        "featured_artists",
        ["month", "is_active"],
    )
    # Partial unique index: only one ACTIVE entry per month allowed.
    # This allows unlimited historical (is_active=False) entries per month.
    op.execute(
        "CREATE UNIQUE INDEX uq_featured_artist_active_month "
        "ON featured_artists (month) WHERE is_active = TRUE"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_featured_artist_active_month")
    op.drop_index("ix_featured_artists_month_active", table_name="featured_artists")
    op.drop_table("featured_artists")
