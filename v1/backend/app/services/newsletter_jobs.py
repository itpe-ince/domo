"""Newsletter cron worker — C-5 newsletter-digest.

R-5 격리: separate file + separate AsyncSessionLocal + separate metric label.
Runs every 3600 seconds (1 hour) via lifespan task in main.py.

Algorithm:
  1. SELECT newsletter_issues WHERE status='sending'
  2. For each issue: SELECT newsletter_preferences WHERE is_subscribed=True
     AND preferred_locale=issue.locale AND user.email IS NOT NULL
     AND (suspended_until IS NULL OR suspended_until < NOW())
  3. Batch-send via SES (50 emails per batch with short sleep between batches)
  4. Update sent_count/failed_count; transition to status='sent' when complete

H'-5 bounce integration:
  - Hard-bounced users (is_subscribed=False) are excluded by is_subscribed filter
  - Soft-bounce suspended users (suspended_until > NOW()) are skipped per sweep
  - Once suspended_until lapses, users are naturally included again

Idempotency: issues already in status='sent' are never re-processed.
Each recipient is identified by (issue_id, user_id) — no per-recipient tracking
table in Phase 7 (carry-over to Phase 8 bounce/click tracking).
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.metrics import (
    cron_rows_processed_total,
    newsletter_failed_total,
    newsletter_sent_total,
    record_cron_run,
)
from app.db.session import AsyncSessionLocal
from app.models.newsletter_issue import NewsletterIssue
from app.models.newsletter_preferences import NewsletterPreferences
from app.models.user import User
from app.services.cron_monitor import record_cron_run as _push_cron_status
from app.services.email_ses import ses_client
from app.services.otel_setup import get_tracer
from app.services.push_notifier import push_notifier

log = logging.getLogger(__name__)

tracer = get_tracer(__name__)

_BATCH_SIZE = 50
_BATCH_SLEEP = 0.1  # seconds between batches (SES rate limit buffer)


# ─── Core functions ───────────────────────────────────────────────────────────


async def _get_recipient_emails(
    db: AsyncSession,
    locale: str,
) -> list[tuple[str, str]]:
    """Return (user_id_str, email) pairs for eligible subscribers matching locale.

    H'-5: excludes hard-bounced (is_subscribed=False) and soft-bounce suspended
    users (suspended_until is not NULL and > current timestamp).
    """
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(User.id, User.email)
        .join(
            NewsletterPreferences,
            NewsletterPreferences.user_id == User.id,
        )
        .where(
            NewsletterPreferences.is_subscribed.is_(True),
            NewsletterPreferences.preferred_locale == locale,
            User.email.isnot(None),
            User.deleted_at.is_(None),
            # H'-5: skip suspended users (soft bounce suspension window active)
            (
                NewsletterPreferences.suspended_until.is_(None)
                | (NewsletterPreferences.suspended_until <= now)
            ),
        )
    )
    return [(str(row[0]), row[1]) for row in result.fetchall()]


async def _send_issue(db: AsyncSession, issue: NewsletterIssue) -> None:
    """Send one issue to all matching subscribers. Updates sent_count/failed_count."""
    recipients = await _get_recipient_emails(db, issue.locale)
    if not recipients:
        log.info(
            "newsletter: no subscribers for locale=%s issue_id=%s",
            issue.locale,
            issue.id,
        )
        # Mark sent with 0 recipients
        await db.execute(
            update(NewsletterIssue)
            .where(NewsletterIssue.id == issue.id)
            .values(
                status="sent",
                sent_at=datetime.now(timezone.utc),
            )
            .execution_options(synchronize_session=False)
        )
        await db.commit()
        return

    sent = 0
    failed = 0

    for i in range(0, len(recipients), _BATCH_SIZE):
        batch = recipients[i : i + _BATCH_SIZE]
        for uid_str, email in batch:
            try:
                await ses_client.send_email(
                    to=email,
                    subject=issue.subject,
                    html_body=issue.body_html,
                )
                sent += 1
            except Exception:
                log.exception(
                    "newsletter: send failed to=%s issue_id=%s", email, issue.id
                )
                failed += 1

            # B'-3: push notification for newsletter (R-5: separate session to avoid
            # interfering with newsletter batch commit flow)
            try:
                import uuid as _uuid
                from app.db.session import AsyncSessionLocal as _ASL
                async with _ASL() as push_db:
                    await push_notifier.notify_user(
                        push_db,
                        _uuid.UUID(uid_str),
                        notification_type="system",
                        title="새 뉴스레터 발행",
                        body=issue.subject[:80],
                        data={"link": "/newsletter"},
                    )
            except Exception:
                log.debug("newsletter: push skipped for uid=%s", uid_str)

        if i + _BATCH_SIZE < len(recipients):
            await asyncio.sleep(_BATCH_SLEEP)

    newsletter_sent_total.labels(locale=issue.locale).inc(sent)
    newsletter_failed_total.labels(locale=issue.locale).inc(failed)

    new_status = "sent" if failed == 0 else "failed"
    await db.execute(
        update(NewsletterIssue)
        .where(NewsletterIssue.id == issue.id)
        .values(
            status=new_status,
            sent_count=NewsletterIssue.sent_count + sent,
            failed_count=NewsletterIssue.failed_count + failed,
            sent_at=datetime.now(timezone.utc),
        )
        .execution_options(synchronize_session=False)
    )
    await db.commit()

    log.info(
        "newsletter issue %s sent: sent=%d failed=%d status=%s",
        issue.id,
        sent,
        failed,
        new_status,
    )
    cron_rows_processed_total.labels(worker="newsletter").inc(sent + failed)


async def process_sending_issues() -> int:
    """Find all 'sending' issues and dispatch emails.

    Returns total number of emails attempted (sent + failed).
    R-5: uses its own AsyncSessionLocal.
    """
    total = 0
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(NewsletterIssue).where(NewsletterIssue.status == "sending")
        )
        issues = list(result.scalars().all())

        for issue in issues:
            try:
                await _send_issue(db, issue)
            except Exception:
                log.exception(
                    "newsletter: failed to process issue_id=%s", issue.id
                )
            total += 1

    return total


async def newsletter_cron_loop(interval_seconds: int = 3600) -> None:
    """1-hour cron loop — R-5 격리: separate AsyncSessionLocal + separate metric label."""
    log.info("newsletter_cron_loop started (interval=%ss)", interval_seconds)
    while True:
        await _push_cron_status("newsletter", "running")
        try:
            with tracer.start_as_current_span("cron.newsletter") as span:
                with record_cron_run("newsletter"):
                    n = await process_sending_issues()
                    log.info("newsletter sweep complete: %d issues processed", n)
                span.set_attribute("issues_processed", n)
            await _push_cron_status("newsletter", "success")
        except Exception as _e:
            log.exception("newsletter cron sweep failed")
            await _push_cron_status("newsletter", "failed", error=str(_e)[:500])
        await asyncio.sleep(interval_seconds)
