"""ExchangeRate model — B'-1 multi-currency-foundation (alembic 0062).

Stores Open Exchange Rates API results with 1h TTL.
Cron job: app/services/exchange_rate_jobs.py (9th worker, R-5 isolated).
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Integer, Numeric, String, UniqueConstraint, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ExchangeRate(Base):
    """Cached exchange rate (base=USD → target currency).

    Updated hourly by exchange_rate_cron_loop.
    Upserted via INSERT ... ON CONFLICT DO UPDATE.
    """

    __tablename__ = "exchange_rates"
    __table_args__ = (
        UniqueConstraint("base_currency", "target_currency", name="ix_exchange_rates_pair"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    base_currency: Mapped[str] = mapped_column(
        String(3), nullable=False, server_default="USD"
    )
    target_currency: Mapped[str] = mapped_column(String(3), nullable=False)
    rate: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
