"""post_engagement_jobs.py — G'-9 post-engagement-cache hourly cron worker.

R-5 격리: separate file + separate AsyncSessionLocal + separate Prometheus label.
Runs every 3600 seconds (1 hour) via lifespan task in main.py.

Algorithm:
  1. SELECT all published posts created within last 7 days (active window)
  2. For each post, COUNT events (likes, comments, bookmarks, bids, shares)
     in a 24h rolling window (created_at > now - 24h)
  3. Compute weighted engagement_score:
       likes × 1 + comments × 2 + bookmarks × 1.5 + bids × 5 + shares × 3
  4. UPSERT into post_engagement_cache (ON CONFLICT post_id DO UPDATE)

Idempotent: safe to run multiple times — each sweep overwrites existing rows.
Cache miss fallback: A-3 feed_scoring.py retains inline subquery as graceful degrade.

Engagement weight rationale:
  - shares (3): viral coefficient — amplifies reach
  - bids (5): highest commercial intent signal
  - comments (2): active engagement > passive like
  - bookmarks (1.5): save-for-later intent
  - likes (1): baseline passive engagement
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import text

from app.core.metrics import (
    cron_rows_processed_total,
    record_cron_run,
    post_engagement_cache_calc_duration_seconds,
    post_engagement_cache_rows_total,
)
from app.db.session import AsyncSessionLocal
from app.services.cron_monitor import record_cron_run as _push_cron_status
from app.services.otel_setup import get_tracer

tracer = get_tracer(__name__)

log = logging.getLogger(__name__)

# ─── Engagement weight constants ─────────────────────────────────────────────

WEIGHT_LIKES = 1.0
WEIGHT_COMMENTS = 2.0
WEIGHT_BOOKMARKS = 1.5
WEIGHT_BIDS = 5.0
WEIGHT_SHARES = 3.0

# Active post window (posts older than this are not re-cached)
_ACTIVE_POST_DAYS = 7

# 24h engagement rolling window
_ENGAGEMENT_WINDOW_HOURS = 24


def _now() -> datetime:
    return datetime.now(timezone.utc)


def compute_engagement_score(
    like_count: int,
    comment_count: int,
    bookmark_count: int,
    bid_count: int,
    share_count: int,
) -> float:
    """Compute weighted engagement score from raw 24h counts.

    Pure function — no DB access. Testable without a database.

    Returns float engagement_score ≥ 0.0.
    """
    return (
        like_count * WEIGHT_LIKES
        + comment_count * WEIGHT_COMMENTS
        + bookmark_count * WEIGHT_BOOKMARKS
        + bid_count * WEIGHT_BIDS
        + share_count * WEIGHT_SHARES
    )


async def _fetch_active_post_ids(db, cutoff_created: datetime) -> list[str]:
    """SELECT id of published posts created within the active window."""
    try:
        result = await db.execute(
            text(
                """
                SELECT id::text
                FROM posts
                WHERE status = 'published'
                  AND created_at >= :cutoff
                  AND deleted_at IS NULL
                """
            ),
            {"cutoff": cutoff_created},
        )
        return [row[0] for row in result.fetchall()]
    except Exception:
        log.debug("posts table unavailable — post_engagement_jobs no-op")
        return []


async def _count_likes_24h(db, post_ids: list[str], window_start: datetime) -> dict[str, int]:
    """Count likes per post in the 24h window."""
    if not post_ids:
        return {}
    try:
        result = await db.execute(
            text(
                """
                SELECT post_id::text, COUNT(*) AS cnt
                FROM likes
                WHERE post_id = ANY(:ids)
                  AND created_at >= :window_start
                GROUP BY post_id
                """
            ),
            {"ids": post_ids, "window_start": window_start},
        )
        return {row[0]: int(row[1]) for row in result.fetchall()}
    except Exception:
        log.debug("likes table unavailable for engagement cache")
        return {}


async def _count_comments_24h(db, post_ids: list[str], window_start: datetime) -> dict[str, int]:
    """Count comments per post in the 24h window."""
    if not post_ids:
        return {}
    try:
        result = await db.execute(
            text(
                """
                SELECT post_id::text, COUNT(*) AS cnt
                FROM comments
                WHERE post_id = ANY(:ids)
                  AND created_at >= :window_start
                GROUP BY post_id
                """
            ),
            {"ids": post_ids, "window_start": window_start},
        )
        return {row[0]: int(row[1]) for row in result.fetchall()}
    except Exception:
        log.debug("comments table unavailable for engagement cache")
        return {}


async def _count_bookmarks_24h(db, post_ids: list[str], window_start: datetime) -> dict[str, int]:
    """Count bookmarks per post in the 24h window."""
    if not post_ids:
        return {}
    try:
        result = await db.execute(
            text(
                """
                SELECT post_id::text, COUNT(*) AS cnt
                FROM bookmarks
                WHERE post_id = ANY(:ids)
                  AND created_at >= :window_start
                GROUP BY post_id
                """
            ),
            {"ids": post_ids, "window_start": window_start},
        )
        return {row[0]: int(row[1]) for row in result.fetchall()}
    except Exception:
        log.debug("bookmarks table unavailable for engagement cache")
        return {}


async def _count_bids_24h(db, post_ids: list[str], window_start: datetime) -> dict[str, int]:
    """Count auction bids per auction (linked by auctionpost) in the 24h window.

    Joins auctions → auction_bids. Falls back to empty on error.
    """
    if not post_ids:
        return {}
    try:
        result = await db.execute(
            text(
                """
                SELECT a.post_id::text, COUNT(ab.id) AS cnt
                FROM auctions a
                JOIN auction_bids ab ON ab.auction_id = a.id
                WHERE a.post_id = ANY(:ids)
                  AND ab.created_at >= :window_start
                GROUP BY a.post_id
                """
            ),
            {"ids": post_ids, "window_start": window_start},
        )
        return {row[0]: int(row[1]) for row in result.fetchall()}
    except Exception:
        log.debug("auctions/auction_bids table unavailable for engagement cache")
        return {}


async def _count_shares_24h(db, post_ids: list[str], window_start: datetime) -> dict[str, int]:
    """Count share events per post in 24h window.

    Shares are tracked in activity_logs with action='post_share'.
    Falls back to empty on error.
    """
    if not post_ids:
        return {}
    try:
        result = await db.execute(
            text(
                """
                SELECT target_id::text, COUNT(*) AS cnt
                FROM user_activity_logs
                WHERE target_id = ANY(:ids)
                  AND action = 'post_share'
                  AND created_at >= :window_start
                GROUP BY target_id
                """
            ),
            {"ids": post_ids, "window_start": window_start},
        )
        return {row[0]: int(row[1]) for row in result.fetchall()}
    except Exception:
        log.debug("user_activity_logs unavailable for engagement cache shares")
        return {}


async def recalc_post_engagement(db) -> int:
    """Recalculate and UPSERT engagement scores for all active posts.

    Returns number of posts processed (upserted).

    Steps:
    1. Fetch IDs of active posts (published, created within last 7d)
    2. Batch-count likes/comments/bookmarks/bids/shares in 24h window
    3. Compute weighted engagement_score
    4. UPSERT into post_engagement_cache
    """
    now = _now()
    active_cutoff = now - timedelta(days=_ACTIVE_POST_DAYS)
    window_start = now - timedelta(hours=_ENGAGEMENT_WINDOW_HOURS)

    # 1. Active post IDs
    post_ids = await _fetch_active_post_ids(db, active_cutoff)
    if not post_ids:
        log.info("post_engagement_cache: no active posts — skipping sweep")
        return 0

    # 2. Batch-fetch 24h engagement counts
    likes = await _count_likes_24h(db, post_ids, window_start)
    comments = await _count_comments_24h(db, post_ids, window_start)
    bookmarks = await _count_bookmarks_24h(db, post_ids, window_start)
    bids = await _count_bids_24h(db, post_ids, window_start)
    shares = await _count_shares_24h(db, post_ids, window_start)

    # 3. Compute scores and UPSERT
    upserted = 0
    for pid in post_ids:
        lc = likes.get(pid, 0)
        cc = comments.get(pid, 0)
        bc = bookmarks.get(pid, 0)
        bdc = bids.get(pid, 0)
        sc = shares.get(pid, 0)
        score = compute_engagement_score(lc, cc, bc, bdc, sc)

        await db.execute(
            text(
                """
                INSERT INTO post_engagement_cache
                    (post_id, like_count_24h, comment_count_24h, bookmark_count_24h,
                     bid_count_24h, share_count_24h, engagement_score, calculated_at)
                VALUES
                    (:post_id, :lc, :cc, :bc, :bdc, :sc, :score, :calculated_at)
                ON CONFLICT (post_id) DO UPDATE SET
                    like_count_24h      = EXCLUDED.like_count_24h,
                    comment_count_24h   = EXCLUDED.comment_count_24h,
                    bookmark_count_24h  = EXCLUDED.bookmark_count_24h,
                    bid_count_24h       = EXCLUDED.bid_count_24h,
                    share_count_24h     = EXCLUDED.share_count_24h,
                    engagement_score    = EXCLUDED.engagement_score,
                    calculated_at       = EXCLUDED.calculated_at
                """
            ),
            {
                "post_id": pid,
                "lc": lc,
                "cc": cc,
                "bc": bc,
                "bdc": bdc,
                "sc": sc,
                "score": score,
                "calculated_at": now,
            },
        )
        upserted += 1

    await db.commit()
    log.info(
        "post_engagement_cache: upserted %d posts (sweep at %s)",
        upserted,
        now.isoformat(),
    )

    post_engagement_cache_rows_total.labels(result="upserted").inc(upserted)
    return upserted


async def post_engagement_cron_loop(interval_seconds: int = 3600) -> None:
    """1-hour cron loop — R-5 격리: separate AsyncSessionLocal + separate metric label."""
    log.info(
        "post_engagement_cron_loop started (interval=%ss)", interval_seconds
    )
    while True:
        await _push_cron_status("post_engagement", "running")
        try:
            with tracer.start_as_current_span("cron.post_engagement") as span:
                with record_cron_run("post_engagement"):
                    with post_engagement_cache_calc_duration_seconds.labels(phase="full").time():
                        async with AsyncSessionLocal() as db:
                            n = await recalc_post_engagement(db)
                        cron_rows_processed_total.labels(worker="post_engagement").inc(n)
                        log.info("post_engagement_cache sweep complete: %d posts", n)
                span.set_attribute("posts_processed", n)
            await _push_cron_status("post_engagement", "success")
        except Exception as _e:
            log.exception("post_engagement_cron sweep failed")
            await _push_cron_status("post_engagement", "failed", error=str(_e)[:500])
        await asyncio.sleep(interval_seconds)
