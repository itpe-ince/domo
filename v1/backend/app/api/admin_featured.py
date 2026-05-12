"""Admin featured artist management endpoints — G'-7.

POST   /admin/featured-artists          — create/update monthly featured artist
GET    /admin/featured-artists          — list monthly history
DELETE /admin/featured-artists/{id}     — soft-delete (deactivate)
"""
from __future__ import annotations

import logging
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.admin_deps import require_admin_with_2fa
from app.core.errors import ApiError
from app.core.rate_limit import rate_limit
from app.db.session import get_db
from app.models.featured_artist import FeaturedArtist
from app.models.user import User
from app.schemas.featured_artist import AdminCreateFeaturedArtistRequest, FeaturedArtistOut

log = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/featured-artists", tags=["admin-featured-artists"])


def _row_to_out(row: FeaturedArtist) -> FeaturedArtistOut:
    return FeaturedArtistOut(
        id=row.id,
        artist_id=row.artist_id,
        month=row.month,
        curation_note=row.curation_note,
        is_active=row.is_active,
        created_at=row.created_at.isoformat(),
        created_by_admin_id=row.created_by_admin_id,
    )


@router.post("", status_code=201)
async def admin_create_featured_artist(
    body: AdminCreateFeaturedArtistRequest,
    admin: User = Depends(require_admin_with_2fa),
    db: AsyncSession = Depends(get_db),
    _rl=rate_limit("featured_artist_write"),
):
    """Create or replace the featured artist for a given month.

    - Validates the target user is an active artist.
    - If a previous active entry for the same month exists, it is deactivated
      (soft-replaced) before the new entry is inserted.
    - Past months (before current month) may not be changed.
    """
    today = date.today()
    current_month_start = date(today.year, today.month, 1)
    if body.month < current_month_start:
        raise ApiError(
            "PAST_MONTH_FORBIDDEN",
            "Cannot set featured artist for a past month.",
            http_status=422,
        )

    # Verify target user is an active artist
    artist_result = await db.execute(
        select(User).where(User.id == body.artist_id)
    )
    artist = artist_result.scalar_one_or_none()
    if artist is None or artist.role != "artist" or artist.status != "active":
        raise ApiError(
            "INVALID_ARTIST",
            "artist_id must refer to an active artist.",
            http_status=422,
        )

    # Deactivate any existing active entry for this month
    await db.execute(
        update(FeaturedArtist)
        .where(FeaturedArtist.month == body.month, FeaturedArtist.is_active.is_(True))
        .values(is_active=False)
    )

    new_entry = FeaturedArtist(
        artist_id=body.artist_id,
        month=body.month,
        curation_note=body.curation_note,
        is_active=True,
        created_by_admin_id=admin.id,
    )
    db.add(new_entry)
    await db.commit()
    await db.refresh(new_entry)

    log.info(
        "AUDIT action=admin_create_featured_artist admin=%s artist=%s month=%s",
        admin.id,
        body.artist_id,
        body.month,
    )
    return {"data": _row_to_out(new_entry).model_dump()}


@router.get("")
async def admin_list_featured_artists(
    month: str | None = Query(None, description="Filter by YYYY-MM, e.g. 2026-05"),
    limit: int = Query(12, ge=1, le=24),
    admin: User = Depends(require_admin_with_2fa),
    db: AsyncSession = Depends(get_db),
):
    """List featured artist history, most recent first.

    Optional ?month=YYYY-MM filter. Default: return last 12 entries.
    """
    stmt = select(FeaturedArtist).order_by(FeaturedArtist.month.desc()).limit(limit)

    if month:
        try:
            year, mon = month.split("-")
            month_date = date(int(year), int(mon), 1)
        except (ValueError, AttributeError) as exc:
            raise ApiError(
                "INVALID_MONTH_FORMAT",
                "month must be YYYY-MM (e.g. 2026-05)",
                http_status=422,
            ) from exc
        stmt = stmt.where(FeaturedArtist.month == month_date)

    result = await db.execute(stmt)
    rows = result.scalars().all()
    return {"data": [_row_to_out(r).model_dump() for r in rows]}


@router.delete("/{entry_id}", status_code=204)
async def admin_delete_featured_artist(
    entry_id: str,
    admin: User = Depends(require_admin_with_2fa),
    db: AsyncSession = Depends(get_db),
    _rl=rate_limit("featured_artist_write"),
):
    """Soft-delete (deactivate) a featured artist entry."""
    import uuid as _uuid

    try:
        eid = _uuid.UUID(entry_id)
    except ValueError as exc:
        raise ApiError("INVALID_ID", "Invalid UUID format", http_status=422) from exc

    result = await db.execute(
        select(FeaturedArtist).where(FeaturedArtist.id == eid)
    )
    entry = result.scalar_one_or_none()
    if entry is None:
        raise ApiError("NOT_FOUND", "Featured artist entry not found", http_status=404)

    entry.is_active = False
    await db.commit()

    log.info(
        "AUDIT action=admin_delete_featured_artist admin=%s entry=%s",
        admin.id,
        eid,
    )
    return None
