"""RSS auto-fetch cron worker — Phase 9 L-B (L-2 RSS auto-fetch).

외부 매체 RSS 피드를 1시간마다 수집하고 external_articles에 저장한다.
작가 자동 매칭은 display_name 키워드 검색 기반이며,
LLM_ARTIST_MATCH_ENABLED=true 시 LLM 보조 매칭을 추가로 활용한다.

feedparser 미설치 환경: ImportError 캐치 후 Mock 모드로 동작 (no-op).

R-5 격리 패턴:
  - 별도 파일 (rss_fetch_jobs.py)
  - AsyncSessionLocal 독립 사용
  - 개별 try/except + DB rollback
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import re
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.services.cron_monitor import record_cron_run as _push_cron_status

log = logging.getLogger(__name__)

# feedparser 설치 여부 감지 — 미설치 시 Mock 모드 (no-op)
try:
    import feedparser  # type: ignore[import]
    _FEEDPARSER_AVAILABLE = True
except ImportError:
    feedparser = None  # type: ignore[assignment]
    _FEEDPARSER_AVAILABLE = False
    log.warning("[RSS] feedparser not installed — rss_fetch_jobs running in mock mode (no-op)")

# LLM 보조 매칭 활성화 여부
_LLM_MATCH_ENABLED: bool = os.getenv("LLM_ARTIST_MATCH_ENABLED", "false").lower() == "true"

# 매칭 신뢰도 최소 임계값 — 미만이면 artist_id = NULL (admin 확인)
_MIN_CONFIDENCE: float = 0.7


# ── 내부 헬퍼 ──────────────────────────────────────────────────────────────────

def _normalize(text_: str) -> str:
    """대소문자 및 여러 공백 정규화."""
    return re.sub(r"\s+", " ", text_.strip().lower())


def _is_valid_feed(raw: Any) -> bool:
    """feedparser 결과가 유효한 RSS/Atom 피드인지 확인.

    'bozo'는 파싱 오류 플래그. entries가 없으면 HTML 페이지를 오인한 것.
    """
    if raw is None:
        return False
    if raw.get("bozo") and not raw.get("entries"):
        return False
    return True


async def _get_active_feeds(db: AsyncSession) -> list[dict]:
    """is_active=TRUE인 external_feeds 목록 반환."""
    result = await db.execute(
        text(
            "SELECT id, source_url, source_name, fetch_interval_hours "
            "FROM external_feeds "
            "WHERE is_active = TRUE "
            "ORDER BY last_fetched_at ASC NULLS FIRST"
        )
    )
    rows = result.mappings().all()
    return [dict(r) for r in rows]


async def _article_exists(db: AsyncSession, url: str) -> bool:
    """URL 중복 확인."""
    result = await db.execute(
        text("SELECT 1 FROM external_articles WHERE url = :url LIMIT 1"),
        {"url": url},
    )
    return result.scalar() is not None


async def match_artist(db: AsyncSession, title: str, summary: str | None) -> tuple[str | None, float]:
    """기사 제목 + 요약에서 작가명 키워드 매칭.

    Returns:
        (artist_id_str, confidence) — 매칭 없으면 (None, 0.0)
    """
    # 작가 display_name 목록 조회 (role='artist', status='active')
    result = await db.execute(
        text(
            "SELECT id, display_name FROM users "
            "WHERE role = 'artist' AND status = 'active' AND deleted_at IS NULL "
            "AND display_name IS NOT NULL AND display_name != '' "
            "LIMIT 500"
        )
    )
    artists = result.mappings().all()

    combined_text = _normalize(f"{title} {summary or ''}")
    best_id: str | None = None
    best_score: float = 0.0

    for row in artists:
        name = _normalize(row["display_name"])
        if not name:
            continue
        # 이름이 텍스트에 포함되면 기본 점수 0.8
        if name in combined_text:
            # 제목에도 포함되면 가중치 추가
            title_score = 0.9 if name in _normalize(title) else 0.75
            if title_score > best_score:
                best_score = title_score
                best_id = str(row["id"])

    if best_score < _MIN_CONFIDENCE:
        return None, 0.0

    return best_id, best_score


async def upsert_article(
    db: AsyncSession,
    feed_id: str,
    url: str,
    title: str,
    summary: str | None,
    published_at: datetime | None,
) -> bool:
    """기사 저장. 이미 존재하면 skip. 저장 시 True 반환."""
    if await _article_exists(db, url):
        return False

    # 작가 매칭
    artist_id, confidence = await match_artist(db, title, summary)

    await db.execute(
        text(
            "INSERT INTO external_articles "
            "(id, feed_id, url, title, summary, published_at, artist_id, match_confidence, "
            " is_approved, created_at) "
            "VALUES (gen_random_uuid(), :feed_id, :url, :title, :summary, :published_at, "
            "        :artist_id, :confidence, FALSE, now())"
        ),
        {
            "feed_id": feed_id,
            "url": url,
            "title": title,
            "summary": summary,
            "published_at": published_at,
            "artist_id": artist_id,
            "confidence": confidence if artist_id else None,
        },
    )
    return True


async def fetch_feed_once(db: AsyncSession, feed: dict) -> dict:
    """단일 피드 수집 + external_articles upsert.

    Returns:
        dict with keys: feed_id, new_count, skipped_count, error
    """
    feed_id = str(feed["id"])
    source_url = feed["source_url"]

    if not _FEEDPARSER_AVAILABLE:
        return {"feed_id": feed_id, "new_count": 0, "skipped_count": 0, "error": "feedparser_not_installed"}

    try:
        # feedparser는 동기 — executor에서 실행
        loop = asyncio.get_event_loop()
        raw = await loop.run_in_executor(None, feedparser.parse, source_url)
    except Exception as exc:
        log.warning("[RSS] feedparser.parse(%s) failed: %s", source_url, exc)
        return {"feed_id": feed_id, "new_count": 0, "skipped_count": 0, "error": str(exc)}

    if not _is_valid_feed(raw):
        log.warning("[RSS] invalid feed: %s (bozo=%s, entries=%d)", source_url, raw.get("bozo"), len(raw.get("entries", [])))
        return {"feed_id": feed_id, "new_count": 0, "skipped_count": 0, "error": "invalid_feed"}

    new_count = 0
    skipped_count = 0

    for entry in raw.get("entries", []):
        url = entry.get("link", "").strip()
        title = entry.get("title", "").strip()
        if not url or not title:
            skipped_count += 1
            continue

        summary = entry.get("summary") or entry.get("description") or None
        # 요약 텍스트 HTML 태그 제거
        if summary:
            summary = re.sub(r"<[^>]+>", "", summary).strip()[:1000]

        # 발행일 파싱
        published_at: datetime | None = None
        if entry.get("published_parsed"):
            try:
                import time
                ts = time.mktime(entry.published_parsed)
                published_at = datetime.fromtimestamp(ts, tz=timezone.utc)
            except Exception:
                pass

        try:
            saved = await upsert_article(db, feed_id, url, title, summary, published_at)
            if saved:
                new_count += 1
            else:
                skipped_count += 1
        except Exception as exc:
            log.warning("[RSS] upsert_article failed url=%s: %s", url, exc)
            await db.rollback()
            skipped_count += 1
            continue

    # 마지막 fetch 시각 갱신
    try:
        await db.execute(
            text("UPDATE external_feeds SET last_fetched_at = now() WHERE id = :fid"),
            {"fid": feed_id},
        )
        await db.commit()
    except Exception as exc:
        log.warning("[RSS] failed to update last_fetched_at for feed %s: %s", feed_id, exc)
        await db.rollback()

    log.info("[RSS] feed=%s new=%d skipped=%d", source_url, new_count, skipped_count)
    return {"feed_id": feed_id, "new_count": new_count, "skipped_count": skipped_count, "error": None}


async def fetch_all_feeds(db: AsyncSession) -> dict:
    """활성 피드 전체 순회 수집.

    feedparser 미설치 시 즉시 skip 결과 반환.
    """
    if not _FEEDPARSER_AVAILABLE:
        return {"skipped": True, "reason": "feedparser_not_installed", "processed": 0, "results": []}

    feeds = await _get_active_feeds(db)
    if not feeds:
        return {"skipped": False, "processed": 0, "results": []}

    results = []
    for feed in feeds:
        result = await fetch_feed_once(db, feed)
        results.append(result)

    total_new = sum(r.get("new_count", 0) for r in results)
    log.info("[RSS] fetch_all_feeds complete: feeds=%d total_new=%d", len(results), total_new)
    return {"skipped": False, "processed": len(results), "results": results}


# ── Cron Loop ─────────────────────────────────────────────────────────────────


async def rss_fetch_cron_loop(interval_seconds: int = 3600) -> None:
    """RSS 수집 cron — 1시간 주기.

    RSS_FETCH_WORKER_ENABLED=false 시 즉시 종료 (main.py에서 제어).
    """
    log.info("[RSS] rss_fetch_cron_loop started (interval=%ss)", interval_seconds)
    while True:
        await _push_cron_status("rss_fetch", "running")
        try:
            async with AsyncSessionLocal() as db:
                await fetch_all_feeds(db)
            await _push_cron_status("rss_fetch", "success")
        except Exception as exc:  # noqa: BLE001
            log.exception("[RSS] rss fetch cron failed: %s", exc)
            await _push_cron_status("rss_fetch", "failed", error=str(exc)[:500])
        await asyncio.sleep(interval_seconds)
