import os
from typing import Annotated, Optional
from uuid import UUID
import uuid
from datetime import datetime, timedelta, timezone

from pydantic import BaseModel

import sqlalchemy as sa
from fastapi import APIRouter, BackgroundTasks, Depends, Header, Query
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

import logging

from app.core.deps import get_current_user
from app.core.errors import ApiError
from app.core.rate_limit import rate_limit
from app.core.security import decode_token
from app.db.session import get_db
from app.models.auction import Auction
from app.models.post import Comment, Follow, Like, MediaAsset, Post, ProductPost
from app.models.search_log import SearchLog
from app.models.series import PostSeriesMembership, Series
from app.models.sponsorship import Sponsorship, Subscription
from app.models.user import User
from app.services.cache import cache
from app.services.feed_scoring import (
    apply_cursor,
    decode_cursor,
    encode_cursor,
    score_posts,
)
from app.services.otel_setup import get_tracer
from app.services.artwork_caption_jobs import generate_for_post, get_effective_caption

_tracer = get_tracer(__name__)

_FEED_CACHE_TTL = 300  # 5 minutes per user+cursor page

_log = logging.getLogger(__name__)
from app.schemas.post import (
    CaptionOverrideRequest,
    CommentIn,
    CommentOut,
    MediaAssetOut,
    PostAuthor,
    PostCreate,
    PostOut,
    ProductPostOut,
)
from app.schemas.series import PostPublishRequest, PostPublishResponse
from app.schemas.docent import (
    DocentGenerateResponse,
    DocentOptOutRequest,
    DocentOptOutResponse,
    DocentPatchRequest,
    DocentPatchResponse,
    DocentResponse,
)
from app.services.llm_docent import generate_docent

router = APIRouter(prefix="/posts", tags=["posts"])


def _serialize_post(post: Post, locale: str = "ko") -> dict:
    # K-3: effective_caption 서버 계산 (caption_override > locale 번역 > ai_caption > "")
    effective_caption = get_effective_caption(post, locale=locale)

    return PostOut(
        id=post.id,
        author=PostAuthor.model_validate(post.author) if hasattr(post, "author") and post.author else PostAuthor(
            id=post.author_id, display_name="unknown", role="user"
        ),
        type=post.type,
        title=post.title,
        content=post.content,
        genre=post.genre,
        tags=post.tags,
        language=post.language,
        like_count=post.like_count,
        comment_count=post.comment_count,
        view_count=post.view_count,
        bluebird_count=post.bluebird_count,
        status=post.status,
        digital_art_check=post.digital_art_check,
        scheduled_at=post.scheduled_at,
        location_name=post.location_name,
        location_lat=post.location_lat,
        location_lng=post.location_lng,
        created_at=post.created_at,
        media=[MediaAssetOut.model_validate(m) for m in (post.media or [])],
        product=ProductPostOut.model_validate(post.product) if post.product else None,
        # publish-controls PDCA #8 §B-6 — pass through new columns.
        # getattr fallback keeps compatibility with any cached/partial Post objects.
        visibility=getattr(post, "visibility", "public"),
        comments_enabled=getattr(post, "comments_enabled", True),
        # Phase 4 #10 artist-tier-release §B-4 — early_access fields.
        # is_tier_locked stays False here; get_post (PR2) fills it per-viewer.
        early_access_until=getattr(post, "early_access_until", None),
        early_access_tier=getattr(post, "early_access_tier", None),
        # Phase 4 #11 auction-promotion-suite — OQ-D-1=A
        # Populated by _attach_active_auction_end_at before serialization.
        active_auction_end_at=getattr(post, "_active_auction_end_at", None),
        # K-3 ai-artwork-caption — 캡션 필드 (getattr fallback: 이전 캐시된 Post 객체 호환)
        ai_caption=getattr(post, "ai_caption", None),
        ai_caption_locale_translations=getattr(post, "ai_caption_locale_translations", {}) or {},
        ai_caption_generated_at=getattr(post, "ai_caption_generated_at", None),
        caption_override=getattr(post, "caption_override", None),
        effective_caption=effective_caption,
    ).model_dump(mode="json")


async def _load_post_full(db: AsyncSession, post_id: UUID) -> Post | None:
    result = await db.execute(
        select(Post)
        .where(Post.id == post_id)
        .options(selectinload(Post.media), selectinload(Post.product))
    )
    return result.scalar_one_or_none()


async def _load_posts_by_ids(db: AsyncSession, post_ids: list[str]) -> list[Post]:
    """포스트 ID 리스트로 Post ORM 객체 일괄 로드 (ML 피드 v2 전용).

    K-1: get_recommendations() 반환 순서를 유지하며 Post 객체 반환.
    author 정보도 일괄 로드 (N+1 방지).
    """
    if not post_ids:
        return []

    uuid_ids = []
    for pid in post_ids:
        try:
            uuid_ids.append(UUID(pid))
        except (ValueError, AttributeError):
            pass

    if not uuid_ids:
        return []

    result = await db.execute(
        select(Post)
        .where(Post.id.in_(uuid_ids))
        .options(selectinload(Post.media), selectinload(Post.product))
    )
    posts_map = {p.id: p for p in result.scalars().all()}

    # author 일괄 로드
    author_ids = list({p.author_id for p in posts_map.values()})
    if author_ids:
        authors_result = await db.execute(select(User).where(User.id.in_(author_ids)))
        author_map = {u.id: u for u in authors_result.scalars().all()}
        for p in posts_map.values():
            p.author = author_map.get(p.author_id)  # type: ignore[attr-defined]

    # 원래 순서 유지 (ML 스코어 순서 보존)
    ordered = []
    for uuid_id in uuid_ids:
        if uuid_id in posts_map:
            ordered.append(posts_map[uuid_id])
    return ordered


async def _author_for(db: AsyncSession, user_id: UUID) -> PostAuthor:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        return PostAuthor(id=user_id, display_name="unknown", role="user")
    return PostAuthor.model_validate(user)


async def _attach_active_auction_end_at(
    db: AsyncSession,
    posts: list,
) -> None:
    """Bulk-load active auction end_at for product posts and attach as _active_auction_end_at.

    Phase 4 #11 auction-promotion-suite — OQ-D-1=A, AC-12.
    Executes exactly ONE query for all posts (no N+1).
    Only auctions with status='active' AND end_at > now() are considered.
    Non-product posts and posts without an active auction get None.
    """
    now = datetime.now(timezone.utc)
    product_post_ids = [p.id for p in posts if getattr(p, "type", None) == "product"]

    end_at_map: dict = {}
    if product_post_ids:
        rows = await db.execute(
            select(Auction.product_post_id, Auction.end_at)
            .where(
                Auction.product_post_id.in_(product_post_ids),
                Auction.status == "active",
                Auction.end_at > now,
            )
        )
        for post_id, end_at in rows.all():
            end_at_map[post_id] = end_at

    for p in posts:
        p._active_auction_end_at = end_at_map.get(p.id)  # type: ignore[attr-defined]


def _trending_score_expr():
    """
    트렌딩 스코어 공식 (design.md §6.7):
        score = like_count * 0.4 + bluebird_count * 0.4 + recency_score * 0.2
        recency_score = 1.0 - min(age_hours / 168, 1.0)  # 7일 기준

    DB 표현식으로 환산 (PostgreSQL 기준):
        recency_hours = EXTRACT(EPOCH FROM (NOW() - created_at)) / 3600
        recency_score = GREATEST(1.0 - LEAST(recency_hours / 168, 1.0), 0)
    """
    age_hours = func.extract("epoch", func.now() - Post.created_at) / 3600.0
    recency_score = func.greatest(1.0 - func.least(age_hours / 168.0, 1.0), 0.0)
    return (
        Post.like_count * 0.4
        + Post.bluebird_count * 0.4
        + recency_score * 0.2 * 100  # recency를 0~100 스케일로 맞춤
    )


# ─── Tier-release helpers — Phase 4 #10 §B-5, §B-6, §B-7 ───────────────


