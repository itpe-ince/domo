"""Admin Analytics API — Phase 12 B-2.

통합 분석 대시보드용 4개 endpoint:
  GET /admin/analytics/cohort-retention    — D7/D30 retention 시계열
  GET /admin/analytics/newsletter-open-rate — 발송/오픈/클릭 시계열
  GET /admin/analytics/feed-ctr            — algo별 CTR
  GET /admin/analytics/ai-features-usage   — AI 기능별 사용률

공통 규칙:
  - require_admin_with_2fa 의존성
  - period 쿼리 파라미터: "7d" | "30d" | "90d" (기본값 "30d")
  - Redis 5분 캐시 (graceful — Redis 미연결 시 skip)
  - Cache-Control: max-age=300
  - 응답 헤더 X-Cache-At: {ISO8601}
  - ?bust=1 쿼리 파라미터로 캐시 강제 갱신
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.admin_deps import require_admin_with_2fa
from app.db.session import get_db
from app.services.cache import cache

log = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/analytics", tags=["admin-analytics"])

# Redis 캐시 TTL (5분)
CACHE_TTL = 300

# period → days 변환
_PERIOD_DAYS: dict[str, int] = {"7d": 7, "30d": 30, "90d": 90}


# ── 캐시 헬퍼 ─────────────────────────────────────────────────────────────────


async def _get_cached_or_compute(
    cache_key: str,
    compute_fn,
    bust: bool = False,
) -> dict:
    """Redis 캐시 조회 → miss 시 compute_fn 실행 → setex.

    bust=True 이면 기존 캐시를 삭제하고 강제 재계산.
    Redis 미연결 시 캐시를 건너뛰고 compute_fn 결과 반환.
    """
    if bust:
        try:
            await cache._client.delete(cache_key)  # type: ignore[union-attr]
        except Exception:
            pass

    if not bust:
        try:
            cached = await cache.get_json(cache_key)
            if cached is not None:
                return cached
        except Exception:
            pass

    result = await compute_fn()
    result["cached_at"] = datetime.now(timezone.utc).isoformat()

    try:
        await cache.set_json(cache_key, result, ttl_seconds=CACHE_TTL)
    except Exception:
        pass

    return result


def _json_response(payload: dict) -> JSONResponse:
    """data + cached_at 분리하여 JSONResponse 반환."""
    cached_at = payload.get("cached_at", "")
    data = {k: v for k, v in payload.items() if k != "cached_at"}
    response = JSONResponse(content=data)
    response.headers["X-Cache-At"] = cached_at
    response.headers["Cache-Control"] = f"max-age={CACHE_TTL}"
    return response


# ── 1. GET /admin/analytics/cohort-retention ──────────────────────────────────


async def _query_cohort_retention(db: AsyncSession, days: int) -> dict:
    """cohort_alerts 테이블에서 D7/D30 retention 시계열 조회."""
    sql = text("""
        SELECT
            cohort_date,
            MAX(CASE WHEN metric_name = 'd7_retention' THEN value END)  AS d7,
            MAX(CASE WHEN metric_name = 'd30_retention' THEN value END) AS d30
        FROM cohort_alerts
        WHERE cohort_date >= CURRENT_DATE - CAST(:days AS INTEGER)
          AND status IN ('sent', 'skipped')
        GROUP BY cohort_date
        ORDER BY cohort_date ASC
    """)
    result = await db.execute(sql, {"days": days})
    rows = result.fetchall()

    series = []
    latest_d7: float | None = None
    latest_d30: float | None = None

    for row in rows:
        entry: dict = {"date": row.cohort_date.isoformat()}
        if row.d7 is not None:
            entry["d7_retention"] = round(float(row.d7), 4)
            latest_d7 = round(float(row.d7), 4)
        if row.d30 is not None:
            entry["d30_retention"] = round(float(row.d30), 4)
            latest_d30 = round(float(row.d30), 4)
        series.append(entry)

    # 임계값 조회 (가장 최근 행 기준)
    threshold_sql = text("""
        SELECT
            MAX(CASE WHEN metric_name = 'd7_retention' THEN threshold END) AS t7,
            MAX(CASE WHEN metric_name = 'd30_retention' THEN threshold END) AS t30
        FROM cohort_alerts
        WHERE cohort_date >= CURRENT_DATE - CAST(:days AS INTEGER)
        LIMIT 1
    """)
    t_result = await db.execute(threshold_sql, {"days": days})
    t_row = t_result.fetchone()

    return {
        "data": {
            "series": series,
            "summary": {
                "latest_d7": latest_d7,
                "latest_d30": latest_d30,
                "threshold_d7": round(float(t_row.t7), 4) if (t_row and t_row.t7) else 0.30,
                "threshold_d30": round(float(t_row.t30), 4) if (t_row and t_row.t30) else 0.15,
            },
            "meta": {
                "below_threshold_only": True,
                "note": "cohort_alerts는 임계치 미달 시에만 기록됩니다.",
            },
        }
    }


@router.get("/cohort-retention")
async def get_cohort_retention(
    period: Literal["7d", "30d", "90d"] = Query("30d"),
    bust: int = Query(0),
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_admin_with_2fa),
) -> JSONResponse:
    """D7/D30 retention 시계열 조회."""
    days = _PERIOD_DAYS.get(period, 30)
    cache_key = f"admin:analytics:cohort_retention:{period}"

    async def compute():
        return await _query_cohort_retention(db, days)

    payload = await _get_cached_or_compute(cache_key, compute, bust=bool(bust))
    return _json_response(payload)


# ── 2. GET /admin/analytics/newsletter-open-rate ──────────────────────────────


async def _query_newsletter_open_rate(db: AsyncSession, days: int) -> dict:
    """newsletter_issues + newsletter_events 집계."""
    sql = text("""
        SELECT
            DATE(ni.sent_at AT TIME ZONE 'UTC')                                      AS sent_date,
            COUNT(DISTINCT ni.id)                                                     AS issues_sent,
            ni.sent_count                                                             AS total_recipients,
            COUNT(DISTINCT CASE WHEN ne.event_type = 'open'  THEN ne.user_id END)   AS unique_opens,
            COUNT(DISTINCT CASE WHEN ne.event_type = 'click' THEN ne.user_id END)   AS unique_clicks
        FROM newsletter_issues ni
        LEFT JOIN newsletter_events ne ON ne.issue_id = ni.id
        WHERE ni.sent_at >= NOW() - make_interval(days => :days)
          AND ni.sent_at IS NOT NULL
          AND ni.status = 'sent'
        GROUP BY sent_date, ni.sent_count
        ORDER BY sent_date ASC
    """)
    result = await db.execute(sql, {"days": days})
    rows = result.fetchall()

    series = []
    total_open_rate = 0.0
    total_click_rate = 0.0
    count = 0

    for row in rows:
        recipients = max(int(row.total_recipients or 0), 1)
        unique_opens = int(row.unique_opens or 0)
        unique_clicks = int(row.unique_clicks or 0)
        open_rate = round(unique_opens / recipients, 4)
        click_rate = round(unique_clicks / recipients, 4)

        series.append({
            "date": row.sent_date.isoformat(),
            "issues_sent": int(row.issues_sent),
            "unique_opens": unique_opens,
            "unique_clicks": unique_clicks,
            "open_rate": open_rate,
            "click_rate": click_rate,
        })
        total_open_rate += open_rate
        total_click_rate += click_rate
        count += 1

    avg_open = round(total_open_rate / count, 4) if count else 0.0
    avg_click = round(total_click_rate / count, 4) if count else 0.0

    return {
        "data": {
            "series": series,
            "summary": {
                "avg_open_rate": avg_open,
                "avg_click_rate": avg_click,
                "total_issues": count,
            },
        }
    }


@router.get("/newsletter-open-rate")
async def get_newsletter_open_rate(
    period: Literal["7d", "30d", "90d"] = Query("30d"),
    bust: int = Query(0),
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_admin_with_2fa),
) -> JSONResponse:
    """Newsletter 발송/오픈/클릭 시계열 조회."""
    days = _PERIOD_DAYS.get(period, 30)
    cache_key = f"admin:analytics:newsletter_open_rate:{period}"

    async def compute():
        return await _query_newsletter_open_rate(db, days)

    payload = await _get_cached_or_compute(cache_key, compute, bust=bool(bust))
    return _json_response(payload)


# ── 3. GET /admin/analytics/feed-ctr ─────────────────────────────────────────


async def _query_feed_ctr(db: AsyncSession, days: int) -> dict:
    """ml_experiment_assignments + post_engagement_cache 로 알고리즘별 CTR 근사."""
    sql = text("""
        SELECT
            mea.variant_name                                                          AS algo,
            COUNT(DISTINCT mea.user_id)                                              AS user_count,
            COALESCE(AVG(pec.engagement_score), 0)                                   AS avg_engagement,
            COALESCE(
                COUNT(DISTINCT CASE WHEN pec.engagement_score > 0 THEN pec.post_id END)::float
                    / NULLIF(COUNT(DISTINCT pec.post_id), 0),
                0
            )                                                                         AS ctr_approx
        FROM ml_experiment_assignments mea
        LEFT JOIN post_engagement_cache pec
            ON pec.calculated_at >= NOW() - make_interval(days => :days)
        WHERE mea.created_at >= NOW() - make_interval(days => :days)
        GROUP BY mea.variant_name
        ORDER BY mea.variant_name
    """)
    result = await db.execute(sql, {"days": days})
    rows = result.fetchall()

    algos = []
    best_algo = None
    best_ctr = -1.0
    v1_ctr = None
    v2_ctr = None

    for row in rows:
        ctr = round(float(row.ctr_approx), 4)
        algos.append({
            "name": row.algo,
            "ctr": ctr,
            "user_count": int(row.user_count),
        })
        if ctr > best_ctr:
            best_ctr = ctr
            best_algo = row.algo
        if row.algo == "v1":
            v1_ctr = ctr
        elif row.algo == "v2":
            v2_ctr = ctr

    delta = round((v2_ctr or 0.0) - (v1_ctr or 0.0), 4)

    return {
        "data": {
            "algos": algos,
            "summary": {
                "best_algo": best_algo,
                "delta_v2_vs_v1": delta,
            },
        }
    }


@router.get("/feed-ctr")
async def get_feed_ctr(
    period: Literal["7d", "30d", "90d"] = Query("30d"),
    bust: int = Query(0),
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_admin_with_2fa),
) -> JSONResponse:
    """알고리즘별 Feed CTR 조회."""
    days = _PERIOD_DAYS.get(period, 30)
    cache_key = f"admin:analytics:feed_ctr:{period}"

    async def compute():
        return await _query_feed_ctr(db, days)

    payload = await _get_cached_or_compute(cache_key, compute, bust=bool(bust))
    return _json_response(payload)


# ── 4. GET /admin/analytics/ai-features-usage ────────────────────────────────


async def _query_ai_features_usage(db: AsyncSession, days: int) -> dict:
    """posts + ai_collections 에서 AI 기능별 사용 건수 집계."""
    sql = text("""
        SELECT 'caption' AS feature, COUNT(*) AS usage_count
        FROM posts
        WHERE ai_caption_generated_at >= NOW() - make_interval(days => :days)
          AND ai_caption_generated_at IS NOT NULL

        UNION ALL

        SELECT 'docent' AS feature, COUNT(*) AS usage_count
        FROM posts
        WHERE ai_docent_generated_at >= NOW() - make_interval(days => :days)
          AND ai_docent_generated_at IS NOT NULL

        UNION ALL

        SELECT 'collection' AS feature, COUNT(*) AS usage_count
        FROM ai_collections
        WHERE published_at >= NOW() - make_interval(days => :days)
          AND published_at IS NOT NULL
    """)
    result = await db.execute(sql, {"days": days})
    rows = result.fetchall()

    raw: dict[str, int] = {}
    for row in rows:
        raw[row.feature] = int(row.usage_count)

    total = sum(raw.values()) or 1  # division guard

    features = []
    for name in ("caption", "docent", "collection"):
        count = raw.get(name, 0)
        features.append({
            "name": name,
            "usage_count": count,
            "rate": round(count / total, 4),
        })

    return {
        "data": {
            "features": features,
            "summary": {
                "total_ai_usages": sum(raw.values()),
            },
        }
    }


@router.get("/ai-features-usage")
async def get_ai_features_usage(
    period: Literal["7d", "30d", "90d"] = Query("30d"),
    bust: int = Query(0),
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_admin_with_2fa),
) -> JSONResponse:
    """AI 기능별(캡션/도슨트/컬렉션) 사용률 조회."""
    days = _PERIOD_DAYS.get(period, 30)
    cache_key = f"admin:analytics:ai_features_usage:{period}"

    async def compute():
        return await _query_ai_features_usage(db, days)

    payload = await _get_cached_or_compute(cache_key, compute, bust=bool(bust))
    return _json_response(payload)
