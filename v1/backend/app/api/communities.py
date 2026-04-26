"""Communities API — groups for school, genre, country, custom."""
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.errors import ApiError
from app.db.session import get_db
from app.models.community import Community, CommunityComment, CommunityMember, CommunityPost
from app.models.user import User

router = APIRouter(prefix="/communities", tags=["communities"])


def _serialize_community(c: Community) -> dict:
    return {
        "id": str(c.id),
        "name": c.name,
        "type": c.type,
        "description": c.description,
        "cover_image_url": c.cover_image_url,
        "member_count": c.member_count,
        "created_at": c.created_at.isoformat() if c.created_at else None,
    }


# ─── Community CRUD ──────────────────────────────────────────────────────


@router.get("")
async def list_communities(
    type: str | None = Query(None),
    q: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    query = select(Community)
    if type:
        query = query.where(Community.type == type)
    if q:
        query = query.where(Community.name.ilike(f"%{q}%"))
    query = query.order_by(Community.member_count.desc()).limit(limit)
    result = await db.execute(query)
    return {"data": [_serialize_community(c) for c in result.scalars().all()]}


@router.get("/{community_id}")
async def get_community(
    community_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Community).where(Community.id == community_id))
    c = result.scalar_one_or_none()
    if not c:
        raise ApiError("NOT_FOUND", "Community not found", http_status=404)
    return {"data": _serialize_community(c)}


class CommunityCreateRequest(BaseModel):
    name: str
    type: str = "custom"
    description: str | None = None
    cover_image_url: str | None = None


