"""Background job: auction end-approaching notifications (24h / 6h / 1h).

Runs every 60 seconds — SEPARATE from auction_jobs.py 5-min settlement cron (R-5 격리).
Uses SELECT FOR UPDATE SKIP LOCKED + UPDATE WHERE col IS NULL for idempotent delivery (R-1).

Notification recipients (OQ-2=B, OQ-8=B):
  - seller (always)
  - current_winner if current_winner != seller_id (R-4)
"""
from __future__ import annotations

import asyncio
import io
import logging
from datetime import datetime, timedelta, timezone

import httpx
from PIL import Image, ImageDraw, ImageFont
from sqlalchemy import select, update

from app.core.metrics import (
    cron_rows_processed_total,
    notification_dispatched_total,
    record_cron_run,
)
from app.db.session import AsyncSessionLocal
from app.models.auction import Auction
from app.models.notification import Notification
from app.models.user import User
from app.services.analytics import capture_event
from app.services.cron_monitor import record_cron_run as _push_cron_status
from app.services.i18n import t as _t
from app.services.otel_setup import get_tracer
from app.services.push_notifier import push_notifier

log = logging.getLogger(__name__)

tracer = get_tracer(__name__)

# ─── Notification slot definitions ──────────────────────────────────────────
# (column_name, time_delta_before_end, notification_type)
_SLOTS = [
    ("notified_24h_at", timedelta(hours=24), "auction_ending_24h"),
    ("notified_6h_at",  timedelta(hours=6),  "auction_ending_6h"),
    ("notified_1h_at",  timedelta(hours=1),  "auction_ending_1h"),
]

# _TITLE_MAP and _BODY_MAP removed in D-5 carry-over.
# Notification text now resolved via app.services.i18n._t() keyed on user.language.


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def _get_user_language(db, user_id) -> str | None:
    """Fetch user.language for the given user_id. Returns None on miss (i18n fallback to ko)."""
    if user_id is None:
        return None
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    return user.language if user else None


def _make_notifs(
    auction: Auction,
    notif_type: str,
    seller_lang: str | None = None,
    winner_lang: str | None = None,
) -> list[Notification]:
    """Create Notification rows for seller + winner (winner != seller, R-4).

    D-5: title/body resolved via i18n service per recipient's user.language.
    seller_lang / winner_lang: user.language values (None → "ko" fallback).
    """
    link = f"/auctions/{auction.id}"

    notifs: list[Notification] = [
        Notification(
            user_id=auction.seller_id,
            type=notif_type,
            title=_t(notif_type, "title", seller_lang),
            body=_t(notif_type, "body", seller_lang),
            link=link,
        )
    ]

    if auction.current_winner and auction.current_winner != auction.seller_id:
        notifs.append(
            Notification(
                user_id=auction.current_winner,
                type=notif_type,
                title=_t(notif_type, "title", winner_lang),
                body=_t(notif_type, "body", winner_lang),
                link=link,
            )
        )

    return notifs


async def dispatch_pending_notifications_once(db) -> dict[str, int]:
    """Process 3 notification slots in order.

    For each slot:
      SELECT auctions WHERE status='active' AND end_at in window AND col IS NULL
      FOR UPDATE SKIP LOCKED
      → INSERT notifications (seller + winner)
      → UPDATE notified_Xh_at = now() WHERE col IS NULL (idempotent)
      → COMMIT

    Returns summary dict: {notif_type: count_dispatched}.
    """
    now = _now()
    summary: dict[str, int] = {}

    for col_name, delta, notif_type in _SLOTS:
        col = getattr(Auction, col_name)
        threshold = now + delta

        result = await db.execute(
            select(Auction).where(
                Auction.status == "active",
                Auction.end_at > now,
                Auction.end_at <= threshold,
                col.is_(None),
            ).with_for_update(skip_locked=True)
        )
        auctions = list(result.scalars().all())

        for auction in auctions:
            # D-5: resolve per-recipient language for i18n
            seller_lang = await _get_user_language(db, auction.seller_id)
            winner_lang = (
                await _get_user_language(db, auction.current_winner)
                if auction.current_winner and auction.current_winner != auction.seller_id
                else None
            )
            for notif in _make_notifs(auction, notif_type, seller_lang=seller_lang, winner_lang=winner_lang):
                db.add(notif)
            await db.execute(
                update(Auction)
                .where(Auction.id == auction.id, col.is_(None))
                .values({col_name: now})
                .execution_options(synchronize_session=False)
            )

        if auctions:
            await db.commit()
            log.info("auction_promotion: dispatched %d %s notification(s)", len(auctions), notif_type)
            notification_dispatched_total.labels(type=notif_type).inc(len(auctions))
            # G'-4: server-side notification batch event (one event per slot, not per user)
            for auction in auctions:
                capture_event(
                    str(auction.seller_id),
                    "notification_sent_server",
                    {"type": notif_type, "channel": "in_app"},
                )
                # B'-3: push dispatch to seller (and winner if different)
                push_title = _t(notif_type, "title", None)
                push_body = _t(notif_type, "body", None)
                try:
                    await push_notifier.notify_user(
                        db, auction.seller_id, notif_type, push_title, push_body,
                        data={"link": f"/auctions/{auction.id}"},
                    )
                    if auction.current_winner and auction.current_winner != auction.seller_id:
                        await push_notifier.notify_user(
                            db, auction.current_winner, notif_type, push_title, push_body,
                            data={"link": f"/auctions/{auction.id}"},
                        )
                except Exception:
                    log.exception("auction_promotion: push failed for auction=%s", auction.id)

        summary[notif_type] = len(auctions)

    # Count total rows (auctions processed across all slots) for cron_rows_processed_total.
    # This is called from within record_cron_run context in the loop, so we expose summary
    # for the caller to track externally.
    return summary


