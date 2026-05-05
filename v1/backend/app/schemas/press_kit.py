"""Press kit schemas — C-2 press-kit-auto-export."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class PressKitOut(BaseModel):
    """Response schema for a generated press kit."""

    id: uuid.UUID
    artist_id: uuid.UUID
    locale: str
    storage_key: str
    download_url: str  # presigned or local URL for PDF download
    file_size_bytes: int
    page_count: int
    interview_id: uuid.UUID | None = None
    is_public: bool
    expires_at: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


class PressKitGenerateRequest(BaseModel):
    """Admin: trigger press kit generation for an artist."""

    artist_id: uuid.UUID
    locale: str = Field(default="ko", pattern="^(ko|en|ja|zh|es)$")
    force: bool = Field(
        default=False,
        description="Set true to regenerate even if a valid 30d cache exists.",
    )
