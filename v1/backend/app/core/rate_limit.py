"""Rate limiting service (Phase 4 M6).

Reference: phase4.design.md §3
"""
from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass

from fastapi import Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ApiError
from app.core.redis_client import get_redis
from app.db.session import get_db
from app.models.user import User
from app.services.settings import get_setting

log = logging.getLogger(__name__)


# Mode: 'enforce' | 'monitor' | 'off'
RATE_LIMIT_MODE = os.environ.get("RATE_LIMIT_MODE", "enforce").lower()


# Default limits if system_settings.rate_limits is missing
DEFAULT_LIMITS: dict[str, dict] = {
    "auth_login": {"limit": 10, "window_sec": 60, "by": "ip"},
    "auth_refresh": {"limit": 30, "window_sec": 60, "by": "user"},
    "sponsorship_create": {"limit": 30, "window_sec": 60, "by": "user"},
    "subscription_create": {"limit": 10, "window_sec": 60, "by": "user"},
    "bid_create": {"limit": 60, "window_sec": 60, "by": "user"},
    "buy_now": {"limit": 10, "window_sec": 60, "by": "user"},
    "report_create": {"limit": 5, "window_sec": 60, "by": "user"},
    "media_upload": {"limit": 20, "window_sec": 60, "by": "user"},
    "feed_read": {"limit": 120, "window_sec": 60, "by": "user"},
    "explore_read": {"limit": 60, "window_sec": 60, "by": "ip"},
    "default_read": {"limit": 120, "window_sec": 60, "by": "user"},
}


@dataclass
class RateLimitResult:
    allowed: bool
    limit: int
    remaining: int
    reset_at: int  # unix seconds


async def _lookup_config(db: AsyncSession, scope: str) -> dict:
    """Look up scope config from system_settings, fallback to defaults."""
    settings_value = await get_setting(db, "rate_limits")
    if isinstance(settings_value, dict) and scope in settings_value:
        cfg = settings_value[scope]
        # Merge with defaults to fill missing fields
        default = DEFAULT_LIMITS.get(scope, DEFAULT_LIMITS["default_read"])
        return {**default, **cfg}
    return DEFAULT_LIMITS.get(scope, DEFAULT_LIMITS["default_read"])


async def check_rate_limit(
    scope: str,
    key: str,
    limit: int,
    window_sec: int = 60,
) -> RateLimitResult:
    """Increment counter and check if allowed."""
    now = int(time.time())
    window_start = (now // window_sec) * window_sec
    bucket = f"rl:{scope}:{key}:{window_start}"
    r = get_redis()

    pipe = r.pipeline()
    pipe.incr(bucket)
    pipe.expire(bucket, window_sec + 5)
    count, _ = await pipe.execute()

    allowed = int(count) <= limit
    return RateLimitResult(
        allowed=allowed,
        limit=limit,
        remaining=max(0, limit - int(count)),
        reset_at=window_start + window_sec,
    )


def rate_limit(scope: str):
    """FastAPI dependency factory."""

    async def dependency(
        request: Request,
        response: Response,
        db: AsyncSession = Depends(get_db),
    ) -> RateLimitResult | None:
        if RATE_LIMIT_MODE == "off":
            return None

        cfg = await _lookup_config(db, scope)
        limit = int(cfg["limit"])
        window_sec = int(cfg.get("window_sec", 60))
        by = cfg.get("by", "user")

        # Identify caller
        if by == "ip":
            key = request.client.host if request.client else "unknown"
        else:  # by user_id from JWT, fallback to ip
            from app.core.security import decode_token

            auth = request.headers.get("authorization", "")
            user_id = None
            if auth.lower().startswith("bearer "):
                try:
                    payload = decode_token(auth.split(" ", 1)[1])
                    if payload.get("type") == "access":
                        user_id = payload.get("sub")
                except ValueError:
                    pass
            key = user_id or (
                request.client.host if request.client else "unknown"
            )

        result = await check_rate_limit(scope, key, limit, window_sec)

        # Attach headers directly on the response
        response.headers["X-RateLimit-Limit"] = str(result.limit)
        response.headers["X-RateLimit-Remaining"] = str(result.remaining)
        response.headers["X-RateLimit-Reset"] = str(result.reset_at)

        if not result.allowed:
            if RATE_LIMIT_MODE == "enforce":
                raise ApiError(
                    "RATE_LIMITED",
                    f"Rate limit exceeded ({limit}/{window_sec}s)",
                    details={
                        "scope": scope,
                        "limit": limit,
                        "window_sec": window_sec,
                        "reset_at": result.reset_at,
                    },
                    http_status=429,
                )
            else:
                # monitor mode: log only
                log.warning(
                    "rate_limit_exceeded (monitor): scope=%s key=%s count>%s",
                    scope,
                    key,
                    limit,
                )

        return result

    return Depends(dependency)
