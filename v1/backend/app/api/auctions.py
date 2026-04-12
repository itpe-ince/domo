"""Auction API.

Reference: design.md §3.2, §6.2 (bid concurrency), §6.3 (finalize)
"""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.errors import ApiError
from app.core.rate_limit import rate_limit
from app.db.session import get_db
from app.models.auction import Auction, Bid, Order
from app.models.notification import Notification
from app.models.post import Post, ProductPost
from app.models.user import User
from app.schemas.auction import (
    AuctionCreate,
    AuctionOut,
    BidCreate,
    BidOut,
    OrderOut,
)
from app.services.settings import get_setting

router = APIRouter(prefix="/auctions", tags=["auctions"])


def _serialize_auction(a: Auction) -> dict:
    return {
        "id": str(a.id),
        "product_post_id": str(a.product_post_id),
        "seller_id": str(a.seller_id),
        "start_price": str(a.start_price),
        "min_increment": str(a.min_increment),
        "current_price": str(a.current_price),
        "current_winner": str(a.current_winner) if a.current_winner else None,
        "currency": a.currency,
        "start_at": a.start_at.isoformat(),
        "end_at": a.end_at.isoformat(),
        "status": a.status,
        "bid_count": a.bid_count,
        "payment_deadline": a.payment_deadline.isoformat()
        if a.payment_deadline
        else None,
        "created_at": a.created_at.isoformat(),
    }


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ─── Auction lifecycle helpers ──────────────────────────────────────────


async def _auto_transition(db: AsyncSession, auction: Auction) -> Auction:
    """Lazily transition auction status when read.

    scheduled → active when start_at <= now
    active → ended when end_at <= now (and create order if winner)
    """
    now = _now()
    changed = False

    if auction.status == "scheduled" and auction.start_at <= now:
        auction.status = "active"
        changed = True

    if auction.status == "active" and auction.end_at <= now:
        auction.status = "ended"
        changed = True
        # Create order for winner if any
        if auction.current_winner is not None and auction.bid_count > 0:
            await _create_order_for_winner(db, auction)

    if changed:
        await db.commit()
        await db.refresh(auction)
    return auction


async def _create_order_for_winner(db: AsyncSession, auction: Auction) -> None:
    deadline_setting = await get_setting(db, "auction_payment_deadline_days")
    days = int(deadline_setting["days"]) if deadline_setting else 3
    fee_setting = await get_setting(db, "platform_fee_auction")
    fee_pct = Decimal(str(fee_setting["percent"])) if fee_setting else Decimal("10")
    fee = (auction.current_price * fee_pct / Decimal("100")).quantize(Decimal("0.01"))

    order = Order(
        buyer_id=auction.current_winner,
        seller_id=auction.seller_id,
        product_post_id=auction.product_post_id,
        source="auction",
        auction_id=auction.id,
        amount=auction.current_price,
        currency=auction.currency,
        platform_fee=fee,
        status="pending_payment",
        payment_due_at=_now() + timedelta(days=days),
    )
    db.add(order)
    auction.payment_deadline = order.payment_due_at

    db.add(
        Notification(
            user_id=auction.current_winner,
            type="auction_won",
            title="🎉 경매 낙찰",
            body=f"낙찰가 ₩{int(auction.current_price):,} 결제 기한 {days}일",
            link=f"/orders/{order.id}",
        )
    )
    db.add(
        Notification(
            user_id=auction.seller_id,
            type="auction_ended_won",
            title="경매 종료 (낙찰)",
            body=f"낙찰가 ₩{int(auction.current_price):,}",
            link=f"/auctions/{auction.id}",
        )
    )


# ─── Endpoints ──────────────────────────────────────────────────────────


@router.post("")
async def create_auction(
    body: AuctionCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if user.role not in ("artist", "admin"):
        raise ApiError("FORBIDDEN", "Only artists can create auctions", http_status=403)

    pp_result = await db.execute(
        select(ProductPost).where(ProductPost.post_id == body.product_post_id)
    )
    pp = pp_result.scalar_one_or_none()
    if not pp:
        raise ApiError("NOT_FOUND", "Product post not found", http_status=404)

    post_result = await db.execute(
        select(Post).where(Post.id == body.product_post_id)
    )
    post = post_result.scalar_one_or_none()
    if not post or post.author_id != user.id:
        raise ApiError("FORBIDDEN", "Not your post", http_status=403)

    # Check no active auction exists for this product
    existing = await db.execute(
        select(Auction).where(
            Auction.product_post_id == body.product_post_id,
            Auction.status.in_(["scheduled", "active"]),
        )
    )
    if existing.scalar_one_or_none():
        raise ApiError(
            "CONFLICT",
            "An active or scheduled auction already exists for this product",
            http_status=409,
        )

    start_at = body.start_at or _now()
    end_at = start_at + timedelta(hours=body.duration_hours)
    initial_status = "active" if start_at <= _now() else "scheduled"

    auction = Auction(
        product_post_id=body.product_post_id,
        seller_id=user.id,
        start_price=body.start_price,
        min_increment=body.min_increment,
        current_price=body.start_price,
        current_winner=None,
        currency=pp.currency or "KRW",
        start_at=start_at,
        end_at=end_at,
        status=initial_status,
    )
    db.add(auction)

    # Mark product as auction-enabled
    if not pp.is_auction:
        pp.is_auction = True

    await db.commit()
    await db.refresh(auction)
    return {"data": _serialize_auction(auction)}


@router.get("")
async def list_auctions(
    status: str | None = Query(None),
    seller_id: UUID | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    query = select(Auction).order_by(Auction.end_at.asc()).limit(limit)
    if status:
        query = query.where(Auction.status == status)
    if seller_id:
        query = query.where(Auction.seller_id == seller_id)
    result = await db.execute(query)
    auctions = list(result.scalars().all())

    # Lazy auto-transition for active list
    for a in auctions:
        await _auto_transition(db, a)

    return {
        "data": [_serialize_auction(a) for a in auctions],
        "pagination": {"next_cursor": None, "has_more": False},
    }


@router.get("/{auction_id}")
async def get_auction(
    auction_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Auction).where(Auction.id == auction_id))
    auction = result.scalar_one_or_none()
    if not auction:
        raise ApiError("NOT_FOUND", "Auction not found", http_status=404)
    auction = await _auto_transition(db, auction)
    return {"data": _serialize_auction(auction)}


@router.get("/{auction_id}/bids")
async def list_bids(
    auction_id: UUID,
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Bid)
        .where(Bid.auction_id == auction_id)
        .order_by(Bid.amount.desc())
        .limit(limit)
    )
    bids = list(result.scalars().all())
    return {
        "data": [BidOut.model_validate(b).model_dump(mode="json") for b in bids]
    }


