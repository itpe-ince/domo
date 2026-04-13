"""Artist and artwork rankings API.

Provides TOP 10 rankings for Netflix-style gallery view.
Score = like_count*0.3 + bluebird_count*0.3 + follower_count*0.2 + view_count*0.2
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.post import Follow, Post
from app.models.user import ArtistProfile, User

router = APIRouter(prefix="/rankings", tags=["rankings"])


@router.get("/artists")
async def top_artists(
    genre: str | None = Query(None),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """Top artists by composite score (followers + bluebird + likes on their posts)."""
    follower_sub = (
        select(func.count())
        .select_from(Follow)
        .where(Follow.followee_id == User.id)
        .correlate(User)
        .scalar_subquery()
    )

    # Aggregate post stats per artist
    post_stats = (
        select(
            Post.author_id,
            func.sum(Post.like_count).label("total_likes"),
            func.sum(Post.bluebird_count).label("total_bluebirds"),
            func.sum(Post.view_count).label("total_views"),
            func.count(Post.id).label("post_count"),
        )
        .where(Post.status == "published")
        .group_by(Post.author_id)
    )
    if genre:
        post_stats = post_stats.where(Post.genre == genre)
    post_stats = post_stats.subquery()

    query = (
        select(
            User,
            follower_sub.label("follower_count"),
            func.coalesce(post_stats.c.total_likes, 0).label("total_likes"),
            func.coalesce(post_stats.c.total_bluebirds, 0).label("total_bluebirds"),
            func.coalesce(post_stats.c.total_views, 0).label("total_views"),
            func.coalesce(post_stats.c.post_count, 0).label("post_count"),
        )
        .outerjoin(post_stats, post_stats.c.author_id == User.id)
        .where(User.role == "artist", User.status == "active")
        .order_by(
            (
                func.coalesce(post_stats.c.total_likes, 0) * 0.3
                + func.coalesce(post_stats.c.total_bluebirds, 0) * 0.3
                + follower_sub * 0.2
                + func.coalesce(post_stats.c.total_views, 0) * 0.002
            ).desc()
        )
        .limit(limit)
    )

    result = await db.execute(query)
    rows = result.all()

    data = []
    for i, (user, followers, likes, bluebirds, views, posts) in enumerate(rows):
        data.append({
            "rank": i + 1,
            "id": str(user.id),
            "display_name": user.display_name,
            "avatar_url": user.avatar_url,
            "role": user.role,
            "badge_level": None,
            "follower_count": followers or 0,
            "total_likes": likes or 0,
            "total_bluebirds": bluebirds or 0,
            "total_views": views or 0,
            "post_count": posts or 0,
        })

    # Try to get badge_level from artist_profiles
    artist_ids = [row[0].id for row in rows]
    if artist_ids:
        profiles = await db.execute(
            select(ArtistProfile).where(ArtistProfile.user_id.in_(artist_ids))
        )
        badge_map = {p.user_id: p.badge_level for p in profiles.scalars()}
        for item in data:
            from uuid import UUID
            item["badge_level"] = badge_map.get(UUID(item["id"]))

    return {"data": data}


@router.get("/artworks")
async def top_artworks(
    genre: str | None = Query(None),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """Top artworks (product posts) by trending score."""
    from app.api.posts import _trending_score_expr, _serialize_post
    from sqlalchemy.orm import selectinload

    query = (
        select(Post)
        .where(Post.status == "published", Post.type == "product")
        .options(selectinload(Post.media), selectinload(Post.product))
        .order_by(_trending_score_expr().desc())
        .limit(limit)
    )
    if genre:
        query = query.where(Post.genre == genre)

    result = await db.execute(query)
    posts = list(result.scalars().all())

    author_ids = list({p.author_id for p in posts})
    if author_ids:
        authors_result = await db.execute(select(User).where(User.id.in_(author_ids)))
        author_map = {u.id: u for u in authors_result.scalars()}
    else:
        author_map = {}
    for p in posts:
        p.author = author_map.get(p.author_id)

    data = []
    for i, post in enumerate(posts):
        serialized = _serialize_post(post)
        serialized["rank"] = i + 1
        data.append(serialized)

    return {"data": data}
