"""Pydantic schemas for artist interviews — C-1 ai-artist-interview-generation."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


VALID_LOCALES = frozenset({"ko", "en", "ja", "zh", "es"})
VALID_STATUSES = frozenset(
    {"draft", "admin_review", "approved", "published", "rejected", "archived"}
)


class AdminGenerateInterviewRequest(BaseModel):
    """POST /admin/artist-interviews/generate"""

    artist_id: UUID
    locale: str = Field(default="ko", pattern="^(ko|en|ja|zh|es)$")


class AdminPatchInterviewRequest(BaseModel):
    """PATCH /admin/artist-interviews/{id}"""

    status: str | None = Field(
        default=None, pattern="^(approved|rejected)$"
    )
    title: str | None = Field(default=None, max_length=200)
    body_markdown: str | None = None
    review_note: str | None = Field(default=None, max_length=2000)


class ArtistInterviewOut(BaseModel):
    """Serialised ArtistInterview row — admin views."""

    id: UUID
    artist_id: UUID
    locale: str
    title: str
    body_markdown: str
    status: str
    llm_model: str | None
    reviewed_by_admin_id: UUID | None
    reviewed_at: datetime | None
    review_note: str | None
    artist_consent_at: datetime | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ArtistInterviewPublicOut(BaseModel):
    """Public view — omits admin-internal fields."""

    id: UUID
    artist_id: UUID
    locale: str
    title: str
    body_markdown: str
    published_at: datetime  # created_at proxy

    class Config:
        from_attributes = True
