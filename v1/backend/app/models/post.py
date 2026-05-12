import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

# K-3 ai-artwork-caption: 기본 모델 버전 상수
AI_CAPTION_DEFAULT_MODEL = "gemma4-e4b"


class Post(Base):
    __tablename__ = "posts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    author_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    # 'general' | 'product'
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    genre: Mapped[str | None] = mapped_column(String(50), nullable=True)
    tags: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    language: Mapped[str] = mapped_column(String(10), default="ko")
    like_count: Mapped[int] = mapped_column(Integer, default=0)
    comment_count: Mapped[int] = mapped_column(Integer, default=0)
    view_count: Mapped[int] = mapped_column(Integer, default=0)
    bluebird_count: Mapped[int] = mapped_column(Integer, default=0)

    status: Mapped[str] = mapped_column(String(20), default="pending_review")
    # 'draft' | 'pending_review' | 'published' | 'hidden' | 'deleted'
    digital_art_check: Mapped[str] = mapped_column(String(20), default="pending")

    # publish-controls PDCA #8 §B-2 — visibility + comments_enabled.
    # OQ-1=A: enum 'public'/'followers_only'/'unlisted'. String(20) leaves room for
    # Phase 4 #10 'tier_only' additive expansion.
    visibility: Mapped[str] = mapped_column(
        String(20), nullable=False, default="public",
        comment="OQ-1=A. Phase 4 #10 may add 'tier_only' etc."
    )
    # OQ-3=A: False blocks new POST /comments; existing comments preserved (read-only).
    comments_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True,
        comment="OQ-3=A. False → POST /comments 403; existing comments preserved."
    )
    # Phase 4 #10 artist-tier-release §B-2
    early_access_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None,
        comment="Phase 4 #10. UTC. NULL=early_access off.",
    )
    early_access_tier: Mapped[str | None] = mapped_column(
        String(20), nullable=True, default=None,
        comment="Phase 4 #10. 'subscriber'|'sponsor'|'follower'. NULL=off.",
    )
    # 'pending' | 'approved' | 'rejected' | 'not_required'

    # K-3 ai-artwork-caption — Phase 9
    # AI 생성 캡션 (한국어 원본, LLM Gateway vision 호출 결과)
    ai_caption: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    # 5 locale 번역 JSONB {"en": "...", "ja": "...", "zh": "...", "es": "..."}
    ai_caption_locale_translations: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )
    # 캡션 생성에 사용한 LLM 모델 식별자 (예: "gemma4-e4b")
    ai_caption_model_version: Mapped[str | None] = mapped_column(
        String(50), nullable=True, default=None
    )
    # 캡션 최초 생성 시각 (NULL이면 아직 미생성 → batch sweep 대상)
    ai_caption_generated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )
    # 작가 수동 입력 캡션 — 이 값이 있으면 AI 캡션 무시 (effective_caption 로직)
    caption_override: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)

    scheduled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    location_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    location_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    location_lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_live: Mapped[bool] = mapped_column(Boolean, default=False)
    live_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    # K-5 LLM 도슨트 컬럼 (alembic 0079)
    # README 비전 "스토리텔링 hub"과 "AI 시대 작가의 정체성 재정의" 구현
    # 작가 해설이 항상 우선 노출, AI 도슨트는 작가 요청 시 생성
    artist_docent_text: Mapped[str | None] = mapped_column(
        Text, nullable=True, default=None,
        comment="K-5: 작가가 직접 작성한 해설 (AI 도슨트보다 우선 노출)",
    )
    ai_docent_text: Mapped[str | None] = mapped_column(
        Text, nullable=True, default=None,
        comment="K-5: LLM 생성 원본 해설 (한국어, 3~5문단 큐레이터 톤)",
    )
    ai_docent_translations: Mapped[dict] = mapped_column(
        JSONB, server_default="{}", nullable=False, default=dict,
        comment="K-5: 5 locale 번역 캐시 {'en':..., 'ja':..., 'zh':..., 'es':...}",
    )
    ai_docent_model_version: Mapped[str | None] = mapped_column(
        String(50), nullable=True, default=None,
        comment="K-5: 생성에 사용된 모델 식별자 (예: gemma4-e4b)",
    )
    ai_docent_generated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None,
        comment="K-5: AI 도슨트 최초 생성 시각 (24h idempotency 체크용)",
    )
    ai_docent_opted_out: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False,
        comment="K-5: 작가 AI 도슨트 비활성화 플래그 (opt-out 방식)",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    media: Mapped[list["MediaAsset"]] = relationship(
        back_populates="post", cascade="all, delete-orphan"
    )
    product: Mapped["ProductPost | None"] = relationship(
        back_populates="post", uselist=False, cascade="all, delete-orphan"
    )


