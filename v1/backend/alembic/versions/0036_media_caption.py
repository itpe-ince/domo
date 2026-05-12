"""Add caption column to media_assets — editor-media-ux PDCA #4.

Adds an optional text column for per-media captions. Maximum 280 characters
is enforced at the Pydantic schema level (MediaAssetIn.caption), not at the
DB level, to allow future limit changes without data migration.

Additive migration — existing rows get caption=NULL automatically.
Downgrade drops the column and irrevocably loses caption data.

Revision ID: 0036_media_caption
Revises: 0035_draft_limit_index
Create Date: 2026-05-02
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0036_media_caption"
down_revision: Union[str, None] = "0035_draft_limit_index"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "media_assets",
        sa.Column(
            "caption",
            sa.Text(),
            nullable=True,
            comment="Optional per-media caption (max 280 chars enforced at schema level)",
        ),
    )


def downgrade() -> None:
    # WARNING: Drops all caption data irreversibly.
    op.drop_column("media_assets", "caption")
