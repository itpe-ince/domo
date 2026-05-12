"""Cohort Retention 자동 알림 cron — Phase 9 L-F.

일 1회(06:00 UTC) 어제 cohort 날짜의 D7/D30 retention 지표를 측정하고,
임계치 미달 시 Slack Incoming Webhook으로 자동 알림을 발송한다.

설계 결정:
  - UNIQUE INDEX on (cohort_date, metric_name): 같은 날 같은 지표 중복 알림 차단.
  - SLACK_WEBHOOK_URL 미설정 시: log.warning 출력 후 status='sent' 기록 (Mock 모드).
    Mock 모드에서도 cohort_alerts 행을 INSERT해 24h cooldown이 동작하도록 한다.
  - cohort 크기 < COHORT_ALERT_MIN_COHORT_SIZE 시: 측정 skip (통계 신뢰도 부족).
  - behavioral_history 테이블 기반 retention 측정 (Phase 8 H'-6 기반).
    테이블 미존재 시(CI 환경 등) 우아하게 None 반환.

임계값 환경변수:
  COHORT_ALERT_7D_THRESHOLD   (기본 0.30 — D7 retention 30% 미만 시 경고)
  COHORT_ALERT_30D_THRESHOLD  (기본 0.15 — D30 retention 15% 미만 시 경고)
  COHORT_ALERT_MIN_COHORT_SIZE (기본 10 — cohort 크기 미만 시 측정 skip)
  SLACK_WEBHOOK_URL           (미설정 시 Mock 모드)
  COHORT_ALERT_WORKER_ENABLED  (기본 true)
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import date, datetime, timedelta, timezone
from typing import Any

import httpx
from sqlalchemy import func, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.models.cohort_alert import CohortAlert
from app.services.cron_monitor import record_cron_run as _push_cron_status

log = logging.getLogger(__name__)

# ─── 환경변수 기반 임계값 ───────────────────────────────────────────────────────


def _get_threshold_7d() -> float:
    return float(os.getenv("COHORT_ALERT_7D_THRESHOLD", "0.30"))


def _get_threshold_30d() -> float:
    return float(os.getenv("COHORT_ALERT_30D_THRESHOLD", "0.15"))


def _get_min_cohort_size() -> int:
    return int(os.getenv("COHORT_ALERT_MIN_COHORT_SIZE", "10"))


def _get_slack_webhook_url() -> str:
    return os.getenv("SLACK_WEBHOOK_URL", "")


# ─── Retention 측정 ───────────────────────────────────────────────────────────


async def _measure_cohort_retention(
    db: AsyncSession,
    cohort_date: date,
    days: int,
) -> float | None:
    """cohort_date에 가입한 사용자의 days일 후 retention 비율 계산.

    retention = (cohort_date 가입 유저 중 days일 후 접속한 유저 수) / (cohort_date 가입 유저 수)

    Returns:
        retention 비율 (0.0~1.0), 또는 아래 사유로 None:
        - cohort_date 가입자 수 < COHORT_ALERT_MIN_COHORT_SIZE
        - behavioral_history 테이블 미존재 (CI 환경 등)
        - days일 후 날짜가 오늘 이후 (미래 — 측정 불가)
    """
    min_size = _get_min_cohort_size()

    # days일 후 날짜 — 오늘 이후면 측정 불가
    retention_check_date = cohort_date + timedelta(days=days)
    today = date.today()
    if retention_check_date >= today:
        log.debug(
            "cohort_alert: D%d retention 측정 불가 (retention_check_date=%s >= today=%s)",
            days, retention_check_date, today,
        )
        return None

    try:
        # cohort_date 가입자 수
        cohort_count_result = await db.execute(
            text(
                "SELECT COUNT(*) FROM users "
                "WHERE DATE(created_at AT TIME ZONE 'UTC') = :cohort_date"
            ),
            {"cohort_date": cohort_date},
        )
        cohort_count = cohort_count_result.scalar() or 0

        if cohort_count < min_size:
            log.debug(
                "cohort_alert: D%d skip — cohort_date=%s size=%d < min=%d",
                days, cohort_date, cohort_count, min_size,
            )
            return None

        # days일 후 접속한 cohort 유저 수 (behavioral_history 기반)
        # behavioral_history 테이블이 없으면 IntrospectionError 발생 → None 반환
        active_result = await db.execute(
            text(
                "SELECT COUNT(DISTINCT user_id) FROM behavioral_history "
                "WHERE user_id IN ("
                "    SELECT id FROM users "
                "    WHERE DATE(created_at AT TIME ZONE 'UTC') = :cohort_date"
                ") "
                "AND DATE(created_at AT TIME ZONE 'UTC') = :retention_date"
            ),
            {"cohort_date": cohort_date, "retention_date": retention_check_date},
        )
        active_count = active_result.scalar() or 0

        retention = active_count / cohort_count
        log.info(
            "cohort_alert: D%d retention cohort_date=%s active=%d / cohort=%d = %.4f",
            days, cohort_date, active_count, cohort_count, retention,
        )
        return retention

    except Exception as exc:  # noqa: BLE001
        log.warning(
            "cohort_alert: D%d retention 측정 실패 cohort_date=%s — %s",
            days, cohort_date, exc,
        )
        return None


# ─── Slack 알림 발송 ──────────────────────────────────────────────────────────


async def _send_slack_alert(
    cohort_date: date,
    metric_name: str,
    value: float,
    threshold: float,
) -> str | None:
    """Slack Incoming Webhook으로 알림 발송.

    Returns:
        성공 시 Slack ts 문자열 (또는 Mock 모드 시 None).

    Raises:
        httpx.HTTPStatusError: Slack API 오류 시 (status != 200).
    """
    webhook_url = _get_slack_webhook_url()

    # metric_name → 사람이 읽기 좋은 레이블 변환
    label_map = {
        "d7_retention": "D7 Retention",
        "d30_retention": "D30 Retention",
    }
    label = label_map.get(metric_name, metric_name)

    value_pct = value * 100
    threshold_pct = threshold * 100
    diff_pct = value_pct - threshold_pct

    # SLACK_WEBHOOK_URL 미설정 시 Mock 모드
    if not webhook_url:
        log.warning(
            "[CohortAlert] Mock mode — SLACK_WEBHOOK_URL 미설정. "
            "metric=%s cohort_date=%s value=%.4f threshold=%.4f",
            metric_name, cohort_date, value, threshold,
        )
        return None

    payload: dict[str, Any] = {
        "text": ":warning: Cohort Retention 임계치 미달",
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"*:warning: Cohort Retention Alert*\n\n"
                        f"*Cohort 날짜*: {cohort_date}\n"
                        f"*지표*: {label}\n"
                        f"*현재값*: {value_pct:.1f}%\n"
                        f"*임계치*: {threshold_pct:.1f}%\n"
                        f"*차이*: {diff_pct:+.1f}%p\n\n"
                        f"<https://domo.app/admin/analytics|대시보드 바로가기>"
                    ),
                },
            }
        ],
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            webhook_url,
            content=json.dumps(payload),
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()

    log.info(
        "[CohortAlert] Slack 발송 성공 metric=%s cohort_date=%s value=%.4f",
        metric_name, cohort_date, value,
    )
    # Slack Incoming Webhook은 응답 body가 "ok" (ts 없음)
    # 메시지 식별을 위해 타임스탬프 문자열 생성
    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return ts


# ─── 핵심 check-and-alert 함수 ────────────────────────────────────────────────


async def check_and_alert_once(db: AsyncSession) -> dict:
    """일 1회 실행. 어제 cohort 지표를 측정하고 임계치 미달 시 Slack 알림 발송.

    UNIQUE INDEX on (cohort_date, metric_name)로 같은 날 중복 INSERT 차단.
    INSERT ON CONFLICT DO NOTHING → 중복 재실행 시 skipped 처리.

    Returns:
        {"checked": int, "alerted": int, "skipped": int, "errors": int}
    """
    yesterday = date.today() - timedelta(days=1)

    thresholds = {
        "d7_retention": (7, _get_threshold_7d()),
        "d30_retention": (30, _get_threshold_30d()),
    }

    result_summary = {"checked": 0, "alerted": 0, "skipped": 0, "errors": 0}

    for metric_name, (days, threshold) in thresholds.items():
        result_summary["checked"] += 1

        # 이미 오늘 같은 cohort_date + metric_name 처리됐으면 skip
        existing = await db.execute(
            select(CohortAlert).where(
                CohortAlert.cohort_date == yesterday,
                CohortAlert.metric_name == metric_name,
            )
        )
        if existing.scalar_one_or_none() is not None:
            log.debug(
                "cohort_alert: skip — 이미 처리됨 cohort_date=%s metric=%s",
                yesterday, metric_name,
            )
            result_summary["skipped"] += 1
            continue

        # Retention 측정
        value = await _measure_cohort_retention(db, yesterday, days)
        if value is None:
            log.debug(
                "cohort_alert: skip — 측정 불가 cohort_date=%s metric=%s days=%d",
                yesterday, metric_name, days,
            )
            result_summary["skipped"] += 1
            continue

        # 임계치 초과 시 알림 불필요
        if value >= threshold:
            log.info(
                "cohort_alert: OK — %s cohort_date=%s value=%.4f >= threshold=%.4f",
                metric_name, yesterday, value, threshold,
            )
            result_summary["skipped"] += 1
            continue

        # 임계치 미달 — Slack 알림 발송
        now = datetime.now(timezone.utc)
        slack_ts = None
        status = "pending"
        error_message = None

        try:
            slack_ts = await _send_slack_alert(yesterday, metric_name, value, threshold)
            # Mock 모드(slack_ts=None) 포함해 성공 처리
            status = "sent"
        except Exception as exc:  # noqa: BLE001
            log.error(
                "cohort_alert: Slack 발송 실패 metric=%s — %s",
                metric_name, exc,
            )
            status = "error"
            error_message = str(exc)
            result_summary["errors"] += 1

        # cohort_alerts INSERT (ON CONFLICT DO NOTHING — 동시 실행 안전)
        stmt = pg_insert(CohortAlert).values(
            cohort_date=yesterday,
            metric_name=metric_name,
            value=value,
            threshold=threshold,
            status=status,
            slack_message_ts=slack_ts,
            error_message=error_message,
            created_at=now,
            sent_at=now if status == "sent" else None,
        )
        stmt = stmt.on_conflict_do_nothing(
            index_elements=["cohort_date", "metric_name"]
        )
        await db.execute(stmt)
        await db.commit()

        if status == "sent":
            log.info(
                "cohort_alert: 알림 기록 완료 metric=%s cohort_date=%s value=%.4f threshold=%.4f status=%s",
                metric_name, yesterday, value, threshold, status,
            )
            result_summary["alerted"] += 1

    return result_summary


# ─── cron loop ───────────────────────────────────────────────────────────────


async def cohort_alert_cron_loop(interval_seconds: int = 86400) -> None:
    """14번째 cron worker — 매일 1회(86400s 간격) cohort alert 체크.

    R-5 격리: 별도 AsyncSessionLocal 사용.
    COHORT_ALERT_WORKER_ENABLED=false 시 즉시 종료.
    """
    log.info("cohort_alert_cron_loop started (interval=%ss)", interval_seconds)
    while True:
        await _push_cron_status("cohort_alert", "running")
        try:
            async with AsyncSessionLocal() as db:
                summary = await check_and_alert_once(db)
            log.info("cohort_alert sweep done: %s", summary)
            await _push_cron_status("cohort_alert", "success")
        except Exception as exc:  # noqa: BLE001
            log.exception("cohort_alert cron sweep failed: %s", exc)
            await _push_cron_status("cohort_alert", "failed", error=str(exc)[:500])
        await asyncio.sleep(interval_seconds)
