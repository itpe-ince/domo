"""Add post_collections and post_collection_items tables

Revision ID: 0012_collections
Revises: 0011_post_editor_fields
Create Date: 2026-04-13
"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision: str = "0012_collections"
down_revision: Union[str, None] = "0011_post_editor_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "post_collections",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("author_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("cover_image_url", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "post_collection_items",
        sa.Column("collection_id", UUID(as_uuid=True), sa.ForeignKey("post_collections.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("post_id", UUID(as_uuid=True), sa.ForeignKey("posts.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("order_index", sa.Integer, server_default="0"),
        sa.Column("added_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_collections_author", "post_collections", ["author_id"])


def downgrade() -> None:
    op.drop_index("idx_collections_author", table_name="post_collections")
    op.drop_table("post_collection_items")
    op.drop_table("post_collections")
