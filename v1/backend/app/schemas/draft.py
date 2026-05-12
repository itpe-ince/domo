"""Draft Pydantic schemas — editor-draft-autosave PDCA.

Draft는 status='draft'인 Post를 의미. 발행되지 않은 임시저장 컨텐츠.
- title/content 빈 값 허용 (둘 다 None/빈 문자열도 OK)
- product 필드는 type='product'여도 draft 단계에서 생략 가능
- 자동저장(localStorage) 외에 명시적 "임시저장" 버튼으로 서버에 저장
"""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.post import MediaAssetIn, MediaAssetOut, ProductPostIn, ProductPostOut


class DraftUpsertBody(BaseModel):
    """Draft 생성/업데이트 공통 body.

    `draft_id` 있으면 update, 없으면 create.
    """
    draft_id: UUID | None = None
    type: str = Field("general", pattern="^(general|product)$")
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


class DraftView(BaseModel):
    """Draft 응답 model. status 필드 제외 (항상 'draft').

    `updated_at`은 Q-5 충돌 해결의 timestamp 비교 기준.
    """
    id: UUID
    type: str
    title: str | None = None
    content: str | None = None
    genre: str | None = None
    tags: list[str] | None = None
    language: str
    media: list[MediaAssetOut] = []
    product: ProductPostOut | None = None
    scheduled_at: datetime | None = None
    location_name: str | None = None
    location_lat: float | None = None
    location_lng: float | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DraftListResponse(BaseModel):
    data: list[DraftView]
    total: int
    limit: int
    offset: int


class DraftDeleteResponse(BaseModel):
    deleted: bool
    id: UUID
