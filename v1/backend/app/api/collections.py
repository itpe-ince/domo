"""Post collections (series) API."""
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import get_current_user
from app.core.errors import ApiError
from app.db.session import get_db
from app.models.collection import PostCollection, PostCollectionItem
from app.models.post import Post
from app.models.user import User

router = APIRouter(prefix="/collections", tags=["collections"])


class CollectionCreate(BaseModel):
    title: str
    description: str | None = None
    cover_image_url: str | None = None


class CollectionItemAdd(BaseModel):
    post_id: UUID


@router.post("")
async def create_collection(
    body: CollectionCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    collection = PostCollection(
        author_id=user.id,
        title=body.title,
        description=body.description,
        cover_image_url=body.cover_image_url,
    )
    db.add(collection)
    await db.commit()
    await db.refresh(collection)
    return {"data": _serialize(collection, 0)}


@router.get("/mine")
async def my_collections(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PostCollection)
        .where(PostCollection.author_id == user.id)
        .order_by(PostCollection.created_at.desc())
    )
    collections = result.scalars().all()
    data = []
    for c in collections:
        count = await db.scalar(
            select(func.count()).select_from(PostCollectionItem)
            .where(PostCollectionItem.collection_id == c.id)
        ) or 0
        data.append(_serialize(c, count))
    return {"data": data}


@router.get("/{collection_id}")
async def get_collection(
    collection_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PostCollection).where(PostCollection.id == collection_id)
    )
    collection = result.scalar_one_or_none()
    if not collection:
        raise ApiError("NOT_FOUND", "Collection not found", http_status=404)

    items_result = await db.execute(
        select(Post)
        .join(PostCollectionItem, PostCollectionItem.post_id == Post.id)
        .where(PostCollectionItem.collection_id == collection_id)
        .options(selectinload(Post.media), selectinload(Post.product))
        .order_by(PostCollectionItem.order_index.asc())
    )
    posts = list(items_result.scalars().all())

    author_ids = list({p.author_id for p in posts})
    author_map = {}
    if author_ids:
        authors = await db.execute(select(User).where(User.id.in_(author_ids)))
        author_map = {u.id: u for u in authors.scalars()}
    for p in posts:
        p.author = author_map.get(p.author_id)

    from app.api.posts import _serialize_post
    return {
        "data": {
            **_serialize(collection, len(posts)),
            "posts": [_serialize_post(p) for p in posts],
        }
    }


@router.post("/{collection_id}/items")
async def add_to_collection(
    collection_id: UUID,
    body: CollectionItemAdd,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PostCollection).where(PostCollection.id == collection_id)
    )
    collection = result.scalar_one_or_none()
    if not collection:
        raise ApiError("NOT_FOUND", "Collection not found", http_status=404)
    if collection.author_id != user.id:
        raise ApiError("FORBIDDEN", "Not your collection", http_status=403)

    count = await db.scalar(
        select(func.count()).select_from(PostCollectionItem)
        .where(PostCollectionItem.collection_id == collection_id)
    ) or 0

    db.add(PostCollectionItem(
        collection_id=collection_id,
        post_id=body.post_id,
        order_index=count,
    ))
    await db.commit()
    return {"data": {"ok": True}}


@router.delete("/{collection_id}/items/{post_id}")
async def remove_from_collection(
    collection_id: UUID,
    post_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PostCollection).where(PostCollection.id == collection_id)
    )
    collection = result.scalar_one_or_none()
    if not collection or collection.author_id != user.id:
        raise ApiError("FORBIDDEN", "Not your collection", http_status=403)

    item = await db.execute(
        select(PostCollectionItem).where(
            PostCollectionItem.collection_id == collection_id,
            PostCollectionItem.post_id == post_id,
        )
    )
    item_obj = item.scalar_one_or_none()
    if item_obj:
        await db.delete(item_obj)
        await db.commit()
    return {"data": {"ok": True}}


def _serialize(c: PostCollection, item_count: int) -> dict:
    return {
        "id": str(c.id),
        "author_id": str(c.author_id),
        "title": c.title,
        "description": c.description,
        "cover_image_url": c.cover_image_url,
        "item_count": item_count,
        "created_at": c.created_at.isoformat() if c.created_at else None,
    }
