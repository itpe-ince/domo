"""Add original_storage_key + signature_storage_key — editor-image-studio PDCA #6-image v1.1.

Two columns, two reasons (both surfaced from OQ-D resolution 2026-05-03):

1. media_assets.original_storage_key (OQ-D-A = C, OQ-D-C = B):
   Preserves the original storage key on first transform, so subsequent
   re-edits always re-process from the original (avoids cumulative
   re-encoding quality loss). NULL until first transform — code falls back
   to current storage_key when NULL.

2. users.signature_storage_key (OQ-D-B = C, OQ-D-3 = B):
   Pre-stores the watermark signature image as a separate user asset
   (not avatar reuse). Backend reads directly from storage by key —
   no external URL fetch (SSRF防御). Populated via
   POST /v1/users/me/signature endpoint.

Additive migration — both columns nullable, existing rows get NULL.
Downgrade drops the columns; uploaded signature files are NOT cleaned up
(orphaned in storage, manual cleanup required).

Revision ID: 0038_orig_signature_keys
Revises: 0037_media_crop_meta
Create Date: 2026-05-03

NOTE: revision ID kept under 32 chars (alembic_version.version_num is
varchar(32); the previous "0038_signature_and_original_storage" name
overflowed this limit and caused StringDataRightTruncationError on
upgrade).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0038_orig_signature_keys"
down_revision: Union[str, None] = "0037_media_crop_meta"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "media_assets",
        sa.Column(
            "original_storage_key",
            sa.String(length=512),
            nullable=True,
            comment=(
                "Original storage key preserved on first transform "
                "(OQ-D-A=C). Falls back to storage_key when NULL."
            ),
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "signature_storage_key",
            sa.String(length=512),
            nullable=True,
            comment=(
                "Watermark signature image storage key (OQ-D-B=C). "
                "Populated via POST /v1/users/me/signature."
            ),
        ),
    )


def downgrade() -> None:
    # WARNING: Orphans signature image files in storage; manual cleanup needed.
    op.drop_column("users", "signature_storage_key")
    op.drop_column("media_assets", "original_storage_key")
