"""Add community_comments table

Revision ID: 0028_community_comments
Revises: 0027_order_refunded_at
Create Date: 2026-04-24
"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision: str = "0028_community_comments"
down_revision: Union[str, None] = "0027_order_refunded_at"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "community_comments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "post_id",
            UUID(as_uuid=True),
            sa.ForeignKey("community_posts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "author_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("status", sa.String(20), server_default="active", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_community_comments_post_id",
        "community_comments",
        ["post_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_community_comments_post_id", table_name="community_comments")
    op.drop_table("community_comments")
