"""Integration tests for G''-2 redis-cache-layer.

3 tests covering cache-aside behaviour in endpoints:
  1. search popular — cache hit/miss via mock cache
  2. artist index — cache hit/miss via mock cache
  3. rate limit Redis backend — in-memory fallback when Redis disabled

These tests mock the cache service to avoid requiring a real Redis instance.
They verify that:
  - Endpoints call cache.get_json before querying DB (cache hit → DB bypassed)
  - Endpoints call cache.set_json after a DB miss
  - Rate limit in-memory fallback works correctly (no Redis crash)
"""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch, MagicMock

import pytest


# ─── Test 1: Search popular cache hit ────────────────────────────────────────

@pytest.mark.asyncio
async def test_popular_searches_cache_hit():
    """popular_searches returns cached data without querying DB on hit."""
    from app.api.search import popular_searches

    cached_payload = [{"query": "watercolor", "count": 42}]

    # Inject a mock cache that returns hit
    with patch("app.api.search.cache") as mock_cache:
        mock_cache.get_json = AsyncMock(return_value=cached_payload)
        mock_cache.set_json = AsyncMock()

        mock_db = AsyncMock()

        result = await popular_searches(limit=10, db=mock_db, _rl=None)

        # cache was checked
        mock_cache.get_json.assert_called_once_with(
            "search:popular:10:24h", prefix="search"
        )
        # DB was NOT queried (no execute call)
        mock_db.execute.assert_not_called()
        # Response contains cached data
        assert result.data[0].query == "watercolor"
        assert result.data[0].count == 42


# ─── Test 2: Search popular cache miss → DB query + cache set ────────────────

@pytest.mark.asyncio
async def test_popular_searches_cache_miss_queries_db():
    """popular_searches queries DB on cache miss and populates cache."""
    from app.api.search import popular_searches

    with patch("app.api.search.cache") as mock_cache:
        mock_cache.get_json = AsyncMock(return_value=None)  # cache miss
        mock_cache.set_json = AsyncMock()

        # Simulate DB rows
        mock_row = MagicMock()
        mock_row.query = "abstract"
        mock_row.cnt = 7
        mock_result = MagicMock()
        mock_result.all.return_value = [mock_row]

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await popular_searches(limit=10, db=mock_db, _rl=None)

        # DB was queried
        mock_db.execute.assert_called_once()
        # Cache was populated
        mock_cache.set_json.assert_called_once()
        call_args = mock_cache.set_json.call_args
        assert call_args[0][0] == "search:popular:10:24h"
        assert call_args[0][2] == 300  # TTL 5 min
        # Response contains DB data
        assert result.data[0].query == "abstract"


# ─── Test 3: Artist index cache hit ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_artist_index_cache_hit():
    """get_artist_index returns cached data without querying DB on hit."""
    from app.api.artists import get_artist_index

    cached_response = {
        "data": {
            "data": [{"user_id": "uuid-1", "username": "ArtistA", "rank": 1}],
            "next_cursor": None,
            "total": None,
        }
    }

    with patch("app.api.artists.cache") as mock_cache:
        mock_cache.get_json = AsyncMock(return_value=cached_response)
        mock_cache.set_json = AsyncMock()

        mock_db = AsyncMock()

        result = await get_artist_index(
            region=None, genre=None, limit=50, cursor=None, db=mock_db, _rl=None
        )

        # cache was checked
        mock_cache.get_json.assert_called_once()
        # DB was NOT queried
        mock_db.execute.assert_not_called()
        # Response matches cache
        assert result == cached_response


# ─── Test 4 (bonus): rate limit in-memory fallback ───────────────────────────

@pytest.mark.asyncio
async def test_rate_limit_memory_fallback_no_crash():
    """check_rate_limit uses in-memory counter when Redis is disabled."""
    from app.core.rate_limit import check_rate_limit, RateLimitResult

    # Ensure Redis is None
    with patch("app.core.rate_limit.get_redis", return_value=None):
        result = await check_rate_limit("test_scope", "127.0.0.1", limit=5, window_sec=60)

    assert isinstance(result, RateLimitResult)
    assert result.allowed is True
    assert result.limit == 5
    assert result.remaining <= 5


@pytest.mark.asyncio
async def test_rate_limit_memory_fallback_enforces_limit():
    """In-memory fallback respects limit (count > limit → not allowed)."""
    import time
    from app.core.rate_limit import check_rate_limit

    # Use a unique key so this test doesn't bleed into others
    unique_scope = f"exhaust_test_{time.time()}"
    limit = 3

    with patch("app.core.rate_limit.get_redis", return_value=None):
        # Exhaust the limit
        for _ in range(limit):
            r = await check_rate_limit(unique_scope, "ip_unique", limit=limit, window_sec=60)
            assert r.allowed is True

        # One more should be rejected
        r = await check_rate_limit(unique_scope, "ip_unique", limit=limit, window_sec=60)
        assert r.allowed is False
        assert r.remaining == 0
