"""post_engagement_cache — G'-9 post engagement cache table.

New table: post_engagement_cache
  post_id:            UUID PK, FK posts(id) CASCADE DELETE
  like_count_24h:     INT default 0
  comment_count_24h:  INT default 0
  bookmark_count_24h: INT default 0
  bid_count_24h:      INT default 0
  share_count_24h:    INT default 0
  engagement_score:   FLOAT default 0.0
    formula: likes×1 + comments×2 + bookmarks×1.5 + bids×5 + shares×3
  calculated_at:      TIMESTAMPTZ server_default=now()

Partial index: WHERE engagement_score > 0 (index only active rows).

Revision ID: 0053_post_engagement_cache
Revises: 0052_artist_index_region_genre
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

revision: str = "0053_post_engagement_cache"
down_revision: Union[str, None] = "0052_artist_index_region_genre"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "post_engagement_cache",
        sa.Column("post_id", PG_UUID(as_uuid=True), nullable=False),
        sa.Column("like_count_24h", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("comment_count_24h", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("bookmark_count_24h", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("bid_count_24h", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("share_count_24h", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("engagement_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column(
            "calculated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["post_id"], ["posts.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("post_id"),
    )

    # Partial index: only rows with non-zero engagement_score
    op.create_index(
        "ix_post_engagement_cache_score_partial",
        "post_engagement_cache",
        ["engagement_score"],
        postgresql_where=sa.text("engagement_score > 0"),
    )


def downgrade() -> None:
    op.drop_index(
        "ix_post_engagement_cache_score_partial",
        table_name="post_engagement_cache",
    )
    op.drop_table("post_engagement_cache")
