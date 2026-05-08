"""alembic 0087 — users.github_id 컬럼 추가 (Phase 12 C-2).

GitHub OAuth 로그인을 위한 BIGINT github_id 컬럼 추가.
- sns_id는 VARCHAR(255)이므로 BIGINT GitHub ID는 별도 컬럼으로 관리.
- google_id는 sub 문자열이므로 sns_id로 충분하나, github_id는 BIGINT 타입 보장 필요.

down_revision = "0086_magic_link_tokens"
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0087_github_id"
down_revision = "0086_magic_link_tokens"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("github_id", sa.BigInteger, nullable=True, unique=True),
    )
    op.create_index("ix_users_github_id", "users", ["github_id"])


def downgrade() -> None:
    op.drop_index("ix_users_github_id", table_name="users")
    op.drop_column("users", "github_id")
