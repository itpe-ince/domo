"""Phase 2: sponsorships, subscriptions, system_settings

Revision ID: 0003_phase2_sponsorship
Revises: 0002_phase1_content
Create Date: 2026-04-11

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0003_phase2_sponsorship"
down_revision: Union[str, None] = "0002_phase1_content"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "sponsorships",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "sponsor_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column(
            "artist_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column(
            "post_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("posts.id"),
            nullable=True,
        ),
        sa.Column("bluebird_count", sa.Integer, nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(3), server_default="KRW"),
        sa.Column("is_anonymous", sa.Boolean, server_default=sa.text("false")),
        sa.Column("visibility", sa.String(20), server_default="public"),
        sa.Column("message", sa.Text, nullable=True),
        sa.Column("payment_intent_id", sa.String(100), nullable=True),
        sa.Column("status", sa.String(20), server_default="pending"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "idx_sponsorship_artist", "sponsorships", ["artist_id", "created_at"]
    )
    op.create_index(
        "idx_sponsorship_sponsor", "sponsorships", ["sponsor_id", "created_at"]
    )

    op.create_table(
        "subscriptions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "sponsor_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column(
            "artist_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("monthly_bluebird", sa.Integer, nullable=False),
        sa.Column("monthly_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(3), server_default="KRW"),
        sa.Column("provider_subscription_id", sa.String(100), nullable=True),
        sa.Column("status", sa.String(20), server_default="active"),
        sa.Column(
            "cancel_at_period_end", sa.Boolean, server_default=sa.text("false")
        ),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "idx_subscription_pair",
        "subscriptions",
        ["sponsor_id", "artist_id"],
    )

    op.create_table(
        "system_settings",
        sa.Column("key", sa.String(100), primary_key=True),
        sa.Column("value", postgresql.JSONB, nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # Seed default settings (design.md §2.2 system_settings examples)
    op.execute(
        """
        INSERT INTO system_settings(key, value) VALUES
            ('bluebird_unit_price', '{"amount": 1000, "currency": "KRW"}'),
            ('platform_fee_sponsorship', '{"percent": 5}'),
            ('platform_fee_auction', '{"percent": 10}'),
            ('platform_fee_buy_now', '{"percent": 8}'),
            ('auction_payment_deadline_days', '{"days": 3}'),
            ('warning_threshold', '{"count": 3}')
        """
    )


def downgrade() -> None:
    op.drop_table("system_settings")
    op.drop_index("idx_subscription_pair", table_name="subscriptions")
    op.drop_table("subscriptions")
    op.drop_index("idx_sponsorship_sponsor", table_name="sponsorships")
    op.drop_index("idx_sponsorship_artist", table_name="sponsorships")
    op.drop_table("sponsorships")
