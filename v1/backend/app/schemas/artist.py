from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ArtistApplicationCreate(BaseModel):
    portfolio_urls: list[str] | None = None
    school: str | None = None
    intro_video_url: str | None = None
    sample_images: list[str] | None = None
    statement: str | None = None


class ArtistApplicationOut(BaseModel):
    id: UUID
    user_id: UUID
    portfolio_urls: list[str] | None = None
    school: str | None = None
    intro_video_url: str | None = None
    sample_images: list[str] | None = None
    statement: str | None = None
    status: str
    review_note: str | None = None
    reviewed_at: datetime | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class ApplicationReviewRequest(BaseModel):
    note: str | None = None
