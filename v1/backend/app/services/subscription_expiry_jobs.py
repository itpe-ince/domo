"""Background job: subscription expiry notification cron — A-8 retention-loop-enhancement.

R-5 격리: separate file + separate AsyncSessionLocal + separate metric label.
Runs every 3600 seconds (1 hour) via lifespan task in main.py.

Logic:
  - Find active subscriptions where current_period_end < now + 7 days
  - Skip rows where expiry_notified_at IS NOT NULL (already notified this cycle)
  - Create Notification(type='subscription_expiring') for each eligible user
  - Stamp expiry_notified_at = now so the row is skipped on the next sweep
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, select

from app.core.metrics import (
    cron_rows_processed_total,
    record_cron_run,
    subscription_expiry_notif_total,
    subscription_expiring_count,
)
from app.db.session import AsyncSessionLocal
from app.models.notification import Notification
from app.models.sponsorship import Subscription
from app.services.analytics import capture_event
from app.services.otel_setup import get_tracer
from app.services.push_notifier import push_notifier

log = logging.getLogger(__name__)

tracer = get_tracer(__name__)

# Window ahead of period-end to trigger a notification
_NOTIFY_WINDOW_DAYS = 7


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def notify_expiring_subscriptions_once(db) -> int:
    """Single sweep: detect expiring subscriptions and create in-app notifications.

    Returns the number of notifications created.
    """
    now = _now()
    cutoff = now + timedelta(days=_NOTIFY_WINDOW_DAYS)

    # Snapshot metric: how many active subs are expiring in next 7 days
    count_result = await db.execute(
        select(Subscription).where(
            and_(
                Subscription.status == "active",
                Subscription.current_period_end.isnot(None),
                Subscription.current_period_end < cutoff,
            )
        )
    )
    expiring_subs_all = list(count_result.scalars().all())
    subscription_expiring_count.labels(window_days=str(_NOTIFY_WINDOW_DAYS)).inc(
        len(expiring_subs_all)
    )

    # Candidates: not yet notified (expiry_notified_at IS NULL)
    candidates = [s for s in expiring_subs_all if s.expiry_notified_at is None]

    if not candidates:
        return 0

    notifications_created = 0
    for sub in candidates:
        # Calculate days remaining for the body message
        days_left = (sub.current_period_end - now).days if sub.current_period_end else 7

        notification = Notification(
            id=uuid.uuid4(),
            user_id=sub.sponsor_id,
            type="subscription_expiring",
            title=None,
            body=(
                f"구독이 {days_left}일 후 만료됩니다 — "
                "작가 응원을 이어가시려면 갱신해주세요"
            ),
            link="/me/sponsorships",
            is_read=False,
        )
        db.add(notification)

        # Stamp so we do not re-notify this row until the next billing cycle
        sub.expiry_notified_at = now

        # G'-4: server-side expiry warning event per user
        capture_event(
            str(sub.sponsor_id),
            "expiry_warning_sent",
            {"subscription_id": str(sub.id), "days_left": days_left},
        )

        # B'-3: push notification (R-5: separate session to avoid premature commit)
        try:
            from app.db.session import AsyncSessionLocal as _ASL
            async with _ASL() as push_db:
                await push_notifier.notify_user(
                    push_db,
                    sub.sponsor_id,
                    notification_type="subscription_expiring",
                    title="구독 만료 알림",
                    body=f"구독이 {days_left}일 후 만료됩니다.",
                    data={"link": "/me/sponsorships"},
                )
        except Exception:
            log.exception(
                "subscription_expiry: push failed for sponsor_id=%s", sub.sponsor_id
            )

        notifications_created += 1
        log.info(
            "subscription_expiry_notif created: subscription_id=%s sponsor_id=%s days_left=%d",
            sub.id,
            sub.sponsor_id,
            days_left,
        )

    await db.commit()

    subscription_expiry_notif_total.labels(result="sent").inc(notifications_created)
    return notifications_created


async def subscription_expiry_cron_loop(interval_seconds: int = 3600) -> None:
    log.info(
        "subscription_expiry_cron_loop started (interval=%ss, window=%dd)",
        interval_seconds,
        _NOTIFY_WINDOW_DAYS,
    )
    while True:
        try:
            with tracer.start_as_current_span("cron.subscription_expiry") as span:
                with record_cron_run("subscription_expiry"):
                    async with AsyncSessionLocal() as db:
                        count = await notify_expiring_subscriptions_once(db)
                    span.set_attribute("notifications_created", count)
                    if count:
                        log.info("Created %d subscription expiry notifications", count)
                        cron_rows_processed_total.labels(worker="subscription_expiry").inc(count)
                    else:
                        subscription_expiry_notif_total.labels(result="skipped").inc(1)
        except Exception as e:
            log.exception("subscription_expiry cron sweep failed: %s", e)
        await asyncio.sleep(interval_seconds)
