"""User-related Pydantic schemas — D'-1 tech-debt-cleanup."""
from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, field_validator

# Allowed values for sponsor_validity_days (None = lifetime)
SponsorValidityDays = Literal[1, 7, 30, 90, 365] | None


class UserSponsorSettingsRequest(BaseModel):
    """Body for PATCH /v1/me/sponsor-settings."""

    sponsor_validity_days: SponsorValidityDays = None

    @field_validator("sponsor_validity_days")
    @classmethod
    def validate_days(cls, v: int | None) -> int | None:
        if v is not None and v not in (1, 7, 30, 90, 365):
            raise ValueError(
                "sponsor_validity_days must be one of: null, 1, 7, 30, 90, 365"
            )
        return v


class UserSponsorSettingsOut(BaseModel):
    """Response for GET/PATCH /v1/me/sponsor-settings."""

    sponsor_validity_days: SponsorValidityDays


class UserOut(BaseModel):
    """Minimal user view used by several endpoints."""

    id: UUID
    display_name: str
    role: str
    avatar_url: str | None = None
    sponsor_validity_days: SponsorValidityDays = None

    model_config = {"from_attributes": True}
