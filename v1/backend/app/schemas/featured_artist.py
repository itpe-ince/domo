"""Pydantic schemas for featured artists — G'-7 admin-featured-artists."""
from __future__ import annotations

from datetime import date
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class AdminCreateFeaturedArtistRequest(BaseModel):
    """POST /admin/featured-artists — admin creates a featured artist entry."""

    artist_id: UUID
    month: date = Field(..., description="First day of the month, e.g. 2026-05-01")
    curation_note: str | None = Field(default=None, max_length=1000)

    @field_validator("month")
    @classmethod
    def validate_month_is_first_day(cls, v: date) -> date:
        if v.day != 1:
            raise ValueError("month must be the first day of the month (e.g. 2026-05-01)")
        return v


class FeaturedArtistOut(BaseModel):
    """Serialized FeaturedArtist row — returned by admin endpoints."""

    id: UUID
    artist_id: UUID
    month: date
    curation_note: str | None
    is_active: bool
    created_at: str  # ISO string
    created_by_admin_id: UUID

    class Config:
        from_attributes = True


class ArtistFeaturedView(BaseModel):
    """Public view of the current featured artist.

    Returned by GET /v1/featured/artist/current.
    Combines user info + curation metadata.
    """

    user_id: str
    username: str
    avatar_url: str | None
    bio: str | None
    country: str | None
    primary_genre: str | None
    tier_badge: str | None
    rank: int | None
    score: float | None
    curation_note: str | None
    month: str  # "YYYY-MM"
    # True = from featured_artists table, False = fallback to artist_index rank 1
    is_curated: bool
