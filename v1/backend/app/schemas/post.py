from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.schemas.media_transform import CropMetaSchema


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
    # editor-media-ux PDCA #4 — optional caption (max 280 chars).
    # Validated here so the constraint can change without DB migration.
    caption: str | None = Field(None, max_length=280)
    # editor-image-studio PDCA #6-image — non-destructive edit metadata.
    # Persisted in media_assets.crop_meta JSONB. Stored on POST /transform.
    crop_meta: CropMetaSchema | None = None


class MediaAssetOut(MediaAssetIn):
    id: UUID
    order_index: int

    class Config:
        from_attributes = True


class MediaPatchRequest(BaseModel):
    """PATCH /v1/media/{id} request body — editor-media-ux PDCA #4.

    Currently only caption is editable. Image transforms use the dedicated
    POST /v1/media/{id}/transform endpoint (editor-image-studio PDCA #6-image).
    """

    caption: str | None = Field(None, max_length=280)


class ProductPostIn(BaseModel):
    """Input schema for product post fields.

    G'-10: buy_now_price is accepted as a float/int dollar amount from the UI
    and stored as cents (BigInteger) in the DB. The validator converts on ingest.
    Frontend sends dollars (e.g. 50.00); DB stores 5000 cents.
    """

    is_auction: bool = False
    is_buy_now: bool = False
    # UI sends dollar amount; we convert to cents on validation.
    buy_now_price: float | int | None = None
    currency: str = "KRW"
    dimensions: str | None = None
    medium: str | None = None
    year: int | None = None

    @field_validator("buy_now_price", mode="before")
    @classmethod
    def dollars_to_cents(cls, v: object) -> int | None:
        """Convert dollar input (float) to cents (int) for DB storage."""
        if v is None:
            return None
        try:
            return round(float(v) * 100)
        except (TypeError, ValueError) as exc:
            raise ValueError("buy_now_price must be a numeric dollar amount") from exc


class ProductPostOut(BaseModel):
    """Output schema — buy_now_price exposed as cents integer.

    G'-10: API response uses price_cents semantics.
    Frontend uses formatPriceCents() to render display value.
    """

    is_auction: bool
    is_buy_now: bool
    # Cents integer (e.g. 5000 = $50.00 / ₩5000)
    buy_now_price: int | None = None
    currency: str
    dimensions: str | None = None
    medium: str | None = None
    year: int | None = None
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
    from_draft_id: UUID | None = None


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
    # publish-controls PDCA #8 §B-6 — visibility + comments_enabled surfaced to API.
    # Defaults match DB defaults so existing serialization is backward-compatible.
    visibility: str = "public"
    comments_enabled: bool = True
    # Phase 4 #10 artist-tier-release §B-4
    early_access_until: datetime | None = None
    early_access_tier: str | None = None
    is_tier_locked: bool = False  # viewer 기준 계산값 — get_post에서만 채움 (PR2)
    # Phase 4 #11 auction-promotion-suite — OQ-D-1=A
    # active auction end_at for feed card D-1h compact countdown (AC-12).
    # None when no active auction exists for this post.
    active_auction_end_at: datetime | None = None


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
