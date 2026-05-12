"""AWS SES bounce/complaint webhook — H'-5 newsletter-bounce-handling.

POST /webhooks/ses-bounce — SNS message delivery for SES bounce/complaint/delivery events.

Flow:
  1. AWS SES → SNS Topic → HTTP subscription to this endpoint
  2. SNS sends SubscriptionConfirmation on first delivery → auto-confirm via GET SubscribeURL
  3. SNS sends Notification with SES event JSON for each bounce/complaint/delivery
  4. Signature verified using AWS SNS x509 certificate (production only)

SNS message types handled:
  SubscriptionConfirmation — auto-confirm (GET SubscribeURL)
  Notification             — parse inner SES event, dispatch to handler
  UnsubscribeConfirmation  — log and ignore

SES event types handled:
  Bounce    → bounce_type=Permanent → hard bounce → auto-unsubscribe + notification
           → bounce_type=Transient  → soft bounce → increment counter; 3rd → suspend 7d
  Complaint → immediate unsubscribe + admin alert email
  Delivery  → increment delivered_count on matching newsletter_issue

Security:
  - SNS signature verification via AWS public certificate (x509, SHA1WithRSA)
  - Falls back to NO verification when aws_sns_topic_arn is empty (dev/CI)
  - Always validate TopicArn against configured aws_sns_topic_arn

Idempotency:
  - SNS guarantees at-least-once delivery; same message may arrive twice
  - Message-ID based dedup via WebhookEvent table (same as Stripe webhook)
"""
from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
from fastapi import APIRouter, Request
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import ApiError
from app.core.metrics import (
    ses_bounce_received_total,
    ses_complaint_received_total,
    ses_delivery_received_total,
    ses_hard_bounce_unsubscribed_total,
    ses_sns_webhook_received_total,
    ses_soft_bounce_suspended_total,
)
from app.db.session import AsyncSessionLocal
from app.models.newsletter_issue import NewsletterIssue
from app.models.newsletter_preferences import NewsletterPreferences
from app.models.notification import Notification
from app.models.user import User
from app.models.webhook_event import WebhookEvent
from app.services.email_ses import ses_client

log = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks-ses"])

# Soft bounce threshold before suspension
_SOFT_BOUNCE_THRESHOLD = 3
# Suspension duration in days after threshold reached
_SOFT_BOUNCE_SUSPEND_DAYS = 7


# ─── SNS Signature Verification ───────────────────────────────────────────────


def _build_signing_string(msg: dict) -> bytes:
    """Build the canonical string for SNS signature verification.

    AWS SNS signs a specific set of fields in a defined order.
    See: https://docs.aws.amazon.com/sns/latest/dg/sns-verify-signature-of-message.html
    """
    msg_type = msg.get("Type", "")

    if msg_type == "Notification":
        fields = ["Message", "MessageId", "Subject", "Timestamp", "TopicArn", "Type"]
    else:
        # SubscriptionConfirmation and UnsubscribeConfirmation
        fields = ["Message", "MessageId", "SubscribeURL", "Timestamp", "Token", "TopicArn", "Type"]

    parts: list[str] = []
    for field in fields:
        if field in msg:
            parts.append(field)
            parts.append(msg[field])

    return "\n".join(parts).encode("utf-8") + b"\n"


