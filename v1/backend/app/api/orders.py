"""Orders API: buy-now + payment + listing + cancel.

Reference: design.md §3.2, §6.4 (expired orders), §11 (S-new-1 buy-now ↔ auction)
"""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.errors import ApiError
from app.core.rate_limit import rate_limit
from app.db.session import get_db
from app.models.auction import Auction, Bid, Order
from app.models.notification import Notification
from app.models.post import Post, ProductPost
from app.models.user import User
from app.schemas.auction import OrderOut
from app.services.payments import get_payment_provider
from app.services.settings import get_setting

orders_router = APIRouter(prefix="/orders", tags=["orders"])
products_router = APIRouter(prefix="/products", tags=["products"])


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _serialize_order(o: Order) -> dict:
    return {
        "id": str(o.id),
        "buyer_id": str(o.buyer_id),
        "seller_id": str(o.seller_id),
        "product_post_id": str(o.product_post_id),
        "source": o.source,
        "auction_id": str(o.auction_id) if o.auction_id else None,
        "amount": str(o.amount),
        "currency": o.currency,
        "platform_fee": str(o.platform_fee),
        "status": o.status,
        "payment_intent_id": o.payment_intent_id,
        "payment_due_at": o.payment_due_at.isoformat() if o.payment_due_at else None,
        "paid_at": o.paid_at.isoformat() if o.paid_at else None,
        "created_at": o.created_at.isoformat(),
    }


# ─── Buy Now ────────────────────────────────────────────────────────────


@products_router.post("/{post_id}/buy-now")
async def buy_now(
    post_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _rl=rate_limit("buy_now"),
):
    """Immediately purchase a product post.

    Per design.md §11 / S-new-1: if the product also has an active auction,
    that auction is automatically cancelled and any winning bid notified.
    """
    # Lock the product row
    pp_result = await db.execute(
        select(ProductPost).where(ProductPost.post_id == post_id).with_for_update()
    )
    pp = pp_result.scalar_one_or_none()
    if not pp:
        raise ApiError("NOT_FOUND", "Product not found", http_status=404)
    if not pp.is_buy_now:
        raise ApiError(
            "VALIDATION_ERROR",
            "Buy-now is not enabled for this product",
            http_status=422,
        )
    if pp.is_sold:
        raise ApiError("ALREADY_PURCHASED", "Product already sold", http_status=409)
    if pp.buy_now_price is None or pp.buy_now_price <= 0:
        raise ApiError(
            "VALIDATION_ERROR", "buy_now_price not set", http_status=422
        )

    post_result = await db.execute(select(Post).where(Post.id == post_id))
    post = post_result.scalar_one_or_none()
    if not post:
        raise ApiError("NOT_FOUND", "Post not found", http_status=404)
    if post.author_id == user.id:
        raise ApiError(
            "VALIDATION_ERROR", "Cannot buy your own product", http_status=422
        )
    if user.warning_count >= 3 or user.status == "suspended":
        raise ApiError("ACCOUNT_SUSPENDED", "Account suspended", http_status=403)

    # Compute platform fee
    fee_setting = await get_setting(db, "platform_fee_buy_now")
    fee_pct = (
        Decimal(str(fee_setting["percent"])) if fee_setting else Decimal("8")
    )
    fee = (pp.buy_now_price * fee_pct / Decimal("100")).quantize(Decimal("0.01"))

    # Create payment intent
    deadline = await get_setting(db, "auction_payment_deadline_days")
    deadline_days = int(deadline["days"]) if deadline else 3

    provider = get_payment_provider()
    intent = await provider.create_payment_intent(
        amount=pp.buy_now_price,
        currency=pp.currency or "KRW",
        metadata={
            "purpose": "buy_now",
            "buyer_id": str(user.id),
            "product_post_id": str(post_id),
        },
    )

    order = Order(
        buyer_id=user.id,
        seller_id=post.author_id,
        product_post_id=post_id,
        source="buy_now",
        auction_id=None,
        amount=pp.buy_now_price,
        currency=pp.currency or "KRW",
        platform_fee=fee,
        status="pending_payment",
        payment_intent_id=intent.id,
        payment_due_at=_now() + timedelta(days=deadline_days),
    )
    db.add(order)

    # S-new-1: Cancel any active/scheduled auction tied to this product
    auction_result = await db.execute(
        select(Auction).where(
            Auction.product_post_id == post_id,
            Auction.status.in_(["scheduled", "active"]),
        )
    )
    cancelled_auctions = list(auction_result.scalars().all())
    affected_bidders: set[UUID] = set()
    for auction in cancelled_auctions:
        # Collect distinct bidders for refund-style notifications
        bidder_result = await db.execute(
            select(Bid.bidder_id).where(Bid.auction_id == auction.id).distinct()
        )
        for row in bidder_result.all():
            affected_bidders.add(row[0])
        auction.status = "cancelled"
        # Mark all live bids as cancelled
        await db.execute(
            Bid.__table__.update()
            .where(Bid.auction_id == auction.id, Bid.status == "active")
            .values(status="cancelled")
        )

    await db.commit()
    await db.refresh(order)

    # Notify cancelled-auction bidders post-commit
    for bidder_id in affected_bidders:
        if bidder_id == user.id:
            continue
        db.add(
            Notification(
                user_id=bidder_id,
                type="auction_cancelled_buy_now",
                title="경매가 취소되었습니다",
                body="작품이 즉시 구매로 판매되어 경매가 종료되었습니다.",
                link=f"/posts/{post_id}",
            )
        )
    if cancelled_auctions:
        await db.commit()

    return {
        "data": {
            "order": _serialize_order(order),
            "payment_intent": {
                "id": intent.id,
                "client_secret": intent.client_secret,
                "amount": str(intent.amount),
                "currency": intent.currency,
                "status": intent.status,
            },
            "cancelled_auctions": [str(a.id) for a in cancelled_auctions],
        }
    }