@router.post("")
async def create_community(
    body: CommunityCreateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    community = Community(
        name=body.name,
        type=body.type,
        description=body.description,
        cover_image_url=body.cover_image_url,
        created_by=user.id,
        member_count=1,
    )
    db.add(community)
    await db.flush()
    db.add(CommunityMember(community_id=community.id, user_id=user.id, role="owner"))
    await db.commit()
    await db.refresh(community)
    return {"data": _serialize_community(community)}


# ─── Members ─────────────────────────────────────────────────────────────


@router.post("/{community_id}/join")
async def join_community(
    community_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    existing = await db.execute(
        select(CommunityMember).where(
            CommunityMember.community_id == community_id,
            CommunityMember.user_id == user.id,
        )
    )
    if existing.scalar_one_or_none():
        return {"data": {"joined": True}}

    community = await db.execute(select(Community).where(Community.id == community_id))
    c = community.scalar_one_or_none()
    if not c:
        raise ApiError("NOT_FOUND", "Community not found", http_status=404)

    db.add(CommunityMember(community_id=community_id, user_id=user.id, role="member"))
    c.member_count += 1
    await db.commit()
    return {"data": {"joined": True, "member_count": c.member_count}}


@router.delete("/{community_id}/leave")
async def leave_community(
    community_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(CommunityMember).where(
            CommunityMember.community_id == community_id,
            CommunityMember.user_id == user.id,
        )
    )
    member = result.scalar_one_or_none()
    if not member:
        return {"data": {"left": True}}

    await db.delete(member)
    community = await db.execute(select(Community).where(Community.id == community_id))
    c = community.scalar_one_or_none()
    if c and c.member_count > 0:
        c.member_count -= 1
    await db.commit()
    return {"data": {"left": True}}


@router.get("/{community_id}/members")
async def list_members(
    community_id: UUID,
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(User)
        .join(CommunityMember, CommunityMember.user_id == User.id)
        .where(CommunityMember.community_id == community_id)
        .order_by(CommunityMember.joined_at.desc())
        .limit(limit)
    )
    users = result.scalars().all()
    return {
        "data": [
            {
                "id": str(u.id),
                "display_name": u.display_name,
                "avatar_url": u.avatar_url,
                "role": u.role,
            }
            for u in users
        ]
    }


# ─── Posts ────────────────────────────────────────────────────────────────


class CommunityPostCreate(BaseModel):
    content: str


@router.post("/{community_id}/posts")
async def create_post(
    community_id: UUID,
    body: CommunityPostCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Check membership
    member = await db.execute(
        select(CommunityMember).where(
            CommunityMember.community_id == community_id,
            CommunityMember.user_id == user.id,
        )
    )
    if not member.scalar_one_or_none():
        raise ApiError("FORBIDDEN", "Join the community first", http_status=403)

    post = CommunityPost(
        community_id=community_id,
        author_id=user.id,
        content=body.content,
    )
    db.add(post)
    await db.commit()
    await db.refresh(post)
    return {
        "data": {
            "id": str(post.id),
            "community_id": str(post.community_id),
            "author": {"id": str(user.id), "display_name": user.display_name, "avatar_url": user.avatar_url},
            "content": post.content,
            "created_at": post.created_at.isoformat(),
        }
    }


@router.get("/{community_id}/posts")
async def list_posts(
    community_id: UUID,
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(CommunityPost)
        .where(CommunityPost.community_id == community_id)
        .order_by(CommunityPost.created_at.desc())
        .limit(limit)
    )
    posts = list(result.scalars().all())

    author_ids = list({p.author_id for p in posts})
    author_map = {}
    if author_ids:
        authors = await db.execute(select(User).where(User.id.in_(author_ids)))
        author_map = {u.id: u for u in authors.scalars()}

    return {
        "data": [
            {
                "id": str(p.id),
                "author": {
                    "id": str(a.id), "display_name": a.display_name, "avatar_url": a.avatar_url
                } if (a := author_map.get(p.author_id)) else {"id": str(p.author_id), "display_name": "unknown"},
                "content": p.content,
                "created_at": p.created_at.isoformat(),
            }
            for p in posts
        ]
    }


# ─── Comments ─────────────────────────────────────────────────────────────


class CommunityCommentCreate(BaseModel):
    content: str


def _serialize_comment(c: CommunityComment, author: User | None) -> dict:
    return {
        "id": str(c.id),
        "post_id": str(c.post_id),
        "author": {
            "id": str(author.id),
            "display_name": author.display_name,
            "avatar_url": author.avatar_url,
        } if author else {"id": str(c.author_id), "display_name": "unknown"},
        "content": c.content,
        "status": c.status,
        "created_at": c.created_at.isoformat(),
    }


@router.get("/posts/{post_id}/comments")
async def list_comments(
    post_id: UUID,
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List comments on a community post (public)."""
    result = await db.execute(
        select(CommunityComment)
        .where(
            CommunityComment.post_id == post_id,
            CommunityComment.status == "active",
        )
        .order_by(CommunityComment.created_at.asc())
        .limit(limit)
    )
    comments = list(result.scalars().all())

    author_ids = list({c.author_id for c in comments})
    author_map: dict = {}
    if author_ids:
        authors = await db.execute(select(User).where(User.id.in_(author_ids)))
        author_map = {u.id: u for u in authors.scalars()}

    return {"data": [_serialize_comment(c, author_map.get(c.author_id)) for c in comments]}


@router.post("/posts/{post_id}/comments")
async def create_comment(
    post_id: UUID,
    body: CommunityCommentCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a comment on a community post (members only)."""
    # Verify post exists and get its community_id
    post_result = await db.execute(
        select(CommunityPost).where(CommunityPost.id == post_id)
    )
    post = post_result.scalar_one_or_none()
    if not post:
        raise ApiError("NOT_FOUND", "Post not found", http_status=404)

    # Check membership
    member = await db.execute(
        select(CommunityMember).where(
            CommunityMember.community_id == post.community_id,
            CommunityMember.user_id == user.id,
        )
    )
    if not member.scalar_one_or_none():
        raise ApiError("FORBIDDEN", "Join the community first", http_status=403)

    comment = CommunityComment(
        post_id=post_id,
        author_id=user.id,
        content=body.content,
    )
    db.add(comment)
    await db.commit()
    await db.refresh(comment)
    return {"data": _serialize_comment(comment, user)}


@router.delete("/comments/{comment_id}")
async def delete_comment(
    comment_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a comment (author or admin)."""
    result = await db.execute(
        select(CommunityComment).where(CommunityComment.id == comment_id)
    )
    comment = result.scalar_one_or_none()
    if not comment:
        raise ApiError("NOT_FOUND", "Comment not found", http_status=404)

    if comment.author_id != user.id and user.role != "admin":
        raise ApiError("FORBIDDEN", "Not authorized to delete this comment", http_status=403)

    comment.status = "deleted"
    await db.commit()
    return {"data": {"deleted": True}}
