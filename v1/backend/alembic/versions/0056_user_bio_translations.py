"""Add user_bio_translations table — C-3 multi-language-story.

Stores per-locale artist bio translations (LLM auto-translated or manually edited).
Composite primary key: (user_id, locale).

Revision ID: 0056_user_bio_translations
Revises: 0055_press_kits
Create Date: 2026-05-04
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

revision: str = "0056_user_bio_translations"
down_revision: Union[str, None] = "0055_press_kits"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_bio_translations",
        sa.Column("user_id", PG_UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("locale", sa.String(8), nullable=False),  # ko/en/ja/zh/es
        sa.Column("bio", sa.Text, nullable=False),
        sa.Column("is_machine_translated", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("last_edited_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("last_translated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("user_id", "locale"),
    )
    op.create_index(
        "ix_user_bio_translations_user_id",
        "user_bio_translations",
        ["user_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_user_bio_translations_user_id", table_name="user_bio_translations")
    op.drop_table("user_bio_translations")
