"""User activity tracking + currency conversion API."""
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_token
from app.db.session import get_db
from app.models.activity_log import UserActivityLog
from app.services.currency import convert_usd, get_exchange_rate

router = APIRouter(prefix="/activity", tags=["activity"])


class ActivityEvent(BaseModel):
    event_type: str  # view | like | bookmark | sponsor | bid | purchase | follow | share
    target_type: str  # post | user | auction
    target_id: str
    duration_sec: int | None = None


@router.post("/track")
async def track_activity(
    body: ActivityEvent,
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Track user activity for recommendation engine. Works for both auth and anonymous."""
    user_id = None
    if authorization and authorization.lower().startswith("bearer "):
        try:
            payload = decode_token(authorization.split(" ", 1)[1])
            sub = payload.get("sub")
            if sub and payload.get("type") == "access":
                user_id = UUID(sub)
        except (ValueError, Exception):
            pass

    try:
        target_uuid = UUID(body.target_id)
    except ValueError:
        return {"data": {"ok": False}}

    db.add(UserActivityLog(
        user_id=user_id,
        event_type=body.event_type,
        target_type=body.target_type,
        target_id=target_uuid,
        duration_sec=body.duration_sec,
    ))
    await db.commit()
    return {"data": {"ok": True}}


# ─── Currency Conversion ─────────────────────────────────────────────────


@router.get("/exchange-rate")
async def exchange_rate(
    target: str = Query("KRW", min_length=3, max_length=3),
):
    """Get current USD → target exchange rate."""
    rate = await get_exchange_rate(target.upper())
    return {"data": {"base": "USD", "target": target.upper(), "rate": rate}}


@router.get("/convert")
async def convert_currency(
    amount: float = Query(..., gt=0),
    target: str = Query("KRW", min_length=3, max_length=3),
):
    """Convert USD amount to target currency."""
    result = await convert_usd(amount, target.upper())
    return {"data": result}
