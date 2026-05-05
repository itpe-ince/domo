"""Add artist_index columns to users table — A-6 artist-index-v1.

Adds 4 columns for global ranking score/rank storage plus a partial index
on artist_index_score for efficient ranking queries.

Revision ID: 0047_artist_index
Revises: 0046_applied_coupons
Create Date: 2026-05-04
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0047_artist_index"
down_revision: Union[str, None] = "0046_applied_coupons"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("artist_index_score", sa.Float(), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("artist_index_rank", sa.Integer(), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("artist_index_rank_region", sa.Integer(), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column(
            "artist_index_calculated_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    # Partial index: only ranked artists (score IS NOT NULL), orders by rank for fast list queries
    op.create_index(
        "ix_users_artist_index_score",
        "users",
        ["artist_index_score"],
        postgresql_where=sa.text("artist_index_score IS NOT NULL"),
    )
    op.create_index(
        "ix_users_artist_index_rank",
        "users",
        ["artist_index_rank"],
        postgresql_where=sa.text("artist_index_rank IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "ix_users_artist_index_rank",
        table_name="users",
        postgresql_where=sa.text("artist_index_rank IS NOT NULL"),
    )
    op.drop_index(
        "ix_users_artist_index_score",
        table_name="users",
        postgresql_where=sa.text("artist_index_score IS NOT NULL"),
    )
    op.drop_column("users", "artist_index_calculated_at")
    op.drop_column("users", "artist_index_rank_region")
    op.drop_column("users", "artist_index_rank")
    op.drop_column("users", "artist_index_score")
