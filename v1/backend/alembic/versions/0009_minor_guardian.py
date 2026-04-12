"""Phase 4 M5: guardian_consents table + users.birth_year + minor settings

Revision ID: 0009_minor_guardian
Revises: 0008_media_storage
Create Date: 2026-04-11

Adds:
- users.birth_year (GDPR-safer than full birth_date)
- users.onboarded_at (track whether user has completed onboarding)
- guardian_consents table (magic link based consent flow)
- system_settings seeds: minor_age_by_country, minor_max_bid_amount
"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0009_minor_guardian"
down_revision: Union[str, None] = "0008_media_storage"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # users: birth_year + onboarded flag
    op.add_column("users", sa.Column("birth_year", sa.Integer, nullable=True))
    op.add_column(
        "users",
        sa.Column("onboarded_at", sa.DateTime(timezone=True), nullable=True),
    )

    # guardian_consents
    op.create_table(
        "guardian_consents",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "minor_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("guardian_email", sa.String(255), nullable=False),
        sa.Column("guardian_name", sa.String(100), nullable=True),
        sa.Column(
            "consent_token", sa.String(128), unique=True, nullable=False
        ),
        sa.Column("consented_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("withdrawn_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "idx_guardian_minor", "guardian_consents", ["minor_user_id"]
    )
    op.create_index(
        "idx_guardian_active",
        "guardian_consents",
        ["minor_user_id"],
        postgresql_where=sa.text(
            "consented_at IS NOT NULL AND withdrawn_at IS NULL"
        ),
    )

    # Seed minor policy
    op.execute(
        """
        INSERT INTO system_settings(key, value) VALUES
            ('minor_age_by_country', '{"KR": 14, "US": 13, "EU": 16, "JP": 18, "default": 16}'),
            ('minor_max_bid_amount', '{"amount": 100000, "currency": "KRW"}')
        ON CONFLICT (key) DO NOTHING
        """
    )


def downgrade() -> None:
    op.execute(
        "DELETE FROM system_settings WHERE key IN ('minor_age_by_country', 'minor_max_bid_amount')"
    )
    op.drop_index("idx_guardian_active", table_name="guardian_consents")
    op.drop_index("idx_guardian_minor", table_name="guardian_consents")
    op.drop_table("guardian_consents")
    op.drop_column("users", "onboarded_at")
    op.drop_column("users", "birth_year")
