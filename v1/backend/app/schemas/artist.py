from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class RepresentativeWork(BaseModel):
    title: str
    description: str | None = None
    image_url: str
    dimensions: str | None = None
    medium: str | None = None
    year: int | None = None


class HistoryEntry(BaseModel):
    title: str
    year: int | None = None
    description: str | None = None


class ArtistApplicationCreate(BaseModel):
    school: str
    department: str
    graduation_year: int
    is_enrolled: bool = True
    genre_tags: list[str] = Field(..., min_length=1, max_length=5)
    statement: str = Field(..., max_length=200)
    enrollment_proof_url: str
    representative_works: list[RepresentativeWork] = Field(
        ..., min_length=3, max_length=6
    )
    portfolio_urls: list[str] | None = None
    intro_video_url: str | None = None
    exhibitions: list[HistoryEntry] | None = None
    awards: list[HistoryEntry] | None = None


class ArtistApplicationOut(BaseModel):
    id: UUID
    user_id: UUID
    school: str | None = None
    department: str | None = None
    graduation_year: int | None = None
    is_enrolled: bool = True
    genre_tags: list[str] | None = None
    portfolio_urls: list[str] | None = None
    intro_video_url: str | None = None
    sample_images: list[str] | None = None
    enrollment_proof_url: str | None = None
    representative_works: list | None = None
    exhibitions: list | None = None
    awards: list | None = None
    statement: str | None = None
    status: str
    review_note: str | None = None
    reviewed_at: datetime | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class ApplicationReviewRequest(BaseModel):
    note: str | None = None


BADGE_LABELS = {
    "student": "🎓 학생 작가",
    "emerging": "✨ 신진 작가",
    "recommended": "🕊 추천 작가",
    "popular": "🔥 인기 작가",
}
