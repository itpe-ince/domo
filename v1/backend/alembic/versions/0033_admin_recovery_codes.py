"""Add admin_recovery_codes table for TOTP backup codes.

Revision ID: 0033_admin_recovery_codes
Revises: 0032_admin_credentials
Create Date: 2026-04-26

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import INET, UUID

revision: str = "0033_admin_recovery_codes"
down_revision: Union[str, None] = "0032_admin_credentials"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "admin_recovery_codes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("code_hash", sa.String(length=255), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("used_user_agent", sa.Text(), nullable=True),
        sa.Column("used_ip", INET(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_admin_recovery_codes_user_id",
        "admin_recovery_codes",
        ["user_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_admin_recovery_codes_user_id",
        table_name="admin_recovery_codes",
    )
    op.drop_table("admin_recovery_codes")
