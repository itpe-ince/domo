"""Pydantic schemas for Series CRUD + publish controls — PDCA #8 §B-6.

Visibility type: OQ-1=A (enum 'public'/'followers_only'/'unlisted').
PostPublishRequest.publish_at validator: OQ-6=A (5min ~ 1yr range).
"""
import uuid
from datetime import datetime, timedelta, timezone
from typing import Literal

from pydantic import BaseModel, Field, field_validator

# OQ-1=A: three-value enum; String(20) in DB leaves room for Phase 4 #10 expansion.
Visibility = Literal["public", "followers_only", "unlisted"]

# Phase 4 #10 artist-tier-release §B-4
EarlyAccessTier = Literal["subscriber", "sponsor", "follower"]
EARLY_ACCESS_DURATIONS: frozenset[int] = frozenset({1, 6, 24, 72, 168})


# ─── Series ─────────────────────────────────────────────────────────────────


class SeriesCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: str | None = Field(None, max_length=2000)
    cover_url: str | None = None  # OQ-4=C: manual first; fallback in frontend


class SeriesPatch(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = Field(None, max_length=2000)
    cover_url: str | None = None


class SeriesOut(BaseModel):
    id: uuid.UUID
    author_id: uuid.UUID
    title: str
    description: str | None
    cover_url: str | None
    created_at: datetime
    updated_at: datetime
    post_count: int = 0

    model_config = {"from_attributes": True}


class SeriesMemberOut(BaseModel):
    """Single post entry inside GET /v1/series/{id} response."""

    id: uuid.UUID
    title: str | None
    status: str
    order_index: int
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── Publish ────────────────────────────────────────────────────────────────


class PostPublishRequest(BaseModel):
    """Body for POST /v1/posts/{id}/publish (Step 2 endpoint, schemas defined in Step 1).

    publish_at=None → immediate publish.
    publish_at set  → scheduled publish (OQ-6=A: 5min ≤ delay ≤ 1yr).
    """

    publish_at: datetime | None = Field(
        None,
        description="None=즉시 발행. 설정 시 예약 발행. UTC 권장.",
    )
    visibility: Visibility = "public"
    comments_enabled: bool = True
    series_ids: list[uuid.UUID] = Field(default_factory=list)
    # Phase 4 #10 artist-tier-release §B-4
    early_access_duration: int | None = Field(None,
        description="우선 공개 기간(시간). 허용값: 1|6|24|72|168. None=비활성.")
    early_access_tier: EarlyAccessTier | None = Field(None)

    @field_validator("publish_at", mode="before")
    @classmethod
    def _validate_publish_at(cls, v):
        if v is None:
            return v
        if isinstance(v, str):
            v = datetime.fromisoformat(v)
        if v.tzinfo is None:
            # OQ-6=A / R-4: coerce naive datetime to UTC (TZ mismatch mitigation)
            v = v.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        if v < now + timedelta(minutes=5):
            raise ValueError("SCHEDULED_AT_TOO_SOON")
        if v > now + timedelta(days=365):
            raise ValueError("SCHEDULED_AT_TOO_FAR")
        return v

    @field_validator("early_access_duration", mode="before")
    @classmethod
    def _validate_duration(cls, v):
        if v is None:
            return v
        if int(v) not in EARLY_ACCESS_DURATIONS:
            raise ValueError(f"INVALID_DURATION: must be one of {sorted(EARLY_ACCESS_DURATIONS)}")
        return int(v)

    def model_post_init(self, __context) -> None:
        d = self.early_access_duration
        t = self.early_access_tier
        if (d is None) != (t is None):
            raise ValueError("TIER_FIELDS_INCONSISTENT: 둘 다 set이거나 둘 다 None")


class PostPublishResponse(BaseModel):
    id: uuid.UUID
    status: str
    visibility: Visibility
    comments_enabled: bool
    scheduled_at: datetime | None
    series_count: int
    updated_at: datetime
    # Phase 4 #10
    early_access_until: datetime | None = None
    early_access_tier: str | None = None


class PostSeriesUpdateIn(BaseModel):
    """Body for POST /v1/posts/{id}/series — replace full series membership list."""

    series_ids: list[uuid.UUID] = Field(...)