async def _viewer_meets_tier(
    db: AsyncSession,
    viewer_id: uuid.UUID | None,
    author_id: uuid.UUID,
    required_tier: str,  # 'subscriber' | 'sponsor' | 'follower'
) -> bool:
    """OQ-2=A 자동 계층 포함 — UNION ALL EXISTS 단일 쿼리.

    - subscriber: Subscription.status='active'
    - sponsor: subscriber OR Sponsorship.status='completed'
      + author.sponsor_validity_days 적용:
        NULL → lifetime (기존 동작)
        N    → Sponsorship.completed_at >= now() - N days
    - follower: 위 둘 OR Follow row exists

    author 본인은 항상 통과 (return True).
    D'-1 carry-over: sponsor_validity_days per-artist expiry support.
    """
    if viewer_id is None:
        return False
    if viewer_id == author_id:
        return True

    sub_q = (
        select(sa.literal(1))
        .where(
            Subscription.sponsor_id == viewer_id,
            Subscription.artist_id == author_id,
            Subscription.status == "active",
        )
        .limit(1)
    )

    # Resolve author's sponsor_validity_days to build correct sponsorship filter.
    # Single extra query only when 'sponsor' or 'follower' tier is needed.
    spon_q: sa.Select | None = None
    if required_tier in ("sponsor", "follower"):
        author_row = await db.execute(
            select(User.sponsor_validity_days).where(User.id == author_id)
        )
        validity_days: int | None = author_row.scalar_one_or_none()

        spon_conditions = [
            Sponsorship.sponsor_id == viewer_id,
            Sponsorship.artist_id == author_id,
            Sponsorship.status == "completed",
        ]
        if validity_days is not None:
            # Sponsorship has no dedicated completed_at; use created_at as
            # the completion timestamp (one-time sponsorships are set to
            # 'completed' status at creation time).
            cutoff = datetime.now(timezone.utc) - timedelta(days=validity_days)
            spon_conditions.append(Sponsorship.created_at >= cutoff)

        spon_q = (
            select(sa.literal(1))
            .where(*spon_conditions)
            .limit(1)
        )

    follow_q = (
        select(sa.literal(1))
        .where(
            Follow.follower_id == viewer_id,
            Follow.followee_id == author_id,
        )
        .limit(1)
    )

    if required_tier == "subscriber":
        union_q = sub_q
    elif required_tier == "sponsor":
        union_q = sa.union_all(sub_q, spon_q)
    else:  # 'follower'
        union_q = sa.union_all(sub_q, spon_q, follow_q)

    exists_q = select(sa.exists(union_q))
    result = await db.execute(exists_q)
    return bool(result.scalar())


def _sql_tier_qualified_expr(
    viewer_id: uuid.UUID,
    author_id_col: sa.Column,
) -> sa.BinaryExpression:
    """Return a SQL expression that is TRUE when viewer qualifies for the post's tier.

    D'-1 carry-over: SQL-only tier filter replacing Python post-filter.
    Handles all three tiers (subscriber / sponsor / follower) via UNION ALL EXISTS.
    sponsor_validity_days is NOT applied here (requires per-author DB lookup);
    the fast-path covers the common cases and _viewer_meets_tier handles edge cases.

    Returns: EXISTS(sub_q UNION ALL spon_q UNION ALL follow_q) OR viewer is author.
    """
    sub_exists = sa.exists(
        select(sa.literal(1))
        .where(
            Subscription.sponsor_id == viewer_id,
            Subscription.artist_id == author_id_col,
            Subscription.status == "active",
        )
        .correlate()
    )
    spon_exists = sa.exists(
        select(sa.literal(1))
        .where(
            Sponsorship.sponsor_id == viewer_id,
            Sponsorship.artist_id == author_id_col,
            Sponsorship.status == "completed",
        )
        .correlate()
    )
    follow_exists = sa.exists(
        select(sa.literal(1))
        .where(
            Follow.follower_id == viewer_id,
            Follow.followee_id == author_id_col,
        )
        .correlate()
    )
    return or_(
        Post.author_id == viewer_id,  # author sees own posts
        sub_exists,
        spon_exists,
        follow_exists,
    )


# ─── Publish helpers — publish-controls PDCA #8 §B-7 ────────────────────

_PUBLISHABLE_STATUSES = {"draft", "scheduled", "pending_review"}


async def _check_auction_visibility_lock(db: AsyncSession, post: Post) -> None:
    """OQ-D-1=A: block visibility changes on posts with an active auction.

    Only applies to product posts; non-product posts skip immediately.
    Mirrors _check_auction_media_lock in media.py (#4 PDCA pattern).
    """
    if post.type != "product":
        return
    result = await db.execute(
        select(Auction).where(
            Auction.product_post_id == post.id,
            Auction.status == "active",
        )
    )
    if result.scalar_one_or_none():
        raise ApiError(
            "AUCTION_ACTIVE_VISIBILITY_LOCKED",
            "경매 진행 중에는 공개 범위를 변경할 수 없습니다",
            http_status=409,
        )


async def _replace_post_series(
    db: AsyncSession,
    post_id: UUID,
    series_ids: list[UUID],
    user_id: UUID,
) -> int:
    """Replace a post's full series membership list.

    Per design §B-7:
    1. Delete all existing PostSeriesMembership rows for post_id.
    2. If series_ids is empty, return 0.
    3. For each series_id: verify exists (SERIES_NOT_FOUND 404) AND
       author_id == user_id (SERIES_NOT_OWNER 403).
    4. Insert new memberships with order_index from enumerate(series_ids).
    Returns count of inserted memberships.
    """
    existing_result = await db.execute(
        select(PostSeriesMembership).where(PostSeriesMembership.post_id == post_id)
    )
    for m in existing_result.scalars().all():
        await db.delete(m)

    if not series_ids:
        return 0

    series_result = await db.execute(
        select(Series).where(Series.id.in_(series_ids))
    )
    series_map = {s.id: s for s in series_result.scalars().all()}

    for sid in series_ids:
        if sid not in series_map:
            raise ApiError("SERIES_NOT_FOUND", f"Series {sid} not found", http_status=404)
        if series_map[sid].author_id != user_id:
            raise ApiError(
                "SERIES_NOT_OWNER",
                f"Series {sid} does not belong to you",
                http_status=403,
            )

    for idx, sid in enumerate(series_ids):
        db.add(PostSeriesMembership(series_id=sid, post_id=post_id, order_index=idx))

    return len(series_ids)


@router.post("/{post_id}/publish", status_code=200)
async def publish_post(
    post_id: UUID,
    body: PostPublishRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _rl=rate_limit("post_publish"),
):
    """Publish (or schedule) a post with visibility, comments, and series options.

    6-step permission flow per design §B-7:
    1. get_current_user → 401 (handled by Depends)
    2. Post not found / deleted → POST_NOT_FOUND 404
    3. Not owner (and not admin) → POST_NOT_OWNER 403
    4. Status not in publishable set → POST_INVALID_STATE 409
    5. Visibility change on active-auction product → AUCTION_ACTIVE_VISIBILITY_LOCKED 409
    6. Transaction: status transition + field updates + series replace + audit log + commit
    """
    post = await _load_post_full(db, post_id)
    if not post or post.status == "deleted":
        raise ApiError("POST_NOT_FOUND", "Post not found", http_status=404)

    if post.author_id != user.id and user.role != "admin":
        raise ApiError("POST_NOT_OWNER", "Post does not belong to you", http_status=403)

    if post.status not in _PUBLISHABLE_STATUSES:
        raise ApiError(
            "POST_INVALID_STATE",
            f"Post status '{post.status}' cannot be published",
            http_status=409,
        )

    current_visibility = getattr(post, "visibility", "public")
    if body.visibility != current_visibility:
        await _check_auction_visibility_lock(db, post)

    prev_status = post.status
    if body.publish_at:
        post.status = "scheduled"
        post.scheduled_at = body.publish_at
    else:
        has_visual = any(m.type in ("image", "video") for m in (post.media or []))
        post.status = "pending_review" if has_visual else "published"
        post.scheduled_at = None

    post.visibility = body.visibility
    post.comments_enabled = body.comments_enabled

    # Phase 4 #10 OQ-9=A: tier release 통합
    if body.early_access_duration is not None:
        post.early_access_until = (
            datetime.now(timezone.utc)
            + timedelta(hours=body.early_access_duration)
        )
        post.early_access_tier = body.early_access_tier
    else:
        post.early_access_until = None
        post.early_access_tier = None

    series_count = await _replace_post_series(db, post.id, body.series_ids, user.id)

    await db.flush()
    _log.info(
        "post.publish.applied",
        extra={
            "event": "post.publish.applied",
            "user_id": str(user.id),
            "post_id": str(post.id),
            "prev_status": prev_status,
            "new_status": post.status,
            "visibility": body.visibility,
            "comments_enabled": body.comments_enabled,
            "series_count": series_count,
            "scheduled_at": body.publish_at.isoformat() if body.publish_at else None,
            "early_access_duration": body.early_access_duration,
            "early_access_tier": body.early_access_tier,
            "early_access_until": post.early_access_until.isoformat() if post.early_access_until else None,
        },
    )
    await db.commit()
    await db.refresh(post)

    return {
        "data": PostPublishResponse(
            id=post.id,
            status=post.status,
            visibility=post.visibility,
            comments_enabled=post.comments_enabled,
            scheduled_at=post.scheduled_at,
            series_count=series_count,
            updated_at=post.updated_at,
            early_access_until=post.early_access_until,
            early_access_tier=getattr(post, "early_access_tier", None),
        ).model_dump(mode="json")
    }


