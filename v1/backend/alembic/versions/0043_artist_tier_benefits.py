"""Add artist_tier_benefits table — B-4 tier-benefits-customization.

artist_tier_benefits: per-artist override for tier benefits text
(subscriber | sponsor | follower). Platform default used when no
override row exists for a given (artist_id, tier) pair.

Revision ID: 0043_artist_tier_benefits
Revises: 0042_auction_promotion
Create Date: 2026-05-04
"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from alembic import op

revision: str = "0043_artist_tier_benefits"
down_revision: Union[str, None] = "0042_auction_promotion"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "artist_tier_benefits",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "artist_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("tier", sa.String(20), nullable=False),
        sa.Column("benefits", JSONB, nullable=False, server_default="[]"),
        sa.Column("welcome_message", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("artist_id", "tier", name="uq_atb_artist_tier"),
    )
    # Index for fast lookup by artist_id
    op.create_index("ix_atb_artist", "artist_tier_benefits", ["artist_id"])


def downgrade() -> None:
    op.drop_index("ix_atb_artist", table_name="artist_tier_benefits")
    op.drop_table("artist_tier_benefits")
