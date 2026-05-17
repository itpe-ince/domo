"""Public onboarding endpoints — A-2 onboarding-funnel.

GET /v1/onboarding/recommended-artists?limit=N — list top N artists for the
growth-funnel wizard's "follow / first sponsor" steps.

Anonymous-accessible. Ranking prefers:
1. Artists with an existing artist_index_rank (cron-computed, full signal).
2. Fallback: ordered by follower count (Follow rows where followee_id = user.id).

Result is shuffled within the top pool so the same user sees variety across
sessions and unrelated users don't all see identical first cards.

Phase 6 carry-over (was deferred to Phase 6.5 per
docs/archive/2026-05/domo-phase6-roadmap/report.md).
"""

from __future__ import annotations

import logging
import random

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rate_limit import rate_limit
from app.db.session import get_db
from app.models.post import Follow, Post
from app.models.user import ArtistProfile, User

log = logging.getLogger(__name__)

router = APIRouter(prefix="/onboarding", tags=["onboarding"])

# Pull a slightly larger pool than `limit` so the shuffle has room to randomize.
_POOL_MULTIPLIER = 3
_POOL_MAX = 30
_BIO_SHORT_MAX_LEN = 100


def _truncate_bio(bio: str | None) -> str | None:
    if not bio:
        return None
    text = bio.strip()
    if len(text) <= _BIO_SHORT_MAX_LEN:
        return text
    return text[: _BIO_SHORT_MAX_LEN - 1].rstrip() + "…"


@router.get("/recommended-artists")
async def list_recommended_artists(
    limit: int = Query(default=5, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
    _rl=rate_limit("onboarding_recommended_read"),
):
    """Return up to `limit` shuffled active artists for onboarding CTAs.

    Response shape matches RecommendedArtist[] expected by
    v1/frontend/src/lib/api.ts:fetchRecommendedArtists().
    """
    pool_size = min(_POOL_MAX, limit * _POOL_MULTIPLIER)

    # 1) Primary candidates: artists with a computed artist_index_rank.
    primary_stmt = (
        select(User, ArtistProfile)
        .join(ArtistProfile, ArtistProfile.user_id == User.id, isouter=True)
        .where(
            User.role == "artist",
            User.status == "active",
            User.artist_index_rank.isnot(None),
        )
        .order_by(User.artist_index_rank.asc())
        .limit(pool_size)
    )
    primary_rows = (await db.execute(primary_stmt)).all()

    # 2) Fill remaining slots by follower count when index ranking is sparse.
    candidates = list(primary_rows)
    if len(candidates) < pool_size:
        already_ids = {row.User.id for row in candidates}
        follower_count = (
            select(Follow.followee_id, func.count().label("c"))
            .group_by(Follow.followee_id)
            .subquery()
        )
        fallback_stmt = (
            select(User, ArtistProfile)
            .join(ArtistProfile, ArtistProfile.user_id == User.id, isouter=True)
            .join(
                follower_count,
                follower_count.c.followee_id == User.id,
                isouter=True,
            )
            .where(
                User.role == "artist",
                User.status == "active",
            )
            .order_by(func.coalesce(follower_count.c.c, 0).desc(), User.created_at.desc())
            .limit(pool_size)
        )
        fallback_rows = (await db.execute(fallback_stmt)).all()
        for row in fallback_rows:
            if row.User.id not in already_ids and len(candidates) < pool_size:
                candidates.append(row)
                already_ids.add(row.User.id)

    if not candidates:
        return {"data": []}

    # Shuffle the pool, then take the top `limit`.
    random.shuffle(candidates)
    selected = candidates[:limit]

    # Recent works count: total published posts per author (no time window —
    # see plan §6.2: emerging artists have few posts; a 30-day filter would
    # frequently return 0 and hurt the onboarding CTA).
    selected_ids = [row.User.id for row in selected]
    works_count_stmt = (
        select(Post.author_id, func.count().label("c"))
        .where(
            Post.author_id.in_(selected_ids),
            Post.status == "published",
        )
        .group_by(Post.author_id)
    )
    works_rows = (await db.execute(works_count_stmt)).all()
    works_count_by_user: dict = {row.author_id: row.c for row in works_rows}

    out: list[dict] = []
    for row in selected:
        user_row = row.User
        profile = row.ArtistProfile
        tier_default = (profile.badge_level if profile else None) or "free"
        out.append(
            {
                "user_id": str(user_row.id),
                "username": user_row.display_name,
                "avatar_url": user_row.avatar_url,
                "bio_short": _truncate_bio(user_row.bio),
                "tier_default": tier_default,
                "recent_works_count": int(works_count_by_user.get(user_row.id, 0)),
            }
        )

    return {"data": out}
