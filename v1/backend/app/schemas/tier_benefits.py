"""Pydantic schemas for tier benefits API — B-4."""
from __future__ import annotations

import re
from typing import Annotated

from pydantic import BaseModel, Field, field_validator

# Strip all HTML tags (XSS defense)
_HTML_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(text: str) -> str:
    return _HTML_TAG_RE.sub("", text).strip()


VALID_TIERS = frozenset({"subscriber", "sponsor", "follower"})


class TierBenefitsUpsert(BaseModel):
    benefits: Annotated[list[str], Field(max_length=10)] = Field(default_factory=list)
    welcome_message: str | None = Field(default=None, max_length=500)

    @field_validator("benefits", mode="before")
    @classmethod
    def validate_benefits(cls, v: list) -> list[str]:
        if not isinstance(v, list):
            raise ValueError("benefits must be a list")
        if len(v) > 10:
            raise ValueError("benefits cannot exceed 10 items")
        result = []
        for item in v:
            if not isinstance(item, str):
                raise ValueError("each benefit must be a string")
            cleaned = _strip_html(item)
            if len(cleaned) > 200:
                raise ValueError("each benefit cannot exceed 200 characters")
            result.append(cleaned)
        return result

    @field_validator("welcome_message", mode="before")
    @classmethod
    def validate_welcome_message(cls, v: str | None) -> str | None:
        if v is None:
            return None
        cleaned = _strip_html(v)
        if len(cleaned) > 500:
            raise ValueError("welcome_message cannot exceed 500 characters")
        return cleaned or None


class TierBenefitsOut(BaseModel):
    tier: str
    benefits: list[str]
    welcome_message: str | None
    is_platform_default: bool
    # i18n key for UI to display the platform default benefit text
    platform_default_key: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class AllTierBenefitsOut(BaseModel):
    subscriber: TierBenefitsOut
    sponsor: TierBenefitsOut
    follower: TierBenefitsOut
