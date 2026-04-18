"""KYC: identity verification fields + kyc_sessions table

Revision ID: 0021_kyc
Revises: 0020_activity_logs
Create Date: 2026-04-18
"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

from alembic import op

revision: str = "0021_kyc"
down_revision: Union[str, None] = "0020_activity_logs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("identity_verified_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("identity_provider", sa.String(20), nullable=True))

    op.create_table(
        "kyc_sessions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("provider", sa.String(20), nullable=False),
        sa.Column("external_session_id", sa.String(200), nullable=True),
        sa.Column("status", sa.String(20), server_default="pending"),
        sa.Column("result_data", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("idx_kyc_user", "kyc_sessions", ["user_id"])


def downgrade() -> None:
    op.drop_index("idx_kyc_user", table_name="kyc_sessions")
    op.drop_table("kyc_sessions")
    op.drop_column("users", "identity_provider")
    op.drop_column("users", "identity_verified_at")
