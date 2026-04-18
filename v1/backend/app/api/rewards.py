"""Sponsor rewards API — artists set tiers, sponsors claim rewards."""
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.errors import ApiError
from app.db.session import get_db
from app.models.notification import Notification
from app.models.reward import RewardClaim, SponsorReward
from app.models.sponsorship import Sponsorship
from app.models.user import User

router = APIRouter(prefix="/rewards", tags=["rewards"])


def _serialize_reward(r: SponsorReward) -> dict:
    return {
        "id": str(r.id), "artist_id": str(r.artist_id),
        "tier": r.tier, "name": r.name, "description": r.description,
        "min_bluebirds": r.min_bluebirds, "reward_type": r.reward_type,
    }


# ─── Artist: manage reward tiers ─────────────────────────────────────────


class RewardCreate(BaseModel):
    tier: str  # bronze | silver | gold | platinum
    name: str
    description: str | None = None
    min_bluebirds: int
    reward_type: str  # badge | poster | card | message | custom


@router.get("/artist/{artist_id}")
async def get_artist_rewards(
    artist_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(SponsorReward)
        .where(SponsorReward.artist_id == artist_id)
        .order_by(SponsorReward.min_bluebirds.asc())
    )
    return {"data": [_serialize_reward(r) for r in result.scalars().all()]}


@router.post("")
async def create_reward(
    body: RewardCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if user.role not in ("artist", "admin"):
        raise ApiError("FORBIDDEN", "Only artists can create rewards", http_status=403)

    reward = SponsorReward(
        artist_id=user.id,
        tier=body.tier,
        name=body.name,
        description=body.description,
        min_bluebirds=body.min_bluebirds,
        reward_type=body.reward_type,
    )
    db.add(reward)
    await db.commit()
    await db.refresh(reward)
    return {"data": _serialize_reward(reward)}


@router.delete("/{reward_id}")
async def delete_reward(
    reward_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(SponsorReward).where(SponsorReward.id == reward_id))
    reward = result.scalar_one_or_none()
    if not reward:
        raise ApiError("NOT_FOUND", "Reward not found", http_status=404)
    if reward.artist_id != user.id and user.role != "admin":
        raise ApiError("FORBIDDEN", "Not your reward", http_status=403)
    await db.delete(reward)
    await db.commit()
    return {"data": {"ok": True}}


# ─── Sponsor: check + claim rewards ──────────────────────────────────────


@router.get("/unlocked/{artist_id}")
async def get_unlocked_rewards(
    artist_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get rewards unlocked by current user's cumulative bluebirds to this artist."""
    total_bluebirds = await db.scalar(
        select(func.coalesce(func.sum(Sponsorship.bluebird_count), 0)).where(
            Sponsorship.sponsor_id == user.id,
            Sponsorship.artist_id == artist_id,
            Sponsorship.status == "completed",
        )
    ) or 0

    result = await db.execute(
        select(SponsorReward)
        .where(SponsorReward.artist_id == artist_id)
        .order_by(SponsorReward.min_bluebirds.asc())
    )
    rewards = result.scalars().all()

    # Check existing claims
    claims_result = await db.execute(
        select(RewardClaim.reward_id).where(RewardClaim.sponsor_id == user.id)
    )
    claimed_ids = {row[0] for row in claims_result.all()}

    data = []
    for r in rewards:
        data.append({
            **_serialize_reward(r),
            "unlocked": total_bluebirds >= r.min_bluebirds,
            "claimed": r.id in claimed_ids,
        })

    return {"data": data, "total_bluebirds": total_bluebirds}


@router.post("/{reward_id}/claim")
async def claim_reward(
    reward_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    reward = await db.execute(select(SponsorReward).where(SponsorReward.id == reward_id))
    r = reward.scalar_one_or_none()
    if not r:
        raise ApiError("NOT_FOUND", "Reward not found", http_status=404)

    # Check bluebird count
    total = await db.scalar(
        select(func.coalesce(func.sum(Sponsorship.bluebird_count), 0)).where(
            Sponsorship.sponsor_id == user.id,
            Sponsorship.artist_id == r.artist_id,
            Sponsorship.status == "completed",
        )
    ) or 0

    if total < r.min_bluebirds:
        raise ApiError("INSUFFICIENT", f"Need {r.min_bluebirds} bluebirds, have {total}", http_status=422)

    # Check duplicate
    existing = await db.execute(
        select(RewardClaim).where(
            RewardClaim.reward_id == reward_id,
            RewardClaim.sponsor_id == user.id,
        )
    )
    if existing.scalar_one_or_none():
        raise ApiError("CONFLICT", "Already claimed", http_status=409)

    claim = RewardClaim(reward_id=reward_id, sponsor_id=user.id, status="pending")
    db.add(claim)

    # Notify artist
    db.add(Notification(
        user_id=r.artist_id,
        type="reward_claimed",
        title="리워드 수령 요청",
        body=f"{user.display_name}님이 '{r.name}' 리워드를 수령 요청했습니다.",
    ))

    await db.commit()
    return {"data": {"claimed": True, "reward_name": r.name}}


# ─── Artist: fulfill claims ──────────────────────────────────────────────


@router.get("/claims/pending")
async def get_pending_claims(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Artist: get pending reward claims to fulfill."""
    result = await db.execute(
        select(RewardClaim, SponsorReward, User)
        .join(SponsorReward, SponsorReward.id == RewardClaim.reward_id)
        .join(User, User.id == RewardClaim.sponsor_id)
        .where(
            SponsorReward.artist_id == user.id,
            RewardClaim.status == "pending",
        )
        .order_by(RewardClaim.claimed_at.desc())
    )
    rows = result.all()
    return {
        "data": [
            {
                "claim_id": str(claim.id),
                "reward": _serialize_reward(reward),
                "sponsor": {"id": str(sponsor.id), "display_name": sponsor.display_name},
                "claimed_at": claim.claimed_at.isoformat(),
            }
            for claim, reward, sponsor in rows
        ]
    }


@router.post("/claims/{claim_id}/fulfill")
async def fulfill_claim(
    claim_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(RewardClaim)
        .join(SponsorReward, SponsorReward.id == RewardClaim.reward_id)
        .where(RewardClaim.id == claim_id, SponsorReward.artist_id == user.id)
    )
    claim = result.scalar_one_or_none()
    if not claim:
        raise ApiError("NOT_FOUND", "Claim not found", http_status=404)

    claim.status = "fulfilled"
    claim.fulfilled_at = datetime.now(timezone.utc)

    db.add(Notification(
        user_id=claim.sponsor_id,
        type="reward_fulfilled",
        title="리워드 발송 완료",
        body="요청하신 리워드가 발송되었습니다!",
    ))

    await db.commit()
    return {"data": {"fulfilled": True}}
