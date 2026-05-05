"""Public featured artist endpoint — G'-7.

GET /v1/featured/artist/current — returns the current month's featured artist.

Falls back to artist_index rank 1 when no curated entry exists for this month.
"""
from __future__ import annotations

import logging
from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rate_limit import rate_limit
from app.db.session import get_db
from app.models.featured_artist import FeaturedArtist
from app.models.user import ArtistProfile, User
from app.schemas.featured_artist import ArtistFeaturedView
from app.services.artist_index_scoring import derive_tier_badge

log = logging.getLogger(__name__)

router = APIRouter(prefix="/featured", tags=["featured"])


@router.get("/artist/current")
async def get_current_featured_artist(
    db: AsyncSession = Depends(get_db),
    _rl=rate_limit("featured_artist_read"),
):
    """Return the current month's featured artist.

    Priority:
    1. Active curated entry in featured_artists for this month.
    2. Fallback: artist_index rank 1 (active artist with highest score).

    Response always includes `is_curated` flag so the frontend can render
    a curation note when available.
    """
    today = date.today()
    current_month = date(today.year, today.month, 1)
    month_label = f"{today.year}-{today.month:02d}"

    # 1. Try curated entry
    fa_result = await db.execute(
        select(FeaturedArtist).where(
            FeaturedArtist.month == current_month,
            FeaturedArtist.is_active.is_(True),
        )
    )
    featured_entry = fa_result.scalar_one_or_none()

    if featured_entry is not None:
        # Load artist user row
        user_result = await db.execute(
            select(User).where(User.id == featured_entry.artist_id)
        )
        artist_user = user_result.scalar_one_or_none()
        if artist_user and artist_user.status == "active":
            profile_result = await db.execute(
                select(ArtistProfile).where(ArtistProfile.user_id == artist_user.id)
            )
            profile = profile_result.scalar_one_or_none()
            tier = derive_tier_badge(
                getattr(artist_user, "artist_index_rank", None)
            )
            return {
                "data": ArtistFeaturedView(
                    user_id=str(artist_user.id),
                    username=artist_user.display_name,
                    avatar_url=artist_user.avatar_url,
                    bio=artist_user.bio,
                    country=getattr(artist_user, "country_code", None),
                    primary_genre=(
                        profile.genre_tags[0]
                        if profile and profile.genre_tags
                        else None
                    ),
                    tier_badge=tier,
                    rank=getattr(artist_user, "artist_index_rank", None),
                    score=getattr(artist_user, "artist_index_score", None),
                    curation_note=featured_entry.curation_note,
                    month=month_label,
                    is_curated=True,
                ).model_dump()
            }

    # 2. Fallback: artist_index rank 1
    fallback_result = await db.execute(
        select(User)
        .where(
            User.role == "artist",
            User.status == "active",
            User.artist_index_rank.isnot(None),
        )
        .order_by(User.artist_index_rank.asc())
        .limit(1)
    )
    fallback_user = fallback_result.scalar_one_or_none()

    if fallback_user is None:
        from app.core.errors import ApiError
        raise ApiError(
            "NO_FEATURED_ARTIST",
            "No featured artist available.",
            http_status=404,
        )

    profile_result = await db.execute(
        select(ArtistProfile).where(ArtistProfile.user_id == fallback_user.id)
    )
    profile = profile_result.scalar_one_or_none()
    tier = derive_tier_badge(getattr(fallback_user, "artist_index_rank", None))

    return {
        "data": ArtistFeaturedView(
            user_id=str(fallback_user.id),
            username=fallback_user.display_name,
            avatar_url=fallback_user.avatar_url,
            bio=fallback_user.bio,
            country=getattr(fallback_user, "country_code", None),
            primary_genre=(
                profile.genre_tags[0]
                if profile and profile.genre_tags
                else None
            ),
            tier_badge=tier,
            rank=getattr(fallback_user, "artist_index_rank", None),
            score=getattr(fallback_user, "artist_index_score", None),
            curation_note=None,
            month=month_label,
            is_curated=False,
        ).model_dump()
    }
