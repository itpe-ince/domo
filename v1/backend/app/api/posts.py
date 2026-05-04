from typing import Annotated
from uuid import UUID
import uuid
from datetime import datetime, timedelta, timezone

import sqlalchemy as sa
from fastapi import APIRouter, Depends, Header, Query
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

_log = logging.getLogger(__name__)
from app.schemas.post import (
    CommentIn,
    CommentOut,
    MediaAssetOut,
    PostAuthor,
    PostCreate,
    PostOut,
    ProductPostOut,
)
from app.schemas.series import PostPublishRequest, PostPublishResponse

router = APIRouter(prefix="/posts", tags=["posts"])


def _serialize_post(post: Post) -> dict:
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
    ).model_dump(mode="json")


async def _load_post_full(db: AsyncSession, post_id: UUID) -> Post | None:
    result = await db.execute(
        select(Post)
        .where(Post.id == post_id)
        .options(selectinload(Post.media), selectinload(Post.product))
    )
    return result.scalar_one_or_none()


async def _author_for(db: AsyncSession, user_id: UUID) -> PostAuthor:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        return PostAuthor(id=user_id, display_name="unknown", role="user")
    return PostAuthor.model_validate(user)


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
    - follower: 위 둘 OR Follow row exists

    author 본인은 항상 통과 (return True).
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
    spon_q = (
        select(sa.literal(1))
        .where(
            Sponsorship.sponsor_id == viewer_id,
            Sponsorship.artist_id == author_id,
            Sponsorship.status == "completed",
        )
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


async def _filter_active_tier_only(
    db: AsyncSession,
    posts: list,
    viewer_id: uuid.UUID | None,
) -> list:
    """Python post-filter — active tier_only 포스트의 viewer별 자격 검증.

    SQL fast-path가 followee author 등 명백한 자격을 통과시킨 후,
    실제 tier 자격 (subscription/sponsorship/follow OR)을 viewer별로 재검증.
    """
    now = datetime.now(timezone.utc)
    filtered = []
    for p in posts:
        ea_until = getattr(p, "early_access_until", None)
        ea_tier = getattr(p, "early_access_tier", None)
        if (
            ea_until is not None
            and ea_until > now
            and ea_tier is not None
        ):
            qualifies = await _viewer_meets_tier(
                db, viewer_id, p.author_id, ea_tier
            )
            if not qualifies:
                continue
        filtered.append(p)
    return filtered


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
    return {"data": _serialize_post(full_post)}


# ─── Read ────────────────────────────────────────────────────────────────


@router.get("/feed")
async def home_feed(
    limit: int = Query(20, ge=1, le=100),
    following_only: bool = Query(False),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
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
        result = await db.execute(
            select(Post)
            .where(
                and_(
                    Post.author_id.in_(followee_ids),
                    Post.status == "published",
                    vis_filter,
                )
            )
            .options(selectinload(Post.media), selectinload(Post.product))
            .order_by(Post.created_at.desc())
            .limit(follow_limit)
        )
        follow_posts = list(result.scalars().all())
        # Phase 4 #10 §B-9: Python post-filter for active tier_only posts
        follow_posts = await _filter_active_tier_only(db, follow_posts, user.id)

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
