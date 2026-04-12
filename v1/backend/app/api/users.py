import asyncio
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.errors import ApiError
from app.core.rate_limit import rate_limit
from app.core.security import decode_token
from app.db.session import get_db
from app.models.post import Follow
from app.models.search_log import SearchLog
from app.models.sponsorship import Sponsorship
from app.models.user import ArtistProfile, User

router = APIRouter(prefix="/users", tags=["users"])

_log = logging.getLogger(__name__)


async def _optional_user_id(authorization: str | None) -> UUID | None:
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    try:
        payload = decode_token(authorization.split(" ", 1)[1])
    except ValueError:
        return None
    sub = payload.get("sub")
    return UUID(sub) if sub and payload.get("type") == "access" else None


@router.get("/search")
async def search_users(
    q: str = Query(..., min_length=2, max_length=100),
    role: str | None = Query(None, pattern="^(user|artist)$"),
    limit: int = Query(20, ge=1, le=50),
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
    _rl=rate_limit("search"),
):
    user_id = await _optional_user_id(authorization)

    follower_sub = (
        select(func.count())
        .select_from(Follow)
        .where(Follow.followee_id == User.id)
        .correlate(User)
        .scalar_subquery()
    )

    query = (
        select(User, follower_sub.label("follower_count"))
        .where(
            User.status == "active",
            User.deleted_at.is_(None),
            (
                User.display_name.ilike(f"%{q}%")
                | User.bio.ilike(f"%{q}%")
            ),
        )
        .order_by(follower_sub.desc(), User.created_at.desc())
        .limit(limit)
    )
    if role:
        query = query.where(User.role == role)

    result = await db.execute(query)
    rows = result.all()

    data = [
        {
            "id": str(u.id),
            "display_name": u.display_name,
            "avatar_url": u.avatar_url,
            "bio": u.bio,
            "role": u.role,
            "follower_count": fc or 0,
        }
        for u, fc in rows
    ]

    # Async search log (non-blocking)
    try:
        db.add(SearchLog(
            user_id=user_id,
            query=q,
            tab="artists",
            result_count=len(data),
            filters={"role": role},
        ))
        await db.commit()
    except Exception:
        _log.warning("Failed to save search log", exc_info=True)

    return {"data": data, "pagination": {"next_cursor": None, "has_more": False}}


@router.get("/{user_id}")
async def get_user_profile(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise ApiError("NOT_FOUND", "User not found", http_status=404)

    artist_profile = None
    if user.role == "artist":
        prof_result = await db.execute(
            select(ArtistProfile).where(ArtistProfile.user_id == user_id)
        )
        prof = prof_result.scalar_one_or_none()
        if prof:
            artist_profile = {
                "school": prof.school,
                "intro_video_url": prof.intro_video_url,
                "portfolio_urls": prof.portfolio_urls,
                "statement": prof.statement,
                "badge_level": prof.badge_level,
                "verified_at": prof.verified_at.isoformat()
                if prof.verified_at
                else None,
            }

    follower_count = await db.scalar(
        select(func.count()).select_from(Follow).where(Follow.followee_id == user_id)
    )
    following_count = await db.scalar(
        select(func.count()).select_from(Follow).where(Follow.follower_id == user_id)
    )

    return {
        "data": {
            "id": str(user.id),
            "display_name": user.display_name,
            "avatar_url": user.avatar_url,
            "bio": user.bio,
            "role": user.role,
            "country_code": user.country_code,
            "language": user.language,
            "follower_count": follower_count or 0,
            "following_count": following_count or 0,
            "artist_profile": artist_profile,
        }
    }


@router.post("/{user_id}/follow")
async def follow_user(
    user_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if user_id == user.id:
        raise ApiError("VALIDATION_ERROR", "Cannot follow yourself", http_status=422)

    target = await db.execute(select(User).where(User.id == user_id))
    if not target.scalar_one_or_none():
        raise ApiError("NOT_FOUND", "User not found", http_status=404)

    existing = await db.execute(
        select(Follow).where(
            Follow.follower_id == user.id,
            Follow.followee_id == user_id,
        )
    )
    if existing.scalar_one_or_none():
        return {"data": {"ok": True, "already_following": True}}

    db.add(Follow(follower_id=user.id, followee_id=user_id))
    await db.commit()
    return {"data": {"ok": True}}


@router.delete("/{user_id}/follow")
async def unfollow_user(
    user_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Follow).where(
            Follow.follower_id == user.id,
            Follow.followee_id == user_id,
        )
    )
    follow = result.scalar_one_or_none()
    if not follow:
        return {"data": {"ok": True, "already_unfollowed": True}}

    await db.delete(follow)
    await db.commit()
    return {"data": {"ok": True}}


# ─── Received sponsorships (GAP-S1, Phase 3 Week 13) ───────────────────


async def _viewer_id(authorization: str | None) -> UUID | None:
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    try:
        payload = decode_token(authorization.split(" ", 1)[1])
    except ValueError:
        return None
    if payload.get("type") != "access":
        return None
    sub = payload.get("sub")
    return UUID(sub) if sub else None


@router.get("/{user_id}/sponsorships")
async def get_received_sponsorships(
    user_id: UUID,
    limit: int = Query(20, ge=1, le=100),
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Sponsorships received by an artist with visibility masking.

    Visibility rules (design.md §2.2):
    - public: visible to everyone
    - artist_only: visible only to artist (target user) and admin
    - private: visible only to sponsor themselves
    Anonymous donors hide sponsor_id from non-self viewers.
    """
    target_result = await db.execute(select(User).where(User.id == user_id))
    target = target_result.scalar_one_or_none()
    if not target:
        raise ApiError("NOT_FOUND", "User not found", http_status=404)

    viewer_id = await _viewer_id(authorization)
    is_artist_self = viewer_id == user_id

    # Check admin
    is_admin = False
    if viewer_id and not is_artist_self:
        admin_check = await db.execute(
            select(User).where(User.id == viewer_id, User.role == "admin")
        )
        is_admin = admin_check.scalar_one_or_none() is not None

    result = await db.execute(
        select(Sponsorship)
        .where(
            Sponsorship.artist_id == user_id,
            Sponsorship.status == "completed",
        )
        .order_by(Sponsorship.created_at.desc())
        .limit(limit)
    )
    items = list(result.scalars().all())

    out: list[dict] = []
    for s in items:
        # Visibility filter
        is_self_sponsor = viewer_id == s.sponsor_id
        if s.visibility == "private" and not is_self_sponsor and not is_admin:
            continue
        if s.visibility == "artist_only" and not (
            is_artist_self or is_self_sponsor or is_admin
        ):
            continue

        # Sponsor identity masking
        sponsor_id = None
        if not s.is_anonymous or is_self_sponsor or is_admin:
            sponsor_id = s.sponsor_id

        out.append(
            {
                "id": str(s.id),
                "sponsor_id": str(sponsor_id) if sponsor_id else None,
                "post_id": str(s.post_id) if s.post_id else None,
                "bluebird_count": s.bluebird_count,
                "amount": str(s.amount),
                "currency": s.currency,
                "is_anonymous": s.is_anonymous,
                "visibility": s.visibility,
                "message": s.message,
                "created_at": s.created_at.isoformat(),
            }
        )
    return {"data": out}
