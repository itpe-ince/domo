"""Redis cache service — G''-2 redis-cache-layer.

CacheClient wraps redis.asyncio with:
- Graceful Mock mode: when REDIS_URL is not set all methods are no-ops.
- JSON helpers: get_json / set_json for structured payloads.
- Rate-limit helper: incr (INCR + EXPIRE on first write).
- Prometheus metrics: cache_hit / cache_miss / cache_set / cache_invalidate.

Usage:
    from app.services.cache import cache

    # Cache-aside pattern
    cached = await cache.get_json("my:key")
    if cached is None:
        cached = await compute_expensive()
        await cache.set_json("my:key", cached, ttl_seconds=300)

PII constraint: never store email, phone, or payment data in cache values.
"""
from __future__ import annotations

import json
import logging

from app.core.config import get_settings
from app.core.metrics import (
    cache_hit_total,
    cache_invalidate_total,
    cache_miss_total,
    cache_set_total,
)

log = logging.getLogger(__name__)


class CacheClient:
    """Async Redis cache client with graceful Mock fallback."""

    def __init__(self) -> None:
        self._client = None  # redis.asyncio.Redis | None

    async def connect(self) -> None:
        """Connect to Redis; silently disable when REDIS_URL is not set."""
        settings = get_settings()
        if not settings.redis_url:
            log.info("Redis disabled (REDIS_URL not set) — cache is a no-op")
            return

        try:
            import redis.asyncio as redis  # type: ignore[import]

            # redis.from_url is a synchronous factory (redis-py v5) — do not await.
            self._client = redis.from_url(
                settings.redis_url,
                password=settings.redis_password,
                max_connections=settings.redis_max_connections,
                decode_responses=False,
            )
            await self._client.ping()
            log.info("Redis connected: %s", settings.redis_url)
        except Exception as exc:
            log.error("Redis connection failed — running without cache: %s", exc)
            self._client = None

    @property
    def is_enabled(self) -> bool:
        return self._client is not None

    # ── Low-level get/set ─────────────────────────────────────────────────────

    async def get(self, key: str, *, prefix: str = "") -> str | None:
        """Return cached string, or None on miss / error / disabled."""
        if not self.is_enabled:
            cache_miss_total.labels(cache_key_prefix=prefix or _prefix(key)).inc()
            return None
        try:
            raw = await self._client.get(key)
            if raw is None:
                cache_miss_total.labels(cache_key_prefix=prefix or _prefix(key)).inc()
                return None
            cache_hit_total.labels(cache_key_prefix=prefix or _prefix(key)).inc()
            return raw.decode() if isinstance(raw, bytes) else raw
        except Exception as exc:
            log.warning("Redis get(%s) error: %s", key, exc)
            cache_miss_total.labels(cache_key_prefix=prefix or _prefix(key)).inc()
            return None

    async def set(
        self,
        key: str,
        value: str,
        ttl_seconds: int | None = None,
        *,
        prefix: str = "",
    ) -> None:
        """Set cache value; no-op on error / disabled."""
        if not self.is_enabled:
            return
        try:
            if ttl_seconds:
                await self._client.setex(key, ttl_seconds, value)
            else:
                await self._client.set(key, value)
            cache_set_total.labels(cache_key_prefix=prefix or _prefix(key)).inc()
        except Exception as exc:
            log.warning("Redis set(%s) error: %s", key, exc)

    # ── JSON helpers ──────────────────────────────────────────────────────────

    async def get_json(self, key: str, *, prefix: str = "") -> dict | list | None:
        """Return parsed JSON value, or None on miss / parse error / disabled."""
        raw = await self.get(key, prefix=prefix)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            log.warning("Redis get_json(%s): JSON decode error — treating as miss", key)
            return None

    async def set_json(
        self,
        key: str,
        value: dict | list,
        ttl_seconds: int | None = None,
        *,
        prefix: str = "",
    ) -> None:
        """Serialize value to JSON and cache it."""
        await self.set(key, json.dumps(value, default=str), ttl_seconds, prefix=prefix)

    # ── Delete / invalidate ───────────────────────────────────────────────────

    async def delete(self, *keys: str, reason: str = "explicit") -> None:
        """Delete one or more keys.  No-op on error / disabled."""
        if not self.is_enabled or not keys:
            return
        try:
            await self._client.delete(*keys)
            cache_invalidate_total.labels(reason=reason).inc(len(keys))
        except Exception as exc:
            log.warning("Redis delete(%s) error: %s", keys, exc)

    async def delete_pattern(self, pattern: str, reason: str = "pattern") -> int:
        """Delete all keys matching a glob pattern (SCAN + DEL).

        Warning: SCAN is O(N) — use only for cache invalidation on mutation,
        not in hot paths.  Returns count of deleted keys.
        """
        if not self.is_enabled:
            return 0
        deleted = 0
        try:
            async for key in self._client.scan_iter(match=pattern, count=100):
                await self._client.delete(key)
                deleted += 1
            if deleted:
                cache_invalidate_total.labels(reason=reason).inc(deleted)
                log.debug("cache.delete_pattern(%s): deleted %d keys", pattern, deleted)
        except Exception as exc:
            log.warning("Redis delete_pattern(%s) error: %s", pattern, exc)
        return deleted

    # ── Rate-limit helper ─────────────────────────────────────────────────────

    async def incr(self, key: str, ttl_seconds: int | None = None) -> int:
        """INCR with optional EXPIRE on first write.  Returns new count (0 on disabled)."""
        if not self.is_enabled:
            return 0
        try:
            value = await self._client.incr(key)
            if ttl_seconds and value == 1:
                await self._client.expire(key, ttl_seconds)
            return int(value)
        except Exception as exc:
            log.warning("Redis incr(%s) error: %s", key, exc)
            return 0

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def shutdown(self) -> None:
        """Graceful close — no-op when disabled."""
        if self._client is not None:
            try:
                await self._client.aclose()
            except Exception as exc:
                log.warning("Redis shutdown error: %s", exc)


def _prefix(key: str) -> str:
    """Extract the first colon-delimited segment as metric label (e.g. 'feed')."""
    return key.split(":")[0] if ":" in key else key


# Module-level singleton — import and use directly.
cache = CacheClient()
