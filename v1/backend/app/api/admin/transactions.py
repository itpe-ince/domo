"""Admin: auction, order, and refund management endpoints."""
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.admin_deps import require_admin_with_2fa
from app.core.errors import ApiError
from app.db.session import get_db
from app.models.auction import Auction, Order
from app.models.notification import Notification
from app.models.user import User
from app.schemas.auction import RefundRequest
from app.services.auction_jobs import process_expired_orders_once
from app.services.payments import get_payment_provider

router = APIRouter(tags=["admin"])

_REFUNDABLE_STATUSES = {"paid", "shipped", "inspection"}


def _serialize_order_admin(o: Order) -> dict:
    """Minimal order serialiser for admin responses."""
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
        "paid_at": o.paid_at.isoformat() if o.paid_at else None,
        "refunded_at": o.refunded_at.isoformat() if o.refunded_at else None,
        "created_at": o.created_at.isoformat(),
    }


@router.post("/auctions/process-expired")
async def trigger_process_expired(
    admin: User = Depends(require_admin_with_2fa),
    db: AsyncSession = Depends(get_db),
):
    """Manually trigger the auction expiry sweep (also runs every 5 min in background)."""
    summary = await process_expired_orders_once(db)
    return {"data": summary}


@router.get("/auctions/list")
async def list_auctions_admin(
    status: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    _admin: User = Depends(require_admin_with_2fa),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import func as sqlfunc

    query = select(Auction)
    if status:
        query = query.where(Auction.status == status)
    total = await db.scalar(select(sqlfunc.count()).select_from(query.subquery()))
    result = await db.execute(query.order_by(Auction.created_at.desc()).offset(offset).limit(limit))
    auctions = result.scalars().all()

    seller_ids = list({a.seller_id for a in auctions})
    seller_map = {}
    if seller_ids:
        sellers = await db.execute(select(User).where(User.id.in_(seller_ids)))
        seller_map = {u.id: u for u in sellers.scalars()}

    return {
        "data": [
            {
                "id": str(a.id),
                "seller_name": seller_map[a.seller_id].display_name if a.seller_id in seller_map else "unknown",
                "start_price": float(a.start_price), "current_price": float(a.current_price),
                "currency": a.currency, "bid_count": a.bid_count, "status": a.status,
                "end_at": a.end_at.isoformat(),
            }
            for a in auctions
        ],
        "pagination": {"total": total or 0, "offset": offset, "limit": limit},
    }


@router.get("/orders/list")
async def list_orders_admin(
    status: str | None = Query(None),
    source: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    _admin: User = Depends(require_admin_with_2fa),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import func as sqlfunc

    query = select(Order)
    if status:
        query = query.where(Order.status == status)
    if source:
        query = query.where(Order.source == source)
    total = await db.scalar(select(sqlfunc.count()).select_from(query.subquery()))
    result = await db.execute(query.order_by(Order.created_at.desc()).offset(offset).limit(limit))
    orders = result.scalars().all()

    user_ids = list({o.buyer_id for o in orders} | {o.seller_id for o in orders})
    user_map = {}
    if user_ids:
        users = await db.execute(select(User).where(User.id.in_(user_ids)))
        user_map = {u.id: u for u in users.scalars()}

    return {
        "data": [
            {
                "id": str(o.id),
                "buyer_name": user_map[o.buyer_id].display_name if o.buyer_id in user_map else "unknown",
                "seller_name": user_map[o.seller_id].display_name if o.seller_id in user_map else "unknown",
                "amount": float(o.amount), "currency": o.currency,
                "platform_fee": float(o.platform_fee),
                "source": o.source, "status": o.status,
                "created_at": o.created_at.isoformat(),
            }
            for o in orders
        ],
        "pagination": {"total": total or 0, "offset": offset, "limit": limit},
    }


@router.post("/orders/{order_id}/refund")
async def refund_order(
    order_id: UUID,
    body: RefundRequest,
    admin: User = Depends(require_admin_with_2fa),
    db: AsyncSession = Depends(get_db),
):
    """Issue a full or partial refund for an order (admin only).

    Reference: phase4.design.md §4.4
    """
    result = await db.execute(
        select(Order).where(Order.id == order_id).with_for_update()
    )
    order = result.scalar_one_or_none()
    if not order:
        raise ApiError("NOT_FOUND", "Order not found", http_status=404)

    if order.status not in _REFUNDABLE_STATUSES:
        raise ApiError(
            "CONFLICT",
            f"Only orders with status {_REFUNDABLE_STATUSES} can be refunded "
            f"(current: {order.status})",
            http_status=409,
        )

    if not order.payment_intent_id:
        raise ApiError(
            "CONFLICT",
            "Order has no associated payment intent — cannot issue refund",
            http_status=409,
        )

    refund_amount: Decimal | None = body.amount

    provider = get_payment_provider()
    await provider.refund(
        payment_intent_id=order.payment_intent_id,
        amount=refund_amount,
        reason=body.reason,
    )

    now = datetime.now(timezone.utc)
    order.status = "refunded"
    order.refunded_at = now

    db.add(
        Notification(
            user_id=order.seller_id,
            type="order_refunded",
            title="주문이 환불되었습니다",
            body=(
                f"관리자가 주문을 환불 처리했습니다."
                + (f" 사유: {body.reason}" if body.reason else "")
            ),
            link=f"/orders/{order.id}",
        )
    )
    db.add(
        Notification(
            user_id=order.buyer_id,
            type="order_refunded",
            title="환불이 완료되었습니다",
            body=(
                f"주문에 대한 환불이 완료되었습니다."
                + (f" 사유: {body.reason}" if body.reason else "")
            ),
            link=f"/orders/{order.id}",
        )
    )

    await db.commit()
    await db.refresh(order)
    return {"data": _serialize_order_admin(order)}
