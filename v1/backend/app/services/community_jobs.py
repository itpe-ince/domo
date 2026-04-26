"""Auto-seed default communities on startup (P3-1).

Creates school, genre, and country communities idempotently
so the communities page always has content.
"""
from __future__ import annotations

import logging

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.community import Community
from app.models.user import ArtistProfile, User

log = logging.getLogger(__name__)

DEFAULT_GENRES = [
    "회화",
    "조각",
    "디지털 아트",
    "사진",
    "일러스트",
    "공예",
    "영상",
    "설치 미술",
    "그래피티",
    "판화",
]


async def seed_default_communities(db: AsyncSession) -> None:
    """Idempotent community seeding — safe to run on every startup.

    Creates:
    - Genre communities (10 fixed types)
    - School communities (one per distinct school in artist_profiles)
    - Country communities (one per distinct country_code in users)
    """
    created = 0

    # ── Genre communities ──────────────────────────────────────────────────
    for genre in DEFAULT_GENRES:
        exists = await db.scalar(
            select(Community).where(
                Community.type == "genre",
                Community.name == genre,
            )
        )
        if not exists:
            db.add(Community(name=genre, type="genre", description=f"{genre} 장르 커뮤니티"))
            created += 1

    # ── School communities ─────────────────────────────────────────────────
    school_result = await db.execute(
        select(ArtistProfile.school)
        .where(ArtistProfile.school.isnot(None))
        .distinct()
    )
    schools = [row[0] for row in school_result.all() if row[0]]

    for school in schools:
        exists = await db.scalar(
            select(Community).where(
                Community.type == "school",
                Community.name == school,
            )
        )
        if not exists:
            db.add(
                Community(
                    name=school,
                    type="school",
                    description=f"{school} 재학생/졸업생 커뮤니티",
                )
            )
            created += 1

    # ── Country communities ────────────────────────────────────────────────
    country_result = await db.execute(
        select(User.country_code)
        .where(User.country_code.isnot(None))
        .distinct()
    )
    country_codes = [row[0] for row in country_result.all() if row[0]]

    for code in country_codes:
        exists = await db.scalar(
            select(Community).where(
                Community.type == "country",
                Community.name == code,
            )
        )
        if not exists:
            db.add(
                Community(
                    name=code,
                    type="country",
                    description=f"{code} 아티스트 커뮤니티",
                )
            )
            created += 1

    if created:
        await db.commit()
        log.info("community_seed: created %d communities", created)
    else:
        log.debug("community_seed: all communities already exist, skipping")
