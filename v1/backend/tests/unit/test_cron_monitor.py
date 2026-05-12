"""Unit tests for app/services/cron_monitor.py — Phase 13 C-1.

10 tests covering:
  1. record_cron_run: Redis 미설정 시 graceful skip
  2. record_cron_run: success 상태 Redis hash 기록
  3. record_cron_run: failed 상태 + error_message 기록
  4. record_cron_run: Redis 오류 시 graceful (exception 삼킴)
  5. get_all_cron_status: 전체 worker 반환 (Redis mock)
  6. get_all_cron_status: Redis 미설정 시 모든 worker is_overdue=True
  7. check_overdue_workers: 5분 기준 overdue 판정
  8. check_overdue_workers: last_run_at 최근 → overdue=False
  9. Slack alert 포맷 검증 (httpx mock)
  10. track_cron 데코레이터 success 경로
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest

from app.services.cron_monitor import (
    WORKER_REGISTRY,
    check_overdue_workers,
    get_all_cron_status,
    record_cron_run,
    track_cron,
)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _recent_iso(seconds_ago: int = 10) -> str:
    """최근 N초 전 ISO8601 문자열 반환."""
    return (datetime.now(timezone.utc) - timedelta(seconds=seconds_ago)).isoformat()


def _old_iso(seconds_ago: int = 600) -> str:
    """오래된 N초 전 ISO8601 문자열 반환."""
    return (datetime.now(timezone.utc) - timedelta(seconds=seconds_ago)).isoformat()


def _make_redis_mock(hgetall_return: dict | None = None) -> AsyncMock:
    """기본 async Redis mock 생성."""
    r = AsyncMock()
    r.hset = AsyncMock(return_value=1)
    r.hincrby = AsyncMock(return_value=1)
    r.expire = AsyncMock(return_value=True)
    r.hgetall = AsyncMock(return_value=hgetall_return or {})
    return r


# ─── Test 1: Redis 미설정 시 record_cron_run graceful skip ────────────────────

@pytest.mark.asyncio
async def test_record_cron_run_redis_disabled():
    """Redis None → no error, no Redis call."""
    with patch("app.services.cron_monitor.get_redis", return_value=None):
        # Should not raise
        await record_cron_run("auction", "success")


# ─── Test 2: record_cron_run success 상태 기록 ────────────────────────────────

@pytest.mark.asyncio
async def test_record_cron_run_success():
    """success 상태 기록: hset + hincrby + expire 호출."""
    mock_redis = _make_redis_mock()
    with patch("app.services.cron_monitor.get_redis", return_value=mock_redis):
        await record_cron_run("auction", "success")

    mock_redis.hset.assert_called_once()
    call_kwargs = mock_redis.hset.call_args
    mapping = call_kwargs.kwargs.get("mapping") or call_kwargs[1].get("mapping")
    assert mapping["status"] == "success"
    assert mapping["error_message"] == ""
    assert "last_run_at" in mapping

    mock_redis.hincrby.assert_called_once_with("cron:status:auction", "run_count", 1)
    mock_redis.expire.assert_called_once_with("cron:status:auction", 3600)


# ─── Test 3: record_cron_run failed + error_message ──────────────────────────

@pytest.mark.asyncio
async def test_record_cron_run_failed_with_error():
    """failed 상태 + error 메시지 기록."""
    mock_redis = _make_redis_mock()
    with patch("app.services.cron_monitor.get_redis", return_value=mock_redis):
        await record_cron_run("badge", "failed", error="DB timeout")

    mapping = mock_redis.hset.call_args.kwargs.get("mapping") or \
              mock_redis.hset.call_args[1].get("mapping")
    assert mapping["status"] == "failed"
    assert mapping["error_message"] == "DB timeout"


# ─── Test 4: Redis 오류 시 graceful (exception 삼킴) ──────────────────────────

@pytest.mark.asyncio
async def test_record_cron_run_redis_error_graceful():
    """Redis hset 오류 → exception이 caller로 전파되지 않아야 함."""
    mock_redis = _make_redis_mock()
    mock_redis.hset = AsyncMock(side_effect=ConnectionError("Redis down"))
    with patch("app.services.cron_monitor.get_redis", return_value=mock_redis):
        # Should not raise
        await record_cron_run("schedule", "success")


# ─── Test 5: get_all_cron_status 정상 반환 ────────────────────────────────────

@pytest.mark.asyncio
async def test_get_all_cron_status_with_redis():
    """Redis에 데이터 있는 worker 상태 정상 반환."""
    recent = _recent_iso(10)
    mock_data = {
        "auction": {
            "last_run_at": recent,
            "status": "success",
            "error_message": "",
            "run_count": "42",
        }
    }

    def fake_hgetall(key: str) -> dict:
        worker = key.replace("cron:status:", "")
        return mock_data.get(worker, {})

    mock_redis = AsyncMock()
    mock_redis.hgetall = AsyncMock(side_effect=fake_hgetall)

    with patch("app.services.cron_monitor.get_redis", return_value=mock_redis):
        result = await get_all_cron_status()

    assert len(result) == len(WORKER_REGISTRY)

    auction_status = next(w for w in result if w["name"] == "auction")
    assert auction_status["status"] == "success"
    assert auction_status["run_count"] == 42
    assert auction_status["last_run_at"] == recent
    assert auction_status["is_overdue"] is False  # 10초 전 = 5분 기준 overdue 아님

    # 데이터 없는 worker → None + overdue=True
    badge_status = next(w for w in result if w["name"] == "badge")
    assert badge_status["status"] is None
    assert badge_status["is_overdue"] is True


# ─── Test 6: get_all_cron_status Redis 미설정 ─────────────────────────────────

@pytest.mark.asyncio
async def test_get_all_cron_status_redis_disabled():
    """Redis None → 전체 worker is_overdue=True, status=None."""
    with patch("app.services.cron_monitor.get_redis", return_value=None):
        result = await get_all_cron_status()

    assert len(result) == len(WORKER_REGISTRY)
    for w in result:
        assert w["is_overdue"] is True
        assert w["status"] is None


# ─── Test 7: check_overdue_workers 5분 기준 overdue 판정 ──────────────────────

@pytest.mark.asyncio
async def test_check_overdue_workers_threshold():
    """6분 전 실행 worker → overdue 목록에 포함."""
    old = _old_iso(360)  # 6분 전

    def fake_hgetall(key: str) -> dict:
        return {"last_run_at": old, "status": "success", "error_message": "", "run_count": "1"}

    mock_redis = AsyncMock()
    mock_redis.hgetall = AsyncMock(side_effect=fake_hgetall)

    with patch("app.services.cron_monitor.get_redis", return_value=mock_redis):
        overdue = await check_overdue_workers()

    # 모든 worker가 6분 전 실행 → 전체 overdue
    assert len(overdue) == len(WORKER_REGISTRY)
    assert "auction" in overdue
    assert "audit_partition" in overdue


# ─── Test 8: check_overdue_workers 최근 실행 → not overdue ────────────────────

@pytest.mark.asyncio
async def test_check_overdue_workers_recent_not_overdue():
    """10초 전 실행 worker → overdue 목록에 미포함."""
    recent = _recent_iso(10)

    def fake_hgetall(key: str) -> dict:
        return {"last_run_at": recent, "status": "success", "error_message": "", "run_count": "1"}

    mock_redis = AsyncMock()
    mock_redis.hgetall = AsyncMock(side_effect=fake_hgetall)

    with patch("app.services.cron_monitor.get_redis", return_value=mock_redis):
        overdue = await check_overdue_workers()

    assert len(overdue) == 0


# ─── Test 9: Slack alert 포맷 검증 ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_slack_alert_format():
    """send_slack_alert: payload Block Kit 포맷 검증."""
    from app.services.slack_alert_cron import _build_slack_payload

    now = datetime(2026, 5, 9, 3, 0, 0, tzinfo=timezone.utc)
    payload = _build_slack_payload(["auction", "badge"], now)

    assert "blocks" in payload
    blocks = payload["blocks"]
    # header block
    assert blocks[0]["type"] == "header"
    assert "Overdue" in blocks[0]["text"]["text"]
    # section block — worker names
    section_text = blocks[1]["text"]["text"]
    assert "auction" in section_text
    assert "badge" in section_text
    # context block — count
    context_text = blocks[2]["elements"][0]["text"]
    assert "2개" in context_text


@pytest.mark.asyncio
async def test_slack_alert_no_webhook_graceful():
    """SLACK_WEBHOOK_URL 미설정 시 예외 없이 log.warning만 출력."""
    from app.services.slack_alert_cron import send_slack_alert

    with patch.dict("os.environ", {}, clear=True):
        # Should not raise
        await send_slack_alert(["auction"])


# ─── Test 10: track_cron 데코레이터 success 경로 ──────────────────────────────

@pytest.mark.asyncio
async def test_track_cron_decorator_success():
    """@track_cron success 경로: running → success 두 번 record_cron_run 호출."""
    calls: list[tuple] = []

    async def fake_record(worker_name: str, status: str, error: str | None = None):
        calls.append((worker_name, status, error))

    with patch("app.services.cron_monitor.record_cron_run", side_effect=fake_record):
        @track_cron("test_worker")
        async def _run():
            return "ok"

        result = await _run()

    assert result == "ok"
    assert calls[0] == ("test_worker", "running", None)
    assert calls[1] == ("test_worker", "success", None)