# ─── Payment / Cancel ───────────────────────────────────────────────────


@orders_router.post("/{order_id}/pay")
async def pay_order(
    order_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mock-confirm payment for an order (auction win or buy-now)."""
    result = await db.execute(
        select(Order).where(Order.id == order_id).with_for_update()
    )
    order = result.scalar_one_or_none()
    if not order:
        raise ApiError("NOT_FOUND", "Order not found", http_status=404)
    if order.buyer_id != user.id:
        raise ApiError("FORBIDDEN", "Not your order", http_status=403)
    if order.status != "pending_payment":
        raise ApiError(
            "CONFLICT",
            f"Order is not pending payment (current: {order.status})",
            http_status=409,
        )
    if order.payment_due_at and order.payment_due_at < _now():
        raise ApiError(
            "CONFLICT", "Payment deadline has passed", http_status=409
        )

    provider = get_payment_provider()

    # If no payment intent yet (auction-created order), create one now
    if not order.payment_intent_id:
        intent = await provider.create_payment_intent(
            amount=order.amount,
            currency=order.currency,
            metadata={
                "purpose": "auction_settlement",
                "order_id": str(order.id),
                "buyer_id": str(user.id),
            },
        )
        order.payment_intent_id = intent.id

    await provider.confirm_payment_intent(order.payment_intent_id)
    order.status = "paid"
    order.paid_at = _now()

    # Mark product as sold
    pp_result = await db.execute(
        select(ProductPost).where(ProductPost.post_id == order.product_post_id)
    )
    pp = pp_result.scalar_one_or_none()
    if pp:
        pp.is_sold = True

    # Settle auction
    if order.auction_id:
        auc_result = await db.execute(
            select(Auction).where(Auction.id == order.auction_id)
        )
        auction = auc_result.scalar_one_or_none()
        if auction and auction.status in ("ended",):
            auction.status = "settled"

    db.add(
        Notification(
            user_id=order.seller_id,
            type="order_paid",
            title="결제 완료",
            body=f"구매자가 결제를 완료했습니다. ₩{int(order.amount):,}",
            link=f"/orders/{order.id}",
        )
    )
    await db.commit()
    await db.refresh(order)
    return {"data": _serialize_order(order)}


@orders_router.post("/{order_id}/cancel")
async def cancel_order(
    order_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Buyer cancels a pending order before paying."""
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise ApiError("NOT_FOUND", "Order not found", http_status=404)
    if order.buyer_id != user.id:
        raise ApiError("FORBIDDEN", "Not your order", http_status=403)
    if order.status != "pending_payment":
        raise ApiError("CONFLICT", "Cannot cancel", http_status=409)

    order.status = "cancelled"
    await db.commit()
    await db.refresh(order)
    return {"data": _serialize_order(order)}


# ─── Listings ───────────────────────────────────────────────────────────


@orders_router.get("/mine")
async def my_orders(
    role: str = Query("buyer"),  # 'buyer' | 'seller'
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if role == "seller":
        query = (
            select(Order)
            .where(Order.seller_id == user.id)
            .order_by(Order.created_at.desc())
        )
    else:
        query = (
            select(Order)
            .where(Order.buyer_id == user.id)
            .order_by(Order.created_at.desc())
        )
    result = await db.execute(query)
    orders = list(result.scalars().all())
    return {"data": [_serialize_order(o) for o in orders]}


@orders_router.get("/{order_id}")
async def get_order(
    order_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise ApiError("NOT_FOUND", "Order not found", http_status=404)
    if order.buyer_id != user.id and order.seller_id != user.id:
        raise ApiError("FORBIDDEN", "Not your order", http_status=403)
    return {"data": _serialize_order(order)}