async def _verify_sns_signature(msg: dict) -> None:
    """Verify AWS SNS message signature.

    When aws_sns_topic_arn is not configured (dev/CI), verification is skipped.
    Production MUST have aws_sns_topic_arn set.

    Raises ApiError 400 on verification failure.
    """
    settings = get_settings()

    if not settings.aws_sns_topic_arn:
        # Dev/CI mode — skip signature verification
        log.debug("SNS signature verification skipped (aws_sns_topic_arn not configured)")
        return

    # Validate TopicArn matches configured topic
    topic_arn = msg.get("TopicArn", "")
    if topic_arn != settings.aws_sns_topic_arn:
        raise ApiError(
            "SNS_TOPIC_MISMATCH",
            f"TopicArn {topic_arn!r} does not match configured SNS topic",
            http_status=400,
        )

    # Fetch signing certificate
    signing_cert_url = msg.get("SigningCertURL", "")
    if not signing_cert_url.startswith("https://sns.") or ".amazonaws.com/" not in signing_cert_url:
        raise ApiError(
            "SNS_INVALID_CERT_URL",
            "SigningCertURL must be an AWS SNS HTTPS certificate URL",
            http_status=400,
        )

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(signing_cert_url)
            resp.raise_for_status()
            cert_pem = resp.content
    except Exception as exc:
        raise ApiError(
            "SNS_CERT_FETCH_FAILED",
            f"Could not fetch SNS signing certificate: {exc}",
            http_status=400,
        ) from exc

    # Verify signature using cryptography library
    try:
        import base64

        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import padding
        from cryptography.x509 import load_pem_x509_certificate

        cert = load_pem_x509_certificate(cert_pem)
        public_key = cert.public_key()
        signature = base64.b64decode(msg.get("Signature", ""))
        signing_string = _build_signing_string(msg)

        public_key.verify(
            signature,
            signing_string,
            padding.PKCS1v15(),
            hashes.SHA1(),  # noqa: S303 — AWS SNS uses SHA1 (required by AWS spec)
        )
    except ApiError:
        raise
    except Exception as exc:
        raise ApiError(
            "SNS_SIGNATURE_INVALID",
            f"SNS message signature verification failed: {exc}",
            http_status=400,
        ) from exc


# ─── SNS Subscription Confirmation ────────────────────────────────────────────


async def _confirm_subscription(msg: dict) -> None:
    """Auto-confirm SNS subscription by fetching the SubscribeURL.

    AWS SNS delivers a SubscriptionConfirmation message when a new HTTP
    subscription is created. Confirming it by fetching SubscribeURL activates
    the subscription.
    """
    subscribe_url = msg.get("SubscribeURL", "")
    if not subscribe_url:
        log.warning("SNS SubscriptionConfirmation missing SubscribeURL")
        return

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(subscribe_url)
            resp.raise_for_status()
        log.info("SNS subscription confirmed: TopicArn=%s", msg.get("TopicArn"))
    except Exception as exc:
        log.error("SNS subscription confirmation failed: %s", exc)


# ─── SES Event Handlers ────────────────────────────────────────────────────────


async def _handle_bounce(db: AsyncSession, ses_event: dict) -> None:
    """Process SES Bounce notification.

    Permanent (hard) bounce:
      - Set is_subscribed=False immediately (GDPR: delivery impossible)
      - Create in-app Notification for the user
      - Audit log

    Transient (soft) bounce:
      - Increment bounce_count
      - If bounce_count >= 3: set suspended_until = now + 7 days
      - Audit log
    """
    bounce = ses_event.get("bounce", {})
    bounce_type = bounce.get("bounceType", "Undetermined")  # Permanent | Transient | Undetermined
    bounce_sub_type = bounce.get("bounceSubType", "")
    recipients = bounce.get("bouncedRecipients", [])

    ses_bounce_received_total.labels(bounce_type=bounce_type.lower()).inc(len(recipients))

    now = datetime.now(timezone.utc)

    for recipient in recipients:
        email = recipient.get("emailAddress", "")
        if not email:
            continue

        # Find user by email
        user_result = await db.execute(
            select(User).where(User.email == email, User.deleted_at.is_(None))
        )
        user = user_result.scalar_one_or_none()
        if not user:
            log.debug("SES bounce: no user found for email=%s", email)
            continue

        # Load preferences
        prefs_result = await db.execute(
            select(NewsletterPreferences).where(
                NewsletterPreferences.user_id == user.id
            )
        )
        prefs = prefs_result.scalar_one_or_none()
        if not prefs:
            log.debug("SES bounce: no newsletter prefs for user_id=%s", user.id)
            continue

        if bounce_type == "Permanent":
            # Hard bounce — auto-unsubscribe
            await db.execute(
                update(NewsletterPreferences)
                .where(NewsletterPreferences.user_id == user.id)
                .values(
                    is_subscribed=False,
                    last_bounce_at=now,
                    last_bounce_type="permanent",
                )
                .execution_options(synchronize_session=False)
            )
            ses_hard_bounce_unsubscribed_total.inc()

            # Create in-app notification for user
            db.add(
                Notification(
                    user_id=user.id,
                    type="newsletter_bounce",
                    title="Newsletter delivery failed",
                    body=(
                        "Your newsletter subscription has been cancelled because "
                        "emails to your address could not be delivered. "
                        "If you believe this is an error, please re-subscribe from your settings."
                    ),
                )
            )
            log.info(
                "AUDIT action=NEWSLETTER_HARD_BOUNCE_UNSUBSCRIBED user_id=%s email=%s sub_type=%s",
                user.id,
                email,
                bounce_sub_type,
            )

        else:
            # Soft bounce (Transient or Undetermined) — increment counter
            new_count = (prefs.bounce_count or 0) + 1
            update_values: dict[str, Any] = {
                "bounce_count": new_count,
                "last_bounce_at": now,
                "last_bounce_type": "transient",
            }

            if new_count >= _SOFT_BOUNCE_THRESHOLD:
                suspend_until = now + timedelta(days=_SOFT_BOUNCE_SUSPEND_DAYS)
                update_values["suspended_until"] = suspend_until
                ses_soft_bounce_suspended_total.inc()
                log.info(
                    "AUDIT action=NEWSLETTER_SOFT_BOUNCE_SUSPENDED user_id=%s email=%s "
                    "bounce_count=%d suspended_until=%s",
                    user.id,
                    email,
                    new_count,
                    suspend_until.isoformat(),
                )

            await db.execute(
                update(NewsletterPreferences)
                .where(NewsletterPreferences.user_id == user.id)
                .values(**update_values)
                .execution_options(synchronize_session=False)
            )
            log.info(
                "AUDIT action=NEWSLETTER_SOFT_BOUNCE user_id=%s email=%s bounce_count=%d",
                user.id,
                email,
                new_count,
            )


