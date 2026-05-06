"""Async Redis client singleton.

G''-2: Updated to support optional REDIS_URL (Mock/disabled mode).
When REDIS_URL is not set, get_redis() returns None — callers must
guard with `if r is not None`.
"""
from __future__ import annotations

import logging
from functools import lru_cache

import redis.asyncio as redis

from app.core.config import get_settings

log = logging.getLogger(__name__)


@lru_cache
def get_redis() -> redis.Redis | None:
    """Return a Redis client, or None when REDIS_URL is not configured."""
    settings = get_settings()
    if not settings.redis_url:
        log.info("Redis disabled (REDIS_URL not set) — Mock mode active")
        return None
    return redis.from_url(
        settings.redis_url,
        password=settings.redis_password,
        max_connections=settings.redis_max_connections,
        encoding="utf-8",
        decode_responses=True,
    )
