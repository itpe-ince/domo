"""Unit tests for active_auction_end_at supply — Phase 4 #11 §B-13.

3 test cases:
  1. _serialize_post returns active_auction_end_at when attribute is set
  2. _serialize_post returns None when attribute is absent (no auction)
  3. _attach_active_auction_end_at (async): product post with active auction populates end_at;
     general post and product post without active auction get None
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.api.posts import _attach_active_auction_end_at, _serialize_post


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_post(
    *,
    post_id: uuid.UUID | None = None,
    post_type: str = "product",
    active_auction_end_at: datetime | None = None,
    set_attr: bool = True,
) -> MagicMock:
    """Build a minimal Post-like mock for serialization tests."""
    p = MagicMock()
    p.id = post_id or uuid.uuid4()
    p.author_id = uuid.uuid4()
    p.author = MagicMock()
    p.author.id = p.author_id
    p.author.display_name = "Test Artist"
    p.author.avatar_url = None
    p.author.role = "artist"
    p.type = post_type
    p.title = "Test Post"
    p.content = "Test content"
    p.genre = "painting"
    p.tags = ["test"]
    p.language = "ko"
    p.like_count = 0
    p.comment_count = 0
    p.view_count = 0
    p.bluebird_count = 0
    p.status = "published"
    p.digital_art_check = "not_required"
    p.scheduled_at = None
    p.location_name = None
    p.location_lat = None
    p.location_lng = None
    p.created_at = datetime.now(UTC)
    p.media = []
    p.product = None
    p.visibility = "public"
    p.comments_enabled = True
    p.early_access_until = None
    p.early_access_tier = None
    if set_attr:
        p._active_auction_end_at = active_auction_end_at
    return p


# ---------------------------------------------------------------------------
# Test 1 — _serialize_post returns active_auction_end_at when attribute is set
# ---------------------------------------------------------------------------


def test_serialize_post_returns_active_auction_end_at_when_set():
    end_at = datetime.now(UTC) + timedelta(minutes=45)
    post = _make_post(post_type="product", active_auction_end_at=end_at)

    result = _serialize_post(post)

    assert result["active_auction_end_at"] is not None
    # model_dump(mode="json") serializes datetime to ISO string
    assert isinstance(result["active_auction_end_at"], str)
    assert "T" in result["active_auction_end_at"]


# ---------------------------------------------------------------------------
# Test 2 — _serialize_post returns None when _active_auction_end_at not set
# ---------------------------------------------------------------------------


def test_serialize_post_returns_none_when_no_active_auction():
    post = _make_post(post_type="product", active_auction_end_at=None)
    post._active_auction_end_at = None

    result = _serialize_post(post)

    assert result["active_auction_end_at"] is None


# ---------------------------------------------------------------------------
# Test 3 — _attach_active_auction_end_at bulk-loads correctly (no N+1)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_attach_active_auction_end_at_bulk():
    """Verify that:
    - product post with active auction → end_at populated
    - product post without active auction → None
    - general post → None (no query hit expected)
    """
    product_post_id = uuid.uuid4()
    other_product_id = uuid.uuid4()
    future_end_at = datetime.now(UTC) + timedelta(hours=0, minutes=45)

    product_post = MagicMock()
    product_post.id = product_post_id
    product_post.type = "product"

    other_product = MagicMock()
    other_product.id = other_product_id
    other_product.type = "product"

    general_post = MagicMock()
    general_post.id = uuid.uuid4()
    general_post.type = "general"

    # DB mock: returns one row for product_post_id → future_end_at
    db = AsyncMock()
    rows_mock = MagicMock()
    rows_mock.all.return_value = [(product_post_id, future_end_at)]
    db.execute = AsyncMock(return_value=rows_mock)

    posts = [product_post, other_product, general_post]
    await _attach_active_auction_end_at(db, posts)

    # Exactly one DB query should have been executed (no N+1)
    assert db.execute.call_count == 1

    # product_post gets end_at, other_product and general_post get None
    assert product_post._active_auction_end_at == future_end_at
    assert other_product._active_auction_end_at is None
    assert general_post._active_auction_end_at is None
