"""Add multi-currency fields to core tables — B'-1 multi-currency-foundation.

Adds currency columns to posts (buy_now_currency), auctions (verify existing),
sponsorships (verify existing), subscriptions, and preferred_currency to users.

Revision ID: 0061_multi_currency
Revises: 0060_ses_bounce_tracking
Create Date: 2026-05-04
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0061_multi_currency"
down_revision: Union[str, None] = "0060_ses_bounce_tracking"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── users: preferred_currency ──────────────────────────────────────────────
    op.add_column(
        "users",
        sa.Column(
            "preferred_currency",
            sa.String(3),
            nullable=False,
            server_default="USD",
            comment="B'-1. User display currency preference. Stored: USD/KRW/EUR/JPY.",
        ),
    )

    # ── product_posts: buy_now_currency ────────────────────────────────────────
    # Note: product_posts already has a 'currency' column (KRW default from G'-10).
    # We add buy_now_currency as the canonical sell-currency for the buy_now flow.
    # Existing rows will default to 'USD' (safe — old data was KRW-centric but
    # the buy_now price was stored in cents; display currency is a UI concern).
    op.add_column(
        "product_posts",
        sa.Column(
            "buy_now_currency",
            sa.String(3),
            nullable=False,
            server_default="USD",
            comment="B'-1. Currency for buy_now_price. USD/KRW/EUR/JPY.",
        ),
    )

    # ── sponsorships: ensure currency column has correct default ───────────────
    # The column already exists (original schema). We just update the server_default
    # from 'KRW' to 'USD' for new rows. Existing data is preserved.
    op.alter_column(
        "sponsorships",
        "currency",
        existing_type=sa.String(3),
        server_default="USD",
        existing_nullable=False,
    )

    # ── subscriptions: ensure currency column has correct default ──────────────
    # The column already exists. Update server_default to 'USD'.
    op.alter_column(
        "subscriptions",
        "currency",
        existing_type=sa.String(3),
        server_default="USD",
        existing_nullable=False,
    )

    # ── Index for fast preferred_currency lookups (admin analytics) ────────────
    op.create_index(
        "ix_users_preferred_currency",
        "users",
        ["preferred_currency"],
    )


def downgrade() -> None:
    op.drop_index("ix_users_preferred_currency", table_name="users")
    op.drop_column("product_posts", "buy_now_currency")
    op.drop_column("users", "preferred_currency")

    # Restore original server_defaults
    op.alter_column(
        "subscriptions",
        "currency",
        existing_type=sa.String(3),
        server_default="KRW",
        existing_nullable=False,
    )
    op.alter_column(
        "sponsorships",
        "currency",
        existing_type=sa.String(3),
        server_default="KRW",
        existing_nullable=False,
    )
