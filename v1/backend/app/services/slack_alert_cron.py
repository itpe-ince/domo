"""Slack Alert Cron Worker — Phase 13 C-1.

26번째 cron worker.
1분마다 check_overdue_workers() 호출 → 5분+ 미실행 시 Slack webhook POST.

env:
  SLACK_WEBHOOK_URL — 미설정 시 graceful skip (log warning only)

자기 자신(slack_alert)도 WORKER_REGISTRY에 포함되어 있어
정상 실행 시 자신의 상태도 갱신됨 (자기참조 OK).
"""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone

import httpx

from app.services.cron_monitor import check_overdue_workers, record_cron_run

log = logging.getLogger(__name__)

_WORKER_NAME = "slack_alert"
_SLACK_TIMEOUT = 10.0  # seconds


def _get_webhook_url() -> str | None:
    return os.getenv("SLACK_WEBHOOK_URL") or None


def _build_slack_payload(overdue: list[str], now: datetime) -> dict:
    """Slack Block Kit 포맷 페이로드 생성."""
    worker_lines = "\n".join(f"• *{w}*" for w in overdue)
    return {
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": ":warning: Cron Worker Overdue Alert",
                    "emoji": True,
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"다음 cron worker가 *5분 이상 미실행* 상태입니다:\n\n"
                        f"{worker_lines}"
                    ),
                },
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": (
                            f"Domo API | "
                            f"{now.strftime('%Y-%m-%dT%H:%M:%SZ')} | "
                            f"총 {len(overdue)}개 overdue"
                        ),
                    }
                ],
            },
        ]
    }


async def send_slack_alert(overdue: list[str]) -> None:
    """Slack webhook으로 overdue 알림 전송.

    SLACK_WEBHOOK_URL 미설정 시 log warning만 남기고 리턴.
    HTTP 오류 시 log error만 남기고 예외를 삼킨다 (모니터 cron 중단 방지).
    """
    webhook_url = _get_webhook_url()
    if not webhook_url:
        log.warning(
            "slack_alert: SLACK_WEBHOOK_URL not set — overdue workers: %s",
            overdue,
        )
        return

    now = datetime.now(timezone.utc)
    payload = _build_slack_payload(overdue, now)

    try:
        async with httpx.AsyncClient(timeout=_SLACK_TIMEOUT) as client:
            resp = await client.post(webhook_url, json=payload)
            resp.raise_for_status()
        log.info("slack_alert: sent alert for %d overdue workers: %s", len(overdue), overdue)
    except httpx.HTTPStatusError as exc:
        log.error(
            "slack_alert: Slack webhook HTTP error %s — %s",
            exc.response.status_code,
            exc.response.text[:200],
        )
    except Exception as exc:  # noqa: BLE001
        log.error("slack_alert: failed to send Slack alert: %s", exc)


async def _run_once() -> None:
    """overdue 체크 → alert 발송 1회 실행."""
    overdue = await check_overdue_workers()
    # slack_alert 자신은 이 시점에 아직 success 기록 전이므로
    # 자기 자신이 overdue 목록에 포함될 수 있음 — 정상 동작
    if overdue:
        log.info("slack_alert: %d overdue workers detected: %s", len(overdue), overdue)
        await send_slack_alert(overdue)
    else:
        log.debug("slack_alert: all workers healthy")


async def slack_alert_cron_loop(interval_seconds: int = 60) -> None:
    """Background task — 1분마다 overdue 체크 + Slack alert.

    26번째 cron worker. main.py lifespan에서 등록.
    자기 자신의 상태도 WORKER_REGISTRY에 포함됨 (자기참조 OK).
    """
    log.info("slack_alert_cron_loop started (interval=%ss)", interval_seconds)
    while True:
        try:
            await record_cron_run(_WORKER_NAME, "running")
            await _run_once()
            await record_cron_run(_WORKER_NAME, "success")
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001
            log.exception("slack_alert cron failed: %s", exc)
            await record_cron_run(_WORKER_NAME, "failed", error=str(exc)[:500])
        await asyncio.sleep(interval_seconds)
