"""Background job: auto-update artist badge levels.

Runs daily. Promotes artists based on graduation status and activity metrics.

Badge levels:
  student     → 학교 인증 + 재학 중
  emerging    → 졸업 또는 학교 미인증
  recommended → 후원 50건+ OR 총 후원금 $500+
  popular     → 팔로워 100+ OR 총 거래 $1000+
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import func, select

from app.db.session import AsyncSessionLocal
from app.models.auction import Order
from app.models.post import Follow
from app.models.sponsorship import Sponsorship
from app.models.user import ArtistProfile, User

log = logging.getLogger(__name__)


async def update_artist_badges_once(db) -> dict:
    """Single sweep: update all artist badge levels based on current data."""
    current_year = datetime.now(timezone.utc).year
    stats = {"student_to_emerging": 0, "to_recommended": 0, "to_popular": 0}

    # Load all artist profiles
    result = await db.execute(
        select(ArtistProfile).join(User, User.id == ArtistProfile.user_id).where(
            User.role == "artist", User.status == "active"
        )
    )
    profiles = list(result.scalars().all())

    for prof in profiles:
        old_badge = prof.badge_level

        # 1. student → emerging (졸업)
        if prof.badge_level == "student":
            graduated = (
                prof.graduation_year is not None
                and prof.graduation_year <= current_year
                and not prof.is_enrolled
            )
            if graduated:
                prof.badge_level = "emerging"
                stats["student_to_emerging"] += 1

        # 2. emerging → recommended (후원 기준)
        if prof.badge_level in ("student", "emerging"):
            sponsorship_count = await db.scalar(
                select(func.count()).select_from(Sponsorship).where(
                    Sponsorship.artist_id == prof.user_id,
                    Sponsorship.status == "completed",
                )
            ) or 0
            sponsorship_total = await db.scalar(
                select(func.coalesce(func.sum(Sponsorship.amount), 0)).where(
                    Sponsorship.artist_id == prof.user_id,
                    Sponsorship.status == "completed",
                )
            ) or 0

            if sponsorship_count >= 50 or float(sponsorship_total) >= 500:
                prof.badge_level = "recommended"
                stats["to_recommended"] += 1

        # 3. recommended → popular (팔로워/거래 기준)
        if prof.badge_level in ("student", "emerging", "recommended"):
            follower_count = await db.scalar(
                select(func.count()).select_from(Follow).where(
                    Follow.followee_id == prof.user_id
                )
            ) or 0
            total_sales = await db.scalar(
                select(func.coalesce(func.sum(Order.amount), 0)).where(
                    Order.seller_id == prof.user_id,
                    Order.status == "paid",
                )
            ) or 0

            if follower_count >= 100 or float(total_sales) >= 1000:
                prof.badge_level = "popular"
                stats["to_popular"] += 1

        if prof.badge_level != old_badge:
            log.info(
                "Badge updated: user=%s %s → %s",
                prof.user_id, old_badge, prof.badge_level,
            )

    await db.commit()
    return stats


async def badge_cron_loop(interval_seconds: int = 86400) -> None:
    """Background task — runs daily (default 24h)."""
    log.info("badge_cron_loop started (interval=%ss)", interval_seconds)
    while True:
        try:
            async with AsyncSessionLocal() as db:
                stats = await update_artist_badges_once(db)
                total = sum(stats.values())
                if total:
                    log.info("Badge sweep: %s", stats)
        except Exception as e:
            log.exception("badge cron sweep failed: %s", e)
        await asyncio.sleep(interval_seconds)
