"""featured_artist_jobs.py — K-4 AI Featured Artist 주간 자동 선정.

R-5 격리 패턴 준수:
  - 별도 파일 (featured_artist_jobs.py)
  - AsyncSessionLocal 독립 사용
  - 개별 Prometheus metric label

동작:
  매주 월요일 09:00 UTC: select_candidates_for_week() → top-5 INSERT
  후보 < 3명 시: admin Slack 알림 + WARNING 로그

FEATURED_ARTIST_WORKER_ENABLED=false 환경변수로 worker 비활성화 가능.
"""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import date, datetime, timedelta, timezone
from typing import Any

from sqlalchemy import text

from app.db.session import AsyncSessionLocal
from app.services.cron_monitor import record_cron_run as _push_cron_status

log = logging.getLogger(__name__)

# ─── 가중치 상수 (환경변수로 튜닝 가능) ──────────────────────────────────────
_W_ENGAGEMENT = float(os.getenv("FEATURED_W_ENGAGEMENT", "0.30"))
_W_RANK       = float(os.getenv("FEATURED_W_RANK", "0.30"))
_W_DIVERSITY  = float(os.getenv("FEATURED_W_DIVERSITY", "0.20"))
_W_NEW_ARTIST = float(os.getenv("FEATURED_W_NEW_ARTIST", "0.20"))
_TOP_N        = int(os.getenv("FEATURED_TOP_N", "5"))
_LOW_CANDIDATE_THRESHOLD = 3

SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")


def _current_week_start() -> date:
    """이번 주 월요일 날짜 반환."""
    today = date.today()
    return today - timedelta(days=today.weekday())


async def _notify_admin_low_candidates(week_start: date, count: int) -> None:
    """후보 < 3명 시 Slack 알림 (L-F 패턴 재사용)."""
    if not SLACK_WEBHOOK_URL:
        log.warning(
            "featured_artist_jobs: 후보 %d명 (< %d) — SLACK_WEBHOOK_URL 미설정, 알림 skip",
            count,
            _LOW_CANDIDATE_THRESHOLD,
        )
        return
    try:
        import httpx

        msg = (
            f":warning: *Featured Artist 후보 부족*\n"
            f"주간: {week_start.isoformat()}, 후보 수: {count}명 (기준: {_LOW_CANDIDATE_THRESHOLD}명)\n"
            f"수동 모드로 전환 필요: <https://console.bkend.ai|Domo Admin>"
        )
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(SLACK_WEBHOOK_URL, json={"text": msg})
    except Exception as exc:  # noqa: BLE001
        log.warning("featured_artist_jobs: Slack 알림 실패: %s", exc)


