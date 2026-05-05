"""Convert product_posts.buy_now_price from Numeric(12,2) to BigInteger (cents).

G'-10 price-unit-consistency: adopts cents (integer) as the canonical unit for
buy_now_price so that DB, API, Stripe, and search filters all agree on the unit.

Migration steps (single revision, development-environment assumption):
  1. Add price_cents BigInteger column (nullable).
  2. Back-fill: ROUND(buy_now_price * 100)::BIGINT.
  3. Validate: no NULLs where buy_now_price was NOT NULL.
  4. Drop old buy_now_price column.
  5. Rename price_cents -> buy_now_price.

Downgrade reverses: add Numeric column, divide by 100, drop BigInteger, rename.

Carry-over (Phase 8+):
  - Auction.start_price / current_price / Bid.amount — KRW Numeric unchanged.
  - Production 2-step split deployment — out of scope here.
  - Multi-currency (KRW/EUR/JPY) — separate PDCA.

Revision ID: 0051_product_price_cents
Revises: 0050_featured_artists
Create Date: 2026-05-04
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0051_product_price_cents"
down_revision: Union[str, None] = "0050_featured_artists"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Step 1: add interim cents column
    op.add_column(
        "product_posts",
        sa.Column("price_cents", sa.BigInteger(), nullable=True),
    )

    # Step 2: back-fill from existing Numeric column
    op.execute(
        """
        UPDATE product_posts
        SET price_cents = ROUND(buy_now_price * 100)::BIGINT
        WHERE buy_now_price IS NOT NULL
        """
    )

    # Step 3: validate no data loss (raises if any row would be NULL after conversion)
    op.execute(
        """
        DO $$
        DECLARE lost_rows BIGINT;
        BEGIN
            SELECT COUNT(*) INTO lost_rows
            FROM product_posts
            WHERE buy_now_price IS NOT NULL AND price_cents IS NULL;
            IF lost_rows > 0 THEN
                RAISE EXCEPTION 'price-unit-consistency migration: % rows lost during cents conversion', lost_rows;
            END IF;
        END $$;
        """
    )

    # Step 4: drop old Numeric column
    op.drop_column("product_posts", "buy_now_price")

    # Step 5: rename price_cents -> buy_now_price
    op.alter_column("product_posts", "price_cents", new_column_name="buy_now_price")


def downgrade() -> None:
    # Reverse: BigInteger cents -> Numeric(12,2) dollars
    op.add_column(
        "product_posts",
        sa.Column("price_numeric", sa.Numeric(precision=12, scale=2), nullable=True),
    )
    op.execute(
        """
        UPDATE product_posts
        SET price_numeric = buy_now_price::NUMERIC / 100
        WHERE buy_now_price IS NOT NULL
        """
    )
    op.drop_column("product_posts", "buy_now_price")
    op.alter_column("product_posts", "price_numeric", new_column_name="buy_now_price")
