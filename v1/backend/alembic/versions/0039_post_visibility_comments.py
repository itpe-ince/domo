"""Add visibility + comments_enabled to posts — publish-controls PDCA #8 Step 1.

Adds:
- posts.visibility  String(20) NOT NULL DEFAULT 'public'
  CHECK (visibility IN ('public', 'followers_only', 'unlisted'))
  OQ-1=A (enum), OQ-2=A (backfill existing rows to 'public').
- posts.comments_enabled  Boolean NOT NULL DEFAULT TRUE
  OQ-3=A (False blocks new POST /comments; existing comments preserved).
- composite index ix_posts_visibility_status_created (visibility, status, created_at DESC)
  OQ-10=A — feeds/explore/search all filter on this triple.

Upgrade: nullable add → backfill → NOT NULL + CHECK (safe for tables with existing rows).
Downgrade: reverse order, drop index first.

Revision ID: 0039_post_visibility_comments
Revises: 0038_orig_signature_keys
Create Date: 2026-05-03
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0039_post_visibility_comments"
down_revision: Union[str, None] = "0038_orig_signature_keys"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. visibility: nullable → backfill → NOT NULL + CHECK
    op.add_column("posts", sa.Column("visibility", sa.String(20), nullable=True))
    op.execute("UPDATE posts SET visibility = 'public' WHERE visibility IS NULL")
    op.alter_column("posts", "visibility", nullable=False)
    op.create_check_constraint(
        "ck_posts_visibility_enum",
        "posts",
        "visibility IN ('public', 'followers_only', 'unlisted')",
    )

    # 2. comments_enabled: nullable → backfill → NOT NULL
    op.add_column("posts", sa.Column("comments_enabled", sa.Boolean, nullable=True))
    op.execute("UPDATE posts SET comments_enabled = TRUE WHERE comments_enabled IS NULL")
    op.alter_column("posts", "comments_enabled", nullable=False)

    # 3. composite index — OQ-10=A
    op.create_index(
        "ix_posts_visibility_status_created",
        "posts",
        ["visibility", "status", sa.text("created_at DESC")],
    )


def downgrade() -> None:
    op.drop_index("ix_posts_visibility_status_created", table_name="posts")
    op.drop_constraint("ck_posts_visibility_enum", "posts", type_="check")
    op.drop_column("posts", "comments_enabled")
    op.drop_column("posts", "visibility")
