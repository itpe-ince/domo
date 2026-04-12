"""Add search_logs table + search performance indexes

Revision ID: 0010_search_logs
Revises: 0009_minor_guardian
Create Date: 2026-04-12

Adds:
- search_logs table (query logging for analytics & recommendation)
- idx_posts_title_lower on posts(lower(title))
- idx_users_display_name_lower on users(lower(display_name))
"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

from alembic import op

revision: str = "0010_search_logs"
down_revision: Union[str, None] = "0009_minor_guardian"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "search_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("session_id", sa.String(64), nullable=True),
        sa.Column("query", sa.String(200), nullable=False),
        sa.Column("tab", sa.String(20), nullable=False),
        sa.Column("result_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("filters", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("idx_search_logs_user", "search_logs", ["user_id", "created_at"])
    op.create_index("idx_search_logs_query", "search_logs", ["query", "created_at"])

    # Search performance indexes (M2)
    op.create_index("idx_posts_title_lower", "posts", [sa.text("lower(title)")])
    op.create_index("idx_users_display_name_lower", "users", [sa.text("lower(display_name)")])


def downgrade() -> None:
    op.drop_index("idx_users_display_name_lower", table_name="users")
    op.drop_index("idx_posts_title_lower", table_name="posts")
    op.drop_index("idx_search_logs_query", table_name="search_logs")
    op.drop_index("idx_search_logs_user", table_name="search_logs")
    op.drop_table("search_logs")