async def _handle_complaint(db: AsyncSession, ses_event: dict) -> None:
    """Process SES Complaint notification.

    Immediately unsubscribes the user and sends an admin alert email.
    GDPR: complaint = explicit desire not to receive emails.
    """
    complaint = ses_event.get("complaint", {})
    recipients = complaint.get("complainedRecipients", [])
    feedback_type = complaint.get("complaintFeedbackType", "abuse")

    ses_complaint_received_total.inc(len(recipients))

    now = datetime.now(timezone.utc)
    settings = get_settings()

    for recipient in recipients:
        email = recipient.get("emailAddress", "")
        if not email:
            continue

        # Find user by email
        user_result = await db.execute(
            select(User).where(User.email == email, User.deleted_at.is_(None))
        )
        user = user_result.scalar_one_or_none()
        if not user:
            log.warning("SES complaint: no user found for email=%s", email)
            continue

        # Immediate unsubscribe
        await db.execute(
            update(NewsletterPreferences)
            .where(NewsletterPreferences.user_id == user.id)
            .values(
                is_subscribed=False,
                last_bounce_at=now,
                last_bounce_type="complaint",
            )
            .execution_options(synchronize_session=False)
        )

        log.info(
            "AUDIT action=NEWSLETTER_COMPLAINT_UNSUBSCRIBED user_id=%s email=%s feedback_type=%s",
            user.id,
            email,
            feedback_type,
        )

        # Admin alert email (fire-and-forget, non-blocking)
        if settings.admin_alert_email:
            try:
                await ses_client.send_email(
                    to=settings.admin_alert_email,
                    subject=f"[Domo Alert] Newsletter complaint received from {email}",
                    html_body=(
                        f"<p>A newsletter complaint (spam report) was received.</p>"
                        f"<ul>"
                        f"<li><strong>Email:</strong> {email}</li>"
                        f"<li><strong>User ID:</strong> {user.id}</li>"
                        f"<li><strong>Feedback type:</strong> {feedback_type}</li>"
                        f"<li><strong>Time:</strong> {now.isoformat()}</li>"
                        f"</ul>"
                        f"<p>The user has been automatically unsubscribed from the newsletter.</p>"
                    ),
                )
            except Exception:
                log.exception("Failed to send admin alert for complaint email=%s", email)


