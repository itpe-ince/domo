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

from app.db.session import AsyncSessionLocal
from app.models.auction import Auction
from app.models.notification import Notification

log = logging.getLogger(__name__)

# ─── Notification slot definitions ──────────────────────────────────────────
# (column_name, time_delta_before_end, notification_type)
_SLOTS = [
    ("notified_24h_at", timedelta(hours=24), "auction_ending_24h"),
    ("notified_6h_at",  timedelta(hours=6),  "auction_ending_6h"),
    ("notified_1h_at",  timedelta(hours=1),  "auction_ending_1h"),
]

_TITLE_MAP: dict[str, str] = {
    "auction_ending_24h": "경매 종료 24시간 전",
    "auction_ending_6h":  "경매 종료 6시간 전",
    "auction_ending_1h":  "경매 종료 1시간 전",
}

_BODY_MAP: dict[str, str] = {
    "auction_ending_24h": "경매가 24시간 후에 종료됩니다. 지금 확인해보세요.",
    "auction_ending_6h":  "경매가 6시간 후에 종료됩니다. 마지막 입찰 기회를 놓치지 마세요.",
    "auction_ending_1h":  "경매가 1시간 후에 종료됩니다! 서두르세요.",
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _make_notifs(auction: Auction, notif_type: str) -> list[Notification]:
    """Create Notification rows for seller + winner (winner != seller, R-4)."""
    title = _TITLE_MAP[notif_type]
    body = _BODY_MAP[notif_type]
    link = f"/auctions/{auction.id}"

    notifs: list[Notification] = [
        Notification(
            user_id=auction.seller_id,
            type=notif_type,
            title=title,
            body=body,
            link=link,
        )
    ]

    if auction.current_winner and auction.current_winner != auction.seller_id:
        notifs.append(
            Notification(
                user_id=auction.current_winner,
                type=notif_type,
                title=title,
                body=body,
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
            for notif in _make_notifs(auction, notif_type):
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

        summary[notif_type] = len(auctions)

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
        try:
            async with AsyncSessionLocal() as db:
                await dispatch_pending_notifications_once(db)
        except Exception:
            log.exception("auction_promotion cron sweep failed")
        await asyncio.sleep(interval_seconds)
