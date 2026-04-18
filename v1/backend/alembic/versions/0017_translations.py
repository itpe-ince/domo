"""Add post_translations table for content translation cache

Revision ID: 0017_translations
Revises: 0016_escrow_buyer_fee
Create Date: 2026-04-18
"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision: str = "0017_translations"
down_revision: Union[str, None] = "0016_escrow_buyer_fee"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "post_translations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("post_id", UUID(as_uuid=True), sa.ForeignKey("posts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("language", sa.String(10), nullable=False),
        sa.Column("title_translated", sa.Text, nullable=True),
        sa.Column("content_translated", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_post_translations_lookup", "post_translations", ["post_id", "language"], unique=True)


def downgrade() -> None:
    op.drop_index("idx_post_translations_lookup", table_name="post_translations")
    op.drop_table("post_translations")
