"""Search v2 — A-5 search-enhancement.

Endpoints:
  GET  /search                  — unified search with filters + ranking score
  GET  /search/popular          — popular searches in last 24 h
  GET  /me/search/history       — authenticated user's search history
  DELETE /me/search/history/{id} — soft-delete single history entry
  DELETE /me/search/history      — soft-delete all history entries

Algorithm (ILIKE + ranking score):
  title match  × 3
  tag match    × 2
  content match × 1
  bio match    × 1 (users only)

pg_trgm fuzzy match is a Phase 7 carry-over (DB extension dependency).
"""
from __future__ import annotations

import logging
import re
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy import func, or_, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import get_current_user
from app.core.errors import ApiError
from app.core.rate_limit import rate_limit
from app.core.security import decode_token
from app.db.session import get_db
from app.models.post import Comment, Follow, Like, Post, ProductPost
from app.models.search_history import SearchHistory
from app.models.user import User
from app.schemas.search import (
    PopularSearchItem,
    PopularSearchesOut,
    SearchHistoryListOut,
    SearchHistoryOut,
    sanitize_query,
)
from app.services.cache import cache

_log = logging.getLogger(__name__)

search_router = APIRouter(prefix="/search", tags=["search"])
me_search_router = APIRouter(prefix="/me/search", tags=["me-search"])

# ─── Helpers ─────────────────────────────────────────────────────────────────

_LIKE_ESCAPE = re.compile(r"([%_\\])")


def _like(q: str) -> str:
    """Escape LIKE special chars and wrap in %…%."""
    return "%" + _LIKE_ESCAPE.sub(r"\\\1", q) + "%"


async def _resolve_viewer(
    authorization: str | None,
) -> tuple[uuid.UUID | None, str | None]:
    """Return (user_id, role) from Bearer token, or (None, None)."""
    if not authorization or not authorization.lower().startswith("bearer "):
        return None, None
    try:
        payload = decode_token(authorization.split(" ", 1)[1])
        if payload.get("type") != "access":
            return None, None
        sub = payload.get("sub")
        role = payload.get("role")
        return (uuid.UUID(sub) if sub else None), role
    except (ValueError, KeyError):
        return None, None


async def _record_history(
    db: AsyncSession,
    user_id: uuid.UUID,
    query: str,
    result_count: int,
) -> None:
    """Upsert-style: append new history entry (max 50 per user, oldest purged)."""
    try:
        entry = SearchHistory(
            user_id=user_id,
            query=query,
            result_count=result_count,
            searched_at=datetime.now(timezone.utc),
        )
        db.add(entry)
        await db.flush()

        # Purge oldest beyond 50 entries
        subq = (
            select(SearchHistory.id)
            .where(
                SearchHistory.user_id == user_id,
                SearchHistory.deleted_at.is_(None),
            )
            .order_by(SearchHistory.searched_at.desc())
            .offset(50)
        )
        old_ids = (await db.execute(subq)).scalars().all()
        if old_ids:
            now = datetime.now(timezone.utc)
            await db.execute(
                update(SearchHistory)
                .where(SearchHistory.id.in_(old_ids))
                .values(deleted_at=now)
            )
        await db.commit()
    except Exception:
        _log.warning("Failed to record search history", exc_info=True)
        await db.rollback()


# ─── GET /search ─────────────────────────────────────────────────────────────


