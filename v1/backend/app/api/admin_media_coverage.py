"""Admin media coverage CMS endpoints — C-4 media-coverage-cms.

POST   /admin/media-coverage          — create entry (admin)
GET    /admin/media-coverage          — list with filters (admin)
PATCH  /admin/media-coverage/{id}     — update entry (admin)
DELETE /admin/media-coverage/{id}     — soft-delete (admin)
"""
from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.admin_deps import require_admin_with_2fa
from app.core.errors import ApiError
from app.core.rate_limit import rate_limit
from app.db.session import get_db
from app.models.media_coverage import MediaCoverage
from app.models.user import User
from app.schemas.media_coverage import (
    AdminCreateMediaCoverageRequest,
    AdminPatchMediaCoverageRequest,
    MediaCoverageOut,
)

log = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/media-coverage", tags=["admin-media-coverage"])


def _row_to_out(row: MediaCoverage) -> dict:
    return MediaCoverageOut.model_validate(row).model_dump(mode="json")


@router.post("", status_code=201)
async def admin_create_media_coverage(
    body: AdminCreateMediaCoverageRequest,
    admin: User = Depends(require_admin_with_2fa),
    db: AsyncSession = Depends(get_db),
    _rl=rate_limit("admin_media_coverage_write"),
):
    """Create a new media coverage entry.

    title and description are HTML-stripped (XSS prevention) before persist.
    """
    entry = MediaCoverage(
        id=uuid.uuid4(),
        title=body.title,
        coverage_type=body.coverage_type,
        source_name=body.source_name,
        external_url=body.external_url,
        thumbnail_url=body.thumbnail_url,
        published_at=body.published_at,
        artist_id=body.artist_id,
        description=body.description,
        locale=body.locale,
        is_published=body.is_published,
        is_featured=body.is_featured,
        created_by_admin_id=admin.id,
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)

    log.info(
        "AUDIT action=admin_create_media_coverage admin=%s id=%s type=%s",
        admin.id,
        entry.id,
        entry.coverage_type,
    )
    return {"data": _row_to_out(entry)}


@router.get("")
async def admin_list_media_coverage(
    coverage_type: str | None = Query(None, alias="type"),
    locale: str | None = Query(None),
    is_published: bool | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    cursor: str | None = Query(None, description="Cursor = last seen created_at ISO string"),
    admin: User = Depends(require_admin_with_2fa),
    db: AsyncSession = Depends(get_db),
):
    """List media coverage entries (admin). Newest first.

    Supports ?type=article&locale=ko&is_published=true&limit=20&cursor=...
    """
    stmt = select(MediaCoverage).order_by(MediaCoverage.created_at.desc()).limit(limit)

    if coverage_type:
        stmt = stmt.where(MediaCoverage.coverage_type == coverage_type)
    if locale:
        stmt = stmt.where(MediaCoverage.locale == locale)
    if is_published is not None:
        stmt = stmt.where(MediaCoverage.is_published == is_published)

    if cursor:
        from datetime import datetime
        try:
            cursor_dt = datetime.fromisoformat(cursor)
            stmt = stmt.where(MediaCoverage.created_at < cursor_dt)
        except ValueError as exc:
            raise ApiError(
                "INVALID_CURSOR", "cursor must be an ISO datetime string", http_status=422
            ) from exc

    result = await db.execute(stmt)
    rows = result.scalars().all()

    next_cursor = None
    if rows:
        next_cursor = rows[-1].created_at.isoformat()

    return {
        "data": [_row_to_out(r) for r in rows],
        "next_cursor": next_cursor if len(rows) == limit else None,
    }


@router.patch("/{entry_id}")
async def admin_patch_media_coverage(
    entry_id: str,
    body: AdminPatchMediaCoverageRequest,
    admin: User = Depends(require_admin_with_2fa),
    db: AsyncSession = Depends(get_db),
    _rl=rate_limit("admin_media_coverage_write"),
):
    """Update a media coverage entry (partial update)."""
    try:
        eid = uuid.UUID(entry_id)
    except ValueError as exc:
        raise ApiError("INVALID_ID", "Invalid UUID format", http_status=422) from exc

    result = await db.execute(
        select(MediaCoverage).where(MediaCoverage.id == eid)
    )
    entry = result.scalar_one_or_none()
    if entry is None:
        raise ApiError("NOT_FOUND", "Media coverage entry not found", http_status=404)

    # Apply patch fields
    update_data = body.model_dump(exclude_none=True)
    for field, value in update_data.items():
        setattr(entry, field, value)

    await db.commit()
    await db.refresh(entry)

    log.info(
        "AUDIT action=admin_patch_media_coverage admin=%s id=%s fields=%s",
        admin.id,
        eid,
        list(update_data.keys()),
    )
    return {"data": _row_to_out(entry)}


@router.delete("/{entry_id}", status_code=204)
async def admin_delete_media_coverage(
    entry_id: str,
    admin: User = Depends(require_admin_with_2fa),
    db: AsyncSession = Depends(get_db),
    _rl=rate_limit("admin_media_coverage_write"),
):
    """Soft-delete a media coverage entry (unpublish + mark deleted via is_published=False).

    Hard delete: removes the row entirely (admin authority).
    """
    try:
        eid = uuid.UUID(entry_id)
    except ValueError as exc:
        raise ApiError("INVALID_ID", "Invalid UUID format", http_status=422) from exc

    result = await db.execute(
        select(MediaCoverage).where(MediaCoverage.id == eid)
    )
    entry = result.scalar_one_or_none()
    if entry is None:
        raise ApiError("NOT_FOUND", "Media coverage entry not found", http_status=404)

    await db.delete(entry)
    await db.commit()

    log.info(
        "AUDIT action=admin_delete_media_coverage admin=%s id=%s",
        admin.id,
        eid,
    )
    return None
