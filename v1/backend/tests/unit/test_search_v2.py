"""Unit tests for A-5 search-enhancement — search.py helpers.

8 tests covering:
  1. sanitize_query strips XSS chars
  2. sanitize_query preserves normal text
  3. _like escapes LIKE special chars
  4. _resolve_viewer returns (None, None) when no header
  5. _resolve_viewer returns (None, None) for non-Bearer header
  6. popular_searches schema serialization
  7. SearchHistoryOut model_validate from attribute object
  8. sanitize_query strips angle brackets (HTML injection)
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.schemas.search import (
    PopularSearchItem,
    PopularSearchesOut,
    SearchHistoryOut,
    sanitize_query,
)
from app.api.search import _like


# ─── 1. sanitize_query strips dangerous chars ─────────────────────────────────


def test_sanitize_query_strips_dangerous():
    raw = "hello<script>alert(1)</script>"
    result = sanitize_query(raw)
    assert "<" not in result
    assert ">" not in result
    assert "script" in result  # word kept, tags stripped


# ─── 2. sanitize_query preserves normal search text ──────────────────────────


def test_sanitize_query_preserves_normal():
    raw = "  oil painting portrait  "
    result = sanitize_query(raw)
    assert result == "oil painting portrait"


# ─── 3. _like escapes LIKE special chars ──────────────────────────────────────


def test_like_escapes_percent():
    result = _like("50% off")
    # % in query must be escaped so it doesn't act as wildcard
    assert r"\%" in result


def test_like_escapes_underscore():
    result = _like("a_b")
    assert r"\_" in result


# ─── 4. _resolve_viewer returns (None, None) with no header ──────────────────


@pytest.mark.asyncio
async def test_resolve_viewer_no_header():
    from app.api.search import _resolve_viewer
    uid, role = await _resolve_viewer(None)
    assert uid is None
    assert role is None


# ─── 5. _resolve_viewer returns (None, None) for non-Bearer header ───────────


@pytest.mark.asyncio
async def test_resolve_viewer_non_bearer():
    from app.api.search import _resolve_viewer
    uid, role = await _resolve_viewer("Basic dXNlcjpwYXNz")
    assert uid is None
    assert role is None


# ─── 6. PopularSearchesOut serialization ─────────────────────────────────────


def test_popular_searches_out_serialization():
    item = PopularSearchItem(query="portrait", count=42)
    out = PopularSearchesOut(data=[item])
    d = out.model_dump()
    assert d["data"][0] == {"query": "portrait", "count": 42}


# ─── 7. SearchHistoryOut from_attributes ─────────────────────────────────────


def test_search_history_out_from_obj():
    entry_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    obj = SimpleNamespace(
        id=entry_id,
        query="cubism",
        result_count=7,
        searched_at=now,
    )
    out = SearchHistoryOut.model_validate(obj)
    assert out.id == entry_id
    assert out.query == "cubism"
    assert out.result_count == 7
    assert out.searched_at == now


# ─── 8. sanitize_query strips HTML angle brackets ────────────────────────────


def test_sanitize_query_strips_angle_brackets():
    raw = "<b>bold</b>"
    result = sanitize_query(raw)
    assert result == "bbold/b"  # only angle brackets removed, text stays