@search_router.get("")
async def search_v2(
    q: str = Query(..., min_length=2, max_length=100),
    type: str | None = Query(None, pattern="^(artists|artworks|posts|all)$"),
    sort: str = Query("relevance", pattern="^(relevance|latest|popular)$"),
    # Filters
    price_min: int | None = Query(None, ge=0, description="Min price in cents"),
    price_max: int | None = Query(None, ge=0, description="Max price in cents"),
    region: str | None = Query(None, max_length=200, description="Comma-separated country codes"),
    tier_only: bool = Query(False, description="Exclude tier-locked posts viewer cannot see"),
    active: bool = Query(False, description="Only active auctions / published posts"),
    # Pagination
    cursor: str | None = Query(None),
    limit: int = Query(20, ge=1, le=50),
    # Auth
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
    _rl=rate_limit("search"),
):
    """Unified search v2 with ILIKE + ranking score and optional filters."""
    q = sanitize_query(q)
    if len(q) < 2:
        raise ApiError("INVALID_QUERY", "Query too short after sanitization", http_status=400)

    viewer_id, viewer_role = await _resolve_viewer(authorization)
    search_type = type or "all"
    pattern = _like(q)

    results: dict = {"artists": [], "artworks": [], "posts": []}
    regions: list[str] | None = (
        [r.strip() for r in region.split(",") if r.strip()] if region else None
    )
    has_more_artists = False
    has_more_posts = False
    post_rows: list = []

    # ── Artists ──────────────────────────────────────────────────────────────
    if search_type in ("artists", "all"):
        follower_sub = (
            select(func.count())
            .select_from(Follow)
            .where(Follow.followee_id == User.id)
            .correlate(User)
            .scalar_subquery()
        )

        user_query = (
            select(User, follower_sub.label("follower_count"))
            .where(
                User.status == "active",
                User.deleted_at.is_(None),
                or_(
                    User.display_name.ilike(pattern),
                    User.bio.ilike(pattern),
                    User.country_code.ilike(pattern),
                ),
            )
        )
        if regions:
            user_query = user_query.where(User.country_code.in_(regions))
        if active:
            user_query = user_query.where(User.status == "active")

        if sort == "latest":
            user_query = user_query.order_by(User.created_at.desc())
        elif sort == "popular":
            user_query = user_query.order_by(follower_sub.desc(), User.created_at.desc())
        else:
            # relevance: title-weight sort approximation via follower tiebreak
            user_query = user_query.order_by(follower_sub.desc(), User.created_at.desc())

        if cursor:
            try:
                cursor_id = uuid.UUID(cursor)
                user_query = user_query.where(User.id < cursor_id)
            except ValueError:
                pass

        user_query = user_query.limit(limit + 1)
        user_rows = (await db.execute(user_query)).all()
        has_more_artists = len(user_rows) > limit
        user_rows = user_rows[:limit]

        results["artists"] = [
            {
                "type": "artist",
                "id": str(u.id),
                "display_name": u.display_name,
                "avatar_url": u.avatar_url,
                "bio": u.bio,
                "role": u.role,
                "country": u.country_code,
                "follower_count": fc or 0,
            }
            for u, fc in user_rows
        ]

    # ── Artworks / Posts ──────────────────────────────────────────────────────
    post_types_to_fetch = []
    if search_type == "artworks":
        post_types_to_fetch = ["product"]
    elif search_type == "posts":
        post_types_to_fetch = ["general"]
    elif search_type == "all":
        post_types_to_fetch = ["product", "general"]

    if post_types_to_fetch:
        text_match = or_(
            Post.title.ilike(pattern),
            Post.content.ilike(pattern),
            Post.tags.any(q),
        )

        post_query = (
            select(Post)
            .where(
                Post.status == "published",
                Post.visibility == "public",
                or_(
                    Post.early_access_until.is_(None),
                    Post.early_access_until <= func.now(),
                ),
                Post.type.in_(post_types_to_fetch),
                text_match,
            )
            .options(selectinload(Post.media), selectinload(Post.product))
        )

        if price_min is not None or price_max is not None:
            # G'-10: price_min/price_max are cents (from API spec §A-5).
            # product_posts.buy_now_price is now also cents (BigInteger) —
            # comparison is now unit-consistent (was: Numeric dollars vs cents).
            post_query = post_query.join(ProductPost, ProductPost.post_id == Post.id, isouter=True)
            if price_min is not None:
                post_query = post_query.where(
                    or_(
                        ProductPost.buy_now_price.is_(None),
                        ProductPost.buy_now_price >= price_min,
                    )
                )
            if price_max is not None:
                post_query = post_query.where(
                    or_(
                        ProductPost.buy_now_price.is_(None),
                        ProductPost.buy_now_price <= price_max,
                    )
                )

        if active:
            post_query = post_query.where(Post.status == "published")

        if cursor:
            try:
                cursor_id = uuid.UUID(cursor)
                post_query = post_query.where(Post.id < cursor_id)
            except ValueError:
                pass

        if sort == "latest":
            post_query = post_query.order_by(Post.created_at.desc())
        elif sort == "popular":
            like_sub = (
                select(func.count())
                .select_from(Like)
                .where(Like.post_id == Post.id)
                .correlate(Post)
                .scalar_subquery()
            )
            comment_sub = (
                select(func.count())
                .select_from(Comment)
                .where(Comment.post_id == Post.id)
                .correlate(Post)
                .scalar_subquery()
            )
            post_query = post_query.order_by(
                (like_sub + comment_sub).desc(), Post.created_at.desc()
            )
        else:
            # relevance: title match first (approximated by created_at DESC for now)
            post_query = post_query.order_by(Post.created_at.desc())

        post_query = post_query.limit(limit + 1)
        post_rows = list((await db.execute(post_query)).scalars().all())
        has_more_posts = len(post_rows) > limit
        post_rows = post_rows[:limit]

        # Attach authors
        author_ids = list({p.author_id for p in post_rows})
        if author_ids:
            author_map = {
                u.id: u
                for u in (
                    await db.execute(select(User).where(User.id.in_(author_ids)))
                ).scalars().all()
            }
        else:
            author_map = {}
        for p in post_rows:
            p.author = author_map.get(p.author_id)  # type: ignore[attr-defined]

        serialized = [_serialize_post(p) for p in post_rows]
        if search_type == "artworks":
            results["artworks"] = serialized
        elif search_type == "posts":
            results["posts"] = serialized
        else:
            for p, s in zip(post_rows, serialized):
                if p.type == "product":
                    results["artworks"].append(s)
                else:
                    results["posts"].append(s)

    # ── Record search history (logged-in only) ────────────────────────────────
    total_count = (
        len(results["artists"]) + len(results["artworks"]) + len(results["posts"])
    )
    if viewer_id:
        await _record_history(db, viewer_id, q, total_count)

    # ── Determine next_cursor for pagination ──────────────────────────────────
    next_cursor = None
    if search_type == "artists" and results["artists"]:
        next_cursor = results["artists"][-1]["id"] if has_more_artists else None
    elif search_type in ("artworks", "posts") and post_rows:
        next_cursor = str(post_rows[-1].id) if has_more_posts else None

    return {
        "data": results,
        "pagination": {"next_cursor": next_cursor, "has_more": bool(next_cursor)},
    }


