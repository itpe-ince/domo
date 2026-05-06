"""Unit tests — og_scraper.py (Phase 9 L-B, L-3 OG auto-thumbnail).

테스트 범위:
  - OG 추출 성공: og:image 우선순위 정상 동작
  - 의존성 미설치(httpx/bs4) → OGData(all None) 반환 (Mock 모드)
  - Redis 캐시 hit → 스크래핑 생략
  - Redis 미연결 → in-process LRU 캐시 fallback
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import app.services.og_scraper as og_module
from app.services.og_scraper import OGData, _lru_get, _lru_set, _LOCAL_CACHE


# ──────────────────────────────────────────────────────────────────────────────
# Helper
# ──────────────────────────────────────────────────────────────────────────────

def _clear_lru():
    """테스트 격리를 위한 in-process LRU 캐시 초기화."""
    _LOCAL_CACHE.clear()


# ──────────────────────────────────────────────────────────────────────────────
# 1. Mock 모드 — httpx/bs4 미설치
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_scrape_og_mock_mode_returns_null():
    """httpx 미설치(Mock 모드) 시 OGData(all None) 반환."""
    _clear_lru()
    original = og_module._OG_AVAILABLE
    og_module._OG_AVAILABLE = False
    try:
        result = await og_module.scrape_og("https://example.com", cache_client=None)
        assert isinstance(result, OGData)
        assert result.title is None
        assert result.image_url is None
        assert result.description is None
        assert result.site_name is None
    finally:
        og_module._OG_AVAILABLE = original


@pytest.mark.asyncio
async def test_scrape_og_scraper_disabled_env():
    """OG_SCRAPER_ENABLED=false 시 OGData(all None) 반환."""
    _clear_lru()
    original_enabled = og_module._SCRAPER_ENABLED
    og_module._SCRAPER_ENABLED = False
    try:
        result = await og_module.scrape_og("https://example.com", cache_client=None)
        assert result.title is None
    finally:
        og_module._SCRAPER_ENABLED = original_enabled


# ──────────────────────────────────────────────────────────────────────────────
# 2. 실제 스크래핑 — OG 추출 우선순위
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_scrape_og_extracts_og_image():
    """og:image가 있으면 image_url에 반영된다."""
    _clear_lru()
    original = og_module._OG_AVAILABLE
    og_module._OG_AVAILABLE = True
    og_module._SCRAPER_ENABLED = True

    html = """
    <html><head>
    <meta property="og:title" content="Test Title"/>
    <meta property="og:image" content="https://cdn.example.com/thumb.jpg"/>
    <meta property="og:description" content="Test desc"/>
    <meta property="og:site_name" content="TestSite"/>
    </head><body></body></html>
    """

    mock_response = MagicMock()
    mock_response.headers = {"content-type": "text/html; charset=utf-8"}
    mock_response.text = html
    mock_response.status_code = 200

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = AsyncMock(return_value=mock_response)

    try:
        with patch.object(og_module._httpx, "AsyncClient", return_value=mock_client):
            result = await og_module.scrape_og("https://example.com/article", cache_client=None)

        assert result.title == "Test Title"
        assert result.image_url == "https://cdn.example.com/thumb.jpg"
        assert result.description == "Test desc"
        assert result.site_name == "TestSite"
    finally:
        og_module._OG_AVAILABLE = original


# ──────────────────────────────────────────────────────────────────────────────
# 3. Redis 캐시 hit → 스크래핑 생략
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_scrape_og_redis_cache_hit():
    """Redis 캐시에 데이터가 있으면 스크래핑을 호출하지 않는다."""
    _clear_lru()

    cached_json = '{"title":"Cached","description":null,"image_url":"https://img.com/c.jpg","site_name":null}'

    mock_cache = AsyncMock()
    mock_cache.is_enabled = True
    mock_cache.get = AsyncMock(return_value=cached_json)

    with patch.object(og_module, "_scrape_with_httpx", AsyncMock()) as mock_scrape:
        result = await og_module.scrape_og("https://cached.com", cache_client=mock_cache)

    assert result.title == "Cached"
    assert result.image_url == "https://img.com/c.jpg"
    mock_scrape.assert_not_called()


# ──────────────────────────────────────────────────────────────────────────────
# 4. in-process LRU fallback
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_scrape_og_lru_cache_fallback():
    """Redis 미연결 시 in-process LRU 캐시에 저장하고, 두 번째 호출에서 재사용한다."""
    _clear_lru()

    original_og = og_module._OG_AVAILABLE
    og_module._OG_AVAILABLE = True
    og_module._SCRAPER_ENABLED = True

    mock_data = OGData(title="LRU Hit", image_url="https://img.com/lru.jpg")

    try:
        with patch.object(og_module, "_scrape_with_httpx", AsyncMock(return_value=mock_data)) as mock_scrape:
            # 첫 번째 호출 — LRU miss → scrape → LRU 저장
            r1 = await og_module.scrape_og("https://lru.com", cache_client=None)
            # 두 번째 호출 — LRU hit → scrape 생략
            r2 = await og_module.scrape_og("https://lru.com", cache_client=None)

        assert r1.title == "LRU Hit"
        assert r2.title == "LRU Hit"
        # scrape는 첫 번째에만 호출
        assert mock_scrape.call_count == 1
    finally:
        og_module._OG_AVAILABLE = original_og