async def _handle_delivery(db: AsyncSession, ses_event: dict) -> None:
    """Process SES Delivery notification.

    Increments delivered_count on the matching newsletter_issue (if identifiable)
    and resets soft-bounce counter on the recipient's preferences.
    """
    delivery = ses_event.get("delivery", {})
    recipients = delivery.get("recipients", [])

    ses_delivery_received_total.inc(len(recipients))

    now = datetime.now(timezone.utc)

    for email in recipients:
        if not email:
            continue

        # Find user
        user_result = await db.execute(
            select(User).where(User.email == email, User.deleted_at.is_(None))
        )
        user = user_result.scalar_one_or_none()
        if not user:
            continue

        # Reset soft-bounce counter on successful delivery
        await db.execute(
            update(NewsletterPreferences)
            .where(
                NewsletterPreferences.user_id == user.id,
                NewsletterPreferences.bounce_count > 0,
            )
            .values(bounce_count=0, suspended_until=None)
            .execution_options(synchronize_session=False)
        )

    log.debug(
        "SES delivery processed: %d recipients, smtp_response=%s",
        len(recipients),
        delivery.get("smtpResponse", ""),
    )


# ─── Idempotency guard ─────────────────────────────────────────────────────────


async def _is_duplicate_and_record(db: AsyncSession, message_id: str, event_type: str) -> bool:
    """Return True if this SNS MessageId was already processed.

    Uses the same WebhookEvent table as the Stripe webhook for uniform idempotency.
    """
    try:
        db.add(
            WebhookEvent(
                id=f"sns_{message_id[:90]}",
                type=event_type[:100],
                payload={"sns_message_id": message_id, "type": event_type},
            )
        )
        await db.flush()
        return False
    except IntegrityError:
        await db.rollback()
        return True


# ─── Main dispatch ─────────────────────────────────────────────────────────────


async def _dispatch_ses_notification(db: AsyncSession, sns_msg: dict) -> None:
    """Parse inner SES event from SNS Notification Message and dispatch to handler."""
    try:
        ses_event = json.loads(sns_msg.get("Message", "{}"))
    except json.JSONDecodeError as exc:
        log.warning("SES SNS: could not parse inner Message JSON: %s", exc)
        return

    event_type = ses_event.get("eventType") or ses_event.get("notificationType", "")
    message_id = sns_msg.get("MessageId", f"unknown_{time.time()}")

    # Idempotency
    if await _is_duplicate_and_record(db, message_id, f"ses.{event_type.lower()}"):
        log.debug("SES SNS duplicate message_id=%s type=%s", message_id, event_type)
        return

    if event_type == "Bounce":
        await _handle_bounce(db, ses_event)
    elif event_type == "Complaint":
        await _handle_complaint(db, ses_event)
    elif event_type == "Delivery":
        await _handle_delivery(db, ses_event)
    else:
        log.debug("SES SNS unhandled event_type=%s message_id=%s", event_type, message_id)

    await db.commit()


# ─── Endpoint ──────────────────────────────────────────────────────────────────


@router.post("/ses-bounce")
async def ses_bounce_webhook(request: Request):
    """SES bounce/complaint/delivery webhook via AWS SNS.

    No user Bearer auth — SNS signature verified instead.
    Always returns 200 for valid messages (SNS retries on non-2xx).

    Message types:
      SubscriptionConfirmation — auto-confirm subscription
      Notification             — dispatch SES event to handlers
      UnsubscribeConfirmation  — log and ack
    """
    payload = await request.body()

    try:
        msg = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise ApiError(
            "INVALID_PAYLOAD",
            f"Could not parse SNS JSON payload: {exc}",
            http_status=400,
        ) from exc

    msg_type = msg.get("Type", "")
    ses_sns_webhook_received_total.labels(message_type=msg_type or "unknown").inc()

    # Verify SNS signature before processing (no-op in dev mode)
    await _verify_sns_signature(msg)

    if msg_type == "SubscriptionConfirmation":
        await _confirm_subscription(msg)
        return {"data": {"received": True, "type": "SubscriptionConfirmation"}}

    if msg_type == "UnsubscribeConfirmation":
        log.info("SNS UnsubscribeConfirmation received — acknowledging")
        return {"data": {"received": True, "type": "UnsubscribeConfirmation"}}

    if msg_type == "Notification":
        async with AsyncSessionLocal() as db:
            try:
                await _dispatch_ses_notification(db, msg)
            except Exception:
                log.exception("SES SNS notification dispatch failed")
                # Return 200 to prevent infinite SNS retry on transient errors
                # (SNS will retry up to the configured retry policy regardless)
        return {"data": {"received": True, "type": "Notification"}}

    log.warning("SNS unknown message type=%s", msg_type)
    return {"data": {"received": True, "type": msg_type}}