@router.post("/{auction_id}/bids")
async def place_bid(
    auction_id: UUID,
    body: BidCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _rl=rate_limit("bid_create"),
):
    """Place a bid with FOR UPDATE row lock (design.md §6.2)."""
    # Lock the auction row
    locked = await db.execute(
        select(Auction).where(Auction.id == auction_id).with_for_update()
    )
    auction = locked.scalar_one_or_none()
    if not auction:
        raise ApiError("NOT_FOUND", "Auction not found", http_status=404)

    # Auto-transition status under lock
    now = _now()
    if auction.status == "scheduled" and auction.start_at <= now:
        auction.status = "active"

    # Status checks
    if auction.status == "scheduled":
        raise ApiError("AUCTION_NOT_STARTED", "Auction has not started", http_status=409)
    if auction.status != "active" or auction.end_at <= now:
        raise ApiError("AUCTION_CLOSED", "Auction is closed", http_status=409)

    # Account checks
    if user.warning_count >= 3 or user.status == "suspended":
        raise ApiError("ACCOUNT_SUSPENDED", "Account suspended", http_status=403)
    if user.status == "pending_guardian":
        raise ApiError(
            "FORBIDDEN",
            "Guardian consent required to bid",
            http_status=403,
        )
    if user.id == auction.seller_id:
        raise ApiError("SELF_BID_FORBIDDEN", "Cannot bid on own auction", http_status=409)

    # Minor bid limit (M5)
    if user.is_minor:
        minor_limit_setting = await get_setting(db, "minor_max_bid_amount")
        if minor_limit_setting:
            limit = Decimal(str(minor_limit_setting["amount"]))
            if Decimal(str(body.amount)) > limit:
                raise ApiError(
                    "VALIDATION_ERROR",
                    f"Minor bid limit: ₩{int(limit):,}",
                    details={"limit": str(limit)},
                    http_status=422,
                )

    # Amount validation
    min_required = auction.current_price + auction.min_increment
    if Decimal(str(body.amount)) < min_required:
        raise ApiError(
            "INSUFFICIENT_BID",
            "Bid must be >= current_price + min_increment",
            details={
                "current_price": str(auction.current_price),
                "min_increment": str(auction.min_increment),
                "min_required": str(min_required),
            },
            http_status=409,
        )

    previous_winner = auction.current_winner

    # Mark prior 'active' bid (if any) as outbid
    await db.execute(
        Bid.__table__.update()
        .where(Bid.auction_id == auction_id, Bid.status == "active")
        .values(status="outbid")
    )

    # Insert new bid
    new_bid = Bid(
        auction_id=auction_id,
        bidder_id=user.id,
        amount=body.amount,
        status="active",
    )
    db.add(new_bid)

    # Update auction
    auction.current_price = body.amount
    auction.current_winner = user.id
    auction.bid_count = (auction.bid_count or 0) + 1

    await db.commit()
    await db.refresh(new_bid)
    await db.refresh(auction)

    # Notifications (post-commit)
    if previous_winner and previous_winner != user.id:
        db.add(
            Notification(
                user_id=previous_winner,
                type="bid_outbid",
                title="입찰이 밀렸습니다",
                body=f"새 최고가 ₩{int(body.amount):,}",
                link=f"/auctions/{auction_id}",
            )
        )
    db.add(
        Notification(
            user_id=auction.seller_id,
            type="bid_placed",
            title="새로운 입찰",
            body=f"₩{int(body.amount):,} (총 {auction.bid_count}건)",
            link=f"/auctions/{auction_id}",
        )
    )
    await db.commit()

    return {
        "data": {
            "bid": BidOut.model_validate(new_bid).model_dump(mode="json"),
            "auction": _serialize_auction(auction),
        }
    }
