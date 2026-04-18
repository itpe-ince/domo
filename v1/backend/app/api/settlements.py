"""Settlement API for artists + admin."""
from datetime import date, datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.admin_deps import require_admin
from app.core.deps import get_current_user
from app.core.errors import ApiError
from app.db.session import get_db
from app.models.notification import Notification
from app.models.settlement import Settlement, SettlementItem
from app.models.user import User
from app.services.settlement_jobs import generate_settlement_batch

router = APIRouter(prefix="/settlements", tags=["settlements"])


def _serialize(s: Settlement) -> dict:
    return {
        "id": str(s.id),
        "artist_id": str(s.artist_id),
        "period_start": s.period_start.isoformat(),
        "period_end": s.period_end.isoformat(),
        "order_count": s.order_count,
        "gross_amount": str(s.gross_amount),
        "platform_fee": str(s.platform_fee),
        "net_amount": str(s.net_amount),
        "currency": s.currency,
        "status": s.status,
        "approved_at": s.approved_at.isoformat() if s.approved_at else None,
        "paid_at": s.paid_at.isoformat() if s.paid_at else None,
        "payout_reference": s.payout_reference,
        "created_at": s.created_at.isoformat() if s.created_at else None,
    }


# ─── Artist API ─────────────────────────────────────────────────────────

@router.get("/mine")
async def my_settlements(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Settlement)
        .where(Settlement.artist_id == user.id)
        .order_by(Settlement.period_end.desc())
    )
    return {"data": [_serialize(s) for s in result.scalars().all()]}


@router.get("/{settlement_id}")
async def get_settlement(
    settlement_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Settlement).where(Settlement.id == settlement_id))
    s = result.scalar_one_or_none()
    if not s:
        raise ApiError("NOT_FOUND", "Settlement not found", http_status=404)
    if s.artist_id != user.id and user.role != "admin":
        raise ApiError("FORBIDDEN", "Not your settlement", http_status=403)
    return {"data": _serialize(s)}


# ─── Admin API ──────────────────────────────────────────────────────────


@router.get("/admin/list")
async def list_settlements_admin(
    status: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    query = select(Settlement)
    if status:
        query = query.where(Settlement.status == status)

    total = await db.scalar(select(func.count()).select_from(query.subquery()))
    result = await db.execute(query.order_by(Settlement.created_at.desc()).offset(offset).limit(limit))
    settlements = result.scalars().all()

    # Load artist names
    artist_ids = list({s.artist_id for s in settlements})
    artist_map = {}
    if artist_ids:
        artists = await db.execute(select(User).where(User.id.in_(artist_ids)))
        artist_map = {u.id: u.display_name for u in artists.scalars()}

    data = []
    for s in settlements:
        item = _serialize(s)
        item["artist_name"] = artist_map.get(s.artist_id, "unknown")
        data.append(item)

    return {"data": data, "pagination": {"total": total or 0, "offset": offset, "limit": limit}}


class GenerateRequest(BaseModel):
    period_start: date
    period_end: date


@router.post("/admin/generate")
async def generate_batch(
    body: GenerateRequest,
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    batches = await generate_settlement_batch(db, body.period_start, body.period_end)
    return {"data": {"generated": len(batches)}}


@router.post("/admin/{settlement_id}/approve")
async def approve_settlement(
    settlement_id: UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Settlement).where(Settlement.id == settlement_id))
    s = result.scalar_one_or_none()
    if not s:
        raise ApiError("NOT_FOUND", "Settlement not found", http_status=404)
    if s.status != "pending":
        raise ApiError("CONFLICT", "Only pending settlements can be approved", http_status=409)

    s.status = "approved"
    s.approved_by = admin.id
    s.approved_at = datetime.now(timezone.utc)
    await db.commit()
    return {"data": _serialize(s)}


@router.post("/admin/{settlement_id}/pay")
async def pay_settlement(
    settlement_id: UUID,
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Settlement).where(Settlement.id == settlement_id))
    s = result.scalar_one_or_none()
    if not s:
        raise ApiError("NOT_FOUND", "Settlement not found", http_status=404)
    if s.status != "approved":
        raise ApiError("CONFLICT", "Settlement must be approved first", http_status=409)

    s.status = "paid"
    s.paid_at = datetime.now(timezone.utc)
    s.payout_reference = f"MOCK_PAYOUT_{s.id.hex[:8]}"

    db.add(Notification(
        user_id=s.artist_id,
        type="settlement_paid",
        title="정산 지급 완료",
        body=f"${float(s.net_amount):.2f}가 지급되었습니다. (참조: {s.payout_reference})",
    ))
    await db.commit()
    return {"data": _serialize(s)}