class MediaAsset(Base):
    __tablename__ = "media_assets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    post_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("posts.id", ondelete="CASCADE"),
        nullable=False,
    )
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    # 'image' | 'video' | 'external_embed'
    url: Mapped[str] = mapped_column(Text, nullable=False)
    thumbnail_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_sec: Mapped[int | None] = mapped_column(Integer, nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    external_source: Mapped[str | None] = mapped_column(String(20), nullable=True)
    external_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    is_making_video: Mapped[bool] = mapped_column(Boolean, default=False)

    # editor-media-ux PDCA #4 — optional per-media caption.
    # Max 280 chars enforced at Pydantic schema level (MediaAssetIn.caption)
    # to allow future limit changes without data migration.
    caption: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)

    # editor-image-studio PDCA #6-image — non-destructive edit metadata (alembic 0037).
    # Schema validated at Pydantic level (CropMetaSchema in app/schemas/media_transform.py).
    # OQ-3 = A: stores rotate/crop/mosaic/watermark ops to allow re-entry restoration.
    crop_meta: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=None)

    # editor-image-studio PDCA #6-image v1.1 — original key preserved on first transform.
    # OQ-D-A = C, OQ-D-C = B: ensures re-edits always re-process from the original
    # (avoids cumulative re-encoding loss). NULL until first transform; code falls
    # back to current storage_key when NULL.
    original_storage_key: Mapped[str | None] = mapped_column(
        String(512), nullable=True, default=None
    )

    # M4 storage abstraction
    storage_provider: Mapped[str] = mapped_column(String(20), default="local")
    # 'local' | 's3' | 'external'
    storage_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    thumb_small_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    thumb_medium_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    thumb_large_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    post: Mapped["Post"] = relationship(back_populates="media")


class ProductPost(Base):
    __tablename__ = "product_posts"

    post_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("posts.id", ondelete="CASCADE"),
        primary_key=True,
    )
    is_auction: Mapped[bool] = mapped_column(Boolean, default=False)
    is_buy_now: Mapped[bool] = mapped_column(Boolean, default=False)
    # G'-10 price-unit-consistency: cents (BigInteger) — was Numeric(12,2) dollars.
    # API accepts dollars from UI, backend converts to cents before persistence.
    buy_now_price: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    # B'-1: buy_now_currency = native currency the artist priced in (USD/KRW/EUR/JPY).
    # currency = auction currency (kept KRW default for backward compat).
    buy_now_currency: Mapped[str] = mapped_column(String(3), default="USD")
    currency: Mapped[str] = mapped_column(String(3), default="KRW")
    dimensions: Mapped[str | None] = mapped_column(String(100), nullable=True)
    medium: Mapped[str | None] = mapped_column(String(100), nullable=True)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_sold: Mapped[bool] = mapped_column(Boolean, default=False)

    post: Mapped["Post"] = relationship(back_populates="product")


class Follow(Base):
    __tablename__ = "follows"

    follower_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True
    )
    followee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Like(Base):
    __tablename__ = "likes"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True
    )
    post_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("posts.id"), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Comment(Base):
    __tablename__ = "comments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    post_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("posts.id"), nullable=False
    )
    author_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("comments.id"), nullable=True
    )
    # Phase 1: always NULL (1-depth only). 2차에서 대댓글 활성화.
    content: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="visible")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
