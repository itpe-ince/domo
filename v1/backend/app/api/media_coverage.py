"""Public media coverage endpoints — C-4 media-coverage-cms.

GET /media-coverage                  — public list (locale + type + artist filter)
GET /media-coverage/featured         — featured items for storyhub hero grid
"""
from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rate_limit import rate_limit
from app.db.session import get_db
from app.models.media_coverage import MediaCoverage, SUPPORTED_LOCALES
from app.schemas.media_coverage import MediaCoverageOut

log = logging.getLogger(__name__)

router = APIRouter(prefix="/media-coverage", tags=["media-coverage"])


def _row_to_out(row: MediaCoverage) -> dict:
    return MediaCoverageOut.model_validate(row).model_dump(mode="json")


@router.get("/featured")
async def get_featured_media_coverage(
    locale: str = Query("ko"),
    limit: int = Query(3, ge=1, le=10),
    db: AsyncSession = Depends(get_db),
    _rl=rate_limit("media_coverage_read"),
):
    """Return featured+published media coverage entries.

    Used by storyhub MediaCoverageGrid (A-7 booster).
    Returns at most `limit` entries (default 3), newest published_at first.
    """
    if locale not in SUPPORTED_LOCALES:
        locale = "ko"

    stmt = (
        select(MediaCoverage)
        .where(
            MediaCoverage.is_featured.is_(True),
            MediaCoverage.is_published.is_(True),
            MediaCoverage.locale == locale,
        )
        .order_by(MediaCoverage.published_at.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    rows = result.scalars().all()

    # Graceful fallback: if no locale-specific featured, try 'ko'
    if not rows and locale != "ko":
        stmt_ko = (
            select(MediaCoverage)
            .where(
                MediaCoverage.is_featured.is_(True),
                MediaCoverage.is_published.is_(True),
                MediaCoverage.locale == "ko",
            )
            .order_by(MediaCoverage.published_at.desc())
            .limit(limit)
        )
        result_ko = await db.execute(stmt_ko)
        rows = result_ko.scalars().all()

    return {"data": [_row_to_out(r) for r in rows]}


@router.get("")
async def list_media_coverage(
    coverage_type: str | None = Query(None, alias="type"),
    locale: str | None = Query(None),
    artist_id: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    cursor: str | None = Query(None, description="Cursor = last seen published_at ISO string"),
    db: AsyncSession = Depends(get_db),
    _rl=rate_limit("media_coverage_read"),
):
    """List published media coverage entries.

    Filters: ?type=article&locale=ko&artist_id=<uuid>&limit=20&cursor=...
    Sorted by published_at DESC.
    """
    stmt = (
        select(MediaCoverage)
        .where(MediaCoverage.is_published.is_(True))
        .order_by(MediaCoverage.published_at.desc())
        .limit(limit)
    )

    if coverage_type:
        stmt = stmt.where(MediaCoverage.coverage_type == coverage_type)

    if locale and locale in SUPPORTED_LOCALES:
        stmt = stmt.where(MediaCoverage.locale == locale)

    if artist_id:
        try:
            aid = uuid.UUID(artist_id)
            stmt = stmt.where(MediaCoverage.artist_id == aid)
        except ValueError:
            # Invalid UUID — return empty list gracefully
            return {"data": [], "next_cursor": None}

    if cursor:
        from datetime import date
        try:
            cursor_date = date.fromisoformat(cursor)
            stmt = stmt.where(MediaCoverage.published_at < cursor_date)
        except ValueError:
            # Invalid cursor — ignore and return from start
            pass

    result = await db.execute(stmt)
    rows = result.scalars().all()

    next_cursor = None
    if len(rows) == limit and rows:
        next_cursor = rows[-1].published_at.isoformat()

    return {"data": [_row_to_out(r) for r in rows], "next_cursor": next_cursor}
