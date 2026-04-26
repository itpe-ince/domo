"""Add admin credential auth columns (password_hash, TOTP, lockout).

Adds bcrypt password hash + TOTP 2FA secret + login lockout tracking
to the users table. These columns are NULLable because regular users
continue to authenticate via SNS only — only admin-role accounts are
required to populate them.

Revision ID: 0032_admin_credentials
Revises: 0031_kyc_status_check
Create Date: 2026-04-25

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0032_admin_credentials"
down_revision: Union[str, None] = "0031_kyc_status_check"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("password_hash", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("password_changed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("totp_secret", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("totp_enabled_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column(
            "failed_login_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "users",
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "locked_until")
    op.drop_column("users", "failed_login_count")
    op.drop_column("users", "totp_enabled_at")
    op.drop_column("users", "totp_secret")
    op.drop_column("users", "password_changed_at")
    op.drop_column("users", "password_hash")