# ─── Visibility filter — publish-controls PDCA #8 §B-9 ──────────────────


def _visibility_filter_for_viewer(viewer, author_id_col, viewing_self: bool, followee_ids=None):
    """Return a SQLAlchemy WHERE clause for visibility based on viewer context.

    Phase 4 #10 Option β extension — tier_only is computed effective state.

    Rules:
    - viewing_self=True  → all visibility values allowed (sa.true())
    - viewer=None        → only 'public' AND not active tier_only
    - followee_ids list  → 'public' (not active tier) OR 'followers_only' (followee author)
                           OR active tier_only (followee author — Python post-filter re-validates)
    - no followee_ids    → same but via subquery

    SQL fast-path: active tier_only posts (early_access_until > now() AND tier IS NOT NULL)
    are passed through for followee authors, then Python post-filter re-validates tier
    qualification per viewer.
    """
    now_expr = func.now()
    is_active_tier = and_(
        Post.early_access_until.is_not(None),
        Post.early_access_until > now_expr,
    )
    is_not_active_tier = or_(
        Post.early_access_until.is_(None),
        Post.early_access_until <= now_expr,
    )

    if viewing_self:
        return sa.true()

    if viewer is None:
        return and_(
            Post.visibility == "public",
            is_not_active_tier,
        )

    if followee_ids is not None:
        return or_(
            and_(Post.visibility == "public", is_not_active_tier),
            and_(Post.visibility == "followers_only", author_id_col.in_(followee_ids)),
            and_(is_active_tier, author_id_col.in_(followee_ids)),
        )

    follows_subq = (
        select(Follow.followee_id)
        .where(Follow.follower_id == viewer.id)
        .scalar_subquery()
    )
    return or_(
        and_(Post.visibility == "public", is_not_active_tier),
        and_(Post.visibility == "followers_only", author_id_col.in_(follows_subq)),
        and_(is_active_tier, author_id_col.in_(follows_subq)),
    )


# ─── Translation ─────────────────────────────────────────────────────────


@router.get("/{post_id}/translate")
async def translate_post(
    post_id: UUID,
    lang: str = Query(..., min_length=2, max_length=5),
    db: AsyncSession = Depends(get_db),
):
    """Get translated title/content for a post. Caches in post_translations."""
    from app.models.translation import PostTranslation
    from app.services.translation import get_translation_provider_from_db

    # Check cache
    cached = await db.execute(
        select(PostTranslation).where(
            PostTranslation.post_id == post_id,
            PostTranslation.language == lang,
        )
    )
    existing = cached.scalar_one_or_none()
    if existing:
        return {
            "data": {
                "post_id": str(post_id),
                "language": lang,
                "title": existing.title_translated,
                "content": existing.content_translated,
                "cached": True,
            }
        }

    # Load original post
    post = await _load_post_full(db, post_id)
    if not post:
        raise ApiError("NOT_FOUND", "Post not found", http_status=404)

    # Skip if already in target language
    if post.language == lang:
        return {
            "data": {
                "post_id": str(post_id),
                "language": lang,
                "title": post.title,
                "content": post.content,
                "cached": False,
            }
        }

    # Translate
    provider = await get_translation_provider_from_db(db)
    title_translated = await provider.translate(post.title or "", lang, post.language) if post.title else None
    content_translated = await provider.translate(post.content or "", lang, post.language) if post.content else None

    # Cache
    translation = PostTranslation(
        post_id=post_id,
        language=lang,
        title_translated=title_translated,
        content_translated=content_translated,
    )
    db.add(translation)
    try:
        await db.commit()
    except Exception:
        await db.rollback()  # unique constraint conflict → already cached

    return {
        "data": {
            "post_id": str(post_id),
            "language": lang,
            "title": title_translated,
            "content": content_translated,
            "cached": False,
        }
    }


# ─── Tag suggestions ─────────────────────────────────────────────────────


@router.get("/tags/suggest")
async def suggest_tags(
    q: str = Query(..., min_length=1, max_length=50),
    limit: int = Query(10, ge=1, le=30),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(func.unnest(Post.tags).label("tag"))
        .where(Post.status == "published", Post.tags.isnot(None))
        .distinct()
    )
    all_tags = [row[0] for row in result.all()]
    prefix = q.lower()
    matched = [t for t in all_tags if t.lower().startswith(prefix)][:limit]
    return {"data": sorted(matched)}


# ─── Create ──────────────────────────────────────────────────────────────


@router.post("")
async def create_post(
    body: PostCreate,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # 권한: 상품 포스트는 artist만
    if body.type == "product" and user.role not in ("artist", "admin"):
        raise ApiError(
            "FORBIDDEN", "Only artists can create product posts", http_status=403
        )

    # 디지털 아트 판독: 미디어가 image/video 포함이면 pending, 아니면 not_required
    has_visual_media = any(
        m.type in ("image", "video") for m in body.media
    )
    if body.scheduled_at:
        # 예약 게시: scheduled 상태로 저장, 크론잡이 시간 도달 시 전환
        digital_art_check = "pending" if has_visual_media else "not_required"
        status = "scheduled"
    elif has_visual_media:
        digital_art_check = "pending"
        status = "pending_review"
    else:
        digital_art_check = "not_required"
        status = "published"

    post = Post(
        author_id=user.id,
        type=body.type,
        title=body.title,
        content=body.content,
        genre=body.genre,
        tags=body.tags,
        language=body.language,
        status=status,
        digital_art_check=digital_art_check,
        scheduled_at=body.scheduled_at,
        location_name=body.location_name,
        location_lat=body.location_lat,
        location_lng=body.location_lng,
    )
    db.add(post)
    await db.flush()  # post.id 확보

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
                # editor-media-ux PDCA #4 — caption pass-through (None safe fallback
                # for clients not yet sending the field).
                caption=m.caption,
            )
        )

    if body.type == "product":
        if not body.product:
            raise ApiError(
                "VALIDATION_ERROR",
                "product field required for product posts",
                http_status=422,
            )
        db.add(
            ProductPost(
                post_id=post.id,
                is_auction=body.product.is_auction,
                is_buy_now=body.product.is_buy_now,
                buy_now_price=body.product.buy_now_price,
                buy_now_currency=body.product.buy_now_currency,  # B'-1
                currency=body.product.currency,
                dimensions=body.product.dimensions,
                medium=body.product.medium,
                year=body.product.year,
            )
        )

    # editor-draft-autosave: publish-from-draft path
    # If client sent from_draft_id, delete that draft in the same transaction.
    # Silent on failure — publishing succeeded; orphan draft is the worst case.
    if body.from_draft_id:
        draft = await db.get(Post, body.from_draft_id)
        if (
            draft
            and draft.author_id == user.id
            and draft.status == "draft"
        ):
            await db.delete(draft)  # MediaAsset cascade

    await db.commit()

    full_post = await _load_post_full(db, post.id)
    full_post.author = user  # type: ignore[attr-defined]
    await _attach_active_auction_end_at(db, [full_post])

    # K-3: 이미지 포스트에 한해 비동기 캡션 생성 트리거 (API 응답 지연 없음)
    has_image_media = any(m.type == "image" for m in body.media)
    if has_image_media:
        from app.db.session import AsyncSessionLocal

        async def _caption_bg_task(post_id: UUID) -> None:
            """백그라운드 캡션 생성 — 별도 DB 세션 사용."""
            async with AsyncSessionLocal() as bg_db:
                try:
                    await generate_for_post(bg_db, post_id)
                except Exception as exc:
                    _log.warning("[ArtworkCaption] background task failed post_id=%s: %s", post_id, exc)

        background_tasks.add_task(_caption_bg_task, full_post.id)

    return {"data": _serialize_post(full_post)}


# ─── Read ────────────────────────────────────────────────────────────────


