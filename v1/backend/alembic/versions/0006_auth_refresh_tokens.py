"""Phase 4 Week 15: refresh_tokens table

Revision ID: 0006_auth_refresh_tokens
Revises: 0005_phase3_moderation
Create Date: 2026-04-11

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0006_auth_refresh_tokens"
down_revision: Union[str, None] = "0005_phase3_moderation"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "refresh_tokens",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token_hash", sa.String(128), nullable=False, unique=True),
        sa.Column("family_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "parent_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("refresh_tokens.id"),
            nullable=True,
        ),
        sa.Column(
            "issued_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_reason", sa.String(50), nullable=True),
        sa.Column("user_agent", sa.Text, nullable=True),
        sa.Column("ip_address", postgresql.INET, nullable=True),
    )
    op.create_index(
        "idx_refresh_user", "refresh_tokens", ["user_id", "expires_at"]
    )
    op.create_index("idx_refresh_family", "refresh_tokens", ["family_id"])


def downgrade() -> None:
    op.drop_index("idx_refresh_family", table_name="refresh_tokens")
    op.drop_index("idx_refresh_user", table_name="refresh_tokens")
    op.drop_table("refresh_tokens")
