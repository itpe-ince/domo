"""Pydantic schemas for A-5 search-enhancement endpoints."""
from __future__ import annotations

import re
import uuid
from datetime import datetime

from pydantic import BaseModel, field_validator


# ─── Helpers ─────────────────────────────────────────────────────────────────

# Strip characters that are dangerous in LIKE patterns or potential XSS vectors.
# Keep letters, digits, spaces, and common punctuation useful for search.
_DANGEROUS_CHARS = re.compile(r"[<>\"';&|\\`]")


def sanitize_query(q: str) -> str:
    """Strip potentially dangerous characters from a search query."""
    return _DANGEROUS_CHARS.sub("", q).strip()


# ─── Search history ───────────────────────────────────────────────────────────


class SearchHistoryOut(BaseModel):
    id: uuid.UUID
    query: str
    result_count: int
    searched_at: datetime

    model_config = {"from_attributes": True}


class PopularSearchItem(BaseModel):
    query: str
    count: int


# ─── Popular searches response ────────────────────────────────────────────────


class PopularSearchesOut(BaseModel):
    data: list[PopularSearchItem]


# ─── Search history list ─────────────────────────────────────────────────────


class SearchHistoryListOut(BaseModel):
    data: list[SearchHistoryOut]