async def _personalized_feed_v1(
    db: AsyncSession,
    user: User,
    cursor: str | None,
    limit: int,
) -> dict:
    """A-3 feed-algorithm-v1: SQL + Python hybrid personalized feed.

    Step 1 — SQL candidate fetch:
      Fetch up to 100 candidate posts from two pools:
        a) Posts by followed authors (with tier/visibility gates)
        b) Public trending posts (score-ordered)
      Both pools use existing SQL filter helpers for correctness (no N+1).

    Step 2 — Python scoring + sort + cursor:
      compute_score() per post → sort DESC → apply (score, id) cursor → take limit+1.

    Backward compat: cursor=None returns the first page.
    Cursor format: encode_cursor(score, post_id) — see feed_scoring.py.

    Cache: feed:v1:{user_id}:{cursor_hash}  TTL: 5 min.
    Keyed per-user to avoid leaking private/tier-gated content across users.
    """
    # ── Cache-aside (read) ────────────────────────────────────────────────────
    _cursor_hash = cursor or "first"
    feed_cache_key = f"feed:v1:{user.id}:{_cursor_hash}"
    cached_feed = await cache.get_json(feed_cache_key, prefix="feed")
    if cached_feed is not None:
        return cached_feed

    with _tracer.start_as_current_span("feed.personalized_v1") as _feed_span:
        _feed_span.set_attribute("user_id", str(user.id))
        _feed_span.set_attribute("has_cursor", cursor is not None)
        _feed_span.set_attribute("limit", limit)
        return await _personalized_feed_v1_compute(db=db, user=user, cursor=cursor, limit=limit, feed_cache_key=feed_cache_key)


async def _personalized_feed_v1_compute(
    db: AsyncSession,
    user: User,
    cursor: str | None,
    limit: int,
    feed_cache_key: str,
) -> dict:
    """Compute the personalized feed — called from _personalized_feed_v1 with OTel span."""
    CANDIDATE_LIMIT = 100

    # ── Step 1a: followee posts ──────────────────────────────────────────────
    follow_result = await db.execute(
        select(Follow.followee_id).where(Follow.follower_id == user.id)
    )
    followee_ids_list = [row[0] for row in follow_result.all()]
    followee_set: set[uuid.UUID] = set(followee_ids_list)

    follow_posts: list[Post] = []
    if followee_ids_list:
        vis_filter = _visibility_filter_for_viewer(
            viewer=user,
            author_id_col=Post.author_id,
            viewing_self=False,
            followee_ids=followee_ids_list,
        )
        is_not_active_tier_sql = or_(
            Post.early_access_until.is_(None),
            Post.early_access_until <= func.now(),
            Post.early_access_tier.is_(None),
        )
        tier_qualified = _sql_tier_qualified_expr(user.id, Post.author_id)

        result = await db.execute(
            select(Post)
            .where(
                and_(
                    Post.author_id.in_(followee_ids_list),
                    Post.status == "published",
                    vis_filter,
                    or_(is_not_active_tier_sql, tier_qualified),
                )
            )
            .options(selectinload(Post.media), selectinload(Post.product))
            .order_by(Post.created_at.desc())
            .limit(CANDIDATE_LIMIT)
        )
        follow_posts = list(result.scalars().all())

    # ── Step 1b: trending pool (public, no active tier) ──────────────────────
    follow_post_ids = [p.id for p in follow_posts]
    trending_query = (
        select(Post)
        .where(
            Post.status == "published",
            Post.visibility == "public",
            or_(
                Post.early_access_until.is_(None),
                Post.early_access_until <= func.now(),
            ),
        )
        .options(selectinload(Post.media), selectinload(Post.product))
        .order_by(_trending_score_expr().desc(), Post.created_at.desc())
        .limit(CANDIDATE_LIMIT)
    )
    if follow_post_ids:
        trending_query = trending_query.where(Post.id.notin_(follow_post_ids))
    trending_result = await db.execute(trending_query)
    trending_posts = list(trending_result.scalars().all())

    # ── Merge candidates (deduplicated by SQL already) ───────────────────────
    all_candidates = follow_posts + trending_posts

    # ── Step 2: bulk-load authors + auctions (N+1 zero) ──────────────────────
    author_ids = list({p.author_id for p in all_candidates})
    authors_result = (
        await db.execute(select(User).where(User.id.in_(author_ids)))
        if author_ids else None
    )
    author_map = {u.id: u for u in (authors_result.scalars().all() if authors_result else [])}
    for p in all_candidates:
        p.author = author_map.get(p.author_id)  # type: ignore[attr-defined]

    await _attach_active_auction_end_at(db, all_candidates)

    # ── Score + sort ─────────────────────────────────────────────────────────
    now = datetime.now(timezone.utc)
    scored = score_posts(
        posts=all_candidates,
        viewer_id=user.id,
        followee_ids=followee_set,
        now=now,
    )

    # ── Apply cursor ─────────────────────────────────────────────────────────
    if cursor:
        parsed = decode_cursor(cursor)
        if parsed:
            cursor_score, cursor_id = parsed
            scored = apply_cursor(scored, cursor_score, cursor_id)

    # ── Paginate: take limit + 1 to determine has_more ───────────────────────
    page = scored[: limit + 1]
    has_more = len(page) > limit
    if has_more:
        page = page[:limit]

    # ── Build next_cursor from last item ─────────────────────────────────────
    next_cursor: str | None = None
    if has_more and page:
        last = page[-1]
        next_cursor = encode_cursor(last.score, last.post.id)  # type: ignore[attr-defined]

    # ── Serialize ────────────────────────────────────────────────────────────
    data = []
    for sp in page:
        item = _serialize_post(sp.post)  # type: ignore[arg-type]
        item["recommendation_reason"] = sp.recommendation_reason
        data.append(item)

    feed_result = {
        "data": data,
        "pagination": {"next_cursor": next_cursor, "has_more": has_more},
    }

    # ── Cache-aside (write) ───────────────────────────────────────────────────
    await cache.set_json(feed_cache_key, feed_result, _FEED_CACHE_TTL, prefix="feed")

    return feed_result


def _resolve_ml_algo(algo: str, current_user: User | None) -> bool:
    """algo 파라미터 → ML v2 사용 여부 결정 (K-1 레거시 호환, K-8 이전).

    - v2: 항상 ML
    - v1 / default: 항상 기존 룰 기반
    - auto: ML_FEED_V2_ENABLED=true 이고 로그인 사용자인 경우만 v2
    """
    if algo == "v2":
        return True
    if algo in ("v1", "default"):
        return False
    # auto: 환경변수 + 로그인 사용자 조건
    if current_user is None:
        return False
    return os.getenv("ML_FEED_V2_ENABLED", "false").lower() == "true"


async def _resolve_ml_algo_with_experiment(
    algo: str,
    current_user: User | None,
    db: AsyncSession,
) -> tuple[bool, str | None]:
    """algo 파라미터 → ML 사용 여부 + experiment_variant 결정 (K-8 A/B 테스트).

    반환: (use_ml: bool, variant: str | None)
    - algo=v2:      (True, 'v2')   — 직접 지정, 실험 미적용
    - algo=v1:      (False, 'v1')  — 직접 지정, 실험 미적용
    - algo=default: (False, 'v1')  — 레거시
    - algo=auto:    ml_experiments 조회 → get_user_variant() 호출

    기존 algo=v1|v2|default 직접 지정은 유지 (override).
    """
    if algo == "v2":
        return True, "v2"
    if algo in ("v1", "default"):
        return False, "v1"
    # auto: 실험 기반 분기
    if current_user is None:
        return False, None
    try:
        from app.services.ml_experiments import (  # noqa: PLC0415
            _EXPERIMENT_NAME,
            get_user_variant,
        )
        variant = await get_user_variant(db, _EXPERIMENT_NAME, str(current_user.id))
        return variant == "v2", variant
    except Exception as exc:  # noqa: BLE001
        _log.warning(
            "_resolve_ml_algo_with_experiment 실패 (%s) → v1 fallback", exc
        )
        return False, "v1"


class FeedInteractionIn(BaseModel):
    """POST /feed/interaction 요청 body — K-1 implicit feedback."""

    post_id: str
    interaction_type: str
    weight: Optional[float] = None


# interaction_type별 기본 weight (K-1 설계 §3 Interaction Weight 기준표)
_INTERACTION_WEIGHTS: dict[str, float] = {
    "view": 1.0,
    "click": 1.5,
    "like": 3.0,
    "comment": 4.0,
    "sponsor": 5.0,
}


