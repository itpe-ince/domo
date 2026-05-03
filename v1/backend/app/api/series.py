"""Series CRUD + post series membership — publish-controls PDCA #8 §B-8.

Endpoints:
  GET    /v1/series                  list series (default: current user)
  POST   /v1/series                  create series → 201
  GET    /v1/series/{id}             series detail + published posts (OQ-D-5=A)
  PATCH  /v1/series/{id}             update metadata (owner only)
  DELETE /v1/series/{id}             delete + cascade memberships (owner only) → 204
  POST   /v1/posts/{id}/series       replace post's full series membership list

R-6 mitigation: _check_series_owner helper called in EVERY mutation.
R-8 mitigation: POST /posts/{id}/series cross-checks BOTH post owner AND each series owner.
OQ-D-5=A: GET /series/{id} returns only status='published' posts.
"""
import uuid
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.errors import ApiError
from app.core.rate_limit import rate_limit
from app.db.session import get_db
from app.models.post import Post
from app.models.series import PostSeriesMembership, Series
from app.models.user import User
from app.schemas.series import (
    PostSeriesUpdateIn,
    SeriesCreate,
    SeriesOut,
    SeriesPatch,
)

router = APIRouter(tags=["series"])
_log = logging.getLogger(__name__)


# ─── Helpers ─────────────────────────────────────────────────────────────────


async def _check_series_owner(series: Series, user: User) -> None:
    """R-6/R-8 mitigation: enforce ownership on every series mutation.

    Raises SERIES_NOT_OWNER 403 if user is neither the author nor an admin.
    Must be called in EVERY create/update/delete/membership mutation.
    """
    if series.author_id != user.id and user.role != "admin":
        raise ApiError("SERIES_NOT_OWNER", "Series does not belong to you", http_status=403)


async def _get_series_or_404(db: AsyncSession, series_id: UUID) -> Series:
    result = await db.execute(select(Series).where(Series.id == series_id))
    series = result.scalar_one_or_none()
    if not series:
        raise ApiError("SERIES_NOT_FOUND", f"Series {series_id} not found", http_status=404)
    return series


# ─── List ─────────────────────────────────────────────────────────────────────


@router.get("/series")
async def list_series(
    author_id: UUID | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _rl=rate_limit("series_read"),
):
    """List series. Defaults to current user's series when author_id is omitted."""
    target_id = author_id or user.id
    result = await db.execute(
        select(Series)
        .where(Series.author_id == target_id)
        .order_by(Series.created_at.desc())
        .limit(limit)
    )
    series_list = list(result.scalars().all())

    # post_count: count memberships per series
    out = []
    for s in series_list:
        count_result = await db.execute(
            select(PostSeriesMembership).where(PostSeriesMembership.series_id == s.id)
        )
        post_count = len(count_result.scalars().all())
        out.append(
            SeriesOut(
                id=s.id,
                author_id=s.author_id,
                title=s.title,
                description=s.description,
                cover_url=s.cover_url,
                created_at=s.created_at,
                updated_at=s.updated_at,
                post_count=post_count,
            ).model_dump(mode="json")
        )
    return {"data": out}


# ─── Create ───────────────────────────────────────────────────────────────────


@router.post("/series", status_code=201)
async def create_series(
    body: SeriesCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _rl=rate_limit("series_write"),
):
    """Create a new series owned by the current user."""
    series = Series(
        author_id=user.id,
        title=body.title,
        description=body.description,
        cover_url=body.cover_url,
    )
    db.add(series)
    await db.commit()
    await db.refresh(series)

    _log.info("series.created series_id=%s author=%s", series.id, user.id)
    return {
        "data": SeriesOut(
            id=series.id,
            author_id=series.author_id,
            title=series.title,
            description=series.description,
            cover_url=series.cover_url,
            created_at=series.created_at,
            updated_at=series.updated_at,
            post_count=0,
        ).model_dump(mode="json")
    }


# ─── Get detail ───────────────────────────────────────────────────────────────


