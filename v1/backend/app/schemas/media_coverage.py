"""Pydantic schemas for MediaCoverage — C-4 media-coverage-cms."""
from __future__ import annotations

import re
import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field, field_validator, model_validator

# Allowed coverage types (mirrors model constant)
COVERAGE_TYPES = ("article", "youtube", "radio", "podcast", "tv")
SUPPORTED_LOCALES = ("ko", "en", "ja", "zh", "es")

# ──────────────────────────────────────────────────────────────────────────────
# HTML sanitisation (strip dangerous tags/attrs — XSS prevention)
# We use a minimal allowlist approach: strip all HTML tags entirely from
# title and description since they are rendered as plain text in the UI.
# ──────────────────────────────────────────────────────────────────────────────
_TAG_RE = re.compile(r"<[^>]+>", re.IGNORECASE)
_SCRIPT_RE = re.compile(r"<script[\s\S]*?>[\s\S]*?</script>", re.IGNORECASE)
_IFRAME_RE = re.compile(r"<iframe[\s\S]*?>[\s\S]*?</iframe>", re.IGNORECASE)


def _strip_html(value: str) -> str:
    """Remove all HTML tags from a string (XSS prevention)."""
    if not value:
        return value
    # Remove script/iframe blocks first
    value = _SCRIPT_RE.sub("", value)
    value = _IFRAME_RE.sub("", value)
    # Strip remaining tags
    value = _TAG_RE.sub("", value)
    return value.strip()


# ──────────────────────────────────────────────────────────────────────────────
# Request schemas
# ──────────────────────────────────────────────────────────────────────────────

class AdminCreateMediaCoverageRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    coverage_type: str = Field(...)
    source_name: str = Field(..., min_length=1, max_length=100)
    external_url: str = Field(..., min_length=1)
    thumbnail_url: str | None = None
    published_at: date
    artist_id: uuid.UUID | None = None
    description: str | None = None
    locale: str = Field("ko")
    is_published: bool = False
    is_featured: bool = False

    @field_validator("title")
    @classmethod
    def sanitize_title(cls, v: str) -> str:
        return _strip_html(v)

    @field_validator("description")
    @classmethod
    def sanitize_description(cls, v: str | None) -> str | None:
        if v is None:
            return None
        return _strip_html(v) or None

    @field_validator("coverage_type")
    @classmethod
    def validate_coverage_type(cls, v: str) -> str:
        if v not in COVERAGE_TYPES:
            raise ValueError(f"coverage_type must be one of {COVERAGE_TYPES}")
        return v

    @field_validator("locale")
    @classmethod
    def validate_locale(cls, v: str) -> str:
        if v not in SUPPORTED_LOCALES:
            raise ValueError(f"locale must be one of {SUPPORTED_LOCALES}")
        return v


class AdminPatchMediaCoverageRequest(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = None
    thumbnail_url: str | None = None
    is_published: bool | None = None
    is_featured: bool | None = None
    source_name: str | None = Field(None, min_length=1, max_length=100)
    coverage_type: str | None = None
    external_url: str | None = None
    published_at: date | None = None
    locale: str | None = None
    artist_id: uuid.UUID | None = None

    @field_validator("title")
    @classmethod
    def sanitize_title(cls, v: str | None) -> str | None:
        if v is None:
            return None
        return _strip_html(v) or None

    @field_validator("description")
    @classmethod
    def sanitize_description(cls, v: str | None) -> str | None:
        if v is None:
            return None
        return _strip_html(v) or None

    @field_validator("coverage_type")
    @classmethod
    def validate_coverage_type(cls, v: str | None) -> str | None:
        if v is None:
            return None
        if v not in COVERAGE_TYPES:
            raise ValueError(f"coverage_type must be one of {COVERAGE_TYPES}")
        return v

    @field_validator("locale")
    @classmethod
    def validate_locale(cls, v: str | None) -> str | None:
        if v is None:
            return None
        if v not in SUPPORTED_LOCALES:
            raise ValueError(f"locale must be one of {SUPPORTED_LOCALES}")
        return v

    @model_validator(mode="after")
    def at_least_one_field(self) -> "AdminPatchMediaCoverageRequest":
        fields = (
            self.title,
            self.description,
            self.thumbnail_url,
            self.is_published,
            self.is_featured,
            self.source_name,
            self.coverage_type,
            self.external_url,
            self.published_at,
            self.locale,
            self.artist_id,
        )
        if all(f is None for f in fields):
            raise ValueError("At least one field must be provided for PATCH")
        return self


# ──────────────────────────────────────────────────────────────────────────────
# Response schema
# ──────────────────────────────────────────────────────────────────────────────

class MediaCoverageOut(BaseModel):
    id: uuid.UUID
    title: str
    coverage_type: str
    source_name: str
    external_url: str
    thumbnail_url: str | None
    published_at: date
    artist_id: uuid.UUID | None
    description: str | None
    locale: str
    is_published: bool
    is_featured: bool
    created_by_admin_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
