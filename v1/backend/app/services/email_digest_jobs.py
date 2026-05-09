"""Email digest cron worker — B'-3 push-email-digest-foundation.

10th cron worker. R-5 격리: separate file + separate AsyncSessionLocal.
Runs every 3600 seconds (1 hour) via lifespan task in main.py.

Algorithm:
  1. SELECT users with email_enabled=True + email_per_type['digest'] != False
     + digest_frequency != 'never'
  2. Check if digest is due based on frequency (weekly/biweekly/monthly)
     using last_digest_sent_at (tracked via NotificationPreferences.updated_at proxy)
  3. Synthesize digest content:
     - Featured artist of current month
     - Top 3 recent posts by engagement (view_count + like_count)
     - Highlight text with artist count and new post count
  4. Send via SES (C-5)
  5. Update NotificationPreferences.email_per_type to stamp digest sent time
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, func as sa_func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.metrics import cron_rows_processed_total, record_cron_run
from app.db.session import AsyncSessionLocal
from app.services.cron_monitor import record_cron_run as _push_cron_status
from app.services.email_ses import ses_client
from app.services.otel_setup import get_tracer

log = logging.getLogger(__name__)
tracer = get_tracer(__name__)

# Digest due intervals
_FREQUENCY_DELTAS: dict[str, timedelta] = {
    "weekly": timedelta(days=7),
    "biweekly": timedelta(days=14),
    "monthly": timedelta(days=30),
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _is_digest_due(frequency: str, last_sent_iso: str | None) -> bool:
    """Return True if the next digest window has elapsed since last send."""
    delta = _FREQUENCY_DELTAS.get(frequency)
    if delta is None:
        return False  # 'never' or unknown

    if last_sent_iso is None:
        return True  # never sent — always due

    try:
        last_sent = datetime.fromisoformat(last_sent_iso)
        if last_sent.tzinfo is None:
            last_sent = last_sent.replace(tzinfo=timezone.utc)
        return (_now() - last_sent) >= delta
    except (ValueError, TypeError):
        return True  # unparseable — treat as due


def _build_digest_html(
    user_display_name: str,
    featured_artist_name: str | None,
    top_posts: list[dict],
    new_post_count: int,
) -> str:
    """Build simple HTML email body for the digest."""
    featured_section = ""
    if featured_artist_name:
        featured_section = f"""
        <tr>
          <td style="padding:16px 0;">
            <h2 style="color:#D97706;font-size:18px;margin:0 0 8px;">이달의 추천 작가</h2>
            <p style="margin:0;font-size:14px;color:#1a1a1a;">{featured_artist_name}</p>
          </td>
        </tr>"""

    post_rows = ""
    for p in top_posts[:3]:
        title = p.get("title") or "(제목 없음)"
        post_rows += f"""
        <tr>
          <td style="padding:8px 0;font-size:13px;color:#374151;border-bottom:1px solid #f3f4f6;">
            {title}
          </td>
        </tr>"""

    posts_section = ""
    if post_rows:
        posts_section = f"""
        <tr>
          <td style="padding:16px 0;">
            <h2 style="color:#D97706;font-size:18px;margin:0 0 8px;">인기 작품</h2>
            <table width="100%" cellpadding="0" cellspacing="0">{post_rows}</table>
          </td>
        </tr>"""

    return f"""<!DOCTYPE html>
<html lang="ko">
<head><meta charset="UTF-8"><title>Domo 다이제스트</title></head>
<body style="margin:0;padding:0;background:#f9fafb;font-family:sans-serif;">
  <table width="600" align="center" cellpadding="0" cellspacing="0"
         style="background:#ffffff;margin:32px auto;border-radius:8px;overflow:hidden;">
    <tr>
      <td style="background:#1a1a1a;padding:24px;text-align:center;">
        <span style="color:#D97706;font-size:24px;font-weight:bold;">domo</span>
        <p style="color:#9ca3af;font-size:13px;margin:4px 0 0;">아티스트 커뮤니티 다이제스트</p>
      </td>
    </tr>
    <tr>
      <td style="padding:24px;">
        <p style="color:#374151;font-size:15px;">안녕하세요, {user_display_name}님!</p>
        <p style="color:#6b7280;font-size:14px;">
          이번 기간 동안 새 포스트 <strong>{new_post_count}건</strong>이 등록되었습니다.
        </p>
        <table width="100%" cellpadding="0" cellspacing="0">
          {featured_section}
          {posts_section}
        </table>
      </td>
    </tr>
    <tr>
      <td style="background:#f3f4f6;padding:16px;text-align:center;">
        <p style="color:#9ca3af;font-size:12px;margin:0;">
          수신 거부: <a href="https://domo.art/me/notifications/preferences"
          style="color:#D97706;">알림 설정</a>에서 이메일 다이제스트를 끄세요.
        </p>
      </td>
    </tr>
  </table>
