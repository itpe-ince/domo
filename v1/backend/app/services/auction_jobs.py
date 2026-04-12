"""Background jobs for auction settlement.

Reference: design.md §6.4 — process_expired_orders with second-chance logic.

This module is callable from:
- Admin endpoint POST /admin/auctions/process-expired (manual trigger)
- Background task started in main.py lifespan (every 5 minutes)
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.models.auction import Auction, Bid, Order
from app.models.notification import Notification
from app.services.moderation import issue_warning
from app.services.settings import get_setting

log = logging.getLogger(__name__)

MAX_SECOND_CHANCE_ROUNDS = 2  # design.md §6.4


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def process_expired_orders_once(db: AsyncSession) -> dict:
    """Single sweep — run by cron or manual trigger.

    Returns summary {expired, second_chance_offered, relisted_or_ended, warnings_issued}
    """
    summary = {
        "expired": 0,
        "second_chance_offered": 0,
        "relisted_or_ended": 0,
        "warnings_issued": 0,
    }

    expired_result = await db.execute(
        select(Order).where(
            Order.status == "pending_payment",
            Order.payment_due_at.is_not(None),
            Order.payment_due_at < _now(),
        )
    )
    expired_orders = list(expired_result.scalars().all())

    deadline_setting = await get_setting(db, "auction_payment_deadline_days")
    deadline_days = int(deadline_setting["days"]) if deadline_setting else 3

    for order in expired_orders:
        order.status = "expired"
        summary["expired"] += 1

        # Issue formal warning row
        await issue_warning(
            db,
            order.buyer_id,
            f"낙찰 후 결제 기한 ({deadline_days}일) 초과",
        )
        summary["warnings_issued"] += 1

        if order.source != "auction" or order.auction_id is None:
            continue

        # Lock the auction
        auc_result = await db.execute(
            select(Auction).where(Auction.id == order.auction_id).with_for_update()
        )
        auction = auc_result.scalar_one_or_none()
        if not auction:
            continue

        # Count second-chance rounds: number of expired orders for this auction so far
        sc_result = await db.execute(
            select(Order).where(
                Order.auction_id == auction.id,
                Order.status == "expired",
            )
        )
        rounds_used = len(list(sc_result.scalars().all()))

        if rounds_used > MAX_SECOND_CHANCE_ROUNDS:
            # Limit reached → seller relist decision
            auction.status = "ended"
            auction.current_winner = None
            db.add(
                Notification(
                    user_id=auction.seller_id,
                    type="auction_relist_needed",
                    title="경매 재등록 필요",
                    body="여러 차례 미결제로 경매가 종료되었습니다. 재등록을 검토해주세요.",
                    link=f"/auctions/{auction.id}",
                )
            )
            summary["relisted_or_ended"] += 1
            continue

        # Find next-highest bid excluding all already-expired buyers
        expired_buyers_result = await db.execute(
            select(Order.buyer_id).where(
                Order.auction_id == auction.id,
                Order.status == "expired",
            )
        )
        excluded = {row[0] for row in expired_buyers_result.all()}

        next_bid_query = (
            select(Bid)
            .where(Bid.auction_id == auction.id, Bid.bidder_id.notin_(excluded))
            .order_by(Bid.amount.desc())
            .limit(1)
        )
        next_bid_result = await db.execute(next_bid_query)
        next_bid = next_bid_result.scalar_one_or_none()

        if not next_bid:
            auction.status = "ended"
            auction.current_winner = None
            db.add(
                Notification(
                    user_id=auction.seller_id,
                    type="auction_relist_needed",
                    title="경매 재등록 필요",
                    body="차순위 입찰자가 없어 경매가 종료되었습니다.",
                    link=f"/auctions/{auction.id}",
                )
            )
            summary["relisted_or_ended"] += 1
            continue

        # Create new pending order for the next bidder
        fee_setting = await get_setting(db, "platform_fee_auction")
        fee_pct = (
            Decimal(str(fee_setting["percent"])) if fee_setting else Decimal("10")
        )
        fee = (next_bid.amount * fee_pct / Decimal("100")).quantize(Decimal("0.01"))

        new_order = Order(
            buyer_id=next_bid.bidder_id,
            seller_id=order.seller_id,
            product_post_id=order.product_post_id,
            source="auction",
            auction_id=auction.id,
            amount=next_bid.amount,
            currency=order.currency,
            platform_fee=fee,
            status="pending_payment",
            payment_due_at=_now() + timedelta(days=deadline_days),
        )
        db.add(new_order)

        # Update auction current price/winner to reflect second chance
        auction.current_price = next_bid.amount
        auction.current_winner = next_bid.bidder_id
        auction.payment_deadline = new_order.payment_due_at

        db.add(
            Notification(
                user_id=next_bid.bidder_id,
                type="second_chance_offer",
                title="🎁 차순위 낙찰 기회",
                body=f"앞 낙찰자가 결제하지 않아 ₩{int(next_bid.amount):,}에 낙찰 기회가 이전되었습니다.",
                link=f"/orders/{new_order.id}",
            )
        )
        summary["second_chance_offered"] += 1

    await db.commit()
    log.info("process_expired_orders_once: %s", summary)
    return summary


async def auction_cron_loop(interval_seconds: int = 300) -> None:
    """Background task — runs forever, sleeping `interval_seconds` between sweeps."""
    log.info("auction_cron_loop started (interval=%ss)", interval_seconds)
    while True:
        try:
            async with AsyncSessionLocal() as db:
                await process_expired_orders_once(db)
        except Exception as e:  # noqa: BLE001 — never crash the loop
            log.exception("auction cron sweep failed: %s", e)
        await asyncio.sleep(interval_seconds)
