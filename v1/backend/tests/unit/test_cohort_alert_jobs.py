"""Unit tests — cohort_alert_jobs.py (Phase 9 L-F).

테스트 범위:
  - threshold 미달 시 alert 발송 + cohort_alerts INSERT
  - threshold 초과 시 알림 발송 없음 (skipped)
  - UNIQUE INDEX 중복 처리: 같은 날 재실행 시 idempotent (existing 행 발견 → skip)
  - Slack webhook 미설정 시 graceful (status='sent', error 없음)
  - 발송 성공 시 status='sent', sent_at 기록
  - cohort 크기 < min_size 시 측정 skip
  - D30 retention alert 별도 확인
  - 환경변수 임계값 오버라이드 반영
"""
from __future__ import annotations

import os
from datetime import date, datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import app.services.cohort_alert_jobs as caj_module
from app.services.cohort_alert_jobs import (
    _get_threshold_7d,
    _get_threshold_30d,
    _get_min_cohort_size,
    _measure_cohort_retention,
    _send_slack_alert,
    check_and_alert_once,
)


# ──────────────────────────────────────────────────────────────────────────────
# 헬퍼
# ──────────────────────────────────────────────────────────────────────────────

def _make_scalar_result(value) -> MagicMock:
    """db.execute().scalar() 결과 mock."""
    result = MagicMock()
    result.scalar = MagicMock(return_value=value)
    return result


def _make_scalar_one_or_none(value) -> MagicMock:
    """db.execute().scalar_one_or_none() 결과 mock."""
    result = MagicMock()
    result.scalar_one_or_none = MagicMock(return_value=value)
    return result


# ──────────────────────────────────────────────────────────────────────────────
# 1. 환경변수 임계값
# ──────────────────────────────────────────────────────────────────────────────

def test_default_thresholds():
    """기본 임계값: D7=0.30, D30=0.15, min_size=10."""
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("COHORT_ALERT_7D_THRESHOLD", None)
        os.environ.pop("COHORT_ALERT_30D_THRESHOLD", None)
        os.environ.pop("COHORT_ALERT_MIN_COHORT_SIZE", None)
        assert _get_threshold_7d() == 0.30
        assert _get_threshold_30d() == 0.15
        assert _get_min_cohort_size() == 10


def test_env_threshold_override(monkeypatch):
    """환경변수 변경 시 임계값 반영."""
    monkeypatch.setenv("COHORT_ALERT_7D_THRESHOLD", "0.50")
    monkeypatch.setenv("COHORT_ALERT_30D_THRESHOLD", "0.25")
    monkeypatch.setenv("COHORT_ALERT_MIN_COHORT_SIZE", "20")

    assert _get_threshold_7d() == 0.50
    assert _get_threshold_30d() == 0.25
    assert _get_min_cohort_size() == 20


# ──────────────────────────────────────────────────────────────────────────────
# 2. _measure_cohort_retention
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_small_cohort_skipped(monkeypatch):
    """cohort 크기 < min_size 시 None 반환 (측정 skip)."""
    monkeypatch.setenv("COHORT_ALERT_MIN_COHORT_SIZE", "10")

    # 과거 날짜 사용 (D7 측정 가능 범위)
    cohort_date = date.today() - timedelta(days=14)

    db = AsyncMock()
    # cohort_count = 5 (min_size=10 미만)
    db.execute.return_value = _make_scalar_result(5)

    result = await _measure_cohort_retention(db, cohort_date, 7)
    assert result is None


@pytest.mark.asyncio
async def test_future_retention_date_returns_none():
    """D30 측정에서 retention_check_date가 오늘 이후 → None 반환."""
    # 10일 전 가입 cohort → D30 retention date = 20일 후 (미래)
    cohort_date = date.today() - timedelta(days=10)
    db = AsyncMock()

    result = await _measure_cohort_retention(db, cohort_date, 30)
    assert result is None
    db.execute.assert_not_called()


@pytest.mark.asyncio
async def test_measure_retention_calculates_ratio(monkeypatch):
    """cohort_count=100, active=30 → retention=0.30."""
    monkeypatch.setenv("COHORT_ALERT_MIN_COHORT_SIZE", "10")
    cohort_date = date.today() - timedelta(days=14)

    db = AsyncMock()
    # 첫 번째 execute: cohort_count=100
    # 두 번째 execute: active_count=30
    call_count = 0
    def side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return _make_scalar_result(100)
        return _make_scalar_result(30)

    db.execute.side_effect = side_effect

    result = await _measure_cohort_retention(db, cohort_date, 7)
    assert result == pytest.approx(0.30)


# ──────────────────────────────────────────────────────────────────────────────
# 3. _send_slack_alert
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_slack_mock_mode_no_error(monkeypatch):
    """SLACK_WEBHOOK_URL 미설정 시 예외 없이 None 반환 (Mock 모드)."""
    monkeypatch.delenv("SLACK_WEBHOOK_URL", raising=False)

    result = await _send_slack_alert(
        cohort_date=date.today() - timedelta(days=1),
        metric_name="d7_retention",
        value=0.20,
        threshold=0.30,
    )
    # Mock 모드: None 반환 (에러 없음)
    assert result is None


@pytest.mark.asyncio
async def test_slack_sent_returns_ts(monkeypatch):
    """Slack 발송 성공 시 ts 문자열 반환."""
    monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://hooks.slack.com/test")

    with patch("app.services.cohort_alert_jobs.httpx.AsyncClient") as mock_client_cls:
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await _send_slack_alert(
            cohort_date=date.today() - timedelta(days=1),
            metric_name="d7_retention",
            value=0.22,
            threshold=0.30,
        )

    assert result is not None
    assert isinstance(result, str)