async def select_candidates_for_week(
    db,
    week_start: date | None = None,
    n: int = _TOP_N,
) -> list[dict[str, Any]]:
    """주간 Featured Artist 후보 n명 선정.

    composite_score = w1×engagement_norm + w2×rank_norm + w3×diversity + w4×new_artist_bonus
    반환: [{"artist_id": str, "composite_score": float, "reasoning": dict}, ...]
    후보 < _LOW_CANDIDATE_THRESHOLD 시 Slack 알림 + WARNING 로그.
    """
    if week_start is None:
        week_start = _current_week_start()

    four_weeks_ago = week_start - timedelta(weeks=4)
    engagement_window = datetime.now(timezone.utc) - timedelta(days=14)

    # ── Step 1: 기준 1+2 결합 쿼리 ──────────────────────────────────────────
    # artist_index_rank > 80th percentile OR follower_count < 1000
    # + post_engagement_cache 최근 14일 집계
    # + 최근 4주 선정 작가 제외
    # + 이미 이번 주 후보로 INSERT된 작가 제외 (중복 방지)
    try:
        result = await db.execute(
            text("""
                WITH ranked_artists AS (
                    SELECT
                        u.id                    AS artist_id,
                        u.follower_count         AS follower_count,
                        COALESCE(u.artist_index_rank, 0)   AS artist_rank,
                        COALESCE(u.artist_index_score, 0)  AS artist_score,
                        u.region,
                        u.genre
                    FROM users u
                    WHERE u.role = 'artist'
                      AND (
                          u.artist_index_rank > (
                              SELECT PERCENTILE_CONT(0.8) WITHIN GROUP (ORDER BY artist_index_rank)
                              FROM users WHERE role = 'artist' AND artist_index_rank IS NOT NULL
                          )
                          OR u.follower_count < 1000
                      )
                      -- 최근 4주 featured 제외
                      AND u.id NOT IN (
                          SELECT user_id FROM featured_artists
                          WHERE created_at >= :four_weeks_ago
                      )
                      -- 이번 주 이미 후보 제외
                      AND u.id NOT IN (
                          SELECT artist_id FROM featured_artist_candidates
                          WHERE week_start = :week_start
                      )
                ),
                engagement_scores AS (
                    SELECT
                        p.author_id             AS artist_id,
                        SUM(pec.engagement_score) AS total_engagement
                    FROM post_engagement_cache pec
                    JOIN posts p ON p.id = pec.post_id
                    WHERE pec.updated_at >= :engagement_window
                    GROUP BY p.author_id
                ),
                sponsor_counts AS (
                    SELECT
                        artist_id,
                        COUNT(*) AS sponsor_count
                    FROM sponsorships
                    WHERE status = 'active'
                    GROUP BY artist_id
                )
                SELECT
                    ra.artist_id::text,
                    ra.artist_rank,
                    ra.follower_count,
                    ra.region,
                    ra.genre,
                    COALESCE(es.total_engagement, 0) AS engagement_score,
                    COALESCE(sc.sponsor_count, 0)     AS sponsor_count
                FROM ranked_artists ra
                LEFT JOIN engagement_scores es ON es.artist_id = ra.artist_id
                LEFT JOIN sponsor_counts sc ON sc.artist_id = ra.artist_id
                ORDER BY es.total_engagement DESC NULLS LAST
            """),
            {
                "four_weeks_ago": four_weeks_ago,
                "week_start": week_start,
                "engagement_window": engagement_window,
            },
        )
        rows = result.fetchall()
    except Exception as exc:  # noqa: BLE001
        log.warning("featured_artist_jobs: DB 쿼리 실패 (fallback): %s", exc)
        rows = []

    if not rows:
        log.warning(
            "featured_artist_jobs: 후보 pool이 비어있음 (week_start=%s)", week_start
        )
        await _notify_admin_low_candidates(week_start, 0)
        return []

    # ── Step 2: 정규화 ────────────────────────────────────────────────────────
    max_engagement = max((r.engagement_score for r in rows), default=1.0) or 1.0
    max_rank = max((r.artist_rank for r in rows), default=1.0) or 1.0

    scored: list[dict[str, Any]] = []
    for row in rows:
        engagement_norm = row.engagement_score / max_engagement
        rank_norm = row.artist_rank / max_rank
        new_artist_bonus = _W_NEW_ARTIST if row.sponsor_count == 0 else 0.0

        # user_embeddings 미사용 버전: diversity는 MMR 보정 후 적용
        diversity_score = 0.0

        raw_score = (
            _W_ENGAGEMENT * engagement_norm
            + _W_RANK * rank_norm
            + _W_DIVERSITY * diversity_score
            + new_artist_bonus
        )
        scored.append({
            "artist_id": row.artist_id,
            "composite_score": raw_score,
            "reasoning": {
                "engagement": round(engagement_norm, 4),
                "rank": round(rank_norm, 4),
                "diversity": round(diversity_score, 4),
                "new_artist_bonus": round(new_artist_bonus, 4),
                "sponsor_count": int(row.sponsor_count),
                "follower_count": int(row.follower_count),
                "region": row.region,
                "genre": row.genre,
            },
        })

    # ── Step 3: diversity MMR — 장르·지역 분산 보정 ───────────────────────────
    scored = _apply_diversity_mmr(scored, n * 3)  # 후보 풀 3배에서 MMR 적용

    # ── Step 4: 상위 n명 반환 ─────────────────────────────────────────────────
    top_n = sorted(scored, key=lambda x: x["composite_score"], reverse=True)[:n]

    if len(top_n) < _LOW_CANDIDATE_THRESHOLD:
        log.warning(
            "featured_artist_jobs: 후보 %d명 (< %d, week_start=%s)",
            len(top_n),
            _LOW_CANDIDATE_THRESHOLD,
            week_start,
        )
        await _notify_admin_low_candidates(week_start, len(top_n))

    return top_n


