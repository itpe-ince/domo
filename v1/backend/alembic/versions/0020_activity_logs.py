"""Add user_activity_logs table

Revision ID: 0020_activity_logs
Revises: 0019_user_preferences
Create Date: 2026-04-18
"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision: str = "0020_activity_logs"
down_revision: Union[str, None] = "0019_user_preferences"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_activity_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("event_type", sa.String(30), nullable=False),
        sa.Column("target_type", sa.String(20), nullable=False),
        sa.Column("target_id", UUID(as_uuid=True), nullable=False),
        sa.Column("duration_sec", sa.Integer, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_activity_user", "user_activity_logs", ["user_id", "created_at"])
    op.create_index("idx_activity_target", "user_activity_logs", ["target_type", "target_id"])


def downgrade() -> None:
    op.drop_index("idx_activity_target", table_name="user_activity_logs")
    op.drop_index("idx_activity_user", table_name="user_activity_logs")
    op.drop_table("user_activity_logs")