# ──────────────────────────────────────────────────────────────────────────────
# 4. check_and_alert_once
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_alert_triggered_below_threshold(monkeypatch):
    """D7 retention < threshold → alerted=1."""
    monkeypatch.setenv("COHORT_ALERT_7D_THRESHOLD", "0.30")
    monkeypatch.setenv("COHORT_ALERT_30D_THRESHOLD", "0.15")
    monkeypatch.setenv("SLACK_WEBHOOK_URL", "")  # Mock 모드

    db = AsyncMock()
    db.execute.return_value = MagicMock()
    db.execute.return_value.scalar_one_or_none = MagicMock(return_value=None)

    with (
        patch.object(caj_module, "_measure_cohort_retention") as mock_measure,
        patch.object(caj_module, "_send_slack_alert") as mock_slack,
    ):
        # D7 미달, D30 OK
        async def measure_side(db, cohort_date, days):
            if days == 7:
                return 0.20  # 미달 (threshold 0.30)
            return 0.20  # D30도 미달이지만 임계값 0.15 초과 → skip (0.20 > 0.15)

        mock_measure.side_effect = measure_side
        mock_slack.return_value = None  # Mock 모드

        # D30 threshold 0.15보다 높은 0.20이면 알림 안 뜸
        # D7 threshold 0.30보다 낮은 0.20이면 알림 뜸
        result = await check_and_alert_once(db)

    assert result["alerted"] >= 1


@pytest.mark.asyncio
async def test_no_alert_above_threshold(monkeypatch):
    """D7 retention >= threshold → alerted=0."""
    monkeypatch.setenv("COHORT_ALERT_7D_THRESHOLD", "0.30")
    monkeypatch.setenv("COHORT_ALERT_30D_THRESHOLD", "0.15")

    db = AsyncMock()
    db.execute.return_value = MagicMock()
    db.execute.return_value.scalar_one_or_none = MagicMock(return_value=None)

    with (
        patch.object(caj_module, "_measure_cohort_retention") as mock_measure,
        patch.object(caj_module, "_send_slack_alert") as mock_slack,
    ):
        async def measure_ok(db, cohort_date, days):
            if days == 7:
                return 0.40  # threshold 0.30 초과 → OK
            return 0.25  # D30: threshold 0.15 초과 → OK

        mock_measure.side_effect = measure_ok
        mock_slack.return_value = None

        result = await check_and_alert_once(db)

    assert result["alerted"] == 0
    mock_slack.assert_not_called()


@pytest.mark.asyncio
async def test_cooldown_prevents_duplicate(monkeypatch):
    """24h 이내 동일 metric_name 알림 2회 요청 시 2회차 skipped."""
    monkeypatch.setenv("COHORT_ALERT_7D_THRESHOLD", "0.30")
    monkeypatch.setenv("COHORT_ALERT_30D_THRESHOLD", "0.15")

    db = AsyncMock()

    # 이미 오늘 처리된 알림 행이 존재하는 상황
    existing_row = MagicMock()
    db.execute.return_value.scalar_one_or_none = MagicMock(return_value=existing_row)

    with patch.object(caj_module, "_send_slack_alert") as mock_slack:
        result = await check_and_alert_once(db)

    # 모든 지표가 existing_row로 인해 skip
    assert result["skipped"] == 2  # d7_retention + d30_retention 모두 skip
    mock_slack.assert_not_called()


@pytest.mark.asyncio
async def test_d30_retention_alert(monkeypatch):
    """D30 retention < threshold → D30 전용 알림 발송."""
    monkeypatch.setenv("COHORT_ALERT_7D_THRESHOLD", "0.30")
    monkeypatch.setenv("COHORT_ALERT_30D_THRESHOLD", "0.15")
    monkeypatch.setenv("SLACK_WEBHOOK_URL", "")  # Mock 모드

    db = AsyncMock()
    db.execute.return_value = MagicMock()
    db.execute.return_value.scalar_one_or_none = MagicMock(return_value=None)

    with (
        patch.object(caj_module, "_measure_cohort_retention") as mock_measure,
        patch.object(caj_module, "_send_slack_alert") as mock_slack,
    ):
        async def measure_d30_fail(db, cohort_date, days):
            if days == 7:
                return 0.50  # D7 OK
            return 0.10  # D30 미달 (threshold 0.15)

        mock_measure.side_effect = measure_d30_fail
        mock_slack.return_value = None

        result = await check_and_alert_once(db)

    # D30 미달로 인한 알림 1건
    assert result["alerted"] >= 1
    # d30_retention으로 호출 확인
    call_args_list = mock_slack.call_args_list
    assert any("d30_retention" in str(call) for call in call_args_list)


@pytest.mark.asyncio
async def test_slack_webhook_not_set_status_sent(monkeypatch):
    """SLACK_WEBHOOK_URL 미설정 시 status='sent'로 기록 (Mock 모드 정상 동작)."""
    monkeypatch.setenv("COHORT_ALERT_7D_THRESHOLD", "0.30")
    monkeypatch.setenv("COHORT_ALERT_30D_THRESHOLD", "0.15")
    monkeypatch.delenv("SLACK_WEBHOOK_URL", raising=False)

    db = AsyncMock()
    db.execute.return_value = MagicMock()
    db.execute.return_value.scalar_one_or_none = MagicMock(return_value=None)

    with patch.object(caj_module, "_measure_cohort_retention") as mock_measure:
        async def measure_fail(db, cohort_date, days):
            return 0.10  # 두 지표 모두 미달

        mock_measure.side_effect = measure_fail

        # 예외 없이 실행되어야 함
        result = await check_and_alert_once(db)

    assert result["errors"] == 0
    assert result["alerted"] >= 1  # Mock 모드에서도 sent로 기록