</body>
</html>"""


async def _get_digest_recipients(db: AsyncSession) -> list[tuple[uuid.UUID, str, str, str, dict]]:
    """Return (user_id, email, display_name, frequency, email_per_type) for eligible users.

    Eligible = email_enabled=True AND digest_frequency != 'never'
               AND email_per_type.get('digest') is not False.
    """
    from app.models.notification_preferences import NotificationPreferences
    from app.models.user import User

    result = await db.execute(
        select(
            User.id,
            User.email,
            User.display_name,
            NotificationPreferences.digest_frequency,
            NotificationPreferences.email_per_type,
        )
        .join(NotificationPreferences, NotificationPreferences.user_id == User.id)
        .where(
            NotificationPreferences.email_enabled.is_(True),
            NotificationPreferences.digest_frequency != "never",
            User.email.isnot(None),
            User.deleted_at.is_(None),
        )
    )
    rows = result.fetchall()
    return [
        (row[0], row[1], row[2], row[3], row[4] or {})
        for row in rows
        if row[4] is None or row[4].get("digest") is not False
    ]


async def _get_featured_artist_name(db: AsyncSession) -> str | None:
    """Return display_name of this month's active featured artist, if any."""
    from app.models.featured_artist import FeaturedArtist
    from app.models.user import User
    from datetime import date

    today = date.today()
    month_start = today.replace(day=1)

    result = await db.execute(
        select(User.display_name)
        .join(FeaturedArtist, FeaturedArtist.artist_id == User.id)
        .where(
            FeaturedArtist.month == month_start,
            FeaturedArtist.is_active.is_(True),
        )
        .limit(1)
    )
    row = result.first()
    return row[0] if row else None


async def _get_top_posts(db: AsyncSession, limit: int = 3) -> list[dict]:
    """Return top posts by (view_count + like_count) from the last 7 days."""
    from app.models.post import Post

    cutoff = _now() - timedelta(days=7)
    result = await db.execute(
        select(Post.id, Post.title, Post.view_count, Post.like_count)
        .where(
            Post.created_at >= cutoff,
            Post.status == "published",
        )
        .order_by((Post.view_count + Post.like_count).desc())
        .limit(limit)
    )
    return [
        {"id": str(row[0]), "title": row[1], "view_count": row[2], "like_count": row[3]}
        for row in result.fetchall()
    ]


async def _get_new_post_count(db: AsyncSession, since: timedelta = timedelta(days=7)) -> int:
    """Count published posts created in the last `since` window."""
    from app.models.post import Post

    cutoff = _now() - since
    result = await db.execute(
        select(sa_func.count())
        .select_from(Post)
        .where(
            Post.created_at >= cutoff,
            Post.status == "published",
        )
    )
    return int(result.scalar() or 0)


async def send_digests_once() -> int:
    """Single sweep: determine eligible users and send digest emails.

    Returns total number of emails sent.
    R-5: uses its own AsyncSessionLocal.
    """
    total_sent = 0

    async with AsyncSessionLocal() as db:
        recipients = await _get_digest_recipients(db)
        if not recipients:
            return 0

        featured_name = await _get_featured_artist_name(db)
        top_posts = await _get_top_posts(db, limit=3)
        new_post_count = await _get_new_post_count(db)

        for user_id, email, display_name, frequency, email_per_type in recipients:
            # Check if digest is due based on frequency
            last_digest_iso: str | None = email_per_type.get("_last_digest_sent")
            if not _is_digest_due(frequency, last_digest_iso):
                continue

            subject = f"Domo 다이제스트 — {display_name}님을 위한 이번 주 아트"
            html_body = _build_digest_html(
                user_display_name=display_name,
                featured_artist_name=featured_name,
                top_posts=top_posts,
                new_post_count=new_post_count,
            )

            try:
                await ses_client.send_email(
                    to=email,
                    subject=subject,
                    html_body=html_body,
                )
                total_sent += 1

                # Stamp last digest sent time in email_per_type JSONB
                from app.models.notification_preferences import NotificationPreferences
                from sqlalchemy import update

                now_iso = _now().isoformat()
                updated_per_type = {**email_per_type, "_last_digest_sent": now_iso}
                await db.execute(
                    update(NotificationPreferences)
                    .where(NotificationPreferences.user_id == user_id)
                    .values(email_per_type=updated_per_type)
                    .execution_options(synchronize_session=False)
                )
                log.info(
                    "email_digest: sent to user=%s email=%s frequency=%s",
                    user_id,
                    email,
                    frequency,
                )

            except Exception:
                log.exception(
                    "email_digest: send failed to user=%s email=%s", user_id, email
                )

        if total_sent:
            await db.commit()

    return total_sent


async def email_digest_cron_loop(interval_seconds: int = 3600) -> None:
    """1-hour cron loop — R-5 격리: 10th worker, separate AsyncSessionLocal."""
    log.info("email_digest_cron_loop started (interval=%ss)", interval_seconds)
    while True:
        await _push_cron_status("email_digest", "running")
        try:
            with tracer.start_as_current_span("cron.email_digest") as span:
                with record_cron_run("email_digest"):
                    total = await send_digests_once()
                    span.set_attribute("emails_sent", total)
                    if total:
                        log.info("email_digest: sent %d digest email(s)", total)
                        cron_rows_processed_total.labels(worker="email_digest").inc(total)
            await _push_cron_status("email_digest", "success")
        except Exception as _e:
            log.exception("email_digest cron sweep failed")
            await _push_cron_status("email_digest", "failed", error=str(_e)[:500])
        await asyncio.sleep(interval_seconds)
