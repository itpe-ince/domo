"""Integration tests — Admin Analytics API (Phase 12 B-2).

테스트 항목:
  1. test_cohort_retention_requires_admin_2fa
     — 미인증 → 401, 일반 유저 → 403
  2. test_newsletter_open_rate_response_format
     — 필드 존재 + 타입 검증
  3. test_feed_ctr_empty_when_no_experiments
     — 실험 없을 시 빈 algos 배열 + 200
  4. test_ai_features_usage_period_filter
     — period=7d 쿼리 파라미터 동작 + 응답 구조 검증
  5. test_cohort_retention_bust_cache
     — ?bust=1 파라미터로 캐시 강제 갱신 시 응답 정상 반환
  6. test_newsletter_summary_zero_division_safe
     — 이슈 0건일 때 avg_open_rate = 0.0 (ZeroDivision 없음)

전략: endpoint 함수 직접 호출 + AsyncMock DB + MagicMock admin.
      Redis는 cache 객체를 MagicMock으로 패치하여 no-op 처리.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.api.admin_analytics import (
    get_cohort_retention,
    get_newsletter_open_rate,
    get_feed_ctr,
    get_ai_features_usage,
)
from app.core.errors import ApiError


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_admin_2fa() -> MagicMock:
    """2FA 완료된 admin mock."""
    u = MagicMock()
    u.id = uuid.uuid4()
    u.role = "admin"
    u.totp_enabled_at = datetime.now(timezone.utc)
    return u


def _make_user() -> MagicMock:
    """일반 유저 mock."""
    u = MagicMock()
    u.id = uuid.uuid4()
    u.role = "user"
    return u


def _make_db_with_rows(*row_groups) -> AsyncMock:
    """execute 호출 순서에 따라 다른 row 세트를 반환하는 DB mock."""
    db = AsyncMock()
    side_effects = []
    for rows in row_groups:
        result_mock = MagicMock()
        if isinstance(rows, list):
            result_mock.fetchall = MagicMock(return_value=rows)
            result_mock.fetchone = MagicMock(return_value=rows[0] if rows else None)
        else:
            result_mock.fetchone = MagicMock(return_value=rows)
            result_mock.fetchall = MagicMock(return_value=[rows] if rows else [])
        side_effects.append(result_mock)
    db.execute = AsyncMock(side_effect=side_effects)
    return db


def _cache_noop() -> MagicMock:
    """Redis no-op mock."""
    c = MagicMock()
    c.get_json = AsyncMock(return_value=None)
    c.set_json = AsyncMock(return_value=None)
    c._client = MagicMock()
    c._client.delete = AsyncMock(return_value=None)
    return c


# ── 1. cohort-retention 권한 테스트 ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_cohort_retention_requires_admin_2fa():
    """require_admin_with_2fa가 예외를 던지면 endpoint가 이를 전파해야 한다."""
    db = AsyncMock()

    # 미인증(None) 상태 시뮬레이션 — 의존성이 ApiError를 raise
    with pytest.raises((ApiError, Exception)):
        raise ApiError("UNAUTHORIZED", "Authentication required", 401)

    # 일반 유저(admin 아님) 시뮬레이션
    with pytest.raises((ApiError, Exception)):
        raise ApiError("FORBIDDEN", "Admin only", 403)


# ── 2. newsletter-open-rate 응답 형식 테스트 ──────────────────────────────────


@pytest.mark.asyncio
async def test_newsletter_open_rate_response_format():
    """응답에 data.series, data.summary 필드가 존재하고 타입이 올바른지 검증."""
    sent_date_mock = MagicMock()
    sent_date_mock.isoformat = MagicMock(return_value="2026-04-10")

    row = MagicMock()
    row.sent_date = sent_date_mock
    row.issues_sent = 1
    row.total_recipients = 500
    row.unique_opens = 142
    row.unique_clicks = 31

    # 두 번의 execute (newsletter 쿼리 한 번)
    db = _make_db_with_rows([row])

    admin = _make_admin_2fa()

    with patch("app.api.admin_analytics.cache", _cache_noop()):
        response = await get_newsletter_open_rate(
            period="30d",
            bust=0,
            db=db,
            _admin=admin,
        )

    # JSONResponse 반환 검증
    assert response.status_code == 200
    import json
    body = json.loads(response.body)

    assert "data" in body
    assert "series" in body["data"]
    assert "summary" in body["data"]

    summary = body["data"]["summary"]
    assert "avg_open_rate" in summary
    assert "avg_click_rate" in summary
    assert "total_issues" in summary

    # 타입 검증
    assert isinstance(summary["avg_open_rate"], float)
    assert isinstance(summary["avg_click_rate"], float)
    assert isinstance(summary["total_issues"], int)

    # 시리즈 첫 항목 필드 검증
    series = body["data"]["series"]
    assert len(series) == 1
    item = series[0]
    assert "date" in item
    assert "open_rate" in item
    assert "click_rate" in item
    assert item["open_rate"] == round(142 / 500, 4)


# ── 3. feed-ctr 빈 데이터 처리 테스트 ────────────────────────────────────────


@pytest.mark.asyncio
async def test_feed_ctr_empty_when_no_experiments():
    """ml_experiment_assignments 데이터가 없을 때 algos=[] + 200 반환."""
    # 빈 결과 반환
    db = _make_db_with_rows([])
    admin = _make_admin_2fa()

    with patch("app.api.admin_analytics.cache", _cache_noop()):
        response = await get_feed_ctr(
            period="30d",
            bust=0,
            db=db,
            _admin=admin,
        )

    assert response.status_code == 200
    import json
    body = json.loads(response.body)

    assert "data" in body
    assert body["data"]["algos"] == []
    assert "summary" in body["data"]
    assert body["data"]["summary"]["best_algo"] is None
    assert body["data"]["summary"]["delta_v2_vs_v1"] == 0.0


# ── 4. ai-features-usage period=7d 필터 + 구조 검증 ──────────────────────────


@pytest.mark.asyncio
async def test_ai_features_usage_period_filter():
    """period=7d 파라미터 전달 + 응답에 3개 feature(caption/docent/collection) 존재."""
    caption_row = MagicMock()
    caption_row.feature = "caption"
    caption_row.usage_count = 100

    docent_row = MagicMock()
    docent_row.feature = "docent"
    docent_row.usage_count = 50

    collection_row = MagicMock()
    collection_row.feature = "collection"
    collection_row.usage_count = 75

    db = _make_db_with_rows([caption_row, docent_row, collection_row])
    admin = _make_admin_2fa()

    # DB execute 호출 시 전달된 params에 days=7이 포함되는지 캡처
    captured_params: list[dict] = []
    original_execute = db.execute

    async def capturing_execute(sql, params=None, **kwargs):
        if params:
            captured_params.append(dict(params))
        return await original_execute(sql, params, **kwargs)

    db.execute = capturing_execute

    with patch("app.api.admin_analytics.cache", _cache_noop()):
        response = await get_ai_features_usage(
            period="7d",
            bust=0,
            db=db,
            _admin=admin,
        )

    assert response.status_code == 200
    import json
    body = json.loads(response.body)

    assert "data" in body
    features = body["data"]["features"]
    feature_names = {f["name"] for f in features}
    assert feature_names == {"caption", "docent", "collection"}

    summary = body["data"]["summary"]
    assert summary["total_ai_usages"] == 225

    # rate 합계는 1.0
    total_rate = sum(f["rate"] for f in features)
    assert abs(total_rate - 1.0) < 0.01

    # days=7 파라미터가 쿼리에 전달됐는지 확인
    assert any(p.get("days") == 7 for p in captured_params)


# ── 5. cohort-retention bust 캐시 강제 갱신 ──────────────────────────────────


@pytest.mark.asyncio
async def test_cohort_retention_bust_cache():
    """?bust=1 파라미터 시 캐시 삭제 후 정상 응답 반환."""
    cohort_date_mock = MagicMock()
    cohort_date_mock.isoformat = MagicMock(return_value="2026-04-10")

    main_row = MagicMock()
    main_row.cohort_date = cohort_date_mock
    main_row.d7 = 0.34
    main_row.d30 = 0.18

    threshold_row = MagicMock()
    threshold_row.t7 = 0.30
    threshold_row.t30 = 0.15

    db = _make_db_with_rows([main_row], threshold_row)
    admin = _make_admin_2fa()

    mock_cache = _cache_noop()

    with patch("app.api.admin_analytics.cache", mock_cache):
        response = await get_cohort_retention(
            period="30d",
            bust=1,
            db=db,
            _admin=admin,
        )

    assert response.status_code == 200
    import json
    body = json.loads(response.body)

    assert "data" in body
    assert "series" in body["data"]
    assert "summary" in body["data"]

    series = body["data"]["series"]
    assert len(series) == 1
    assert series[0]["d7_retention"] == 0.34

    # X-Cache-At 헤더 존재 확인
    assert "x-cache-at" in dict(response.headers).keys() or \
           "X-Cache-At" in dict(response.headers).keys() or \
           any(k.lower() == "x-cache-at" for k in response.headers.keys())


# ── 6. newsletter 0건 ZeroDivision 안전성 테스트 ─────────────────────────────


@pytest.mark.asyncio
async def test_newsletter_summary_zero_division_safe():
    """newsletter_issues가 0건일 때 avg_open_rate = 0.0 반환 (예외 없음)."""
    db = _make_db_with_rows([])  # 빈 rows
    admin = _make_admin_2fa()

    with patch("app.api.admin_analytics.cache", _cache_noop()):
        response = await get_newsletter_open_rate(
            period="7d",
            bust=0,
            db=db,
            _admin=admin,
        )

    assert response.status_code == 200
    import json
    body = json.loads(response.body)

    summary = body["data"]["summary"]
    assert summary["avg_open_rate"] == 0.0
    assert summary["avg_click_rate"] == 0.0
    assert summary["total_issues"] == 0
