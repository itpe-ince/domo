"""Create exchange_rates table — B'-1 multi-currency-foundation.

ExchangeRate stores Open Exchange Rates API results with 1h TTL.
Used by the exchange_rate cron job (9th worker) and GET /v1/exchange-rates endpoint.

Revision ID: 0062_exchange_rates
Revises: 0061_multi_currency
Create Date: 2026-05-04
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0062_exchange_rates"
down_revision: Union[str, None] = "0061_multi_currency"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "exchange_rates",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "base_currency",
            sa.String(3),
            nullable=False,
            server_default="USD",
            comment="Always USD (Open Exchange Rates free tier base).",
        ),
        sa.Column(
            "target_currency",
            sa.String(3),
            nullable=False,
            comment="Target currency code: KRW, EUR, JPY, USD.",
        ),
        sa.Column(
            "rate",
            sa.Numeric(18, 8),
            nullable=False,
            comment="1 base_currency = rate target_currency.",
        ),
        sa.Column(
            "fetched_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
            comment="When this rate was fetched from the API.",
        ),
        sa.Column(
            "expires_at",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="When the 1h cache TTL expires.",
        ),
    )

    # Unique on (base_currency, target_currency) — upsert pattern
    op.create_index(
        "ix_exchange_rates_pair",
        "exchange_rates",
        ["base_currency", "target_currency"],
        unique=True,
    )

    # Fast lookup for expiry check
    op.create_index(
        "ix_exchange_rates_expires_at",
        "exchange_rates",
        ["expires_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_exchange_rates_expires_at", table_name="exchange_rates")
    op.drop_index("ix_exchange_rates_pair", table_name="exchange_rates")
    op.drop_table("exchange_rates")
