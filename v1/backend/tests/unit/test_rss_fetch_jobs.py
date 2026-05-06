"""Unit tests — rss_fetch_jobs.py (Phase 9 L-B, L-2 RSS auto-fetch).

테스트 범위:
  - feedparser 미설치 시 mock 모드 → fetch_all_feeds skipped=True 반환
  - 정상 피드 수집: 신규 기사 2건 upsert
  - 중복 URL skip: 동일 URL 두 번 처리 시 new_count 증가 없음
  - 작가 자동 매칭: display_name 키워드 일치 시 artist_id 연결
  - 잘못된 피드(bozo=True, entries=[]) → error="invalid_feed"
  - RSS_FETCH_WORKER_ENABLED 환경변수 guard (main.py 연동)
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import app.services.rss_fetch_jobs as rss_module


# ──────────────────────────────────────────────────────────────────────────────
# helpers
# ──────────────────────────────────────────────────────────────────────────────

def _make_entry(url: str, title: str, summary: str = "") -> dict:
    """feedparser entry mock 딕셔너리 생성."""
    return {
        "link": url,
        "title": title,
        "summary": summary,
        "published_parsed": None,
    }


def _make_feed_row(feed_id: str = "feed-001", source_url: str = "https://example.com/rss") -> dict:
    return {
        "id": feed_id,
        "source_url": source_url,
        "source_name": "Test Feed",
        "fetch_interval_hours": 1,
    }


# ──────────────────────────────────────────────────────────────────────────────
# 1. feedparser 미설치 → Mock 모드
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_fetch_all_feeds_feedparser_not_available():
    """feedparser 미설치 시 skipped=True, reason=feedparser_not_installed."""
    original = rss_module._FEEDPARSER_AVAILABLE
    rss_module._FEEDPARSER_AVAILABLE = False
    try:
        db = AsyncMock()
        result = await rss_module.fetch_all_feeds(db)
        assert result["skipped"] is True
        assert result["reason"] == "feedparser_not_installed"
        assert result["processed"] == 0
    finally:
        rss_module._FEEDPARSER_AVAILABLE = original


@pytest.mark.asyncio
async def test_fetch_feed_once_feedparser_not_available():
    """feedparser 미설치 시 fetch_feed_once 개별 호출도 error 반환."""
    original = rss_module._FEEDPARSER_AVAILABLE
    rss_module._FEEDPARSER_AVAILABLE = False
    try:
        db = AsyncMock()
        feed = _make_feed_row()
        result = await rss_module.fetch_feed_once(db, feed)
        assert result["error"] == "feedparser_not_installed"
        assert result["new_count"] == 0
    finally:
        rss_module._FEEDPARSER_AVAILABLE = original


# ──────────────────────────────────────────────────────────────────────────────
# 2. 정상 피드 수집
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_fetch_feed_once_new_articles():
    """feedparser가 2개의 새 기사를 반환하면 new_count=2."""
    # feedparser 사용 가능 상태로 강제
    original = rss_module._FEEDPARSER_AVAILABLE
    rss_module._FEEDPARSER_AVAILABLE = True
    try:
        db = AsyncMock()
        # _article_exists → False (모두 새 기사)
        # match_artist → (None, 0.0)
        # db.execute → 이벤트 기록용 mock

        feed = _make_feed_row()
        fake_raw = {
            "bozo": False,
            "entries": [
                _make_entry("https://a.com/1", "Title One", "summary one"),
                _make_entry("https://a.com/2", "Title Two", "summary two"),
            ],
        }

        with (
            patch.object(rss_module, "feedparser", MagicMock(parse=MagicMock(return_value=fake_raw))),
            patch.object(rss_module, "_article_exists", AsyncMock(return_value=False)),
            patch.object(rss_module, "match_artist", AsyncMock(return_value=(None, 0.0))),
        ):
            # db.execute, db.commit mock
            db.execute = AsyncMock(return_value=MagicMock())
            db.commit = AsyncMock()
            db.rollback = AsyncMock()

            result = await rss_module.fetch_feed_once(db, feed)

        assert result["new_count"] == 2
        assert result["skipped_count"] == 0
        assert result["error"] is None
    finally:
        rss_module._FEEDPARSER_AVAILABLE = original


# ──────────────────────────────────────────────────────────────────────────────
# 3. 중복 URL skip
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_fetch_feed_once_duplicate_skip():
    """이미 존재하는 URL은 skipped_count에 집계된다."""
    original = rss_module._FEEDPARSER_AVAILABLE
    rss_module._FEEDPARSER_AVAILABLE = True
    try:
        db = AsyncMock()
        feed = _make_feed_row()
        fake_raw = {
            "bozo": False,
            "entries": [_make_entry("https://dup.com/1", "Dup Title")],
        }

        with (
            patch.object(rss_module, "feedparser", MagicMock(parse=MagicMock(return_value=fake_raw))),
            patch.object(rss_module, "_article_exists", AsyncMock(return_value=True)),  # 이미 존재
        ):
            db.execute = AsyncMock(return_value=MagicMock())
            db.commit = AsyncMock()
            db.rollback = AsyncMock()

            result = await rss_module.fetch_feed_once(db, feed)

        assert result["new_count"] == 0
        assert result["skipped_count"] == 1
    finally:
        rss_module._FEEDPARSER_AVAILABLE = original


# ──────────────────────────────────────────────────────────────────────────────
# 4. 작가 자동 매칭
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_match_artist_keyword_hit():
    """기사 제목에 작가 display_name이 포함되면 artist_id 반환."""
    db = AsyncMock()

    mock_row = MagicMock()
    mock_row.__getitem__ = lambda self, key: (
        "artist-uuid-001" if key == "id" else "Alice Kim"
    )

    mock_result = MagicMock()
    mock_result.mappings.return_value.all.return_value = [mock_row]
    db.execute = AsyncMock(return_value=mock_result)

    artist_id, confidence = await rss_module.match_artist(
        db, title="Alice Kim solo exhibition opens", summary=""
    )

    assert artist_id == "artist-uuid-001"
    assert confidence >= rss_module._MIN_CONFIDENCE


@pytest.mark.asyncio
async def test_match_artist_no_match():
    """기사에 작가 이름 없으면 (None, 0.0) 반환."""
    db = AsyncMock()

    mock_result = MagicMock()
    mock_result.mappings.return_value.all.return_value = []
    db.execute = AsyncMock(return_value=mock_result)

    artist_id, confidence = await rss_module.match_artist(
        db, title="Art Fair 2026 Opening", summary="Various artists"
    )

    assert artist_id is None
    assert confidence == 0.0


# ──────────────────────────────────────────────────────────────────────────────
# 5. 잘못된 피드 처리
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_fetch_feed_once_invalid_feed():
    """bozo=True + entries=[] 피드는 error='invalid_feed' 반환."""
    original = rss_module._FEEDPARSER_AVAILABLE
    rss_module._FEEDPARSER_AVAILABLE = True
    try:
        db = AsyncMock()
        db.execute = AsyncMock(return_value=MagicMock())
        db.commit = AsyncMock()

        feed = _make_feed_row()
        fake_raw = {"bozo": True, "entries": []}

        with patch.object(
            rss_module, "feedparser", MagicMock(parse=MagicMock(return_value=fake_raw))
        ):
            result = await rss_module.fetch_feed_once(db, feed)

        assert result["error"] == "invalid_feed"
        assert result["new_count"] == 0
    finally:
        rss_module._FEEDPARSER_AVAILABLE = original