@router.post("/feed/interaction", status_code=201)
async def record_feed_interaction(
    body: FeedInteractionIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _rl=rate_limit("feed_interaction"),
):
    """implicit feedback 수집 — user_post_interactions INSERT.

    Interaction Weight 기준표:
      view (≥3초) = 1.0, click = 1.5, like = 3.0, comment = 4.0, sponsor = 5.0
    """
    from sqlalchemy import text

    if body.interaction_type not in _INTERACTION_WEIGHTS:
        raise ApiError(
            "VALIDATION_ERROR",
            f"interaction_type must be one of {list(_INTERACTION_WEIGHTS.keys())}",
            http_status=422,
        )

    # post 존재 확인
    post_check = await db.execute(
        text("SELECT id FROM posts WHERE id = :pid"),
        {"pid": body.post_id},
    )
    if not post_check.fetchone():
        raise ApiError("NOT_FOUND", "Post not found", http_status=404)

    weight = float(
        body.weight if body.weight is not None else _INTERACTION_WEIGHTS[body.interaction_type]
    )

    try:
        await db.execute(
            text("""
                INSERT INTO user_post_interactions (user_id, post_id, interaction_type, weight)
                VALUES (:uid, :pid, :itype, :weight)
            """),
            {
                "uid": str(user.id),
                "pid": body.post_id,
                "itype": body.interaction_type,
                "weight": weight,
            },
        )
        await db.commit()
    except Exception as exc:  # noqa: BLE001
        _log.warning("record_feed_interaction: INSERT 실패 — %s", exc)
        await db.rollback()
        raise ApiError("INTERNAL_ERROR", "Failed to record interaction", http_status=500)

    return {"data": {"ok": True}}


