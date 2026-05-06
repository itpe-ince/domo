"""Pure Stripe webhook event handler functions (G'-1).

Each handler receives a raw Stripe event dict and an AsyncSession.
They are intentionally side-effect only (no return value) and must be
individually testable without the HTTP layer.

Stripe event shape reference:
  {
    "id": "evt_xxx",
    "type": "payment_intent.succeeded",
    "data": {
      "object": { ... }   # the Stripe resource
    }
  }
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification
from app.models.sponsorship import Sponsorship, Subscription

log = logging.getLogger(__name__)


def _get_object(event: dict) -> dict:
    """Extract the Stripe resource from event.data.object."""
    data = event.get("data", {})
    if isinstance(data, dict):
        obj = data.get("object")
        if isinstance(obj, dict):
            return obj
    return {}


def _log_action(action: str, **kwargs: object) -> None:
    """Structured audit log line for webhook processing."""
    parts = " ".join(f"{k}={v!r}" for k, v in kwargs.items())
    log.info("AUDIT action=%s %s", action, parts)


# ─── payment_intent.succeeded ────────────────────────────────────────────────

async def handle_payment_succeeded(db: AsyncSession, event: dict) -> None:
    """Mark Sponsorship completed; notify both artist and sponsor."""
    obj = _get_object(event)
    intent_id = obj.get("id")
    if not intent_id:
        return

    result = await db.execute(
        select(Sponsorship).where(Sponsorship.payment_intent_id == intent_id)
    )
    sponsorship = result.scalar_one_or_none()
    if not sponsorship:
        return

    if sponsorship.status != "completed":
        sponsorship.status = "completed"
        # Notify sponsor
        db.add(Notification(
            user_id=sponsorship.sponsor_id,
            type="payment_succeeded",
            title="후원 결제 완료",
            body="블루버드 후원 결제가 완료되었습니다.",
            link=f"/artists/{sponsorship.artist_id}",
        ))
        # Notify artist
        db.add(Notification(
            user_id=sponsorship.artist_id,
            type="sponsorship_received",
            title="후원을 받았습니다",
            body="누군가 블루버드 후원을 보냈습니다.",
            link="/me/patronage",
        ))
        _log_action(
            "WEBHOOK_PROCESSED",
            event_type="payment_intent.succeeded",
            event_id=event.get("id"),
            intent_id=intent_id,
            sponsorship_id=str(sponsorship.id),
            result="success",
        )


# ─── payment_intent.payment_failed ───────────────────────────────────────────

async def handle_payment_failed(db: AsyncSession, event: dict) -> None:
    """Mark Sponsorship failed; notify sponsor."""
    obj = _get_object(event)
    intent_id = obj.get("id")
    if not intent_id:
        return

    result = await db.execute(
        select(Sponsorship).where(Sponsorship.payment_intent_id == intent_id)
    )
    sponsorship = result.scalar_one_or_none()
    if not sponsorship:
        return

    if sponsorship.status not in ("completed", "failed"):
        sponsorship.status = "failed"
        db.add(Notification(
            user_id=sponsorship.sponsor_id,
            type="payment_failed",
            title="결제 실패",
            body="블루버드 후원 결제가 실패했습니다. 카드 정보를 확인해주세요.",
            link="/me/settings/payment",
        ))
        _log_action(
            "WEBHOOK_PROCESSED",
            event_type="payment_intent.payment_failed",
            event_id=event.get("id"),
            intent_id=intent_id,
            sponsorship_id=str(sponsorship.id),
            result="success",
        )


# ─── payment_intent.requires_action ──────────────────────────────────────────

async def handle_payment_requires_action(db: AsyncSession, event: dict) -> None:
    """Notify sponsor that 3D Secure / SCA authentication is required."""
    obj = _get_object(event)
    intent_id = obj.get("id")
    if not intent_id:
        return

    result = await db.execute(
        select(Sponsorship).where(Sponsorship.payment_intent_id == intent_id)
    )
    sponsorship = result.scalar_one_or_none()
    if not sponsorship:
        return

    db.add(Notification(
        user_id=sponsorship.sponsor_id,
        type="payment_3ds_required",
        title="3D Secure 인증 필요",
        body="결제를 완료하려면 3D Secure 인증이 필요합니다.",
        link="/me/settings/payment",
    ))
    _log_action(
        "WEBHOOK_PROCESSED",
        event_type="payment_intent.requires_action",
        event_id=event.get("id"),
        intent_id=intent_id,
        result="success",
    )


# ─── invoice.payment_succeeded ────────────────────────────────────────────────

async def handle_invoice_payment_succeeded(db: AsyncSession, event: dict) -> None:
    """Update subscription current_period_end on successful recurring charge.

    B'-4 booster: enhanced audit log with renewal confirmation + period reset.
    """
    obj = _get_object(event)
    sub_id = obj.get("subscription")
    if not sub_id:
        return

    result = await db.execute(
        select(Subscription).where(Subscription.provider_subscription_id == sub_id)
    )
    sub = result.scalar_one_or_none()
    if not sub:
        return

    prev_status = sub.status
    prev_period_end = sub.current_period_end

    # Update period end from invoice lines (best-effort)
    lines = obj.get("lines", {})
    data = lines.get("data", []) if isinstance(lines, dict) else []
    new_period_end: datetime | None = None
    if data:
        period = data[0].get("period", {})
        end_unix = period.get("end")
        if end_unix:
            new_period_end = datetime.fromtimestamp(int(end_unix), tz=timezone.utc)

    if new_period_end:
        sub.current_period_end = new_period_end

    # Reset past_due if subscription was in that state
    was_past_due = sub.status == "past_due"
    if was_past_due:
        sub.status = "active"

    # B'-4: reset expiry notification stamp so cron can fire again next cycle
    sub.expiry_notified_at = None

    invoice_id = obj.get("id", "unknown")
    amount_paid = obj.get("amount_paid", 0)
    currency = obj.get("currency", "").upper()

    db.add(Notification(
        user_id=sub.sponsor_id,
        type="subscription_renewed",
        title="구독이 갱신되었습니다",
        body=(
            f"정기 후원이 성공적으로 갱신되었습니다."
            + (f" 결제 금액: {amount_paid / 100:.0f} {currency}" if amount_paid else "")
        ),
        link="/me/patronage",
    ))
    _log_action(
        "WEBHOOK_PROCESSED",
        event_type="invoice.payment_succeeded",
        event_id=event.get("id"),
        invoice_id=invoice_id,
        subscription_id=sub_id,
        sponsor_id=str(sub.sponsor_id),
        prev_status=prev_status,
        new_status=sub.status,
        prev_period_end=str(prev_period_end) if prev_period_end else None,
        new_period_end=str(new_period_end) if new_period_end else None,
        was_past_due=was_past_due,
        amount_paid=amount_paid,
        currency=currency,
        result="success",
    )


# ─── invoice.payment_failed ───────────────────────────────────────────────────

async def handle_invoice_payment_failed(db: AsyncSession, event: dict) -> None:
    """Mark subscription past_due on failed recurring charge.

    B'-4 booster: retry strategy metadata + user notification + admin alert.
    Stripe will automatically retry based on its dunning configuration.
    Backend records the attempt count for escalation logic.
    """
    obj = _get_object(event)
    sub_id = obj.get("subscription")
    if not sub_id:
        return

    result = await db.execute(
        select(Subscription).where(Subscription.provider_subscription_id == sub_id)
    )
    sub = result.scalar_one_or_none()
    if not sub:
        return

    prev_status = sub.status
    if sub.status == "active":
        sub.status = "past_due"

    # Stripe retry metadata
    attempt_count = obj.get("attempt_count", 1)
    next_payment_attempt = obj.get("next_payment_attempt")
    invoice_id = obj.get("id", "unknown")
    amount_due = obj.get("amount_due", 0)
    currency = obj.get("currency", "").upper()

    # User notification — escalate message based on attempt count
    if attempt_count == 1:
        body = "정기 후원 결제가 실패했습니다. 카드 정보를 업데이트해주세요."
    elif attempt_count == 2:
        body = "두 번째 결제 시도도 실패했습니다. 빠른 시일 내에 결제 수단을 업데이트해주세요."
    else:
        body = (
            f"결제가 {attempt_count}회 실패했습니다. "
            "지금 바로 카드를 업데이트하지 않으면 구독이 취소될 수 있습니다."
        )

    db.add(Notification(
        user_id=sub.sponsor_id,
        type="subscription_payment_failed",
        title="구독 결제 실패",
        body=body,
        link="/me/settings/payment",
    ))

    # Admin alert: log structured warning for monitoring/alerting pickup
    log.warning(
        "STRIPE_RENEWAL_FAILED subscription_id=%s sponsor_id=%s invoice_id=%s "
        "attempt_count=%s amount_due=%s %s prev_status=%s next_retry=%s",
        sub_id,
        sub.sponsor_id,
        invoice_id,
        attempt_count,
        amount_due,
        currency,
        prev_status,
        next_payment_attempt,
    )

    _log_action(
        "WEBHOOK_PROCESSED",
        event_type="invoice.payment_failed",
        event_id=event.get("id"),
        invoice_id=invoice_id,
        subscription_id=sub_id,
        sponsor_id=str(sub.sponsor_id),
        attempt_count=attempt_count,
        next_payment_attempt=next_payment_attempt,
        prev_status=prev_status,
        new_status=sub.status,
        amount_due=amount_due,
        currency=currency,
        result="success",
    )


# ─── customer.subscription.created ───────────────────────────────────────────

async def handle_subscription_created(db: AsyncSession, event: dict) -> None:
    """Log subscription creation (our DB record is already created at API time)."""
    obj = _get_object(event)
    sub_id = obj.get("id")
    _log_action(
        "WEBHOOK_PROCESSED",
        event_type="customer.subscription.created",
        event_id=event.get("id"),
        stripe_subscription_id=sub_id,
        result="success",
    )


# ─── customer.subscription.updated ───────────────────────────────────────────

async def handle_subscription_updated(db: AsyncSession, event: dict) -> None:
    """Sync subscription status changes (e.g. cancel_at_period_end)."""
    obj = _get_object(event)
    sub_id = obj.get("id")
    if not sub_id:
        return

    result = await db.execute(
        select(Subscription).where(Subscription.provider_subscription_id == sub_id)
    )
    sub = result.scalar_one_or_none()
    if not sub:
        return

    cancel_at_period_end = obj.get("cancel_at_period_end")
    if cancel_at_period_end is not None:
        sub.cancel_at_period_end = bool(cancel_at_period_end)

    stripe_status = obj.get("status")
    if stripe_status == "past_due" and sub.status == "active":
        sub.status = "past_due"
    elif stripe_status == "active" and sub.status == "past_due":
        sub.status = "active"

    _log_action(
        "WEBHOOK_PROCESSED",
        event_type="customer.subscription.updated",
        event_id=event.get("id"),
        subscription_id=sub_id,
        result="success",
    )


# ─── customer.subscription.deleted ───────────────────────────────────────────

async def handle_subscription_deleted(db: AsyncSession, event: dict) -> None:
    """Mark subscription cancelled and notify sponsor."""
    obj = _get_object(event)
    sub_id = obj.get("id")
    if not sub_id:
        return

    result = await db.execute(
        select(Subscription).where(Subscription.provider_subscription_id == sub_id)
    )
    sub = result.scalar_one_or_none()
    if not sub:
        return

    if sub.status != "cancelled":
        sub.status = "cancelled"
        sub.cancelled_at = datetime.now(timezone.utc)
        db.add(Notification(
            user_id=sub.sponsor_id,
            type="subscription_cancelled",
            title="구독이 취소되었습니다",
            body="정기 후원이 취소되었습니다.",
            link="/me/patronage",
        ))
        _log_action(
            "WEBHOOK_PROCESSED",
            event_type="customer.subscription.deleted",
            event_id=event.get("id"),
            subscription_id=sub_id,
            result="success",
        )
        # G'-2 booster placeholder: Phase 8+ retention loop automation.
        # After subscription.deleted, check cancellation_reason and last
        # winback coupon issuance timestamp. If no winback coupon was issued
        # in the last 24h AND reason is 'too_expensive', auto-issue via
        # background task. Deferred to Phase 8+ (requires async task queue).
        # TODO(Phase 8+): auto-winback on subscription.deleted


# ─── charge.dispute.created ───────────────────────────────────────────────────

async def handle_dispute_created(db: AsyncSession, event: dict) -> None:
    """Log dispute and notify admins via standard notification channel."""
    obj = _get_object(event)
    dispute_id = obj.get("id", "unknown")
    charge_id = obj.get("charge", "unknown")
    amount = obj.get("amount", 0)
    currency = obj.get("currency", "usd").upper()

    # In lieu of a dedicated admin notification table, write a structured log.
    # Admin dashboard polling / alerting picks this up from logs.
    _log_action(
        "WEBHOOK_PROCESSED",
        event_type="charge.dispute.created",
        event_id=event.get("id"),
        dispute_id=dispute_id,
        charge_id=charge_id,
        amount=amount,
        currency=currency,
        result="success",
    )
    log.warning(
        "STRIPE_DISPUTE dispute_id=%s charge_id=%s amount=%s %s",
        dispute_id,
        charge_id,
        amount,
        currency,
    )


# ─── Dispatch table ───────────────────────────────────────────────────────────

HANDLERS: dict[str, Any] = {
    "payment_intent.succeeded": handle_payment_succeeded,
    "payment_intent.payment_failed": handle_payment_failed,
    "payment_intent.requires_action": handle_payment_requires_action,
    "invoice.payment_succeeded": handle_invoice_payment_succeeded,
    "invoice.payment_failed": handle_invoice_payment_failed,
    "customer.subscription.created": handle_subscription_created,
    "customer.subscription.updated": handle_subscription_updated,
    "customer.subscription.deleted": handle_subscription_deleted,
    "charge.dispute.created": handle_dispute_created,
}
