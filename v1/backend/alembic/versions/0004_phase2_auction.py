"""Phase 2 Week 9: auctions, bids, orders

Revision ID: 0004_phase2_auction
Revises: 0003_phase2_sponsorship
Create Date: 2026-04-11

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0004_phase2_auction"
down_revision: Union[str, None] = "0003_phase2_sponsorship"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "auctions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "product_post_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("product_posts.post_id"),
            nullable=False,
        ),
        sa.Column(
            "seller_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("start_price", sa.Numeric(12, 2), nullable=False),
        sa.Column(
            "min_increment", sa.Numeric(12, 2), nullable=False, server_default="1000"
        ),
        sa.Column("current_price", sa.Numeric(12, 2), nullable=False),
        sa.Column(
            "current_winner",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column("currency", sa.String(3), server_default="KRW"),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(20), server_default="scheduled"),
        sa.Column("bid_count", sa.Integer, server_default="0"),
        sa.Column("payment_deadline", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("idx_auctions_status", "auctions", ["status", "end_at"])
    op.create_index("idx_auctions_seller", "auctions", ["seller_id", "created_at"])

    op.create_table(
        "bids",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "auction_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("auctions.id"),
            nullable=False,
        ),
        sa.Column(
            "bidder_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("status", sa.String(20), server_default="active"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("idx_bids_auction", "bids", ["auction_id", "amount"])

    op.create_table(
        "orders",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "buyer_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column(
            "seller_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column(
            "product_post_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("product_posts.post_id"),
            nullable=False,
        ),
        sa.Column("source", sa.String(20), nullable=False),
        sa.Column(
            "auction_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("auctions.id"),
            nullable=True,
        ),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(3), server_default="KRW"),
        sa.Column("platform_fee", sa.Numeric(12, 2), server_default="0"),
        sa.Column("status", sa.String(30), server_default="pending_payment"),
        sa.Column("payment_intent_id", sa.String(100), nullable=True),
        sa.Column("payment_due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("idx_orders_buyer", "orders", ["buyer_id", "created_at"])
    op.create_index("idx_orders_seller", "orders", ["seller_id", "created_at"])
    op.create_index("idx_orders_status", "orders", ["status", "payment_due_at"])


def downgrade() -> None:
    op.drop_index("idx_orders_status", table_name="orders")
    op.drop_index("idx_orders_seller", table_name="orders")
    op.drop_index("idx_orders_buyer", table_name="orders")
    op.drop_table("orders")
    op.drop_index("idx_bids_auction", table_name="bids")
    op.drop_table("bids")
    op.drop_index("idx_auctions_seller", table_name="auctions")
    op.drop_index("idx_auctions_status", table_name="auctions")
    op.drop_table("auctions")
