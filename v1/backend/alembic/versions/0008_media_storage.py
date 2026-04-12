"""Phase 4 M4: media_assets storage provider fields

Revision ID: 0008_media_storage
Revises: 0007_gdpr
Create Date: 2026-04-11

Adds storage_provider + storage_key to media_assets so that we can
route serving through a StorageProvider interface (local/s3/etc).
"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0008_media_storage"
down_revision: Union[str, None] = "0007_gdpr"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "media_assets",
        sa.Column(
            "storage_provider",
            sa.String(20),
            server_default="local",
            nullable=False,
        ),
    )
    op.add_column(
        "media_assets",
        sa.Column("storage_key", sa.Text, nullable=True),
    )
    op.add_column(
        "media_assets",
        sa.Column("thumb_small_url", sa.Text, nullable=True),
    )
    op.add_column(
        "media_assets",
        sa.Column("thumb_medium_url", sa.Text, nullable=True),
    )
    op.add_column(
        "media_assets",
        sa.Column("thumb_large_url", sa.Text, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("media_assets", "thumb_large_url")
    op.drop_column("media_assets", "thumb_medium_url")
    op.drop_column("media_assets", "thumb_small_url")
    op.drop_column("media_assets", "storage_key")
    op.drop_column("media_assets", "storage_provider")
