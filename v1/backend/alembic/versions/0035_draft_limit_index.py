"""Partial index for draft list queries — editor-draft-autosave PDCA.

Adds a partial index on posts(author_id, status, updated_at) WHERE status='draft'.
Speeds up `GET /v1/posts/drafts` (per-user list ordered by updated_at desc) and
draft count queries used by the per-user limit (NFR-4: max 20 drafts/user).

The partial WHERE clause keeps the index size small — only draft rows are
indexed, not the much larger published/scheduled posts.

Revision ID: 0035_draft_limit_index
Revises: 0034_webauthn_credentials
Create Date: 2026-04-30

"""
from typing import Sequence, Union

from alembic import op


revision: str = "0035_draft_limit_index"
down_revision: Union[str, None] = "0034_webauthn_credentials"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_posts_author_status_updated",
        "posts",
        ["author_id", "status", "updated_at"],
        postgresql_where="status = 'draft'",
    )


def downgrade() -> None:
    op.drop_index("ix_posts_author_status_updated", table_name="posts")
