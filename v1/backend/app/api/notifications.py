"""Notifications API (Phase 3 Week 13).

Reference: design.md §3.2 notifications endpoints, §8 notification system.

D-4 audit additions:
- GET /notifications: type_filter CSV query param
- POST /notifications/mark-read-by-type: bulk read by type category
"""
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.errors import ApiError
from app.db.session import get_db
from app.models.notification import Notification
from app.models.user import User

router = APIRouter(prefix="/notifications", tags=["notifications"])

# Type → category mapping for filter tab support
_CATEGORY_TYPES: dict[str, list[str]] = {
    "auction": [
        "auction_ending_24h",
        "auction_ending_6h",
        "auction_ending_1h",
        "auction_ended",
        "auction_outbid",
        "auction_won",
        "auction_lost",
    ],
    "sponsorship": [
        "sponsor_received",
        "sponsor_milestone",
        "subscription_new",
        "subscription_cancelled",
    ],
    "engagement": [
        "like",
        "comment",
        "reply",
        "follow",
        "mention",
    ],
    "system": [
        "system",
        "announcement",
        "artist_approved",
        "artist_rejected",
        "warning_issued",
        "tier_release",
    ],
}


def _types_for_category(category: str) -> list[str]:
    """Return the list of type strings that belong to a given category slug."""
    return _CATEGORY_TYPES.get(category, [])


def _serialize(n: Notification) -> dict:
    return {
        "id": str(n.id),
        "user_id": str(n.user_id),
        "type": n.type,
        "title": n.title,
        "body": n.body,
        "link": n.link,
        "is_read": n.is_read,
        "created_at": n.created_at.isoformat() if n.created_at else None,
    }


@router.get("")
async def list_notifications(
    unread_only: bool = Query(False),
    limit: int = Query(30, ge=1, le=100),
    types: str | None = Query(
        None,
        description=(
            "CSV of notification types or a category slug "
            "(auction|sponsorship|engagement|system). "
            "Example: ?types=auction_ended,auction_won  or  ?types=auction"
        ),
    ),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(Notification)
        .where(Notification.user_id == user.id)
        .order_by(Notification.created_at.desc())
        .limit(limit)
    )
    if unread_only:
        query = query.where(Notification.is_read.is_(False))
    if types:
        raw = [t.strip() for t in types.split(",") if t.strip()]
        # Expand category slugs to their constituent types
        expanded: list[str] = []
        for t in raw:
            category_types = _types_for_category(t)
            if category_types:
                expanded.extend(category_types)
            else:
                expanded.append(t)
        if expanded:
            query = query.where(Notification.type.in_(expanded))
    result = await db.execute(query)
    items = list(result.scalars().all())
    return {"data": [_serialize(n) for n in items]}


@router.get("/unread-count")
async def unread_count(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    count = await db.scalar(
        select(func.count())
        .select_from(Notification)
        .where(Notification.user_id == user.id, Notification.is_read.is_(False))
    )
    return {"data": {"count": int(count or 0)}}


@router.patch("/{notification_id}/read")
async def mark_read(
    notification_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Notification).where(Notification.id == notification_id)
    )
    notification = result.scalar_one_or_none()
    if not notification:
        raise ApiError("NOT_FOUND", "Notification not found", http_status=404)
    if notification.user_id != user.id:
        raise ApiError("FORBIDDEN", "Not your notification", http_status=403)

    if not notification.is_read:
        notification.is_read = True
        await db.commit()
        await db.refresh(notification)
    return {"data": _serialize(notification)}


@router.post("/read-all")
async def mark_all_read(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        Notification.__table__.update()
        .where(
            Notification.user_id == user.id,
            Notification.is_read.is_(False),
        )
        .values(is_read=True)
    )
    await db.commit()
    return {"data": {"updated": result.rowcount or 0}}


@router.post("/mark-read-by-type")
async def mark_read_by_type(
    types: str = Query(
        ...,
        description=(
            "CSV of notification types or a single category slug "
            "(auction|sponsorship|engagement|system). "
            "Example: ?types=auction  or  ?types=like,comment"
        ),
    ),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark all unread notifications matching the given type list as read.

    Accepts the same `types` syntax as GET /notifications:
    comma-separated type strings or a single category slug.
    """
    raw = [t.strip() for t in types.split(",") if t.strip()]
    expanded: list[str] = []
    for t in raw:
        category_types = _types_for_category(t)
        if category_types:
            expanded.extend(category_types)
        else:
            expanded.append(t)
    if not expanded:
        raise ApiError("INVALID_INPUT", "types parameter is empty", http_status=422)

    result = await db.execute(
        Notification.__table__.update()
        .where(
            Notification.user_id == user.id,
            Notification.is_read.is_(False),
            Notification.type.in_(expanded),
        )
        .values(is_read=True)
    )
    await db.commit()
    return {"data": {"updated": result.rowcount or 0, "types": expanded}}
