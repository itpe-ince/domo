"""Add search_history table — A-5 search-enhancement.

Stores per-user search history with soft delete.
SearchLog (anonymous analytics) remains separate.

Revision ID: 0049_search_history
Revises: 0048_subscription_expiry_notif
Create Date: 2026-05-04
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

revision: str = "0049_search_history"
down_revision: Union[str, None] = "0048_subscription_expiry_notif"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "search_history",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("query", sa.String(200), nullable=False),
        sa.Column("result_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "searched_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Fast user history lookup (DESC by time, filtered to non-deleted)
    op.create_index(
        "idx_search_history_user_active",
        "search_history",
        ["user_id", "searched_at"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    # Popular searches aggregation (recent 24h window)
    op.create_index(
        "idx_search_history_searched_at",
        "search_history",
        ["searched_at"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "idx_search_history_searched_at",
        table_name="search_history",
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.drop_index(
        "idx_search_history_user_active",
        table_name="search_history",
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.drop_table("search_history")
