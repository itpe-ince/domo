"""Admin System API — Phase 13 C-1.

cron worker 상태 모니터링 endpoints.

GET /admin/system/crons              — 전체 worker 상태 목록
GET /admin/system/crons/{worker_name} — 단일 worker 상세

권한: require_admin (2FA 불필요 — 읽기 전용 모니터링)
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from app.core.admin_deps import require_admin
from app.models.user import User
from app.services.cron_monitor import (
    WORKER_REGISTRY,
    get_all_cron_status,
)

log = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/system", tags=["admin-system"])


def _build_summary(workers: list[dict[str, Any]]) -> dict[str, int]:
    """worker 목록에서 요약 통계를 생성한다."""
    total = len(workers)
    success = sum(1 for w in workers if w["status"] == "success")
    failed = sum(1 for w in workers if w["status"] == "failed")
    running = sum(1 for w in workers if w["status"] == "running")
    overdue = sum(1 for w in workers if w["is_overdue"])
    return {
        "total": total,
        "success": success,
        "failed": failed,
        "running": running,
        "overdue": overdue,
    }


@router.get("/crons")
async def list_cron_status(
    admin: User = Depends(require_admin),
) -> dict[str, Any]:
    """전체 cron worker 상태 목록을 반환한다.

    Response:
        workers: 각 worker의 name, status, last_run_at, error_message,
                 run_count, is_overdue, interval_label
        summary: total, success, failed, running, overdue 집계
    """
    workers = await get_all_cron_status()
    return {
        "workers": workers,
        "summary": _build_summary(workers),
    }


@router.get("/crons/{worker_name}")
async def get_cron_status(
    worker_name: str,
    admin: User = Depends(require_admin),
) -> dict[str, Any]:
    """단일 cron worker 상세 상태를 반환한다.

    Args:
        worker_name: WORKER_REGISTRY에 등록된 worker 이름

    Raises:
        404: worker_name이 WORKER_REGISTRY에 없는 경우
    """
    if worker_name not in WORKER_REGISTRY:
        raise HTTPException(
            status_code=404,
            detail=f"Worker '{worker_name}' not found. "
            f"Available: {', '.join(WORKER_REGISTRY)}",
        )

    workers = await get_all_cron_status()
    match = next((w for w in workers if w["name"] == worker_name), None)
    if match is None:
        # registry에 있지만 get_all_cron_status에서 누락된 경우 (방어 코드)
        raise HTTPException(status_code=404, detail=f"Worker '{worker_name}' status not available")

    return match
