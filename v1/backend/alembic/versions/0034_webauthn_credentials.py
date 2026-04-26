"""Add WebAuthn credentials and challenges tables.

Revision ID: 0034_webauthn_credentials
Revises: 0033_admin_recovery_codes
Create Date: 2026-04-26

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "0034_webauthn_credentials"
down_revision: Union[str, None] = "0033_admin_recovery_codes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "webauthn_credentials",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("credential_id", sa.LargeBinary(), nullable=False, unique=True),
        sa.Column("public_key", sa.LargeBinary(), nullable=False),
        sa.Column("sign_count", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("transports", sa.String(length=100), nullable=True),
        sa.Column("nickname", sa.String(length=100), nullable=True),
        sa.Column("aaguid", sa.LargeBinary(), nullable=True),
        sa.Column(
            "backed_up",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_user_agent", sa.Text(), nullable=True),
    )
    op.create_index(
        "ix_webauthn_credentials_user_id",
        "webauthn_credentials",
        ["user_id"],
    )

    op.create_table(
        "webauthn_challenges",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("challenge", sa.LargeBinary(), nullable=False),
        sa.Column("purpose", sa.String(length=20), nullable=False),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("expected_email", sa.String(length=255), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_webauthn_challenges_user_id",
        "webauthn_challenges",
        ["user_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_webauthn_challenges_user_id", table_name="webauthn_challenges")
    op.drop_table("webauthn_challenges")
    op.drop_index("ix_webauthn_credentials_user_id", table_name="webauthn_credentials")
    op.drop_table("webauthn_credentials")
