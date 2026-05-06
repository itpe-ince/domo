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
    "payments_setup_intent": {"limit": 10, "window_sec": 60, "by": "user"},
    "bid_create": {"limit": 60, "window_sec": 60, "by": "user"},
    "buy_now": {"limit": 10, "window_sec": 60, "by": "user"},
    "report_create": {"limit": 5, "window_sec": 60, "by": "user"},
    "media_upload": {"limit": 20, "window_sec": 60, "by": "user"},
    "media_patch": {"limit": 30, "window_sec": 60, "by": "user"},
    # editor-image-studio PDCA #6-image — Pillow processing is heavy;
    # 5/min/user is enough for interactive editing while bounding load.
    "media_transform": {"limit": 5, "window_sec": 60, "by": "user"},
    # OQ-D-3 = B — separate signature upload endpoint. 5/min/user mirrors
    # transform; signature uploads are rare in normal use.
    "signature_upload": {"limit": 5, "window_sec": 60, "by": "user"},
    "feed_read": {"limit": 120, "window_sec": 60, "by": "user"},
    "explore_read": {"limit": 60, "window_sec": 60, "by": "ip"},
    # A-5 search-enhancement — v2 search: 60/min anon (IP), 120/min auth (user)
    # Implementation: rate_limit("search") uses IP; auth path falls back naturally.
    "search": {"limit": 60, "window_sec": 60, "by": "ip"},
    # Search history CRUD — requires auth, so keyed by user
    "search_history_read": {"limit": 60, "window_sec": 60, "by": "user"},
    "search_history_write": {"limit": 120, "window_sec": 60, "by": "user"},
    "search_history_delete": {"limit": 30, "window_sec": 60, "by": "user"},
    # Popular searches — public, read-heavy
    "search_popular": {"limit": 60, "window_sec": 60, "by": "ip"},
    "default_read": {"limit": 120, "window_sec": 60, "by": "user"},
    "gdpr_export": {"limit": 1, "window_sec": 86400, "by": "user"},
    # publish-controls PDCA #8 §B-12
    "post_publish": {"limit": 10, "window_sec": 60, "by": "user"},
    "series_write": {"limit": 30, "window_sec": 60, "by": "user"},
    "series_read": {"limit": 60, "window_sec": 60, "by": "user"},
    "series_reorder": {"limit": 30, "window_sec": 60, "by": "user"},
    # auction-promotion-suite PDCA #11
    "share_card": {"limit": 10, "window_sec": 60, "by": "user"},
    # artist-patronage-dashboard B-2
    "patronage_summary": {"limit": 60, "window_sec": 60, "by": "user"},
    "patronage_supporters": {"limit": 60, "window_sec": 60, "by": "user"},
    "patronage_revenue": {"limit": 30, "window_sec": 60, "by": "user"},
    # tier-benefits-customization B-4
    "tier_benefits_write": {"limit": 30, "window_sec": 60, "by": "user"},
    "tier_benefits_read": {"limit": 120, "window_sec": 60, "by": "user"},
    # D'-1 artist-tier-release carry-over — sponsor validity settings
    "me_sponsor_settings": {"limit": 10, "window_sec": 60, "by": "user"},
    # subscription-cancellation-tracking D'-2
    "patronage_churn": {"limit": 30, "window_sec": 60, "by": "user"},
    # stripe-coupon-foundation D'-3
    "admin_coupons_write": {"limit": 60, "window_sec": 60, "by": "user"},
    "me_coupons_apply": {"limit": 5, "window_sec": 60, "by": "user"},
    "me_coupons_read": {"limit": 60, "window_sec": 60, "by": "user"},
    # A-6 artist-index-v1 — public ranking page (anonymous-friendly)
    # 60/min by IP for anonymous; auth context falls back to user key (120 effective)
    "artist_index_read": {"limit": 60, "window_sec": 60, "by": "ip"},
    # G'-2 winback-coupon-endpoint — 1/day/subscription to prevent abuse
    # window_sec=86400 (24h), by=user (tied to authenticated user)
    "winback_coupon": {"limit": 1, "window_sec": 86400, "by": "user"},
    # G'-7 admin-featured-artists — admin write ops (moderate; monthly cadence)
    "featured_artist_write": {"limit": 60, "window_sec": 60, "by": "user"},
    # G'-7 admin-featured-artists — public read (60/min anon, 120/min auth)
    "featured_artist_read": {"limit": 60, "window_sec": 60, "by": "ip"},
    # C-1 ai-artist-interview-generation
    # LLM generation is expensive — 5/hour per admin prevents runaway costs
    "interview_generate": {"limit": 5, "window_sec": 3600, "by": "user"},
    # Artist consent/reject actions — 10/hour/user is more than enough
    "interview_consent": {"limit": 10, "window_sec": 3600, "by": "user"},
    # C-2 press-kit-auto-export — PDF generation is CPU/storage-intensive
    # 10/hour per admin; 30d cache means real regenerations are rare
    "press_kit_generate": {"limit": 10, "window_sec": 3600, "by": "user"},
    # C-3 multi-language-story — bio auto-translate (LLM cost protection)
    # 5 calls/day/user: each call translates to 4 locales (reasonable daily cap)
    "bio_translate": {"limit": 5, "window_sec": 86400, "by": "user"},
    # C-3 admin — translate existing ArtistInterview to another locale
    "interview_translate": {"limit": 10, "window_sec": 3600, "by": "user"},
    # C-4 admin-media-coverage write — 60/min/user (moderate; batch import allowed)
    "admin_media_coverage_write": {"limit": 60, "window_sec": 60, "by": "user"},
    # C-4 public media coverage read — 60/min anon (IP), 120/min auth (falls back to user key)
    "media_coverage_read": {"limit": 60, "window_sec": 60, "by": "ip"},
    # H'-4 click-tracking — 60/min/IP analytics hit endpoint
    "media_coverage_click": {"limit": 60, "window_sec": 60, "by": "ip"},
    # C-5 newsletter-digest — admin issue management (compose/edit/send)
    "newsletter_admin_write": {"limit": 30, "window_sec": 60, "by": "user"},
    # C-5 newsletter-digest — admin issue listing
    "newsletter_admin_read": {"limit": 60, "window_sec": 60, "by": "user"},
    # C-5 newsletter-digest — user preference reads (lightweight, keyed by user)
    "newsletter_me_read": {"limit": 60, "window_sec": 60, "by": "user"},
    # C-5 newsletter-digest — user preference writes (opt-in/out, frequency)
    "newsletter_me_write": {"limit": 10, "window_sec": 60, "by": "user"},
    # B'-1 multi-currency-foundation — public exchange rates endpoint
    # 60/min anon (IP); auth falls back to user key (120 effective)
    "exchange_rates_read": {"limit": 60, "window_sec": 60, "by": "ip"},
    # B'-1 — user currency preference update/read (low frequency)
    "me_currency_preference": {"limit": 10, "window_sec": 60, "by": "user"},
    # B'-2 dm-messaging — 60/min/user on message send (typing bursts expected)
    "dm_send": {"limit": 60, "window_sec": 60, "by": "user"},
    # L-C group dm — 5 msg/min/user/group (스팸 방지용 보수적 제한)
    "group_msg_send": {"limit": 5, "window_sec": 60, "by": "user"},
    # L-C group dm — 그룹 생성 10/hr/user
    "group_create": {"limit": 10, "window_sec": 3600, "by": "user"},
    # B'-4 stripe-billing-auto-renewal — manual renew (5/min/user, idempotent-safe)
    "subscription_renew": {"limit": 5, "window_sec": 60, "by": "user"},
    # K-3 ai-artwork-caption — 작가 수동 재생성 (LLM 비용 제한)
    # CO-1 PR-2: 'post_caption_regenerate' 키 추가 — 3회/일/포스트
    # Redis key: rl:post_caption_regenerate:{user_id}:{post_id} (post별 독립 카운터)
    # window_sec=86400 (24시간), limit=3
    "caption_regenerate": {"limit": 10, "window_sec": 3600, "by": "user"},
    "post_caption_regenerate": {"limit": 3, "window_sec": 86400, "by": "user"},
    # CO-1 PR-2: 'post_caption_override' 키 추가 — 10회/일/포스트 (user 기준)
    # 수동 override는 재생성보다 빈도가 높을 수 있으나, 남용 방지를 위해 10회/일 제한
    "post_caption_override": {"limit": 10, "window_sec": 86400, "by": "user"},
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
    """Increment counter and check if allowed.

    When Redis is disabled (REDIS_URL not set), falls back to in-memory
    counting.  The in-memory store is per-process and not shared across
    instances — suitable for development and CI only.
    """
    now = int(time.time())
    window_start = (now // window_sec) * window_sec
    bucket = f"rl:{scope}:{key}:{window_start}"
    r = get_redis()

    if r is not None:
        # Redis backend (production / multi-instance safe)
        pipe = r.pipeline()
        pipe.incr(bucket)
        pipe.expire(bucket, window_sec + 5)
        count, _ = await pipe.execute()
        count = int(count)
    else:
        # In-memory fallback (single-process dev / CI)
        count = _incr_memory(bucket, window_sec)

    allowed = count <= limit
    return RateLimitResult(
        allowed=allowed,
        limit=limit,
        remaining=max(0, limit - count),
        reset_at=window_start + window_sec,
    )


# ─── In-memory fallback store ─────────────────────────────────────────────────

_memory_store: dict[str, tuple[int, int]] = {}  # bucket -> (count, expires_at)


def _incr_memory(bucket: str, window_sec: int) -> int:
    """Thread-unsafe in-process counter for dev/CI fallback."""
    now = int(time.time())
    entry = _memory_store.get(bucket)
    if entry is None or entry[1] < now:
        _memory_store[bucket] = (1, now + window_sec + 5)
        return 1
    count = entry[0] + 1
    _memory_store[bucket] = (count, entry[1])
    return count


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
