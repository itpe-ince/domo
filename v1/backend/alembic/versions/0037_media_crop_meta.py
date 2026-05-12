"""Add crop_meta column to media_assets — editor-image-studio PDCA #6-image.

Stores non-destructive image edit metadata (rotate/crop/mosaic/watermark ops)
as JSONB. Enables ImageEditor modal to restore previous edit state on
re-entry (OQ-3 = A — non-destructive editing).

Additive migration — existing rows get crop_meta=NULL automatically.
Downgrade drops the column and irrevocably loses crop metadata.

Revision ID: 0037_media_crop_meta
Revises: 0036_media_caption
Create Date: 2026-05-03
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "0037_media_crop_meta"
down_revision: Union[str, None] = "0036_media_caption"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "media_assets",
        sa.Column(
            "crop_meta",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment=(
                "Non-destructive image edit metadata "
                "(rotate/crop/mosaic/watermark ops as JSONB). "
                "See app/schemas/media_transform.py CropMetaSchema."
            ),
        ),
    )


def downgrade() -> None:
    # WARNING: Drops all crop_meta data irreversibly.
    op.drop_column("media_assets", "crop_meta")
