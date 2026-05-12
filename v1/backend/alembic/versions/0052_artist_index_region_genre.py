"""artist_index_region_genre — G'-8 region/genre ranking columns.

Adds columns to users table for region/genre sub-rankings:
  - artist_index_score_region: float — region-scoped composite score
  - artist_index_rank_genre: int — 1-indexed rank within primary_genre group
  - artist_index_score_genre: float — genre-scoped composite score
  - artist_index_primary_genre: str — most-posted genre tag (cron-computed)

Note: artist_index_rank_region was already added in 0047_artist_index as an
integer placeholder. This migration adds the score column and genre columns.

Partial index on artist_index_rank_region WHERE NOT NULL.
Partial index on artist_index_rank_genre WHERE NOT NULL.

Revision ID: 0052_artist_index_region_genre
Revises: 0051_product_price_cents
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0052_artist_index_region_genre"
down_revision: Union[str, None] = "0051_product_price_cents"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add region score column (artist_index_rank_region already in 0047)
    op.add_column(
        "users",
        sa.Column("artist_index_score_region", sa.Float(), nullable=True),
    )
    # Add genre ranking columns
    op.add_column(
        "users",
        sa.Column("artist_index_rank_genre", sa.Integer(), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("artist_index_score_genre", sa.Float(), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("artist_index_primary_genre", sa.String(100), nullable=True),
    )

    # Partial index: region rank (only rows where region rank is assigned)
    op.create_index(
        "ix_users_artist_index_rank_region_partial",
        "users",
        ["artist_index_rank_region"],
        postgresql_where=sa.text("artist_index_rank_region IS NOT NULL"),
    )

    # Partial index: genre rank (only rows where genre rank is assigned)
    op.create_index(
        "ix_users_artist_index_rank_genre_partial",
        "users",
        ["artist_index_rank_genre"],
        postgresql_where=sa.text("artist_index_rank_genre IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "ix_users_artist_index_rank_genre_partial", table_name="users"
    )
    op.drop_index(
        "ix_users_artist_index_rank_region_partial", table_name="users"
    )
    op.drop_column("users", "artist_index_primary_genre")
    op.drop_column("users", "artist_index_score_genre")
    op.drop_column("users", "artist_index_rank_genre")
    op.drop_column("users", "artist_index_score_region")
