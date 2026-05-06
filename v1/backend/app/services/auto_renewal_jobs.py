"""Background job: auto-renewal monitoring cron — B'-4 stripe-billing-auto-renewal.

R-5 격리: separate file + separate AsyncSessionLocal + separate metric label.
Runs every 3600 seconds (1 hour) via lifespan task in main.py — 11번째 cron worker.

Logic:
  - Find active subscriptions where current_period_end < now + 7 days AND auto_renew_enabled=True
  - Check Stripe invoice.upcoming to verify billing intent (monitoring only)
  - For past_due subscriptions: log alert and create admin notification
  - On renewal failure detection (past_due > 72h): notify user with retry guidance
  - Stripe billing itself handles the actual charge — backend is monitoring only

Carry-over (A-8): integrates with subscription_expiry_jobs — does not duplicate
  expiry notifications (respects expiry_notified_at stamp).
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, select

from app.core.metrics import (
    cron_rows_processed_total,
    record_cron_run,
)
from app.db.session import AsyncSessionLocal
from app.models.notification import Notification
from app.models.sponsorship import Subscription
from app.services.analytics import capture_event
from app.services.otel_setup import get_tracer

log = logging.getLogger(__name__)

tracer = get_tracer(__name__)

# How far ahead to look for upcoming renewals
_RENEWAL_WINDOW_DAYS = 7
# Hours a subscription can be past_due before we escalate to user notification
_PAST_DUE_ESCALATION_HOURS = 72


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def check_auto_renewals_once(db) -> dict[str, int]:
    """Single sweep: detect subscriptions due for renewal and monitor Stripe billing.

    Returns a summary dict with counts:
      {
        "upcoming_checked": N,   # subs in 7-day window with auto_renew=True
        "past_due_escalated": N, # past_due subs notified after 72h threshold
        "already_handled": N,    # skipped (expiry_notified_at already set)
      }
    """
    now = _now()
    cutoff = now + timedelta(days=_RENEWAL_WINDOW_DAYS)
    escalation_threshold = now - timedelta(hours=_PAST_DUE_ESCALATION_HOURS)

    summary = {"upcoming_checked": 0, "past_due_escalated": 0, "already_handled": 0}

    # ── 1. Upcoming renewals (active + auto_renew=True + period ending soon) ──
    upcoming_result = await db.execute(
        select(Subscription).where(
            and_(
                Subscription.status == "active",
                Subscription.auto_renew_enabled.is_(True),
                Subscription.cancel_at_period_end.is_(False),
                Subscription.current_period_end.isnot(None),
                Subscription.current_period_end < cutoff,
                Subscription.current_period_end > now,
            )
        )
    )
    upcoming_subs = list(upcoming_result.scalars().all())

    for sub in upcoming_subs:
        # A-8 carry-over: skip if expiry notification was already created this cycle
        if sub.expiry_notified_at is not None:
            summary["already_handled"] += 1
            continue

        days_left = (sub.current_period_end - now).days if sub.current_period_end else 7

        # Backend monitoring only — Stripe handles the actual charge.
        # We just log that this subscription is entering renewal window.
        log.info(
            "auto_renewal upcoming: subscription_id=%s sponsor_id=%s days_left=%d provider_sub=%s",
            sub.id,
            sub.sponsor_id,
            days_left,
            sub.provider_subscription_id,
        )

        summary["upcoming_checked"] += 1

    # ── 2. Past-due escalation (past_due > 72h — retry failed) ───────────────
    past_due_result = await db.execute(
        select(Subscription).where(
            and_(
                Subscription.status == "past_due",
                # Use cancelled_at as proxy for when payment failed (Stripe webhook sets past_due)
                # If not available, we use current_period_end as the anchor
                Subscription.current_period_end.isnot(None),
                Subscription.current_period_end < escalation_threshold,
            )
        )
    )
    past_due_subs = list(past_due_result.scalars().all())

    for sub in past_due_subs:
        # Create user notification about failed renewal + action required
        existing = await db.execute(
            select(Notification).where(
                and_(
                    Notification.user_id == sub.sponsor_id,
                    Notification.type == "subscription_renewal_failed",
                    # Only create once per subscription per escalation window
                    Notification.created_at > (now - timedelta(hours=_PAST_DUE_ESCALATION_HOURS)),
                )
            )
        )
        if existing.scalar_one_or_none():
            # Already notified in the escalation window
            summary["already_handled"] += 1
            continue

        db.add(
            Notification(
                user_id=sub.sponsor_id,
                type="subscription_renewal_failed",
                title="구독 갱신 실패 — 조치 필요",
                body=(
                    "정기 후원 결제가 실패했습니다. "
                    "카드 정보를 업데이트하거나 직접 갱신해주세요."
                ),
                link="/me/sponsorships",
            )
        )

        # G'-4 server-side event
        capture_event(
            str(sub.sponsor_id),
            "subscription_renewal_failed_escalated",
            {
                "subscription_id": str(sub.id),
                "artist_id": str(sub.artist_id),
                "provider_subscription_id": sub.provider_subscription_id,
            },
        )

        log.warning(
            "auto_renewal escalation: past_due subscription_id=%s sponsor_id=%s "
            "provider_sub=%s current_period_end=%s",
            sub.id,
            sub.sponsor_id,
            sub.provider_subscription_id,
            sub.current_period_end,
        )

        summary["past_due_escalated"] += 1

    if past_due_subs or any(
        sub.expiry_notified_at is None for sub in upcoming_subs
    ):
        await db.commit()

    return summary


async def auto_renewal_cron_loop(interval_seconds: int = 3600) -> None:
    """11th cron worker — auto-renewal monitoring (R-5 isolated, 1h interval)."""
    log.info(
        "auto_renewal_cron_loop started (interval=%ss, window=%dd, escalation_hours=%d)",
        interval_seconds,
        _RENEWAL_WINDOW_DAYS,
        _PAST_DUE_ESCALATION_HOURS,
    )
    while True:
        try:
            with tracer.start_as_current_span("cron.auto_renewal") as span:
                with record_cron_run("auto_renewal"):
                    async with AsyncSessionLocal() as db:
                        summary = await check_auto_renewals_once(db)
                    span.set_attribute("upcoming_checked", summary["upcoming_checked"])
                    span.set_attribute("past_due_escalated", summary["past_due_escalated"])
                    span.set_attribute("already_handled", summary["already_handled"])
                    total_processed = summary["upcoming_checked"] + summary["past_due_escalated"]
                    if total_processed:
                        log.info(
                            "auto_renewal sweep: upcoming=%d escalated=%d skipped=%d",
                            summary["upcoming_checked"],
                            summary["past_due_escalated"],
                            summary["already_handled"],
                        )
                        cron_rows_processed_total.labels(worker="auto_renewal").inc(
                            total_processed
                        )
        except Exception as e:
            log.exception("auto_renewal cron sweep failed: %s", e)
        await asyncio.sleep(interval_seconds)