@router.get("/feed")
async def home_feed(
    limit: int = Query(20, ge=1, le=100),
    following_only: bool = Query(False),
    algo: str = Query("default", pattern="^(default|v1|v2|auto)$"),
    cursor: str | None = Query(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Home feed endpoint.

    algo=default (legacy): 팔로잉 70% + 트렌딩 30% chronological mix. No cursor.
    algo=v1 (A-3): SQL + Python hybrid personalized feed with (score, id) cursor.
    algo=v2 (K-1): ML 협업 필터링 피드 (cold user → chronological fallback 자동).
    algo=auto (K-8): ml_experiments A/B 테스트 기반 v1/v2 자동 결정.

    응답: 기존 {data: PostOut[], pagination: {...}} 형식 동일.
    v2 응답에는 algo_used + experiment_variant 메타 포함 (PostHog A/B 분석 용).
    """
    # ── K-8: A/B 실험 기반 algo 결정 (algo=auto → experiment variant 조회) ────
    use_ml, experiment_variant = await _resolve_ml_algo_with_experiment(
        algo, user, db
    )

    if use_ml:
        from app.services.ml_feed_inference import get_recommendations  # noqa: PLC0415

        post_ids = await get_recommendations(db, str(user.id), top_k=limit)
        if post_ids:
            # post_ids → Post ORM 객체 일괄 로드
            posts = await _load_posts_by_ids(db, post_ids)
            if posts:
                await _attach_active_auction_end_at(db, posts)
                data = [_serialize_post(p) for p in posts]
                return {
                    "data": data,
                    "pagination": {"next_cursor": None, "has_more": False},
                    "algo_used": "v2",
                    "experiment_variant": experiment_variant,
                }
        # post_ids 비어있으면 v1 fallback (cold user 또는 모델 미준비)
        _log.info("home_feed: ML v2 결과 없음 → v1 fallback (user=%s)", user.id)
        result = await _personalized_feed_v1(db, user, cursor, limit)
        result["algo_used"] = "v1"
        result["experiment_variant"] = experiment_variant
        return result

    # ── A-3 personalized feed v1 ─────────────────────────────────────────────
    if algo in ("v1", "auto"):
        result = await _personalized_feed_v1(db, user, cursor, limit)
        result["algo_used"] = "v1"
        result["experiment_variant"] = experiment_variant
        return result

    # ── Legacy chronological feed (algo=default) ──────────────────────────────
    # following_only=false (default): 팔로우 70% + 트렌딩 30% 혼합
    # following_only=true: 팔로우 작가의 포스트만
    follow_result = await db.execute(
        select(Follow.followee_id).where(Follow.follower_id == user.id)
    )
    followee_ids = [row[0] for row in follow_result.all()]

    if following_only:
        follow_limit = limit
        trending_limit = 0
    else:
        follow_limit = max(1, int(limit * 0.7))
        trending_limit = limit - follow_limit

    follow_posts: list[Post] = []
    if followee_ids:
        # publish-controls §B-9: following posts may include followers_only visibility.
        vis_filter = _visibility_filter_for_viewer(
            viewer=user,
            author_id_col=Post.author_id,
            viewing_self=False,
            followee_ids=followee_ids,
        )
        # D'-1 carry-over: SQL-only tier filter replaces Python post-filter.
        # Active tier_only posts included only if viewer qualifies (EXISTS subquery).
        # sponsor_validity_days fast-path: lifetime (NULL) always qualifies.
        # Non-NULL validity days: rare edge case handled at get_post level where
        # _viewer_meets_tier() performs the per-author lookup.
        is_active_tier_sql = and_(
            Post.early_access_until.is_not(None),
            Post.early_access_until > func.now(),
            Post.early_access_tier.is_not(None),
        )
        is_not_active_tier_sql = or_(
            Post.early_access_until.is_(None),
            Post.early_access_until <= func.now(),
            Post.early_access_tier.is_(None),
        )
        tier_qualified = _sql_tier_qualified_expr(user.id, Post.author_id)

        result = await db.execute(
            select(Post)
            .where(
                and_(
                    Post.author_id.in_(followee_ids),
                    Post.status == "published",
                    vis_filter,
                    # Tier gate: pass if not active tier_only, OR if viewer qualifies
                    or_(is_not_active_tier_sql, tier_qualified),
                )
            )
            .options(selectinload(Post.media), selectinload(Post.product))
            .order_by(Post.created_at.desc())
            .limit(follow_limit)
        )
        follow_posts = list(result.scalars().all())

    trending_posts: list[Post] = []
    if trending_limit > 0:
        exclude_ids = [p.id for p in follow_posts]
        # publish-controls §B-9: trending shows public only + not active tier_only.
        trending_query = (
            select(Post)
            .where(
                Post.status == "published",
                Post.visibility == "public",
                or_(
                    Post.early_access_until.is_(None),
                    Post.early_access_until <= func.now(),
                ),
            )
            .options(selectinload(Post.media), selectinload(Post.product))
            .order_by(_trending_score_expr().desc(), Post.created_at.desc())
            .limit(trending_limit)
        )
        if exclude_ids:
            trending_query = trending_query.where(Post.id.notin_(exclude_ids))
        result = await db.execute(trending_query)
        trending_posts = list(result.scalars().all())

    # Tag recommendation reasons
    follow_ids = {p.id for p in follow_posts}
    trending_ids = {p.id for p in trending_posts}
    all_posts = follow_posts + trending_posts

    # author 정보 일괄 로드
    author_ids = list({p.author_id for p in all_posts})
    authors_result = await db.execute(select(User).where(User.id.in_(author_ids))) if author_ids else None
    author_map = {u.id: u for u in (authors_result.scalars().all() if authors_result else [])}
    for p in all_posts:
        p.author = author_map.get(p.author_id)  # type: ignore[attr-defined]

    # Phase 4 #11 — bulk-attach active_auction_end_at (single query, no N+1)
    await _attach_active_auction_end_at(db, all_posts)

    data = []
    for p in all_posts:
        item = _serialize_post(p)
        if p.id in follow_ids:
            item["recommendation_reason"] = "following"
        elif p.id in trending_ids:
            item["recommendation_reason"] = "trending"
        else:
            item["recommendation_reason"] = None
        data.append(item)

    return {
        "data": data,
        "pagination": {"next_cursor": None, "has_more": False},
    }


@router.get("/explore")
async def explore_posts(
    genre: str | None = Query(None),
    type: str | None = Query(None),
    sort: str = Query("latest", pattern="^(latest|popular)$"),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    # publish-controls §B-9: explore shows public only + not active tier_only.
    query = (
        select(Post)
        .where(
            Post.status == "published",
            Post.visibility == "public",
            or_(
                Post.early_access_until.is_(None),
                Post.early_access_until <= func.now(),
            ),
        )
        .options(selectinload(Post.media), selectinload(Post.product))
        .limit(limit)
    )
    if sort == "popular":
        query = query.order_by(
            _trending_score_expr().desc(), Post.created_at.desc()
        )
    else:
        query = query.order_by(Post.created_at.desc())
    if genre:
        query = query.where(Post.genre == genre)
    if type:
        query = query.where(Post.type == type)

    result = await db.execute(query)
    posts = list(result.scalars().all())

    author_ids = list({p.author_id for p in posts})
    authors_result = await db.execute(select(User).where(User.id.in_(author_ids))) if author_ids else None
    author_map = {u.id: u for u in (authors_result.scalars().all() if authors_result else [])}
    for p in posts:
        p.author = author_map.get(p.author_id)  # type: ignore[attr-defined]

    # Phase 4 #11 — bulk-attach active_auction_end_at (single query, no N+1)
    await _attach_active_auction_end_at(db, posts)

    return {
        "data": [_serialize_post(p) for p in posts],
        "pagination": {"next_cursor": None, "has_more": False},
    }


@router.get("/search")
async def search_posts(
    q: str = Query(..., min_length=2, max_length=100),
    type: str | None = Query(None, pattern="^(general|product)$"),
    genre: str | None = Query(None),
    sort: str = Query("latest", pattern="^(latest|popular|ending_soon)$"),
    limit: int = Query(20, ge=1, le=50),
    cursor: str | None = Query(None),
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
    _rl=rate_limit("search"),
):
    if sort == "ending_soon":
        type = "product"

    # Build text match condition (title, content, exact tag, partial tag)
    text_match = (
        Post.title.ilike(f"%{q}%")
        | Post.content.ilike(f"%{q}%")
        | Post.tags.any(q)                    # exact tag match
        | Post.tags.any(func.concat("%", q, "%"))  # partial tag match via LIKE pattern
    )

    # publish-controls §B-9: search shows public only + not active tier_only.
    query = (
        select(Post)
        .where(
            Post.status == "published",
            Post.visibility == "public",
            or_(
                Post.early_access_until.is_(None),
                Post.early_access_until <= func.now(),
            ),
            text_match,
        )
        .options(selectinload(Post.media), selectinload(Post.product))
        .limit(limit + 1)  # fetch one extra to determine has_more
    )
    if type:
        query = query.where(Post.type == type)
    if genre:
        query = query.where(Post.genre == genre)

    # Cursor-based pagination
    if cursor:
        try:
            cursor_id = UUID(cursor)
            query = query.where(Post.id < cursor_id)
        except ValueError:
            pass

    if sort == "ending_soon":
        query = (
            query
            .join(ProductPost, ProductPost.post_id == Post.id)
            .join(
                Auction,
                and_(
                    Auction.product_post_id == ProductPost.post_id,
                    Auction.status == "active",
                ),
            )
            .order_by(Auction.end_at.asc(), Post.created_at.desc())
        )
    elif sort == "popular":
        query = query.order_by(
            _trending_score_expr().desc(), Post.created_at.desc()
        )
    else:
        query = query.order_by(Post.created_at.desc())

    result = await db.execute(query)
    posts = list(result.scalars().all())

    has_more = len(posts) > limit
    if has_more:
        posts = posts[:limit]

    author_ids = list({p.author_id for p in posts})
    if author_ids:
        authors_result = await db.execute(
            select(User).where(User.id.in_(author_ids))
        )
        author_map = {u.id: u for u in authors_result.scalars().all()}
    else:
        author_map = {}
    for p in posts:
        p.author = author_map.get(p.author_id)  # type: ignore[attr-defined]

    # Phase 4 #11 — bulk-attach active_auction_end_at (single query, no N+1)
    await _attach_active_auction_end_at(db, posts)

    data = [_serialize_post(p) for p in posts]
    next_cursor = str(posts[-1].id) if has_more and posts else None

    # Search log (non-blocking)
    viewer_id, _ = await _optional_viewer_id(authorization)
    try:
        db.add(SearchLog(
            user_id=viewer_id,
            query=q,
            tab="artworks" if type == "product" else "posts",
            result_count=len(data),
            filters={"type": type, "genre": genre, "sort": sort},
        ))
        await db.commit()
    except Exception:
        _log.warning("Failed to save search log", exc_info=True)

    return {"data": data, "pagination": {"next_cursor": next_cursor, "has_more": has_more}}


async def _optional_viewer_id(authorization: str | None) -> tuple[UUID | None, str | None]:
    """Decode JWT if present; return (user_id, role) or (None, None)."""
    if not authorization or not authorization.lower().startswith("bearer "):
        return None, None
    try:
        payload = decode_token(authorization.split(" ", 1)[1])
    except ValueError:
        return None, None
    if payload.get("type") != "access":
        return None, None
    sub = payload.get("sub")
    return (UUID(sub) if sub else None, payload.get("role"))


@router.get("/{post_id}")
async def get_post(
    post_id: UUID,
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
):
    post = await _load_post_full(db, post_id)
    if not post or post.status == "deleted":
        raise ApiError("NOT_FOUND", "Post not found", http_status=404)

    # Decode viewer once; reused by visibility, tier checks below.
    viewer_id: UUID | None = None
    viewer_role: str | None = None

    # G2: pending_review/hidden은 작성자 본인 또는 admin만 조회 가능
    if post.status != "published":
        viewer_id, viewer_role = await _optional_viewer_id(authorization)
        is_owner = viewer_id is not None and viewer_id == post.author_id
        is_admin = viewer_role == "admin"
        if not (is_owner or is_admin):
            raise ApiError("NOT_FOUND", "Post not found", http_status=404)
    else:
        # publish-controls §B-9: visibility check for published posts.
        # OQ-7=A: 'unlisted' permits direct URL access (no restriction here).
        # 'followers_only' requires Follow relationship or ownership/admin.
        visibility = getattr(post, "visibility", "public")
        if visibility == "followers_only":
            viewer_id, viewer_role = await _optional_viewer_id(authorization)
            is_owner = viewer_id is not None and viewer_id == post.author_id
            is_admin = viewer_role == "admin"
            if not (is_owner or is_admin):
                if viewer_id is None:
                    raise ApiError(
                        "POST_VISIBILITY_RESTRICTED",
                        "This post is for followers only",
                        http_status=403,
                    )
                follow_check = await db.execute(
                    select(Follow).where(
                        Follow.follower_id == viewer_id,
                        Follow.followee_id == post.author_id,
                    )
                )
                if not follow_check.scalar_one_or_none():
                    raise ApiError(
                        "POST_VISIBILITY_RESTRICTED",
                        "This post is for followers only",
                        http_status=403,
                    )
        # 'unlisted': URL direct access allowed (OQ-7=A) — no action needed.

    # Phase 4 #10 §B-9: active tier_only check
    ea_until = getattr(post, "early_access_until", None)
    ea_tier = getattr(post, "early_access_tier", None)
    is_tier_locked = False

    if ea_until and ea_until > datetime.now(timezone.utc) and ea_tier:
        # viewer_id may still be None if the post was public/unlisted and no token sent
        if viewer_id is None and authorization:
            viewer_id, viewer_role = await _optional_viewer_id(authorization)

        is_owner = viewer_id is not None and viewer_id == post.author_id
        is_admin = viewer_role == "admin"
        if not (is_owner or is_admin):
            qualifies = await _viewer_meets_tier(db, viewer_id, post.author_id, ea_tier)
            if not qualifies:
                raise ApiError(
                    "POST_TIER_RESTRICTED",
                    "이 포스트는 우선 공개 기간 중입니다",
                    http_status=403,
                )
        # All successful responses: is_tier_locked=False (viewer qualifies or is owner/admin)

    post.author = await _author_for(db, post.author_id)  # type: ignore[attr-defined]
    # Phase 4 #11 — attach active_auction_end_at for detail view consistency
    await _attach_active_auction_end_at(db, [post])
    serialized = _serialize_post(post)
    serialized["is_tier_locked"] = is_tier_locked
    return {"data": serialized}


# ─── Likes ──────────────────────────────────────────────────────────────


@router.post("/{post_id}/like")
async def like_post(
    post_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    existing = await db.execute(
        select(Like).where(Like.user_id == user.id, Like.post_id == post_id)
    )
    if existing.scalar_one_or_none():
        return {"data": {"ok": True, "already_liked": True}}

    db.add(Like(user_id=user.id, post_id=post_id))
    post_result = await db.execute(select(Post).where(Post.id == post_id))
    post = post_result.scalar_one_or_none()
    if not post:
        raise ApiError("NOT_FOUND", "Post not found", http_status=404)
    post.like_count += 1
    await db.commit()
    return {"data": {"ok": True, "like_count": post.like_count}}


@router.delete("/{post_id}/like")
async def unlike_post(
    post_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    existing = await db.execute(
        select(Like).where(Like.user_id == user.id, Like.post_id == post_id)
    )
    like = existing.scalar_one_or_none()
    if not like:
        return {"data": {"ok": True, "already_unliked": True}}

    await db.delete(like)
    post_result = await db.execute(select(Post).where(Post.id == post_id))
    post = post_result.scalar_one_or_none()
    if post and post.like_count > 0:
        post.like_count -= 1
    await db.commit()
    return {"data": {"ok": True, "like_count": post.like_count if post else 0}}


# ─── Bookmarks ──────────────────────────────────────────────────────────


@router.post("/{post_id}/bookmark")
async def bookmark_post(
    post_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.models.bookmark import Bookmark
    existing = await db.execute(
        select(Bookmark).where(Bookmark.user_id == user.id, Bookmark.post_id == post_id)
    )
    if existing.scalar_one_or_none():
        return {"data": {"ok": True, "bookmarked": True}}
    db.add(Bookmark(user_id=user.id, post_id=post_id))
    await db.commit()
    return {"data": {"ok": True, "bookmarked": True}}


@router.delete("/{post_id}/bookmark")
async def unbookmark_post(
    post_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.models.bookmark import Bookmark
    result = await db.execute(
        select(Bookmark).where(Bookmark.user_id == user.id, Bookmark.post_id == post_id)
    )
    bm = result.scalar_one_or_none()
    if bm:
        await db.delete(bm)
        await db.commit()
    return {"data": {"ok": True, "bookmarked": False}}


@router.get("/bookmarks/mine")
async def my_bookmarks(
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.models.bookmark import Bookmark
    # publish-controls §B-9: bookmarks show own posts (any visibility) or public posts
    # Phase 4 #10: exclude active tier_only posts that viewer doesn't qualify for.
    result = await db.execute(
        select(Post)
        .join(Bookmark, Bookmark.post_id == Post.id)
        .where(
            Bookmark.user_id == user.id,
            or_(
                Post.author_id == user.id,
                and_(
                    Post.visibility == "public",
                    or_(
                        Post.early_access_until.is_(None),
                        Post.early_access_until <= func.now(),
                    ),
                ),
            ),
        )
        .options(selectinload(Post.media), selectinload(Post.product))
        .order_by(Bookmark.created_at.desc())
        .limit(limit)
    )
    posts = list(result.scalars().all())
    author_ids = list({p.author_id for p in posts})
    author_map = {}
    if author_ids:
        authors = await db.execute(select(User).where(User.id.in_(author_ids)))
        author_map = {u.id: u for u in authors.scalars()}
    for p in posts:
        p.author = author_map.get(p.author_id)
    # Phase 4 #11 — bulk-attach active_auction_end_at (single query, no N+1)
    await _attach_active_auction_end_at(db, posts)
    return {"data": [_serialize_post(p) for p in posts]}


# ─── Comments ───────────────────────────────────────────────────────────


@router.get("/{post_id}/comments")
async def list_comments(
    post_id: UUID,
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Comment)
        .where(Comment.post_id == post_id, Comment.status == "visible")
        .order_by(Comment.created_at.asc())
        .limit(limit)
    )
    comments = list(result.scalars().all())

    author_ids = list({c.author_id for c in comments})
    authors_result = await db.execute(select(User).where(User.id.in_(author_ids))) if author_ids else None
    author_map = {u.id: u for u in (authors_result.scalars().all() if authors_result else [])}

    out = []
    for c in comments:
        author = author_map.get(c.author_id)
        out.append(
            CommentOut(
                id=c.id,
                post_id=c.post_id,
                author=PostAuthor.model_validate(author) if author else PostAuthor(
                    id=c.author_id, display_name="unknown", role="user"
                ),
                content=c.content,
                status=c.status,
                created_at=c.created_at,
            ).model_dump(mode="json")
        )
    return {"data": out}


@router.post("/{post_id}/comments")
async def create_comment(
    post_id: UUID,
    body: CommentIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    post_result = await db.execute(select(Post).where(Post.id == post_id))
    post = post_result.scalar_one_or_none()
    if not post:
        raise ApiError("NOT_FOUND", "Post not found", http_status=404)

    # publish-controls §B-10 / OQ-3=A: block new comments when disabled.
    # Existing comments are preserved (read-only via GET /comments).
    if not getattr(post, "comments_enabled", True):
        raise ApiError(
            "COMMENTS_DISABLED",
            "Comments are disabled for this post",
            http_status=403,
        )

    comment = Comment(
        post_id=post_id,
        author_id=user.id,
        content=body.content,
        status="visible",
    )
    db.add(comment)
    post.comment_count += 1
    await db.commit()
    await db.refresh(comment)

    return {
        "data": CommentOut(
            id=comment.id,
            post_id=comment.post_id,
            author=PostAuthor.model_validate(user),
            content=comment.content,
            status=comment.status,
            created_at=comment.created_at,
        ).model_dump(mode="json")
    }


# ─── K-3 AI Caption Endpoints ────────────────────────────────────────────


@router.post("/{post_id}/regenerate-caption")
async def regenerate_caption(
    post_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _rl=rate_limit("caption_regenerate"),
    _rl_post=rate_limit("post_caption_regenerate"),
):
    """작가 전용 — AI 캡션 수동 재생성.

    K-3: LLM Gateway vision 호출 → ai_caption 저장 + 5 locale 번역.
    CO-1 PR-2: 기존 caption_regenerate(10/hr) 유지 + post_caption_regenerate(3/일) 추가.
    작가 본인만 호출 가능. Mock 모드에서는 503 대신 빈 캡션으로 응답.
    """
    # 포스트 조회 (media 포함)
    result = await db.execute(
        select(Post)
        .where(Post.id == post_id)
        .options(selectinload(Post.media))
    )
    post = result.scalar_one_or_none()
    if not post or post.status == "deleted":
        raise ApiError("POST_NOT_FOUND", "Post not found", http_status=404)

    # 작가 본인 확인
    if post.author_id != user.id and user.role != "admin":
        raise ApiError(
            "POST_NOT_OWNER",
            "캡션 재생성은 작품 작가만 가능합니다",
            http_status=403,
        )

    # 재생성 실행 (force=True: caption_override 무시)
    ok = await generate_for_post(db, post_id, force=True)

    # DB reload (생성된 캡션 반영)
    await db.refresh(post)

    if not ok:
        _log.warning(
            "[ArtworkCaption] regenerate failed or mock mode post_id=%s", post_id
        )
        # Mock 모드 / LLM 장애 시 503 대신 현재 상태 반환 (graceful)
        effective = get_effective_caption(post)
        return {
            "data": {
                "post_id": str(post_id),
                "ai_caption": post.ai_caption,
                "ai_caption_locale_translations": post.ai_caption_locale_translations or {},
                "ai_caption_model_version": post.ai_caption_model_version,
                "ai_caption_generated_at": post.ai_caption_generated_at.isoformat() if post.ai_caption_generated_at else None,
                "effective_caption": effective,
                "message": "캡션 생성 실패 또는 Mock 모드 — ai_caption=null",
            }
        }

    effective = get_effective_caption(post)
    return {
        "data": {
            "post_id": str(post_id),
            "ai_caption": post.ai_caption,
            "ai_caption_locale_translations": post.ai_caption_locale_translations or {},
            "ai_caption_model_version": post.ai_caption_model_version,
            "ai_caption_generated_at": post.ai_caption_generated_at.isoformat() if post.ai_caption_generated_at else None,
            "effective_caption": effective,
        }
    }


@router.patch("/{post_id}/caption-override")
async def update_caption_override(
    post_id: UUID,
    body: CaptionOverrideRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _rl=rate_limit("post_caption_override"),
):
    """작가 전용 — caption_override 저장 또는 제거.

    K-3: clear=True 전송 시 caption_override=NULL (AI 캡션으로 복원).
    body.caption_override: 최대 500자 (Pydantic 검증).
    CO-1 PR-2: rate_limit("post_caption_override") 추가 — 10회/일/사용자.
    """
    # 포스트 조회
    result = await db.execute(select(Post).where(Post.id == post_id))
    post = result.scalar_one_or_none()
    if not post or post.status == "deleted":
        raise ApiError("POST_NOT_FOUND", "Post not found", http_status=404)

    # 작가 본인 확인
    if post.author_id != user.id and user.role != "admin":
        raise ApiError(
            "POST_NOT_OWNER",
            "캡션 수정은 작품 작가만 가능합니다",
            http_status=403,
        )

    if body.clear:
        post.caption_override = None
    else:
        post.caption_override = body.caption_override

    await db.commit()
    await db.refresh(post)

    effective = get_effective_caption(post)
    return {
        "data": {
            "post_id": str(post_id),
            "caption_override": post.caption_override,
            "effective_caption": effective,
        }
    }


# ─── K-5 도슨트 엔드포인트 — llm-docent-artwork ──────────────────────────────
# README 비전 "스토리텔링 hub"과 "AI 시대 작가의 정체성 재정의" 구현


async def _get_post_for_docent(
    db: AsyncSession,
    post_id: UUID,
) -> Post:
    """도슨트 엔드포인트용 포스트 조회 헬퍼."""
    result = await db.execute(
        select(Post)
        .where(Post.id == post_id)
        .options(selectinload(Post.media))
    )
    post = result.scalar_one_or_none()
    if not post:
        raise ApiError("NOT_FOUND", "Post not found", http_status=404)
    return post


def _assert_docent_author(post: Post, user: User) -> None:
    """도슨트 작가 권한 검증 — 다른 작가의 도슨트 수정/생성 시 403."""
    if post.author_id != user.id and user.role != "admin":
        raise ApiError(
            "FORBIDDEN",
            "본인 작품의 도슨트만 수정할 수 있습니다.",
            http_status=403,
        )


@router.post("/{post_id}/docent/generate")
async def generate_post_docent(
    post_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """POST /posts/{id}/docent/generate — AI 도슨트 생성 (작가 전용).

    K-5 llm-docent-artwork: 작가가 "AI 도슨트 생성" 버튼 클릭 시 호출.
    LLM Gateway(tuzigroup gemma4-e4b)로 큐레이터 톤 3~5문단 해설을 생성한다.

    권한: 작가 본인 또는 admin. 불일치 시 403.
    idempotency: 24h 이내 중복 생성 시 409 반환.
    opt_out: True이면 403 반환.
    Mock 모드: LLM 미설정 시 ai_docent_text=None graceful 반환.
    """
    post = await _get_post_for_docent(db, post_id)
    _assert_docent_author(post, user)

    # opt_out 상태 체크
    if getattr(post, "ai_docent_opted_out", False):
        raise ApiError(
            "DOCENT_OPTED_OUT",
            "AI 도슨트가 비활성화 상태입니다. 먼저 활성화해 주세요.",
            http_status=403,
        )

    # 24h idempotency 체크 — 이미 생성된 도슨트가 있으면 409
    generated_at = getattr(post, "ai_docent_generated_at", None)
    if generated_at is not None:
        now = datetime.now(timezone.utc)
        if generated_at.tzinfo is None:
            generated_at = generated_at.replace(tzinfo=timezone.utc)
        if (now - generated_at) < timedelta(hours=24):
            raise ApiError(
                "DOCENT_RECENTLY_GENERATED",
                "24시간 이내에 이미 생성된 도슨트가 있습니다.",
                http_status=409,
                details={"ai_docent_generated_at": generated_at.isoformat()},
            )

    # 작가 정보 조회
    artist_result = await db.execute(
        select(User)
        .where(User.id == post.author_id)
        .options(selectinload(User.artist_profile))
    )
    artist = artist_result.scalar_one_or_none()
    if not artist:
        raise ApiError("NOT_FOUND", "Artist not found", http_status=404)

    # 시리즈 정보 조회 (있는 경우)
    series: Series | None = None
    series_membership_result = await db.execute(
        select(PostSeriesMembership)
        .where(PostSeriesMembership.post_id == post_id)
        .limit(1)
    )
    membership = series_membership_result.scalar_one_or_none()
    if membership:
        series_result = await db.execute(
            select(Series).where(Series.id == membership.series_id)
        )
        series = series_result.scalar_one_or_none()

    # AI 도슨트 생성
    docent_text = await generate_docent(
        db=db,
        post_id=post_id,
        post=post,
        artist=artist,
        series=series,
    )

    from app.services.llm_gateway import LLMGatewayClient as _LLMClient
    is_mock = _LLMClient().is_mock

    if docent_text is None and is_mock:
        return {
            "data": DocentGenerateResponse(
                ai_docent_text=None,
                message="AI 도슨트 생성 서비스가 비활성화 상태입니다.",
            ).model_dump(mode="json")
        }

    return {
        "data": DocentGenerateResponse(
            ai_docent_text=getattr(post, "ai_docent_text", None),
            ai_docent_model_version=getattr(post, "ai_docent_model_version", None),
            ai_docent_generated_at=getattr(post, "ai_docent_generated_at", None),
            ai_docent_translations=getattr(post, "ai_docent_translations", {}) or {},
        ).model_dump(mode="json")
    }


@router.patch("/{post_id}/docent")
async def patch_artist_docent(
    post_id: UUID,
    body: DocentPatchRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """PATCH /posts/{id}/docent — 작가 직접 해설 작성/수정 (작가 전용).

    K-5: 작가가 직접 작성한 해설을 저장한다.
    artist_docent_text가 있으면 공개 API에서 AI 도슨트보다 우선 노출된다.
    OQ-K-5-5=유지: 작가 해설 저장이 AI 도슨트를 삭제하지 않음 (독립적 관리).
    """
    post = await _get_post_for_docent(db, post_id)
    _assert_docent_author(post, user)

    post.artist_docent_text = body.artist_docent_text  # type: ignore[assignment]
    await db.commit()
    await db.refresh(post)

    return {
        "data": DocentPatchResponse(
            artist_docent_text=post.artist_docent_text,  # type: ignore[attr-defined]
            updated_at=datetime.now(timezone.utc),
        ).model_dump(mode="json")
    }


@router.patch("/{post_id}/docent/opt-out")
async def patch_docent_opt_out(
    post_id: UUID,
    body: DocentOptOutRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """PATCH /posts/{id}/docent/opt-out — AI 도슨트 비활성화 토글 (작가 전용).

    K-5: opted_out=True 이후 GET /docent는 ai_docent_text=null 반환.
    재활성화(opted_out=False) 시 기존 ai_docent_text 유지 — 다시 표시됨.
    """
    post = await _get_post_for_docent(db, post_id)
    _assert_docent_author(post, user)

    post.ai_docent_opted_out = body.opted_out  # type: ignore[assignment]
    await db.commit()

    msg = (
        "AI 도슨트가 비활성화되었습니다."
        if body.opted_out
        else "AI 도슨트가 활성화되었습니다."
    )
    return {
        "data": DocentOptOutResponse(
            ai_docent_opted_out=body.opted_out,
            message=msg,
        ).model_dump(mode="json")
    }


@router.get("/{post_id}/docent")
async def get_post_docent(
    post_id: UUID,
    locale: str = Query(default="ko", pattern=r"^(ko|en|ja|zh|es)$"),
    db: AsyncSession = Depends(get_db),
):
    """GET /posts/{id}/docent — 도슨트 조회 (공개, 인증 불필요).

    K-5: 작가 해설(artist_docent_text) + AI 해설(ai_docent_text) 반환.
    locale_docent 결정 로직:
      locale=ko  → ai_docent_text (원본)
      locale 기타 → ai_docent_translations[locale] 없으면 한국어 fallback
      opted_out=True → ai_docent_text=None, locale_docent=None
    """
    result = await db.execute(select(Post).where(Post.id == post_id))
    post = result.scalar_one_or_none()
    if not post:
        raise ApiError("NOT_FOUND", "Post not found", http_status=404)

    opted_out = getattr(post, "ai_docent_opted_out", False)
    ai_docent_text = getattr(post, "ai_docent_text", None) if not opted_out else None
    translations = getattr(post, "ai_docent_translations", {}) or {}

    # locale_docent 결정
    locale_docent: str | None = None
    if not opted_out and ai_docent_text:
        if locale == "ko":
            locale_docent = ai_docent_text
        else:
            locale_docent = translations.get(locale) or ai_docent_text  # fallback to ko

    return {
        "data": DocentResponse(
            post_id=post_id,
            artist_docent_text=getattr(post, "artist_docent_text", None),
            ai_docent_text=ai_docent_text,
            ai_docent_opted_out=opted_out,
            ai_docent_generated_at=getattr(post, "ai_docent_generated_at", None),
            locale_docent=locale_docent,
            locale=locale,
        ).model_dump(mode="json")
    }
