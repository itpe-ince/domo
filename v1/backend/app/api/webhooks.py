"""Payment webhook handler (Phase 4 M1 — Stripe ready).

Handles both mock and real Stripe events via the PaymentProvider
abstraction. Uses the webhook_events table for idempotency so that
Stripe retries don't double-process an event.

Mock provider payload shape:
  { "type": "<event_type>", "data": { ... } }

Real Stripe payload shape (after verify_webhook_signature → dict):
  { "id": "evt_...", "type": "...", "data": { "object": { ... } } }

We handle both shapes by checking the presence of the "id" and
"data.object" fields.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ApiError
from app.db.session import get_db
from app.models.auction import Order
from app.models.notification import Notification
from app.models.sponsorship import Sponsorship, Subscription
from app.models.webhook_event import WebhookEvent
from app.services.payments import get_payment_provider

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


def _extract_object(event: dict, key: str) -> Any:
    """Extract a field from either mock or Stripe payload shapes."""
    data = event.get("data", {})
    # Stripe shape: data.object.<key>
    obj = data.get("object") if isinstance(data, dict) else None
    if obj and key in obj:
        return obj[key]
    # Mock shape: data.<key>
    return data.get(key) if isinstance(data, dict) else None


async def _handle_payment_succeeded(db: AsyncSession, event: dict) -> None:
    intent_id = _extract_object(event, "intent_id") or _extract_object(event, "id")
    if not intent_id:
        return

    # Sponsorship
    spo_result = await db.execute(
        select(Sponsorship).where(Sponsorship.payment_intent_id == intent_id)
    )
    sponsorship = spo_result.scalar_one_or_none()
    if sponsorship and sponsorship.status != "completed":
        sponsorship.status = "completed"

    # Order (auction settlement or buy-now)
    order_result = await db.execute(
        select(Order).where(Order.payment_intent_id == intent_id)
    )
    order = order_result.scalar_one_or_none()
    if order and order.status == "pending_payment":
        order.status = "paid"
        order.paid_at = datetime.now(timezone.utc)


async def _handle_payment_failed(db: AsyncSession, event: dict) -> None:
    intent_id = _extract_object(event, "intent_id") or _extract_object(event, "id")
    if not intent_id:
        return
    spo_result = await db.execute(
        select(Sponsorship).where(Sponsorship.payment_intent_id == intent_id)
    )
    sponsorship = spo_result.scalar_one_or_none()
    if sponsorship:
        sponsorship.status = "failed"
        db.add(
            Notification(
                user_id=sponsorship.sponsor_id,
                type="payment_failed",
                title="결제 실패",
                body="블루버드 후원 결제가 실패했습니다. 카드 정보를 확인해주세요.",
            )
        )


async def _handle_subscription_deleted(db: AsyncSession, event: dict) -> None:
    sub_id = _extract_object(event, "subscription_id") or _extract_object(event, "id")
    if not sub_id:
        return
    result = await db.execute(
        select(Subscription).where(Subscription.provider_subscription_id == sub_id)
    )
    sub = result.scalar_one_or_none()
    if sub and sub.status == "active":
        sub.status = "cancelled"
        sub.cancelled_at = datetime.now(timezone.utc)


async def _handle_subscription_updated(db: AsyncSession, event: dict) -> None:
    sub_id = _extract_object(event, "id") or _extract_object(event, "subscription_id")
    if not sub_id:
        return
    result = await db.execute(
        select(Subscription).where(Subscription.provider_subscription_id == sub_id)
    )
    sub = result.scalar_one_or_none()
    if not sub:
        return
    cancel_at_period_end = _extract_object(event, "cancel_at_period_end")
    if cancel_at_period_end is not None:
        sub.cancel_at_period_end = bool(cancel_at_period_end)


async def _handle_invoice_payment_failed(db: AsyncSession, event: dict) -> None:
    sub_id = _extract_object(event, "subscription")
    if not sub_id:
        return
    result = await db.execute(
        select(Subscription).where(Subscription.provider_subscription_id == sub_id)
    )
    sub = result.scalar_one_or_none()
    if sub:
        sub.status = "past_due"
        db.add(
            Notification(
                user_id=sub.sponsor_id,
                type="subscription_past_due",
                title="정기 후원 결제 실패",
                body="정기 후원 결제가 실패했습니다. 카드 정보를 업데이트해주세요.",
            )
        )


async def _handle_charge_refunded(db: AsyncSession, event: dict) -> None:
    intent_id = _extract_object(event, "payment_intent") or _extract_object(event, "intent_id")
    if not intent_id:
        return
    order_result = await db.execute(
        select(Order).where(Order.payment_intent_id == intent_id)
    )
    order = order_result.scalar_one_or_none()
    if order and order.status == "paid":
        order.status = "refunded"
        db.add(
            Notification(
                user_id=order.buyer_id,
                type="order_refunded",
                title="환불 완료",
                body=f"주문 ₩{int(order.amount):,}이 환불되었습니다.",
                link=f"/orders",
            )
        )


# Event type → handler
HANDLERS = {
    "payment_intent.succeeded": _handle_payment_succeeded,
    "payment_intent.payment_failed": _handle_payment_failed,
    "customer.subscription.deleted": _handle_subscription_deleted,
    "customer.subscription.updated": _handle_subscription_updated,
    "invoice.payment_failed": _handle_invoice_payment_failed,
    "charge.refunded": _handle_charge_refunded,
}


@router.post("/payments")
async def payments_webhook(
    request: Request,
    stripe_signature: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
):
    payload = await request.body()
    provider = get_payment_provider()

    try:
        event = await provider.verify_webhook_signature(payload, stripe_signature)
    except ValueError as e:
        raise ApiError("INVALID_REQUEST", str(e), http_status=400) from e

    event_type = event.get("type")
    event_id = event.get("id") or f"mock_{event_type}_{datetime.now(timezone.utc).timestamp()}"

    # Idempotency: reject duplicate event IDs
    try:
        db.add(
            WebhookEvent(
                id=event_id[:100],
                type=event_type[:100] if event_type else "unknown",
                payload=event,
            )
        )
        await db.flush()
    except IntegrityError:
        await db.rollback()
        return {"data": {"received": True, "duplicate": True, "type": event_type}}

    handler = HANDLERS.get(event_type)
    if handler:
        await handler(db, event)

    await db.commit()
    return {"data": {"received": True, "type": event_type}}
