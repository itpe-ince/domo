"""Stripe webhook handler (G'-1).

POST /v1/webhooks/stripe — primary endpoint for all Stripe webhook events.
POST /v1/webhooks/payments — legacy alias kept for backward compatibility.

Security:
- No Bearer auth (Stripe calls this, not the user).
- Signature verified via stripe.Webhook.construct_event using
  STRIPE_WEBHOOK_SECRET (whsec_...).
- Raw request body must be read before any parsing.

Idempotency:
- WebhookEvent table stores processed event IDs.
- Duplicate event_id → 200 immediately (no reprocessing).

Error contract (Stripe retry behavior):
- 400 → Stripe does NOT retry (permanent client error).
- 500 → Stripe retries with exponential backoff.
- 200 → Stripe marks event delivered.
"""
from __future__ import annotations

import logging
import time

from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import ApiError
from app.core.metrics import (
    webhook_duration_seconds,
    webhook_idempotent_skip_total,
    webhook_received_total,
)
from app.db.session import get_db
from app.models.webhook_event import WebhookEvent
from app.services.payments.webhook_handlers import HANDLERS

log = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


# ─── Signature verification ───────────────────────────────────────────────────

def _verify_stripe_signature(payload: bytes, sig_header: str | None) -> dict:
    """Verify Stripe-Signature and return the parsed event dict.

    Raises ApiError 400 on missing/invalid signature.
    Falls back to JSON-only parsing when PAYMENT_PROVIDER=mock_stripe
    so that integration tests don't need a real webhook secret.
    """
    settings = get_settings()

    if settings.payment_provider == "stripe":
        if not sig_header:
            raise ApiError(
                "MISSING_SIGNATURE",
                "Stripe-Signature header is required",
                http_status=400,
            )
        try:
            import stripe  # noqa: PLC0415  lazy import
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.stripe_webhook_secret
            )
            return dict(event)
        except Exception as exc:
            raise ApiError(
                "INVALID_SIGNATURE",
                f"Stripe signature verification failed: {exc}",
                http_status=400,
            ) from exc
    else:
        # Mock / dev mode — parse raw JSON without signature check
        import json
        try:
            return json.loads(payload)
        except Exception as exc:
            raise ApiError(
                "INVALID_PAYLOAD",
                f"Could not parse webhook payload: {exc}",
                http_status=400,
            ) from exc


# ─── Core processing logic ────────────────────────────────────────────────────

async def _process_event(db: AsyncSession, event: dict) -> dict:
    """Idempotency guard + dispatch to event handler.

    Returns a dict describing what happened.
    """
    event_id: str = event.get("id") or f"mock_{event.get('type', 'unknown')}_{time.time()}"
    event_type: str = event.get("type") or "unknown"
    start = time.perf_counter()

    # Idempotency: attempt to insert — conflict means already processed.
    try:
        db.add(WebhookEvent(
            id=event_id[:100],
            type=event_type[:100],
            payload=event,
        ))
        await db.flush()
    except IntegrityError:
        await db.rollback()
        webhook_idempotent_skip_total.labels(event_type=event_type).inc()
        log.debug("webhook idempotent skip event_id=%s type=%s", event_id, event_type)
        return {"received": True, "duplicate": True, "type": event_type}

    # Dispatch to handler
    handler = HANDLERS.get(event_type)
    if handler:
        try:
            await handler(db, event)
        except Exception as exc:  # noqa: BLE001
            await db.rollback()
            elapsed = time.perf_counter() - start
            webhook_received_total.labels(event_type=event_type, result="error").inc()
            webhook_duration_seconds.labels(event_type=event_type).observe(elapsed)
            log.exception(
                "webhook handler error event_id=%s type=%s: %s",
                event_id,
                event_type,
                exc,
            )
            # Re-raise so Stripe gets a 500 and retries
            raise
    else:
        log.debug("webhook unhandled event_type=%s event_id=%s", event_type, event_id)

    await db.commit()
    elapsed = time.perf_counter() - start
    webhook_received_total.labels(event_type=event_type, result="success").inc()
    webhook_duration_seconds.labels(event_type=event_type).observe(elapsed)
    log.info(
        "AUDIT action=WEBHOOK_PROCESSED event_type=%r event_id=%r result='success'",
        event_type,
        event_id,
    )

    # G'-4 placeholder: after G'-1 merges, extract user_id from handler result and fire:
    # from app.services.analytics import capture_event
    # capture_event(user_id, "webhook_processed_server", {"event_type": event_type, "result": "success"})

    return {"received": True, "type": event_type}


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/stripe")
async def stripe_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    stripe_signature: str | None = Header(default=None, alias="stripe-signature"),
):
    """Primary Stripe webhook endpoint.

    Stripe delivers events here. No user auth — signature-verified only.
    Returns 200 for all valid events (including already-processed duplicates).
    Returns 400 for signature/parsing errors (Stripe will NOT retry).
    Returns 500 for DB/handler errors (Stripe WILL retry).
    """
    payload = await request.body()

    event = _verify_stripe_signature(payload, stripe_signature)
    result = await _process_event(db, event)
    return {"data": result}


@router.post("/payments")
async def payments_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    stripe_signature: str | None = Header(default=None, alias="stripe-signature"),
):
    """Legacy alias for /webhooks/payments → delegates to /webhooks/stripe logic.

    Kept for backward compatibility with existing Stripe webhook configuration
    from Phase 4. New deployments should use /v1/webhooks/stripe.
    """
    payload = await request.body()
    event = _verify_stripe_signature(payload, stripe_signature)
    result = await _process_event(db, event)
    return {"data": result}
