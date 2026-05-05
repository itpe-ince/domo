"""Pydantic schemas for C-3 multi-language-story bio endpoints."""
from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field

LOCALE_PATTERN = "^(ko|en|ja|zh|es)$"


class BioTranslationOut(BaseModel):
    user_id: str
    locale: str
    bio: str
    is_machine_translated: bool
    last_edited_at: datetime
    last_translated_at: datetime | None


class BioTranslateResponse(BaseModel):
    """Response for POST /me/bio/translate — all 5 locale translations."""
    translations: dict[str, str]  # locale → translated bio text


class BioLocaleOut(BaseModel):
    """Response for GET /users/{id}/bio?locale=... and PATCH /me/bio/{locale}."""
    user_id: str
    locale: str
    bio: str
    is_machine_translated: bool
    last_edited_at: datetime
    last_translated_at: datetime | None


class PatchBioRequest(BaseModel):
    bio: Annotated[str, Field(min_length=1, max_length=2000)]
