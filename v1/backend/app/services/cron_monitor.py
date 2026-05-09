"""Cron Monitor Service — Phase 13 C-1.

Redis hash 기반 cron worker 상태 추적 서비스.

스키마:
  key: cron:status:{worker_name}
  fields: last_run_at (ISO8601), status (running/success/failed),
          error_message (str), run_count (int-as-str)
  TTL: 3600초 (1시간)

Usage:
    await record_cron_run("auction", "success")
    await record_cron_run("auction", "failed", error="timeout")
    statuses = await get_all_cron_status()
    overdue = await check_overdue_workers()

또는 데코레이터 패턴:
    @track_cron("auction")
    async def _run():
        ...do work...
"""
from __future__ import annotations

import asyncio
import functools
import logging
from datetime import datetime, timezone
from typing import Any

from app.core.redis_client import get_redis

log = logging.getLogger(__name__)

# Redis key prefix
_PREFIX = "cron:status:"
# TTL: 1시간 (Redis key 만료 = overdue 판정 근거)
_TTL_SECONDS = 3600
# overdue 기준: 5분 (300초)
OVERDUE_THRESHOLD_SECONDS = 300

# 등록된 worker 목록 (26개 — 26번째는 slack_alert 자신)
WORKER_REGISTRY: list[str] = [
    "auction",              # 1 — 5분 interval
    "gdpr",                 # 2 — 1h interval
    "schedule",             # 3 — 1분 interval
    "badge",                # 4 — 1일 interval
    "settlement",           # 5 — 1일 interval
    "webhook_cleanup",      # 6 — 1일 interval
    "draft_cleanup",        # 7 — 1일 interval
    "tier_release",         # 8 — 1분 interval
    "auction_promotion",    # 9 — 1분 interval
    "artist_index",         # 10 — 1h interval
    "post_engagement",      # 11 — 1h interval
    "subscription_expiry",  # 12 — 1h interval
    "newsletter",           # 13 — 1h interval
    "exchange_rate",        # 14 — 1h interval
    "email_digest",         # 15 — 1h interval
    "auto_renewal",         # 16 — 1h interval
    "embedding",            # 17 — quick 60s + batch 24h
    "rss_fetch",            # 18 — 1h interval
    "cohort_alert",         # 19 — 1일 interval
    "ml_training",          # 20 — 1일 interval
    "artwork_caption",      # 21 — quick 60s + batch 24h
    "featured_artist",      # 22 — 주 1회 (월요일)
    "ai_curation",          # 23 — 주 1회 (월요일)
    "audit_log_cleanup",    # 24 — 1일 interval
    "audit_partition",      # 25 — 1일 interval
    "slack_alert",          # 26 — 1분 interval (자기참조 OK)
]

