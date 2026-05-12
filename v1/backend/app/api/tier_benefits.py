"""Tier benefits API — B-4 tier-benefits-customization.

Endpoints:
  GET    /v1/me/tier-benefits                 — artist: fetch own 3-tier benefits
  PUT    /v1/me/tier-benefits/{tier}          — artist: upsert one tier
  DELETE /v1/me/tier-benefits/{tier}          — artist: reset to platform default
  GET    /v1/users/{user_id}/tier-benefits    — public: fetch any artist's benefits
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.errors import ApiError
from app.core.rate_limit import rate_limit
from app.db.session import get_db
from app.models.artist_tier_benefits import ArtistTierBenefits
from app.models.user import User
from app.schemas.tier_benefits import (
    VALID_TIERS,
    AllTierBenefitsOut,
    TierBenefitsOut,
    TierBenefitsUpsert,
)

router = APIRouter(tags=["tier-benefits"])

# Platform default i18n keys (UI resolves these)
_PLATFORM_DEFAULT_KEYS: dict[str, str] = {
    "subscriber": "patronage.supporter.tier.benefits.subscriber",
    "sponsor": "patronage.supporter.tier.benefits.sponsor",
    "follower": "patronage.supporter.tier.benefits.follower",
}


def _build_tier_out(
    tier: str, row: ArtistTierBenefits | None
) -> TierBenefitsOut:
    if row is None:
        return TierBenefitsOut(
            tier=tier,
            benefits=[],
            welcome_message=None,
            is_platform_default=True,
            platform_default_key=_PLATFORM_DEFAULT_KEYS[tier],
            created_at=None,
            updated_at=None,
        )
    return TierBenefitsOut(
        tier=tier,
        benefits=row.benefits or [],
        welcome_message=row.welcome_message,
        is_platform_default=False,
        platform_default_key=None,
        created_at=row.created_at.isoformat() if row.created_at else None,
        updated_at=row.updated_at.isoformat() if row.updated_at else None,
    )


async def _fetch_all_for_artist(
    db: AsyncSession, artist_id: uuid.UUID
) -> dict[str, ArtistTierBenefits | None]:
    result = await db.execute(
        select(ArtistTierBenefits).where(
            ArtistTierBenefits.artist_id == artist_id
        )
    )
    rows = result.scalars().all()
    by_tier: dict[str, ArtistTierBenefits | None] = {
        "subscriber": None,
        "sponsor": None,
        "follower": None,
    }
    for row in rows:
        if row.tier in by_tier:
            by_tier[row.tier] = row
    return by_tier


# ─── Artist: own tier benefits ────────────────────────────────────────────────


@router.get("/me/tier-benefits", response_model=dict)
async def get_my_tier_benefits(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _rl=rate_limit("tier_benefits_read"),
):
    """Fetch the authenticated artist's tier benefits for all 3 tiers."""
    if user.role != "artist":
        raise ApiError(
            "ARTIST_ONLY",
            "Only artists can access their tier benefits settings",
            http_status=403,
        )

    by_tier = await _fetch_all_for_artist(db, user.id)
    out = AllTierBenefitsOut(
        subscriber=_build_tier_out("subscriber", by_tier["subscriber"]),
        sponsor=_build_tier_out("sponsor", by_tier["sponsor"]),
        follower=_build_tier_out("follower", by_tier["follower"]),
    )
    return {"data": out.model_dump()}


@router.put("/me/tier-benefits/{tier}", response_model=dict)
async def upsert_my_tier_benefits(
    tier: str,
    body: TierBenefitsUpsert,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _rl=rate_limit("tier_benefits_write"),
):
    """Upsert benefits for a specific tier (artist only)."""
    if user.role != "artist":
        raise ApiError(
            "ARTIST_ONLY",
            "Only artists can update their tier benefits",
            http_status=403,
        )

    if tier not in VALID_TIERS:
        raise ApiError(
            "VALIDATION_ERROR",
            f"Invalid tier '{tier}'. Must be one of: subscriber, sponsor, follower",
            http_status=422,
        )

    # Upsert: fetch existing or create new
    result = await db.execute(
        select(ArtistTierBenefits).where(
            ArtistTierBenefits.artist_id == user.id,
            ArtistTierBenefits.tier == tier,
        )
    )
    row = result.scalar_one_or_none()

    now = datetime.now(timezone.utc)
    if row is None:
        row = ArtistTierBenefits(
            id=uuid.uuid4(),
            artist_id=user.id,
            tier=tier,
            benefits=body.benefits,
            welcome_message=body.welcome_message,
            created_at=now,
            updated_at=now,
        )
        db.add(row)
    else:
        row.benefits = body.benefits
        row.welcome_message = body.welcome_message
        row.updated_at = now

    await db.commit()
    await db.refresh(row)

    out = _build_tier_out(tier, row)
    return {"data": out.model_dump()}


@router.delete("/me/tier-benefits/{tier}", status_code=204)
async def delete_my_tier_benefits(
    tier: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _rl=rate_limit("tier_benefits_write"),
):
    """Remove artist override for a tier — reverts to platform default."""
    if user.role != "artist":
        raise ApiError(
            "ARTIST_ONLY",
            "Only artists can manage their tier benefits",
            http_status=403,
        )

    if tier not in VALID_TIERS:
        raise ApiError(
            "VALIDATION_ERROR",
            f"Invalid tier '{tier}'. Must be one of: subscriber, sponsor, follower",
            http_status=422,
        )

    result = await db.execute(
        select(ArtistTierBenefits).where(
            ArtistTierBenefits.artist_id == user.id,
            ArtistTierBenefits.tier == tier,
        )
    )
    row = result.scalar_one_or_none()
    if row is not None:
        await db.delete(row)
        await db.commit()

    # Idempotent: 204 even if row didn't exist
    return Response(status_code=204)


# ─── Public: any artist's tier benefits ──────────────────────────────────────


@router.get("/users/{user_id}/tier-benefits", response_model=dict)
async def get_user_tier_benefits(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    _rl=rate_limit("tier_benefits_read"),
):
    """Fetch any artist's tier benefits (public endpoint, no auth required)."""
    try:
        artist_uuid = uuid.UUID(user_id)
    except ValueError:
        raise ApiError("VALIDATION_ERROR", "Invalid user_id format", http_status=422)

    # Verify the user is an artist
    result = await db.execute(select(User).where(User.id == artist_uuid))
    artist = result.scalar_one_or_none()
    if not artist or artist.role != "artist":
        raise ApiError(
            "NOT_FOUND", "Artist not found", http_status=404
        )

    by_tier = await _fetch_all_for_artist(db, artist_uuid)
    out = AllTierBenefitsOut(
        subscriber=_build_tier_out("subscriber", by_tier["subscriber"]),
        sponsor=_build_tier_out("sponsor", by_tier["sponsor"]),
        follower=_build_tier_out("follower", by_tier["follower"]),
    )
    return {"data": out.model_dump()}
