from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class MediaAssetIn(BaseModel):
    type: str  # 'image' | 'video' | 'external_embed'
    url: str
    thumbnail_url: str | None = None
    width: int | None = None
    height: int | None = None
    duration_sec: int | None = None
    size_bytes: int | None = None
    external_source: str | None = None
    external_id: str | None = None
    is_making_video: bool = False


class MediaAssetOut(MediaAssetIn):
    id: UUID
    order_index: int

    class Config:
        from_attributes = True


class ProductPostIn(BaseModel):
    is_auction: bool = False
    is_buy_now: bool = False
    buy_now_price: Decimal | None = None
    currency: str = "KRW"
    dimensions: str | None = None
    medium: str | None = None
    year: int | None = None


class ProductPostOut(ProductPostIn):
    is_sold: bool

    class Config:
        from_attributes = True


class PostCreate(BaseModel):
    type: str = Field(..., pattern="^(general|product)$")
    title: str | None = None
    content: str | None = None
    genre: str | None = None
    tags: list[str] | None = None
    language: str = "ko"
    media: list[MediaAssetIn] = []
    product: ProductPostIn | None = None
    scheduled_at: datetime | None = None
    location_name: str | None = None
    location_lat: float | None = None
    location_lng: float | None = None


class PostAuthor(BaseModel):
    id: UUID
    display_name: str
    avatar_url: str | None = None
    role: str

    class Config:
        from_attributes = True


class PostOut(BaseModel):
    id: UUID
    author: PostAuthor
    type: str
    title: str | None = None
    content: str | None = None
    genre: str | None = None
    tags: list[str] | None = None
    language: str
    like_count: int
    comment_count: int
    view_count: int
    bluebird_count: int
    status: str
    digital_art_check: str
    scheduled_at: datetime | None = None
    location_name: str | None = None
    location_lat: float | None = None
    location_lng: float | None = None
    created_at: datetime
    media: list[MediaAssetOut] = []
    product: ProductPostOut | None = None


class CommentIn(BaseModel):
    content: str


class CommentOut(BaseModel):
    id: UUID
    post_id: UUID
    author: PostAuthor
    content: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True
