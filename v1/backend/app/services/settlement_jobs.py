"""Settlement batch generation and cron job.

Generates settlement batches for artists based on inspection-completed orders.
Runs weekly (Monday) or monthly (1st) based on system_settings.settlement_cycle.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.models.auction import Order
from app.models.notification import Notification
from app.models.settlement import Settlement, SettlementItem
from app.models.user import User
from app.services.settings import get_setting

log = logging.getLogger(__name__)


async def generate_settlement_batch(
    db: AsyncSession,
    period_start: date,
    period_end: date,
) -> list[Settlement]:
    """Generate settlement records for all artists with completed orders in the period."""
    # Find orders that are inspection_complete (검수 완료, 정산 대기)
    # and fall within the period
    result = await db.execute(
        select(Order).where(
            Order.status == "inspection_complete",  # 검수 완료, 정산 대기
            Order.inspection_completed_at.isnot(None),
            func.date(Order.inspection_completed_at) >= period_start,
            func.date(Order.inspection_completed_at) <= period_end,
        )
    )
    orders = list(result.scalars().all())

    if not orders:
        log.info("No orders to settle for period %s ~ %s", period_start, period_end)
        return []

    # Group by artist (seller)
    artist_orders: dict[str, list[Order]] = {}
    for o in orders:
        key = str(o.seller_id)
        artist_orders.setdefault(key, []).append(o)

    settlements = []
    for artist_id_str, artist_order_list in artist_orders.items():
        gross = sum(o.amount for o in artist_order_list)
        fees = sum(o.platform_fee for o in artist_order_list)
        net = gross - fees

        settlement = Settlement(
            artist_id=artist_order_list[0].seller_id,
            period_start=period_start,
            period_end=period_end,
            order_count=len(artist_order_list),
            gross_amount=gross,
            platform_fee=fees,
            net_amount=net,
            currency=artist_order_list[0].currency or "KRW",
            status="pending",
        )
        db.add(settlement)
        await db.flush()

        for o in artist_order_list:
            db.add(SettlementItem(settlement_id=settlement.id, order_id=o.id))
            o.status = "settled"  # included in settlement batch; transitions to paid_out on approval+pay
            o.settled_at = datetime.now(timezone.utc)

        # Notify artist
        db.add(Notification(
            user_id=settlement.artist_id,
            type="settlement_created",
            title="정산 생성",
            body=f"{period_start}~{period_end} 기간 정산이 생성되었습니다. (${float(net):.2f})",
        ))

        settlements.append(settlement)
        log.info(
            "Settlement created: artist=%s orders=%d net=$%.2f",
            artist_id_str[:8], len(artist_order_list), float(net),
        )

    await db.commit()
    return settlements


async def settlement_cron_loop(interval_seconds: int = 86400) -> None:
    """Background task — checks daily, generates batch on settlement day."""
    log.info("settlement_cron_loop started (interval=%ss)", interval_seconds)
    while True:
        try:
            async with AsyncSessionLocal() as db:
                cycle_setting = await get_setting(db, "settlement_cycle")
                cycle = (cycle_setting or {}).get("cycle", "weekly")

                today = date.today()
                should_run = False
                period_start = period_end = today

                if cycle == "weekly" and today.weekday() == 0:  # Monday
                    period_end = today - timedelta(days=1)  # Sunday
                    period_start = period_end - timedelta(days=6)  # Previous Monday
                    should_run = True
                elif cycle == "monthly" and today.day == 1:
                    period_end = today - timedelta(days=1)  # Last day of prev month
                    period_start = period_end.replace(day=1)  # 1st of prev month
                    should_run = True

                if should_run:
                    batches = await generate_settlement_batch(db, period_start, period_end)
                    if batches:
                        log.info("Settlement cron: generated %d batches", len(batches))
        except Exception as e:
            log.exception("settlement cron failed: %s", e)
        await asyncio.sleep(interval_seconds)
