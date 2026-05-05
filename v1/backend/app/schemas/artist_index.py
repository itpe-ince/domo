"""Pydantic schemas for artist-index-v1 (A-6) + G'-8 region/genre ranking."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class ArtistIndexEntry(BaseModel):
    """Single artist entry in the global ranking list.

    G'-8 additions:
      rank_region: 1-indexed rank within artist's country_code group (None if not ranked regionally)
      rank_genre:  1-indexed rank within artist's primary_genre group (None if not ranked by genre)
      primary_genre: most-posted genre tag (cron-computed from posts.genre_tags)
    """

    user_id: str
    username: str
    avatar_url: str | None
    country: str | None
    primary_genre: str | None
    score: float
    rank: int
    tier_badge: str | None  # "top_10" | "top_100" | "top_1000" | None
    # G'-8 region/genre ranking fields
    rank_region: int | None = None
    rank_genre: int | None = None


class ArtistIndexListResponse(BaseModel):
    """Response for GET /v1/artists/index."""

    data: list[ArtistIndexEntry]
    next_cursor: str | None = None
    total: int | None = None


class ArtistRankingResponse(BaseModel):
    """Response for GET /v1/artists/{user_id}/index."""

    score: float
    rank: int
    rank_region: int | None = None
    rank_genre: int | None = None
    primary_genre: str | None = None
    tier_badge: str | None
    last_calculated_at: datetime | None
