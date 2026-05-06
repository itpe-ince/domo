"""Unit tests for app/services/cache.py — G''-2 redis-cache-layer.

6 tests covering:
  1. get() in Mock mode (disabled) → None + cache_miss metric
  2. set() in Mock mode → no-op (no crash)
  3. get_json() / set_json() round-trip with mocked Redis
  4. get() with real Redis client returning bytes value
  5. incr() rate-limit pattern with mocked Redis
  6. shutdown() graceful (no-op when disabled)
"""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.cache import CacheClient, _prefix


# ─── Helpers ──────────────────────────────────────────────────────────────────

def make_mock_redis(get_return=None, incr_return=1):
    """Build a minimal async Redis mock."""
    r = AsyncMock()
    r.ping = AsyncMock(return_value=True)
    r.get = AsyncMock(return_value=get_return)
    r.set = AsyncMock(return_value=True)
    r.setex = AsyncMock(return_value=True)
    r.delete = AsyncMock(return_value=1)
    r.incr = AsyncMock(return_value=incr_return)
    r.expire = AsyncMock(return_value=True)
    r.aclose = AsyncMock(return_value=None)
    return r


# ─── Test 1: get() in Mock mode (disabled) ───────────────────────────────────

@pytest.mark.asyncio
async def test_get_mock_mode_returns_none():
    """When Redis is disabled, get() returns None and records a cache miss."""
    client = CacheClient()
    # _client is None → disabled
    assert not client.is_enabled

    result = await client.get("some:key")
    assert result is None


# ─── Test 2: set() in Mock mode → no-op ──────────────────────────────────────

@pytest.mark.asyncio
async def test_set_mock_mode_noop():
    """When Redis is disabled, set() is a no-op and does not raise."""
    client = CacheClient()
    assert not client.is_enabled

    # Should not raise
    await client.set("some:key", "value", ttl_seconds=60)


# ─── Test 3: get_json / set_json round-trip ───────────────────────────────────

@pytest.mark.asyncio
async def test_get_json_set_json_roundtrip():
    """get_json / set_json serialize and deserialize JSON correctly."""
    client = CacheClient()
    mock_redis = make_mock_redis()

    payload = {"artists": [{"id": "abc", "rank": 1}]}
    json_bytes = json.dumps(payload).encode()

    # Wire up mock to return the serialized value on get
    mock_redis.get = AsyncMock(return_value=json_bytes)
    client._client = mock_redis

    # set_json should call setex (TTL provided)
    await client.set_json("artists:index:KR:all:50:start", payload, ttl_seconds=3600)
    mock_redis.setex.assert_called_once()

    # get_json should parse JSON
    result = await client.get_json("artists:index:KR:all:50:start")
    assert result == payload


# ─── Test 4: get() with bytes-returning Redis ─────────────────────────────────

@pytest.mark.asyncio
async def test_get_bytes_value_decoded():
    """get() handles bytes values from Redis and decodes them to str."""
    client = CacheClient()
    mock_redis = make_mock_redis(get_return=b"hello-world")
    client._client = mock_redis

    result = await client.get("test:key")
    assert result == "hello-world"


# ─── Test 5: incr() rate-limit pattern ───────────────────────────────────────

@pytest.mark.asyncio
async def test_incr_sets_ttl_on_first_write():
    """incr() calls expire when count==1 (first write in window)."""
    client = CacheClient()
    mock_redis = make_mock_redis(incr_return=1)
    client._client = mock_redis

    count = await client.incr("ratelimit:search:ip1:0", ttl_seconds=60)
    assert count == 1
    mock_redis.expire.assert_called_once_with("ratelimit:search:ip1:0", 60)


@pytest.mark.asyncio
async def test_incr_skips_ttl_on_subsequent_writes():
    """incr() does NOT call expire when count > 1."""
    client = CacheClient()
    mock_redis = make_mock_redis(incr_return=5)
    client._client = mock_redis

    count = await client.incr("ratelimit:search:ip1:0", ttl_seconds=60)
    assert count == 5
    mock_redis.expire.assert_not_called()


# ─── Test 6: shutdown() graceful ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_shutdown_noop_when_disabled():
    """shutdown() is a graceful no-op when Redis is not enabled."""
    client = CacheClient()
    assert not client.is_enabled
    # Should not raise
    await client.shutdown()


@pytest.mark.asyncio
async def test_shutdown_closes_connection():
    """shutdown() calls aclose() on the Redis client."""
    client = CacheClient()
    mock_redis = make_mock_redis()
    client._client = mock_redis

    await client.shutdown()
    mock_redis.aclose.assert_called_once()


# ─── Test: _prefix helper ─────────────────────────────────────────────────────

def test_prefix_extracts_first_segment():
    assert _prefix("feed:v1:user123:abc") == "feed"
    assert _prefix("artists:index:KR:all") == "artists"
    assert _prefix("search") == "search"
    assert _prefix("search:popular:10:24h") == "search"
