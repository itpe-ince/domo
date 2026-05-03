"""Create series + post_series_membership tables — publish-controls PDCA #8 Step 1.

Adds:
- series table (id, author_id FK users CASCADE, title, description, cover_url,
  created_at, updated_at) + ix_series_author_id
- post_series_membership table (series_id FK series CASCADE, post_id FK posts CASCADE,
  order_index, created_at) + ix_psm_post_id

OQ-4=C: cover_url nullable — first post thumbnail fallback in frontend.
OQ-5=A: order_index for dnd-kit drag-reorder support (frontend Step 4).
CASCADE: deleting a Series removes memberships only; Posts are preserved.

Revision ID: 0040_series_tables
Revises: 0039_post_visibility_comments
Create Date: 2026-05-03
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "0040_series_tables"
down_revision: Union[str, None] = "0039_post_visibility_comments"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "series",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "author_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("cover_url", sa.Text, nullable=True),  # OQ-4=C
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
    op.create_index("ix_series_author_id", "series", ["author_id"])

    op.create_table(
        "post_series_membership",
        sa.Column(
            "series_id",
            UUID(as_uuid=True),
            sa.ForeignKey("series.id", ondelete="CASCADE"),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "post_id",
            UUID(as_uuid=True),
            sa.ForeignKey("posts.id", ondelete="CASCADE"),
            primary_key=True,
            nullable=False,
        ),
        sa.Column("order_index", sa.Integer, default=0, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_psm_post_id", "post_series_membership", ["post_id"])


def downgrade() -> None:
    op.drop_index("ix_psm_post_id", table_name="post_series_membership")
    op.drop_table("post_series_membership")
    op.drop_index("ix_series_author_id", table_name="series")
    op.drop_table("series")
