"""Phase 3 Week 11: reports, warnings

Revision ID: 0005_phase3_moderation
Revises: 0004_phase2_auction
Create Date: 2026-04-11

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0005_phase3_moderation"
down_revision: Union[str, None] = "0004_phase2_auction"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "reports",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "reporter_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("target_type", sa.String(20), nullable=False),
        sa.Column("target_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reason", sa.String(50), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("status", sa.String(20), server_default="pending"),
        sa.Column(
            "handled_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column("handled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("idx_reports_status", "reports", ["status", "created_at"])
    op.create_index(
        "idx_reports_target", "reports", ["target_type", "target_id"]
    )

    op.create_table(
        "warnings",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("reason", sa.Text, nullable=False),
        sa.Column(
            "report_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("reports.id"),
            nullable=True,
        ),
        sa.Column(
            "issued_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column("is_active", sa.Boolean, server_default=sa.text("true")),
        sa.Column("appealed", sa.Boolean, server_default=sa.text("false")),
        sa.Column("appeal_note", sa.Text, nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "idx_warnings_user_active", "warnings", ["user_id", "is_active"]
    )
    op.create_index(
        "idx_warnings_appealed", "warnings", ["appealed", "is_active"]
    )


def downgrade() -> None:
    op.drop_index("idx_warnings_appealed", table_name="warnings")
    op.drop_index("idx_warnings_user_active", table_name="warnings")
    op.drop_table("warnings")
    op.drop_index("idx_reports_target", table_name="reports")
    op.drop_index("idx_reports_status", table_name="reports")
    op.drop_table("reports")