def _apply_diversity_mmr(
    scored: list[dict[str, Any]],
    pool_size: int,
) -> list[dict[str, Any]]:
    """장르·지역 다양성 보정 (Maximal Marginal Relevance 단순화 버전).

    user_embeddings 미사용 버전: 장르·지역 태그 기반 분산.
    선택된 집합에 이미 있는 장르/지역의 중복 패널티를 composite_score에 반영.
    """
    pool = sorted(scored, key=lambda x: x["composite_score"], reverse=True)[:pool_size]

    selected: list[dict[str, Any]] = []
    seen_genres: dict[str, int] = {}
    seen_regions: dict[str, int] = {}

    for item in pool:
        genre = item["reasoning"].get("genre") or "unknown"
        region = item["reasoning"].get("region") or "unknown"

        genre_penalty = min(seen_genres.get(genre, 0) * 0.05, 0.15)
        region_penalty = min(seen_regions.get(region, 0) * 0.03, 0.09)

        adjusted = item["composite_score"] - genre_penalty - region_penalty
        item["composite_score"] = max(adjusted, 0.0)
        item["reasoning"]["diversity"] = round(genre_penalty + region_penalty, 4)

        seen_genres[genre] = seen_genres.get(genre, 0) + 1
        seen_regions[region] = seen_regions.get(region, 0) + 1
        selected.append(item)

    return selected


async def insert_candidates(
    db,
    candidates: list[dict[str, Any]],
    week_start: date,
) -> int:
    """후보 목록을 featured_artist_candidates에 INSERT (ON CONFLICT DO NOTHING, 멱등).

    반환: 실제 INSERT된 행 수.
    """
    import json

    inserted = 0
    for c in candidates:
        try:
            result = await db.execute(
                text("""
                    INSERT INTO featured_artist_candidates
                        (artist_id, week_start, composite_score, reasoning, status)
                    VALUES (:artist_id, :week_start, :score, :reasoning::jsonb, 'pending')
                    ON CONFLICT (artist_id, week_start) DO NOTHING
                    RETURNING id
                """),
                {
                    "artist_id": c["artist_id"],
                    "week_start": week_start,
                    "score": c["composite_score"],
                    "reasoning": json.dumps(c["reasoning"]),
                },
            )
            if result.fetchone():
                inserted += 1
        except Exception as exc:  # noqa: BLE001
            log.warning("insert_candidates: %s 실패: %s", c["artist_id"], exc)

    await db.commit()
    log.info(
        "insert_candidates: %d/%d 삽입 완료 (week_start=%s)",
        inserted,
        len(candidates),
        week_start,
    )
    return inserted


async def expire_old_candidates(db, week_start: date) -> None:
    """이번 주보다 이전 주의 pending 후보를 expired로 전환."""
    await db.execute(
        text("""
            UPDATE featured_artist_candidates
            SET status = 'expired'
            WHERE status = 'pending'
              AND week_start < :week_start
        """),
        {"week_start": week_start},
    )
    await db.commit()


# ─── Cron loop ───────────────────────────────────────────────────────────────

_FEATURED_INTERVAL_SECONDS = int(
    os.getenv("FEATURED_ARTIST_INTERVAL_SECONDS", "604800")
)  # 7일


async def feature_artist_cron_loop() -> None:
    """주 1회 월요일 09:00 UTC 실행.

    다음 월요일 09:00 UTC까지 대기 후 실행 — 서버 재시작 시 자동 복구.
    """
    while True:
        # 다음 월요일 09:00 UTC까지 대기
        now = datetime.now(timezone.utc)
        days_until_monday = (7 - now.weekday()) % 7
        if days_until_monday == 0 and now.hour < 9:
            next_run = now.replace(hour=9, minute=0, second=0, microsecond=0)
        elif days_until_monday == 0 and now.hour >= 9:
            next_run = now.replace(
                hour=9, minute=0, second=0, microsecond=0
            ) + timedelta(weeks=1)
        else:
            next_run = (now + timedelta(days=days_until_monday)).replace(
                hour=9, minute=0, second=0, microsecond=0
            )

        wait_seconds = (next_run - now).total_seconds()
        log.info(
            "featured_artist_cron_loop: 다음 실행 %s (%.0f초 후)",
            next_run.isoformat(),
            wait_seconds,
        )

        if wait_seconds > 0:
            await asyncio.sleep(wait_seconds)

        await _push_cron_status("featured_artist", "running")
        async with AsyncSessionLocal() as db:
            try:
                week_start = _current_week_start()
                log.info(
                    "featured_artist_cron_loop: 실행 시작 (week_start=%s)", week_start
                )

                candidates = await select_candidates_for_week(db, week_start)
                if candidates:
                    await insert_candidates(db, candidates, week_start)
                await expire_old_candidates(db, week_start)

                log.info(
                    "featured_artist_cron_loop: 완료 (후보 %d명)", len(candidates)
                )
                await _push_cron_status("featured_artist", "success")
            except Exception as exc:  # noqa: BLE001
                log.warning("featured_artist_cron_loop: 오류 (무시): %s", exc)
                await _push_cron_status("featured_artist", "failed", error=str(exc)[:500])
