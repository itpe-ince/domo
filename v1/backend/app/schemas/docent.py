"""Pydantic 스키마 — K-5 LLM 도슨트 (llm-docent-artwork).

Phase 9 K-5: 작품 상세 도슨트 API 요청/응답 스키마.
도슨트는 작가 직접 해설(artist_docent_text)과 AI 생성 해설(ai_docent_text)을
hybrid 방식으로 제공한다.

README 비전 "스토리텔링 hub" — 컬렉터와 관람자의 작품 체류 시간을 높이는 핵심 기능.
"""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class DocentGenerateResponse(BaseModel):
    """POST /api/posts/{id}/docent/generate 응답.

    LLM Gateway 미설정(Mock 모드) 시:
      ai_docent_text=None, message="AI 도슨트 생성 서비스가 비활성화 상태입니다."
    """

    ai_docent_text: str | None = None
    ai_docent_model_version: str | None = None
    ai_docent_generated_at: datetime | None = None
    ai_docent_translations: dict[str, str] = Field(default_factory=dict)
    message: str | None = None


class DocentPatchRequest(BaseModel):
    """PATCH /api/posts/{id}/docent 요청 본문.

    작가가 직접 작성한 해설을 저장한다.
    None 전송 시 artist_docent_text 삭제 (AI 도슨트만 표시).
    """

    artist_docent_text: str | None = Field(
        None,
        max_length=5000,
        description="작가가 직접 작성한 해설 (최대 5000자). None 전송 시 삭제.",
    )


class DocentPatchResponse(BaseModel):
    """PATCH /api/posts/{id}/docent 응답."""

    artist_docent_text: str | None = None
    updated_at: datetime


class DocentOptOutRequest(BaseModel):
    """PATCH /api/posts/{id}/docent/opt-out 요청 본문."""

    opted_out: bool


class DocentOptOutResponse(BaseModel):
    """PATCH /api/posts/{id}/docent/opt-out 응답."""

    ai_docent_opted_out: bool
    message: str


class DocentResponse(BaseModel):
    """GET /api/posts/{id}/docent 응답.

    locale_docent 결정 로직:
      locale=ko  → ai_docent_text (원본)
      locale 기타 → ai_docent_translations[locale]
                    없으면 → ai_docent_text (한국어 fallback)
      opted_out=True → ai_docent_text=None, locale_docent=None
    """

    post_id: UUID
    artist_docent_text: str | None = None
    ai_docent_text: str | None = None
    ai_docent_opted_out: bool = False
    ai_docent_generated_at: datetime | None = None
    locale_docent: str | None = None
    locale: str = "ko"