# worker별 interval 레이블 (UI 표시용)
WORKER_INTERVAL_LABELS: dict[str, str] = {
    "auction": "5분",
    "gdpr": "1시간",
    "schedule": "1분",
    "badge": "1일",
    "settlement": "1일",
    "webhook_cleanup": "1일",
    "draft_cleanup": "1일",
    "tier_release": "1분",
    "auction_promotion": "1분",
    "artist_index": "1시간",
    "post_engagement": "1시간",
    "subscription_expiry": "1시간",
    "newsletter": "1시간",
    "exchange_rate": "1시간",
    "email_digest": "1시간",
    "auto_renewal": "1시간",
    "embedding": "60s+24h",
    "rss_fetch": "1시간",
    "cohort_alert": "1일",
    "ml_training": "1일",
    "artwork_caption": "60s+24h",
    "featured_artist": "주1회",
    "ai_curation": "주1회",
    "audit_log_cleanup": "1일",
    "audit_partition": "1일",
    "slack_alert": "1분",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _is_overdue(last_run_at: str | None) -> bool:
    """last_run_at 기준 5분(300초) 이상 경과 여부."""
    if last_run_at is None:
        return True
    try:
        last = datetime.fromisoformat(last_run_at)
        return (_now_utc() - last).total_seconds() > OVERDUE_THRESHOLD_SECONDS
    except (ValueError, TypeError):
        return True


async def record_cron_run(
    worker_name: str,
    status: str,
    error: str | None = None,
) -> None:
    """Redis hash에 cron 실행 결과를 기록한다.

    Args:
        worker_name: cron worker 이름 (WORKER_REGISTRY에 있어야 함)
        status: "running" | "success" | "failed"
        error: 에러 메시지 (status="failed" 시 설정)
    """
    r = get_redis()
    if r is None:
        log.debug("cron_monitor: Redis not available, skipping record for %s", worker_name)
        return

    key = f"{_PREFIX}{worker_name}"
    mapping: dict[str, str] = {
        "last_run_at": _now_iso(),
        "status": status,
        "error_message": error or "",
    }

    try:
        # HSET all fields atomically
        await r.hset(key, mapping=mapping)  # type: ignore[arg-type]
        # incr run_count
        await r.hincrby(key, "run_count", 1)
        # refresh TTL
        await r.expire(key, _TTL_SECONDS)
    except Exception as exc:  # noqa: BLE001
        log.warning("cron_monitor: failed to record %s → %s: %s", worker_name, status, exc)


async def get_all_cron_status() -> list[dict[str, Any]]:
    """WORKER_REGISTRY 전체 상태를 반환한다.

    Redis에 키가 없는 worker는 status=None, is_overdue=True로 반환.

    Returns:
        list of dicts with keys:
            name, status, last_run_at, error_message, run_count, is_overdue, interval_label
    """
    r = get_redis()
    result: list[dict[str, Any]] = []

    for worker in WORKER_REGISTRY:
        if r is not None:
            try:
                data = await r.hgetall(f"{_PREFIX}{worker}")
            except Exception as exc:  # noqa: BLE001
                log.warning("cron_monitor: hgetall failed for %s: %s", worker, exc)
                data = {}
        else:
            data = {}

        last_run_at = data.get("last_run_at") or None
        status = data.get("status") or None
        error_message = data.get("error_message") or None
        run_count_raw = data.get("run_count", "0")
        try:
            run_count = int(run_count_raw)
        except (ValueError, TypeError):
            run_count = 0

        result.append(
            {
                "name": worker,
                "status": status,
                "last_run_at": last_run_at,
                "error_message": error_message if error_message else None,
                "run_count": run_count,
                "is_overdue": _is_overdue(last_run_at),
                "interval_label": WORKER_INTERVAL_LABELS.get(worker, "?"),
            }
        )

    return result


async def check_overdue_workers() -> list[str]:
    """5분 이상 미실행(또는 Redis 키 미존재) worker 이름 목록을 반환한다.

    Returns:
        overdue worker 이름 리스트
    """
    all_statuses = await get_all_cron_status()
    return [s["name"] for s in all_statuses if s["is_overdue"]]


def track_cron(worker_name: str):
    """cron 실행 함수를 감싸는 async 데코레이터 팩토리.

    시작 시 status="running" 기록,
    정상 종료 시 status="success" 기록,
    예외 발생 시 status="failed" + error 메시지 기록.

    Usage:
        @track_cron("auction")
        async def _run_once():
            ...실제 작업...

        await _run_once()

    기존 with record_cron_run("worker"): 블록과 공존 가능.
    Prometheus metrics는 기존 record_cron_run이 담당하고,
    이 데코레이터는 Redis hash 기록만 처리한다.
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            await record_cron_run(worker_name, "running")
            try:
                result = await func(*args, **kwargs)
                await record_cron_run(worker_name, "success")
                return result
            except asyncio.CancelledError:
                # 정상 종료 (app shutdown) — 상태 유지
                raise
            except Exception as exc:
                await record_cron_run(worker_name, "failed", error=str(exc)[:500])
                raise

        return wrapper

    decorator._worker_name = worker_name  # type: ignore[attr-defined]
    return decorator
