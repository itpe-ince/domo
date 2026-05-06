"""OG(Open Graph) 메타태그 스크래퍼 — Phase 9 L-B (L-3 OG auto-thumbnail).

URL의 Open Graph / Twitter Card 메타태그를 추출한다.
Redis 24시간 캐시 + in-process LRU fallback.

의존성 Mock fallback:
  - httpx 미설치: OGData(all None) 반환
  - beautifulsoup4 미설치: OGData(all None) 반환
  - Redis 미연결: 512 entries LRU 캐시 사용

환경변수:
  OG_SCRAPER_ENABLED=false: Mock 모드 강제 활성화 (테스트용)
"""
from __future__ import annotations

import hashlib
import logging
import os
from collections import OrderedDict
from typing import Any

from pydantic import BaseModel

log = logging.getLogger(__name__)

# httpx + beautifulsoup4 설치 여부 감지
try:
    import httpx as _httpx  # type: ignore[import]
    from bs4 import BeautifulSoup  # type: ignore[import]
    _OG_AVAILABLE = True
except ImportError:
    _httpx = None  # type: ignore[assignment]
    BeautifulSoup = None  # type: ignore[assignment]
    _OG_AVAILABLE = False
    log.warning("[OG] httpx not installed — og_scraper running in mock mode (returns null data)")

# OG_SCRAPER_ENABLED=false 환경변수로 강제 Mock 모드
_SCRAPER_ENABLED: bool = os.getenv("OG_SCRAPER_ENABLED", "true").lower() != "false"

# in-process LRU 캐시 (Redis 미연결 시 fallback)
_LRU_MAX = 512
_LOCAL_CACHE: OrderedDict[str, dict] = OrderedDict()

# 외부 요청 타임아웃 (초)
_REQUEST_TIMEOUT = 5.0


class OGData(BaseModel):
    """OG 메타태그 추출 결과."""
    title: str | None = None
    description: str | None = None
    image_url: str | None = None
    site_name: str | None = None


def _cache_key(url: str) -> str:
    """URL → sha256 캐시 키."""
    return f"og:cache:{hashlib.sha256(url.encode()).hexdigest()}"


def _lru_get(key: str) -> dict | None:
    """in-process LRU 캐시 조회."""
    if key not in _LOCAL_CACHE:
        return None
    # move to end (LRU 갱신)
    _LOCAL_CACHE.move_to_end(key)
    return _LOCAL_CACHE[key]


def _lru_set(key: str, value: dict) -> None:
    """in-process LRU 캐시 저장 (512 entries 초과 시 oldest 제거)."""
    if key in _LOCAL_CACHE:
        _LOCAL_CACHE.move_to_end(key)
    _LOCAL_CACHE[key] = value
    if len(_LOCAL_CACHE) > _LRU_MAX:
        _LOCAL_CACHE.popitem(last=False)


def _extract_og_from_html(html_content: str) -> OGData:
    """HTML에서 OG / Twitter Card 메타태그 추출.

    우선순위:
      1. og:image
      2. twitter:image
      3. 첫 번째 <img> src (100px 이상 추정)
      4. 기본 None
    """
    soup = BeautifulSoup(html_content, "html.parser")

    def _meta(prop: str = "", name: str = "") -> str | None:
        tag = None
        if prop:
            tag = soup.find("meta", property=prop)
        if not tag and name:
            tag = soup.find("meta", attrs={"name": name})
        return tag.get("content") if tag else None  # type: ignore[union-attr]

    title = _meta("og:title") or _meta(name="twitter:title")
    if not title:
        title_tag = soup.find("title")
        title = title_tag.get_text(strip=True) if title_tag else None  # type: ignore[union-attr]

    description = _meta("og:description") or _meta(name="twitter:description") or _meta(name="description")
    image_url = _meta("og:image") or _meta(name="twitter:image")
    site_name = _meta("og:site_name")

    # fallback: 첫 번째 <img> (100x100 이상 추정 — width 속성 기준)
    if not image_url:
        for img in soup.find_all("img", src=True):
            src = img.get("src", "")
            width = img.get("width", "0")
            try:
                if int(str(width)) >= 100:
                    image_url = src
                    break
            except (ValueError, TypeError):
                # width 속성 없거나 파싱 불가 → skip
                continue

    return OGData(
        title=title,
        description=description,
        image_url=image_url,
        site_name=site_name,
    )


async def _scrape_with_httpx(url: str) -> OGData:
    """httpx로 URL 요청 후 OG 데이터 추출.

    - text/html이 아닌 응답(PDF 등)은 즉시 OGData(all None) 반환.
    - 타임아웃: 5초.
    """
    try:
        async with _httpx.AsyncClient(
            timeout=_REQUEST_TIMEOUT,
            follow_redirects=True,
            headers={"User-Agent": "DomoBot/1.0 (OG preview; +https://domo.art)"},
        ) as client:
            resp = await client.get(url)
            content_type = resp.headers.get("content-type", "")
            if "text/html" not in content_type:
                log.debug("[OG] non-HTML content-type=%s url=%s — skip", content_type, url)
                return OGData()
            return _extract_og_from_html(resp.text)
    except Exception as exc:
        log.warning("[OG] scrape failed url=%s: %s", url, exc)
        return OGData()


async def scrape_og(url: str, cache_client: Any = None) -> OGData:
    """OG 메타태그 조회 (캐시 → 스크래핑 순서).

    Args:
        url: 조회할 URL
        cache_client: CacheClient 인스턴스 (없으면 in-process LRU 사용)

    Returns:
        OGData — 실패/mock 모드 시 모든 필드 None
    """
    key = _cache_key(url)

    # ── 1. Redis 캐시 확인 ────────────────────────────────────────────────────
    if cache_client is not None and cache_client.is_enabled:
        cached_raw = await cache_client.get(key)
        if cached_raw:
            try:
                return OGData.model_validate_json(cached_raw)
            except Exception:
                pass

    # ── 2. in-process LRU 캐시 확인 ─────────────────────────────────────────
    local_cached = _lru_get(key)
    if local_cached is not None:
        return OGData(**local_cached)

    # ── 3. Mock 모드 fallback ────────────────────────────────────────────────
    if not _OG_AVAILABLE or not _SCRAPER_ENABLED:
        log.debug("[OG] mock mode — returning null OGData for url=%s", url)
        return OGData()

    # ── 4. 실제 스크래핑 ─────────────────────────────────────────────────────
    result = await _scrape_with_httpx(url)

    # ── 5. 캐시 저장 ─────────────────────────────────────────────────────────
    result_dict = result.model_dump()
    if cache_client is not None and cache_client.is_enabled:
        # Redis 24시간 캐시
        try:
            await cache_client.set(key, result.model_dump_json(), ttl_seconds=86400)
        except Exception as exc:
            log.warning("[OG] Redis cache set failed: %s", exc)
    else:
        # in-process LRU fallback
        log.debug("[OG] Redis unavailable — falling back to in-process LRU cache (512 entries)")
        _lru_set(key, result_dict)

    return result