@router.get("/series/{series_id}")
async def get_series(
    series_id: UUID,
    db: AsyncSession = Depends(get_db),
    _rl=rate_limit("series_read"),
):
    """Get series detail with its published posts in order_index order.

    OQ-D-5=A: only status='published' posts are returned.
    No auth required — public endpoint.
    """
    series = await _get_series_or_404(db, series_id)

    # Fetch membership rows ordered by order_index
    mem_result = await db.execute(
        select(PostSeriesMembership)
        .where(PostSeriesMembership.series_id == series_id)
        .order_by(PostSeriesMembership.order_index.asc())
    )
    memberships = list(mem_result.scalars().all())

    posts_out = []
    if memberships:
        post_ids = [m.post_id for m in memberships]
        # OQ-D-5=A: only published posts in series view.
        posts_result = await db.execute(
            select(Post).where(
                Post.id.in_(post_ids),
                Post.status == "published",
            )
        )
        post_map = {p.id: p for p in posts_result.scalars().all()}
        # Preserve order_index ordering; skip unpublished.
        for m in memberships:
            p = post_map.get(m.post_id)
            if p:
                posts_out.append({
                    "id": str(p.id),
                    "title": p.title,
                    "status": p.status,
                    "order_index": m.order_index,
                    "created_at": p.created_at.isoformat(),
                })

    series_data = SeriesOut(
        id=series.id,
        author_id=series.author_id,
        title=series.title,
        description=series.description,
        cover_url=series.cover_url,
        created_at=series.created_at,
        updated_at=series.updated_at,
        post_count=len(posts_out),
    ).model_dump(mode="json")

    return {"data": {**series_data, "posts": posts_out}}


# ─── Update ───────────────────────────────────────────────────────────────────


@router.patch("/series/{series_id}")
async def patch_series(
    series_id: UUID,
    body: SeriesPatch,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _rl=rate_limit("series_write"),
):
    """Update series metadata. Owner or admin only (R-6 mitigation)."""
    series = await _get_series_or_404(db, series_id)
    await _check_series_owner(series, user)  # R-6 mitigation

    if body.title is not None:
        series.title = body.title
    if body.description is not None:
        series.description = body.description
    if body.cover_url is not None:
        series.cover_url = body.cover_url

    await db.commit()
    await db.refresh(series)

    count_result = await db.execute(
        select(PostSeriesMembership).where(PostSeriesMembership.series_id == series.id)
    )
    post_count = len(count_result.scalars().all())

    return {
        "data": SeriesOut(
            id=series.id,
            author_id=series.author_id,
            title=series.title,
            description=series.description,
            cover_url=series.cover_url,
            created_at=series.created_at,
            updated_at=series.updated_at,
            post_count=post_count,
        ).model_dump(mode="json")
    }


# ─── Delete ───────────────────────────────────────────────────────────────────


@router.delete("/series/{series_id}", status_code=204)
async def delete_series(
    series_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _rl=rate_limit("series_write"),
):
    """Delete series + cascade memberships. Posts themselves are NOT deleted (R-5).

    Owner or admin only (R-6 mitigation).
    """
    series = await _get_series_or_404(db, series_id)
    await _check_series_owner(series, user)  # R-6 mitigation

    await db.delete(series)  # CASCADE removes post_series_membership rows
    await db.commit()
    _log.info("series.deleted series_id=%s by=%s", series_id, user.id)
    # 204 No Content — no response body


# ─── Post series membership (cross-ownership check) ───────────────────────────


@router.post("/posts/{post_id}/series", status_code=200)
async def update_post_series(
    post_id: UUID,
    body: PostSeriesUpdateIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _rl=rate_limit("series_write"),
):
    """Replace a post's full series membership list.

    R-8 (cross-ownership) mitigation:
    1. Verify current user owns the post.
    2. For each series_id, verify current user owns that series.
    Both checks must pass; any failure aborts the entire operation.
    """
    # 1. Post ownership check
    post_result = await db.execute(select(Post).where(Post.id == post_id))
    post = post_result.scalar_one_or_none()
    if not post:
        raise ApiError("POST_NOT_FOUND", "Post not found", http_status=404)
    if post.author_id != user.id and user.role != "admin":
        raise ApiError("POST_NOT_OWNER", "Post does not belong to you", http_status=403)

    # 2. Delete existing memberships for this post
    existing_result = await db.execute(
        select(PostSeriesMembership).where(PostSeriesMembership.post_id == post_id)
    )
    for m in existing_result.scalars().all():
        await db.delete(m)

    if not body.series_ids:
        await db.commit()
        return {"data": {"post_id": str(post_id), "series_count": 0}}

    # 3. Verify each series exists AND belongs to the current user (R-8 core)
    series_result = await db.execute(
        select(Series).where(Series.id.in_(body.series_ids))
    )
    series_map = {s.id: s for s in series_result.scalars().all()}

    for sid in body.series_ids:
        if sid not in series_map:
            raise ApiError("SERIES_NOT_FOUND", f"Series {sid} not found", http_status=404)
        await _check_series_owner(series_map[sid], user)  # R-8 mitigation

    # 4. Insert new memberships preserving caller's order
    for idx, sid in enumerate(body.series_ids):
        db.add(PostSeriesMembership(series_id=sid, post_id=post_id, order_index=idx))

    await db.commit()
    _log.info(
        "post.series.updated post_id=%s series_count=%d by=%s",
        post_id, len(body.series_ids), user.id,
    )
    return {"data": {"post_id": str(post_id), "series_count": len(body.series_ids)}}
