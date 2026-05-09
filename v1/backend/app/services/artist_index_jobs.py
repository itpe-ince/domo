"""Background job: hourly artist index score recalculation — A-6 artist-index-v1.

R-5 격리: separate file + separate AsyncSessionLocal + separate metric label.
Runs every 3600 seconds (1 hour) via lifespan task in main.py.

Algorithm (OQ-5=B — 신진작가 친화):
  score = 0.5 * recent_activity + 0.3 * sales + 0.2 * supporters + 0.1 * tenure

Idempotent: UPDATE is safe to run multiple times — each sweep overwrites
artist_index_score/rank/calculated_at with fresh values.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select, text, update

from app.core.metrics import (
    artist_index_artists_total,
    artist_index_calc_duration_seconds,
    cron_rows_processed_total,
    record_cron_run,
)
from app.db.session import AsyncSessionLocal
from app.models.user import User
from app.services.artist_index_scoring import ScoreComponents, calc_artist_score, calc_genre_score, calc_region_score
from app.services.cron_monitor import record_cron_run as _push_cron_status
from app.services.otel_setup import get_tracer

log = logging.getLogger(__name__)

tracer = get_tracer(__name__)

# ─── Lookback window for "recent activity" ───────────────────────────────────
_RECENT_DAYS = 30


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def _fetch_recent_post_counts(db, user_ids: list[Any]) -> dict[str, int]:
    """Count posts created in last 30 days per user_id."""
    if not user_ids:
        return {}
    cutoff = _now() - timedelta(days=_RECENT_DAYS)
    try:
        result = await db.execute(
            text(
                """
                SELECT author_id::text, COUNT(*) AS cnt
                FROM posts
                WHERE author_id = ANY(:ids)
                  AND created_at >= :cutoff
                  AND status IN ('published', 'scheduled')
                GROUP BY author_id
                """
            ),
            {"ids": [str(uid) for uid in user_ids], "cutoff": cutoff},
        )
        return {row[0]: int(row[1]) for row in result.fetchall()}
    except Exception:
        log.debug("posts table unavailable — using 0 for post_count_30d")
        return {}


async def _fetch_recent_bid_counts(db, user_ids: list[Any]) -> dict[str, int]:
    """Count auction bids placed in last 30 days per user_id (as bidder)."""
    if not user_ids:
        return {}
    cutoff = _now() - timedelta(days=_RECENT_DAYS)
    try:
        result = await db.execute(
            text(
                """
                SELECT bidder_id::text, COUNT(*) AS cnt
                FROM auction_bids
                WHERE bidder_id = ANY(:ids)
                  AND created_at >= :cutoff
                GROUP BY bidder_id
                """
            ),
            {"ids": [str(uid) for uid in user_ids], "cutoff": cutoff},
        )
        return {row[0]: int(row[1]) for row in result.fetchall()}
    except Exception:
        log.debug("auction_bids table unavailable — using 0 for bid_count_30d")
        return {}


async def _fetch_lifetime_sales(db, user_ids: list[Any]) -> dict[str, int]:
    """Sum completed sales (sponsorships + auction wins) in cents per artist."""
    if not user_ids:
        return {}
    ids_str = [str(uid) for uid in user_ids]
    totals: dict[str, int] = {k: 0 for k in ids_str}

    # Completed one-time sponsorships
    try:
        result = await db.execute(
            text(
                """
                SELECT artist_id::text, COALESCE(SUM(amount_cents), 0) AS total
                FROM sponsorships
                WHERE artist_id = ANY(:ids)
                  AND status = 'completed'
                GROUP BY artist_id
                """
            ),
            {"ids": ids_str},
        )
        for row in result.fetchall():
            totals[row[0]] = totals.get(row[0], 0) + int(row[1])
    except Exception:
        log.debug("sponsorships table unavailable for lifetime_sales")

    # Completed auction sales (seller)
    try:
        result = await db.execute(
            text(
                """
                SELECT seller_id::text, COALESCE(SUM(final_price_cents), 0) AS total
                FROM auctions
                WHERE seller_id = ANY(:ids)
                  AND status = 'completed'
                  AND final_price_cents IS NOT NULL
                GROUP BY seller_id
                """
            ),
            {"ids": ids_str},
        )
        for row in result.fetchall():
            totals[row[0]] = totals.get(row[0], 0) + int(row[1])
    except Exception:
        log.debug("auctions table unavailable for lifetime_sales")

    # Completed product orders (seller/artist)
    try:
        result = await db.execute(
            text(
                """
                SELECT p.artist_id::text, COALESCE(SUM(oi.price_cents * oi.quantity), 0) AS total
                FROM order_items oi
                JOIN products p ON p.id = oi.product_id
                JOIN orders o ON o.id = oi.order_id
                WHERE p.artist_id = ANY(:ids)
                  AND o.status IN ('completed', 'delivered')
                GROUP BY p.artist_id
                """
            ),
            {"ids": ids_str},
        )
        for row in result.fetchall():
            totals[row[0]] = totals.get(row[0], 0) + int(row[1])
    except Exception:
        log.debug("order_items/products table unavailable for lifetime_sales")

    return totals


async def _fetch_active_subscribers(db, user_ids: list[Any]) -> dict[str, int]:
    """Count active subscriptions per artist."""
    if not user_ids:
        return {}
    try:
        result = await db.execute(
            text(
                """
                SELECT artist_id::text, COUNT(*) AS cnt
                FROM subscriptions
                WHERE artist_id = ANY(:ids)
                  AND status IN ('active', 'past_due')
                GROUP BY artist_id
                """
            ),
            {"ids": [str(uid) for uid in user_ids]},
        )
        return {row[0]: int(row[1]) for row in result.fetchall()}
    except Exception:
        log.debug("subscriptions table unavailable — using 0 for active_subscribers")
        return {}


async def _fetch_active_sponsors(db, user_ids: list[Any]) -> dict[str, int]:
    """Count active one-time sponsors per artist."""
    if not user_ids:
        return {}
    try:
        result = await db.execute(
            text(
                """
                SELECT artist_id::text, COUNT(*) AS cnt
                FROM sponsorships
                WHERE artist_id = ANY(:ids)
                  AND status = 'completed'
                GROUP BY artist_id
                """
            ),
            {"ids": [str(uid) for uid in user_ids]},
        )
        return {row[0]: int(row[1]) for row in result.fetchall()}
    except Exception:
        log.debug("sponsorships table unavailable — using 0 for active_sponsors")
        return {}


async def _fetch_primary_genres(db, user_ids: list[Any]) -> dict[str, str]:
    """Determine each artist's primary genre from their most-posted genre_tag.

    Queries posts table for genre_tags array unnested, groups by author_id +
    genre_tag, picks the most frequent tag. Falls back to empty dict on error.
    """
    if not user_ids:
        return {}
    try:
        result = await db.execute(
            text(
                """
                SELECT author_id::text, genre_tag, COUNT(*) AS cnt
                FROM posts,
                     LATERAL unnest(genre_tags) AS genre_tag
                WHERE author_id = ANY(:ids)
                  AND status IN ('published', 'scheduled')
                  AND genre_tags IS NOT NULL
                  AND array_length(genre_tags, 1) > 0
                GROUP BY author_id, genre_tag
                ORDER BY author_id, cnt DESC
                """
            ),
            {"ids": [str(uid) for uid in user_ids]},
        )
        primary: dict[str, str] = {}
        for row in result.fetchall():
            uid_str = row[0]
            genre_tag = row[1]
            # First row per author (highest cnt) wins
            if uid_str not in primary:
                primary[uid_str] = genre_tag
        return primary
    except Exception:
        log.debug("posts/genre_tags unavailable — primary_genre will be NULL")
        return {}


async def _fetch_followers(db, user_ids: list[Any]) -> dict[str, int]:
    """Count followers per user from follows table."""
    if not user_ids:
        return {}
    try:
        result = await db.execute(
            text(
                """
                SELECT following_id::text, COUNT(*) AS cnt
                FROM follows
                WHERE following_id = ANY(:ids)
                GROUP BY following_id
                """
            ),
            {"ids": [str(uid) for uid in user_ids]},
        )
        return {row[0]: int(row[1]) for row in result.fetchall()}
    except Exception:
        log.debug("follows table unavailable — using 0 for followers")
        return {}


async def recalc_all_artist_scores(db) -> int:
    """Recalculate artist_index_score + rank for all active artists.

    Returns number of artists processed.

    Steps:
    1. SELECT all active artists (role='artist', status='active')
    2. Batch-fetch activity/sales/supporters/followers in parallel SQL calls
    3. Compute score for each artist
    4. Sort by score descending → assign rank
    5. Bulk UPDATE users table
    """
    now = _now()

    # 1. Fetch all active artists
    result = await db.execute(
        select(User).where(
            User.role == "artist",
            User.status == "active",
            User.deleted_at.is_(None),
        )
    )
    artists = list(result.scalars().all())
    if not artists:
        log.info("artist_index: no active artists found — skipping sweep")
        return 0

    user_ids = [a.id for a in artists]
    id_to_artist = {str(a.id): a for a in artists}

    # 2. Batch-fetch metrics (sequential — all use same session)
    post_counts = await _fetch_recent_post_counts(db, user_ids)
    bid_counts = await _fetch_recent_bid_counts(db, user_ids)
    lifetime_sales = await _fetch_lifetime_sales(db, user_ids)
    active_subs = await _fetch_active_subscribers(db, user_ids)
    active_sponsors = await _fetch_active_sponsors(db, user_ids)
    followers = await _fetch_followers(db, user_ids)
    primary_genres = await _fetch_primary_genres(db, user_ids)

    # 3. Compute per-artist scores + collect components
    artist_components: dict[str, ScoreComponents] = {}
    scored: list[tuple[str, float]] = []
    for uid_str, artist in id_to_artist.items():
        days_since_signup = (now - artist.created_at).days if artist.created_at else 0
        components = ScoreComponents(
            post_count_30d=post_counts.get(uid_str, 0),
            bid_count_30d=bid_counts.get(uid_str, 0),
            comment_count_30d=0,  # comment table query future scope
            lifetime_sales_cents=lifetime_sales.get(uid_str, 0),
            active_subscribers=active_subs.get(uid_str, 0),
            active_sponsors=active_sponsors.get(uid_str, 0),
            followers=followers.get(uid_str, 0),
            days_since_signup=days_since_signup,
        )
        artist_components[uid_str] = components
        score = calc_artist_score(components)
        scored.append((uid_str, score))

    # 4. Sort descending → assign global ranks
    scored.sort(key=lambda x: x[1], reverse=True)

    # ── Step 2 (G'-8): region-scoped ranking ──────────────────────────────────
    # Group by country_code → sort by region_score → ROW_NUMBER within region
    region_groups: dict[str, list[tuple[str, float]]] = {}
    for uid_str, artist in id_to_artist.items():
        country = artist.country_code or "__none__"
        score_r = calc_region_score(artist_components[uid_str])
        region_groups.setdefault(country, []).append((uid_str, score_r))

    region_rank: dict[str, int] = {}
    region_score_map: dict[str, float] = {}
    for country, group in region_groups.items():
        group.sort(key=lambda x: x[1], reverse=True)
        for rank_1i, (uid_str, sc) in enumerate(group, start=1):
            region_rank[uid_str] = rank_1i
            region_score_map[uid_str] = sc

    # ── Step 3 (G'-8): genre-scoped ranking ───────────────────────────────────
    # Group by primary_genre (from posts) → sort by genre_score → ROW_NUMBER
    genre_groups: dict[str, list[tuple[str, float]]] = {}
    for uid_str, artist in id_to_artist.items():
        pg = primary_genres.get(uid_str) or "__none__"
        score_g = calc_genre_score(artist_components[uid_str])
        genre_groups.setdefault(pg, []).append((uid_str, score_g))

    genre_rank: dict[str, int] = {}
    genre_score_map: dict[str, float] = {}
    for genre, group in genre_groups.items():
        group.sort(key=lambda x: x[1], reverse=True)
        for rank_1i, (uid_str, sc) in enumerate(group, start=1):
            genre_rank[uid_str] = rank_1i
            genre_score_map[uid_str] = sc

    # 5. Bulk UPDATE — global + region + genre in a single UPDATE per artist
    for rank_1indexed, (uid_str, score) in enumerate(scored, start=1):
        pg = primary_genres.get(uid_str)
        await db.execute(
            update(User)
            .where(User.id == id_to_artist[uid_str].id)
            .values(
                artist_index_score=score,
                artist_index_rank=rank_1indexed,
                artist_index_calculated_at=now,
                # G'-8 region
                artist_index_score_region=region_score_map.get(uid_str),
                artist_index_rank_region=region_rank.get(uid_str),
                # G'-8 genre
                artist_index_primary_genre=pg,
                artist_index_score_genre=genre_score_map.get(uid_str),
                artist_index_rank_genre=genre_rank.get(uid_str),
            )
            .execution_options(synchronize_session=False)
        )

    await db.commit()
    log.info(
        "artist_index: recalculated scores for %d artists (sweep at %s)",
        len(scored),
        now.isoformat(),
    )

    # Update prometheus gauge metric
    try:
        artist_index_artists_total.labels(status="ranked").inc(0)  # ensure label exists
    except Exception:
        pass

    return len(scored)


async def artist_index_cron_loop(interval_seconds: int = 3600) -> None:
    """1-hour cron loop — R-5 격리: separate AsyncSessionLocal + separate metric label."""
    from app.services.cache import cache  # late import to avoid circular at module load

    log.info(
        "artist_index_cron_loop started (interval=%ss)", interval_seconds
    )
    while True:
        n = 0
        await _push_cron_status("artist_index", "running")
        try:
            with tracer.start_as_current_span("cron.artist_index") as span:
                with record_cron_run("artist_index"):
                    with artist_index_calc_duration_seconds.labels(phase="full").time():
                        async with AsyncSessionLocal() as db:
                            n = await recalc_all_artist_scores(db)
                        cron_rows_processed_total.labels(worker="artist_index").inc(n)
                        artist_index_artists_total.labels(status="ranked").inc(0)
                        log.info("artist_index sweep complete: %d artists ranked", n)
                span.set_attribute("artists_ranked", n)

            # Invalidate artist index cache — fresh rankings available (G''-2)
            deleted = await cache.delete_pattern("artists:index:*", reason="cron_artist_index")
            log.info("artist_index cache invalidated: %d keys deleted", deleted)
            await _push_cron_status("artist_index", "success")
        except Exception as _e:
            log.exception("artist_index cron sweep failed")
            await _push_cron_status("artist_index", "failed", error=str(_e)[:500])
        await asyncio.sleep(interval_seconds)