def _fetch_thumbnail_sync(url: str, timeout: float = 2.0) -> bytes:
    """Synchronous thumbnail fetch via httpx (R-2: raises on failure)."""
    resp = httpx.get(url, timeout=timeout)
    resp.raise_for_status()
    return resp.content


def _generate_share_card(
    *,
    thumbnail_url: str | None,
    artist_name: str,
    current_price: int,
    currency: str,
    end_at: datetime,
) -> bytes:
    """Pillow 합성 — 1200×630 PNG bytes. R-2/R-3 mitigation.

    Left 50%: artwork thumbnail (fallback: amber rect + 🎨 text)
    Right 50%: artist name (amber) + price (white) + remaining time (amber)
    Bottom-right: domo.art watermark (OQ-9=A, RGBA semi-transparent)
    """
    with tracer.start_as_current_span("pillow.generate_share_card") as span:
        span.set_attribute("has_thumbnail", thumbnail_url is not None)
        span.set_attribute("currency", currency)
        return _generate_share_card_inner(
            thumbnail_url=thumbnail_url,
            artist_name=artist_name,
            current_price=current_price,
            currency=currency,
            end_at=end_at,
        )


def _generate_share_card_inner(
    *,
    thumbnail_url: str | None,
    artist_name: str,
    current_price: int,
    currency: str,
    end_at: datetime,
) -> bytes:
    """Inner Pillow compositor — called from _generate_share_card with OTel span."""
    # Canvas: 1200×630, Domo dark background
    canvas = Image.new("RGB", (1200, 630), (26, 20, 16))
    draw = ImageDraw.Draw(canvas, "RGBA")
    font = ImageFont.load_default()

    # Left 50%: thumbnail (R-2 fallback)
    thumb_placed = False
    if thumbnail_url:
        try:
            raw = _fetch_thumbnail_sync(thumbnail_url, timeout=2.0)
            thumb = Image.open(io.BytesIO(raw)).convert("RGB")  # R-3: RGB only
            thumb.thumbnail((600, 630), Image.Resampling.LANCZOS)  # R-3: size limit
            paste_x = (600 - thumb.width) // 2
            paste_y = (630 - thumb.height) // 2
            canvas.paste(thumb, (paste_x, paste_y))
            thumb_placed = True
        except Exception:
            pass  # R-2: silent fallback

    if not thumb_placed:
        draw.rectangle([0, 0, 600, 630], fill=(40, 32, 26))
        draw.text((300, 315), "\U0001f3a8", anchor="mm", fill="white", font=font)

    # Right 50%: text info
    draw.text((640, 80), artist_name, fill=(255, 210, 60), font=font)

    if currency == "KRW":
        price_str = f"₩{current_price:,}"
    else:
        price_str = f"{current_price:,} {currency}"
    draw.text((640, 190), price_str, fill="white", font=font)

    now_utc = datetime.now(timezone.utc)
    delta_seconds = max(0, int((end_at - now_utc).total_seconds()))
    h, remainder = divmod(delta_seconds // 60, 60)
    m = remainder
    draw.text((640, 330), f"{h}시간 {m}분 남음", fill=(255, 210, 60), font=font)

    # OQ-9=A watermark: bottom-right, semi-transparent RGBA
    draw.text(
        (1180, 610),
        f"domo.art  @{artist_name}",
        anchor="rs",
        fill=(200, 200, 200, 160),
        font=font,
    )

    buf = io.BytesIO()
    canvas.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


async def dispatch_auction_ended_notifications(db) -> None:  # noqa: RUF029
    """Stub — no-winner end notification handled in _auto_transition() auctions.py."""
    pass  # noqa: PIE790


async def auction_promotion_cron_loop(interval_seconds: int = 60) -> None:
    """60s cron loop — tier_release_jobs.py pattern mirror (R-5 격리)."""
    log.info("auction_promotion_cron_loop started (interval=%ss)", interval_seconds)
    while True:
        await _push_cron_status("auction_promotion", "running")
        try:
            with tracer.start_as_current_span("cron.auction_promotion") as span:
                with record_cron_run("auction_promotion"):
                    async with AsyncSessionLocal() as db:
                        summary = await dispatch_pending_notifications_once(db)
                    total_rows = sum(summary.values())
                    if total_rows:
                        cron_rows_processed_total.labels(worker="auction_promotion").inc(total_rows)
                    span.set_attribute("rows_processed", total_rows)
            await _push_cron_status("auction_promotion", "success")
        except Exception as _e:
            log.exception("auction_promotion cron sweep failed")
            await _push_cron_status("auction_promotion", "failed", error=str(_e)[:500])
        await asyncio.sleep(interval_seconds)
