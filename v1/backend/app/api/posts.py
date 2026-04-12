from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import get_current_user
from app.core.errors import ApiError
from app.core.security import decode_token
from app.db.session import get_db
from app.models.post import Comment, Follow, Like, MediaAsset, Post, ProductPost
from app.models.user import User
from app.schemas.post import (
    CommentIn,
    CommentOut,
    MediaAssetOut,
    PostAuthor,
    PostCreate,
    PostOut,
    ProductPostOut,
)

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
        created_at=post.created_at,
        media=[MediaAssetOut.model_validate(m) for m in (post.media or [])],
        product=ProductPostOut.model_validate(post.product) if post.product else None,
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
    if has_visual_media:
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
        result = await db.execute(
            select(Post)
            .where(
                and_(
                    Post.author_id.in_(followee_ids),
                    Post.status == "published",
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
        trending_query = (
            select(Post)
            .where(Post.status == "published")
            .options(selectinload(Post.media), selectinload(Post.product))
            .order_by(_trending_score_expr().desc(), Post.created_at.desc())
            .limit(trending_limit)
        )
        if exclude_ids:
            trending_query = trending_query.where(Post.id.notin_(exclude_ids))
        result = await db.execute(trending_query)
        trending_posts = list(result.scalars().all())

    all_posts = follow_posts + trending_posts

    # author 정보 일괄 로드
    author_ids = list({p.author_id for p in all_posts})
    authors_result = await db.execute(select(User).where(User.id.in_(author_ids))) if author_ids else None
    author_map = {u.id: u for u in (authors_result.scalars().all() if authors_result else [])}
    for p in all_posts:
        p.author = author_map.get(p.author_id)  # type: ignore[attr-defined]

    return {
        "data": [_serialize_post(p) for p in all_posts],
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
    query = (
        select(Post)
        .where(Post.status == "published")
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

    # G2: pending_review/hidden은 작성자 본인 또는 admin만 조회 가능
    if post.status != "published":
        viewer_id, viewer_role = await _optional_viewer_id(authorization)
        is_owner = viewer_id is not None and viewer_id == post.author_id
        is_admin = viewer_role == "admin"
        if not (is_owner or is_admin):
            raise ApiError("NOT_FOUND", "Post not found", http_status=404)

    post.author = await _author_for(db, post.author_id)  # type: ignore[attr-defined]
    return {"data": _serialize_post(post)}


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
