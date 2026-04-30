"""Draft endpoints — editor-draft-autosave PDCA.

Separate router for `/v1/posts/drafts` to keep draft authorization
(owner-only CRUD) cleanly isolated from public posts routes.

Architecture decision (design §2.1): split from create_post() because
publish-flow has scheduled_at/digital_art_check branching that doesn't
apply to drafts. Drafts always use status='draft', digital_art_check='not_required'.
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import delete as sql_delete
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import get_current_user
from app.core.errors import ApiError
from app.db.session import get_db
from app.models.post import MediaAsset, Post, ProductPost
from app.models.user import User
from app.schemas.draft import DraftUpsertBody

router = APIRouter(prefix="/posts/drafts", tags=["drafts"])

_DRAFT_LIMIT_PER_USER = 20  # NFR-4: 사용자당 draft 최대 개수


# ─── Helpers ────────────────────────────────────────────────────────────


async def _get_draft_or_404(
    db: AsyncSession, draft_id: UUID, user_id: UUID
) -> Post:
    """Fetch a draft owned by user_id. 404 (not 403) on owner mismatch
    to avoid draft-id enumeration attacks (design §2.8).
    """
    result = await db.execute(
        select(Post)
        .where(Post.id == draft_id, Post.status == "draft")
        .options(selectinload(Post.media), selectinload(Post.product))
    )
    post = result.scalar_one_or_none()
    if not post or post.author_id != user_id:
        raise ApiError("NOT_FOUND", "Draft not found", http_status=404)
    return post


def _serialize_draft(post: Post) -> dict:
    """Convert Post (status='draft') to DraftView-shaped dict."""
    return {
        "id": str(post.id),
        "type": post.type,
        "title": post.title,
        "content": post.content,
        "genre": post.genre,
        "tags": post.tags,
        "language": post.language,
        "media": [
            {
                "id": str(m.id),
                "type": m.type,
                "url": m.url,
                "thumbnail_url": m.thumbnail_url,
                "width": m.width,
                "height": m.height,
                "duration_sec": m.duration_sec,
                "size_bytes": m.size_bytes,
                "external_source": m.external_source,
                "external_id": m.external_id,
                "is_making_video": m.is_making_video,
                "order_index": m.order_index,
            }
            for m in sorted(post.media or [], key=lambda x: x.order_index)
        ],
        "product": (
            {
                "is_auction": post.product.is_auction,
                "is_buy_now": post.product.is_buy_now,
                "buy_now_price": (
                    str(post.product.buy_now_price)
                    if post.product.buy_now_price is not None
                    else None
                ),
                "currency": post.product.currency,
                "dimensions": post.product.dimensions,
                "medium": post.product.medium,
                "year": post.product.year,
                "is_sold": post.product.is_sold,
            }
            if post.product
            else None
        ),
        "scheduled_at": (
            post.scheduled_at.isoformat() if post.scheduled_at else None
        ),
        "location_name": post.location_name,
        "location_lat": post.location_lat,
        "location_lng": post.location_lng,
        "created_at": post.created_at.isoformat() if post.created_at else None,
        "updated_at": post.updated_at.isoformat() if post.updated_at else None,
    }


async def _replace_media(
    db: AsyncSession, post: Post, media_in: list
) -> None:
    """Replace all MediaAsset rows for a post (idempotent draft updates)."""
    await db.execute(
        sql_delete(MediaAsset).where(MediaAsset.post_id == post.id)
    )
    for idx, m in enumerate(media_in):
        db.add(
            MediaAsset(
                post_id=post.id,
                type=m.type,
                url=m.url,
                thumbnail_url=m.thumbnail_url,
                width=m.width,
                height=m.height,
                duration_sec=m.duration_sec,
                size_bytes=m.size_bytes,
                external_source=m.external_source,
                external_id=m.external_id,
                is_making_video=m.is_making_video,
                order_index=idx,
            )
        )


async def _upsert_product(
    db: AsyncSession, post: Post, product_in
) -> None:
    """Upsert ProductPost row (delete existing + insert)."""
    if post.product:
        await db.delete(post.product)
        await db.flush()
    if product_in is None:
        return
    db.add(
        ProductPost(
            post_id=post.id,
            is_auction=product_in.is_auction,
            is_buy_now=product_in.is_buy_now,
            buy_now_price=product_in.buy_now_price,
            currency=product_in.currency,
            dimensions=product_in.dimensions,
            medium=product_in.medium,
            year=product_in.year,
        )
    )


# ─── Endpoints ──────────────────────────────────────────────────────────


@router.post("")
async def upsert_draft(
    body: DraftUpsertBody,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create or update a draft.

    - body.draft_id present  → update existing (404 if not owned)
    - body.draft_id absent   → create new
        - if user already has >= 20 drafts, auto-delete oldest (design §2.6)

    Q-D1=B (Permissive): role check on type='product' applies to NEW drafts only.
    Updates of existing drafts are allowed even after role change. Publish-flow
    still enforces role at posts.py:206-210.
    """
    auto_deleted_id: UUID | None = None

    if body.draft_id:
        # Update path
        post = await _get_draft_or_404(db, body.draft_id, user.id)
        post.type = body.type
        post.title = body.title
        post.content = body.content
        post.genre = body.genre
        post.tags = body.tags
        post.language = body.language
        post.scheduled_at = body.scheduled_at
        post.location_name = body.location_name
        post.location_lat = body.location_lat
        post.location_lng = body.location_lng
        await _replace_media(db, post, body.media)
        await _upsert_product(db, post, body.product)
    else:
        # Create path — Q-D1=B: role check only on new product drafts
        if body.type == "product" and user.role not in ("artist", "admin"):
            raise ApiError(
                "FORBIDDEN",
                "Only artists can create product drafts",
                http_status=403,
            )

        # Enforce per-user draft limit (NFR-4)
        count_result = await db.execute(
            select(func.count(Post.id)).where(
                Post.author_id == user.id, Post.status == "draft"
            )
        )
        draft_count = int(count_result.scalar_one() or 0)
        if draft_count >= _DRAFT_LIMIT_PER_USER:
            # Auto-delete oldest (design §2.6 — silent UX over 409 error)
            oldest_result = await db.execute(
                select(Post)
                .where(Post.author_id == user.id, Post.status == "draft")
                .order_by(Post.updated_at.asc())
                .limit(1)
            )
            oldest = oldest_result.scalar_one_or_none()
            if oldest:
                auto_deleted_id = oldest.id
                await db.delete(oldest)
                await db.flush()

        post = Post(
            author_id=user.id,
            type=body.type,
            title=body.title,
            content=body.content,
            genre=body.genre,
            tags=body.tags,
            language=body.language,
            status="draft",
            digital_art_check="not_required",
            scheduled_at=body.scheduled_at,
            location_name=body.location_name,
            location_lat=body.location_lat,
            location_lng=body.location_lng,
        )
        db.add(post)
        await db.flush()

        # Insert media + product (no need to delete first — new post)
        for idx, m in enumerate(body.media):
            db.add(
                MediaAsset(
                    post_id=post.id,
                    type=m.type,
                    url=m.url,
                    thumbnail_url=m.thumbnail_url,
                    width=m.width,
                    height=m.height,
                    duration_sec=m.duration_sec,
                    size_bytes=m.size_bytes,
                    external_source=m.external_source,
                    external_id=m.external_id,
                    is_making_video=m.is_making_video,
                    order_index=idx,
                )
            )
        if body.product is not None:
            db.add(
                ProductPost(
                    post_id=post.id,
                    is_auction=body.product.is_auction,
                    is_buy_now=body.product.is_buy_now,
                    buy_now_price=body.product.buy_now_price,
                    currency=body.product.currency,
                    dimensions=body.product.dimensions,
                    medium=body.product.medium,
                    year=body.product.year,
                )
            )

    await db.commit()

    # Reload with relationships for serialization
    fresh = await _get_draft_or_404(db, post.id, user.id)
    response: dict = {"data": _serialize_draft(fresh)}
    if auto_deleted_id:
        response["meta"] = {"auto_deleted_draft_id": str(auto_deleted_id)}
    return response


@router.get("")
async def list_drafts(
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List drafts owned by the current user, ordered by updated_at desc."""
    total_result = await db.execute(
        select(func.count(Post.id)).where(
            Post.author_id == user.id, Post.status == "draft"
        )
    )
    total = int(total_result.scalar_one() or 0)

    result = await db.execute(
        select(Post)
        .where(Post.author_id == user.id, Post.status == "draft")
        .order_by(Post.updated_at.desc())
        .limit(limit)
        .offset(offset)
        .options(selectinload(Post.media), selectinload(Post.product))
    )
    drafts = result.scalars().all()

    return {
        "data": [_serialize_draft(d) for d in drafts],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/{draft_id}")
async def get_draft(
    draft_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Fetch a specific draft. 404 if not owned (no enumeration leak)."""
    post = await _get_draft_or_404(db, draft_id, user.id)
    return {"data": _serialize_draft(post)}


@router.delete("/{draft_id}")
async def delete_draft(
    draft_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Hard-delete a draft. MediaAsset cascade-deletes via Post relationship."""
    post = await _get_draft_or_404(db, draft_id, user.id)
    await db.delete(post)
    await db.commit()
    return {"data": {"deleted": True, "id": str(draft_id)}}