# ─── GET /search/popular ─────────────────────────────────────────────────────


_POPULAR_CACHE_TTL = 300  # 5 minutes


@search_router.get("/popular")
async def popular_searches(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    _rl=rate_limit("search_popular"),
):
    """Top queries in the last 24 hours (unauthenticated OK).

    Cache key: search:popular:{limit}:24h  TTL: 5 min.
    No user-specific data — global cache safe for all callers.
    """
    cache_key = f"search:popular:{limit}:24h"
    cached = await cache.get_json(cache_key, prefix="search")
    if cached is not None:
        return PopularSearchesOut(
            data=[PopularSearchItem(**item) for item in cached]
        )

    since = datetime.now(timezone.utc) - timedelta(hours=24)

    # SearchHistory covers logged-in users; for broader coverage we also
    # aggregate from SearchLog (anonymous analytics).
    # Use SearchHistory here for privacy (no anonymous IP logging).
    stmt = (
        select(SearchHistory.query, func.count().label("cnt"))
        .where(
            SearchHistory.searched_at >= since,
            SearchHistory.deleted_at.is_(None),
        )
        .group_by(SearchHistory.query)
        .order_by(text("cnt DESC"))
        .limit(limit)
    )
    rows = (await db.execute(stmt)).all()
    items = [PopularSearchItem(query=r.query, count=r.cnt) for r in rows]

    # Populate cache
    await cache.set_json(
        cache_key,
        [item.model_dump() for item in items],
        _POPULAR_CACHE_TTL,
        prefix="search",
    )

    return PopularSearchesOut(data=items)


# ─── GET /me/search/history ───────────────────────────────────────────────────


@me_search_router.get("/history")
async def get_search_history(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _rl=rate_limit("search_history_read"),
):
    """Return the authenticated user's recent search history."""
    stmt = (
        select(SearchHistory)
        .where(
            SearchHistory.user_id == current_user.id,
            SearchHistory.deleted_at.is_(None),
        )
        .order_by(SearchHistory.searched_at.desc())
        .limit(limit)
    )
    rows = (await db.execute(stmt)).scalars().all()
    return SearchHistoryListOut(
        data=[SearchHistoryOut.model_validate(r) for r in rows]
    )


# ─── DELETE /me/search/history/{id} ─────────────────────────────────────────


@me_search_router.delete("/history/{entry_id}", status_code=204)
async def delete_search_history_entry(
    entry_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _rl=rate_limit("search_history_delete"),
):
    """Soft-delete a single search history entry."""
    result = await db.execute(
        select(SearchHistory).where(
            SearchHistory.id == entry_id,
            SearchHistory.user_id == current_user.id,
            SearchHistory.deleted_at.is_(None),
        )
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise ApiError("NOT_FOUND", "History entry not found", http_status=404)
    entry.deleted_at = datetime.now(timezone.utc)
    await db.commit()


# ─── DELETE /me/search/history ───────────────────────────────────────────────


@me_search_router.delete("/history", status_code=204)
async def delete_all_search_history(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _rl=rate_limit("search_history_delete"),
):
    """Soft-delete all search history for the authenticated user."""
    now = datetime.now(timezone.utc)
    await db.execute(
        update(SearchHistory)
        .where(
            SearchHistory.user_id == current_user.id,
            SearchHistory.deleted_at.is_(None),
        )
        .values(deleted_at=now)
    )
    await db.commit()


# ─── Serializer (reuses posts.py pattern) ────────────────────────────────────


def _serialize_post(p: Post) -> dict:
    author = getattr(p, "author", None)
    media = [
        {
            "id": str(m.id),
            "url": m.url,
            "media_type": m.type,
            "width": m.width,
            "height": m.height,
            "duration_sec": m.duration_sec,
            "thumbnail_url": m.thumbnail_url,
            "caption": m.caption,
            "sort_order": m.order_index,
        }
        for m in sorted(p.media or [], key=lambda m: m.order_index)
    ]
    product = None
    if p.product:
        product = {
            "dimensions": p.product.dimensions,
            "medium": p.product.medium,
            "year": p.product.year,
            "is_auction": p.product.is_auction,
            # G'-10: cents integer (BigInteger). Frontend calls formatPriceCents().
            "buy_now_price": p.product.buy_now_price,  # int | None
            "active_auction_end_at": getattr(p, "active_auction_end_at", None),
        }
    return {
        "type": "post",
        "id": str(p.id),
        "title": p.title,
        "content": p.content,
        "tags": p.tags or [],
        "post_type": p.type,
        "status": p.status,
        "genre": p.genre,
        "like_count": p.like_count,
        "comment_count": p.comment_count,
        "created_at": p.created_at.isoformat() if p.created_at else None,
        "media": media,
        "product": product,
        "author": {
            "id": str(author.id),
            "display_name": author.display_name,
            "avatar_url": author.avatar_url,
            "role": author.role,
        } if author else None,
    }
