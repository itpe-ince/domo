"""Admin ML A/B 테스트 관리 API — Phase 10 K-8.

Endpoints:
  GET  /admin/experiments                 — 활성 실험 목록 + variant 분배 현황
  POST /admin/experiments                 — 실험 생성 또는 상태 변경
  GET  /admin/experiments/{name}/results  — 실험 결과 요약

권한: admin 전용 (require_admin).
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.admin_deps import require_admin
from app.core.errors import ApiError
from app.db.session import get_db
from app.models.user import User
from app.services.audit_log import record_audit

log = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin-experiments"])

_POSTHOG_HOST = os.getenv("POSTHOG_HOST", "https://app.posthog.com")


# ── Pydantic schemas ──────────────────────────────────────────────────────────


class ExperimentCreateRequest(BaseModel):
    """실험 생성/수정 요청 body."""

    name: str = Field(..., max_length=100)
    status: str = Field("draft", pattern="^(draft|running|paused|completed)$")
    variant_distribution: dict[str, float] = Field(
        default_factory=lambda: {"v1": 0.5, "v2": 0.5}
    )
    target_metric: str | None = Field(None, max_length=50)
    hypothesis: str | None = None


# ── Helpers ───────────────────────────────────────────────────────────────────


async def _get_assignment_counts(db: AsyncSession, experiment_id: str) -> dict[str, int]:
    """experiment_id 별 variant 집계."""
    result = await db.execute(
        text("""
            SELECT variant, COUNT(*) AS cnt
            FROM ml_experiment_assignments
            WHERE experiment_id = :exp_id
            GROUP BY variant
        """),
        {"exp_id": experiment_id},
    )
    return {row.variant: int(row.cnt) for row in result.fetchall()}


def _row_to_dict(row: Any) -> dict[str, Any]:
    """SQLAlchemy Row → dict 변환."""
    return dict(row._mapping)


# ── GET /admin/experiments ────────────────────────────────────────────────────


@router.get("/experiments")
async def list_experiments(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """활성 실험 목록 + variant 분배 현황.

    admin 전용. non-admin → 403 Forbidden.
    """
    result = await db.execute(
        text("""
            SELECT id, name, status, variant_distribution,
                   started_at, ended_at, target_metric, hypothesis,
                   created_at, updated_at
            FROM ml_experiments
            ORDER BY created_at DESC
        """)
    )
    rows = result.fetchall()

    data = []
    for row in rows:
        item = _row_to_dict(row)
        # assignment 집계 추가
        item["assignment_counts"] = await _get_assignment_counts(
            db, str(item["id"])
        )
        # JSON-serializable 변환
        item["id"] = str(item["id"])
        data.append(item)

    return {"data": data}


# ── POST /admin/experiments ───────────────────────────────────────────────────


@router.post("/experiments", status_code=201)
async def create_or_update_experiment(
    body: ExperimentCreateRequest,
    request: Request,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """실험 생성 또는 상태 변경.

    name UNIQUE 위반 시 409 Conflict.
    status=running 전환 시 started_at 자동 설정.
    admin 전용.
    """
    # 기존 실험 존재 확인
    existing = await db.execute(
        text("SELECT id FROM ml_experiments WHERE name = :name LIMIT 1"),
        {"name": body.name},
    )
    existing_row = existing.fetchone()

    if existing_row is not None:
        raise ApiError(
            "CONFLICT",
            f"Experiment '{body.name}' already exists. Use PATCH to update.",
            http_status=409,
        )

    # started_at: status=running 전환 시 현재 시각 자동 설정
    started_at = None
    if body.status == "running":
        started_at = datetime.now(timezone.utc)

    import json  # noqa: PLC0415
    result = await db.execute(
        text("""
            INSERT INTO ml_experiments
              (name, status, variant_distribution, target_metric, hypothesis, started_at)
            VALUES
              (:name, :status, :dist, :metric, :hypothesis, :started_at)
            RETURNING id, name, status, variant_distribution,
                      started_at, ended_at, target_metric, hypothesis,
                      created_at, updated_at
        """),
        {
            "name": body.name,
            "status": body.status,
            "dist": json.dumps(body.variant_distribution),
            "metric": body.target_metric,
            "hypothesis": body.hypothesis,
            "started_at": started_at,
        },
    )
    await db.commit()
    row = result.fetchone()
    item = _row_to_dict(row)
    item["id"] = str(item["id"])
    item["assignment_counts"] = {}

    await record_audit(
        db,
        actor=admin,
        action="admin.experiment_create",
        target_type="experiment",
        metadata={"name": body.name, "status": body.status},
        request=request,
    )

    return {"data": item}


# ── GET /admin/experiments/{name}/results ─────────────────────────────────────


@router.get("/experiments/{name}/results")
async def get_experiment_results(
    name: str,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """실험 결과 요약.

    - assignment_counts: variant별 할당 수
    - newsletter_open_rate: L-B newsletter_events 보조 지표 (테이블 없으면 None)
    - posthog_insights_url: PostHog Insights 대시보드 URL
    admin 전용.
    """
    exp_result = await db.execute(
        text("""
            SELECT id, name, status, started_at, ended_at,
                   target_metric, hypothesis, variant_distribution
            FROM ml_experiments
            WHERE name = :name
            LIMIT 1
        """),
        {"name": name},
    )
    exp_row = exp_result.fetchone()
    if exp_row is None:
        raise ApiError("NOT_FOUND", f"Experiment '{name}' not found", http_status=404)

    exp = _row_to_dict(exp_row)
    experiment_id = str(exp["id"])

    # assignment 집계
    assignment_counts = await _get_assignment_counts(db, experiment_id)

    # 운영 기간 계산
    days_running: int | None = None
    if exp.get("started_at"):
        started = exp["started_at"]
        if started.tzinfo is None:
            started = started.replace(tzinfo=timezone.utc)
        ended = exp.get("ended_at") or datetime.now(timezone.utc)
        if ended.tzinfo is None:
            ended = ended.replace(tzinfo=timezone.utc)
        days_running = max(0, (ended - started).days)

    # L-B newsletter open rate (보조 지표 — newsletter_events 테이블 활용)
    newsletter_open_rate = None
    try:
        nr_result = await db.execute(
            text("""
                SELECT
                    mea.variant,
                    COUNT(DISTINCT ne.id) FILTER (WHERE ne.event_type = 'open')  AS opens,
                    COUNT(DISTINCT ne.id)                                          AS total
                FROM newsletter_events ne
                JOIN ml_experiment_assignments mea
                  ON mea.user_id = ne.recipient_user_id
                JOIN ml_experiments me
                  ON me.id = mea.experiment_id AND me.name = :exp_name
                WHERE ne.sent_at >= COALESCE(me.started_at, now() - interval '90 days')
                GROUP BY mea.variant
            """),
            {"exp_name": name},
        )
        nr_rows = nr_result.fetchall()
        if nr_rows:
            newsletter_open_rate = {
                row.variant: round(row.opens / row.total, 4) if row.total else 0.0
                for row in nr_rows
            }
    except Exception as exc:  # noqa: BLE001
        log.debug("newsletter_open_rate 집계 실패 (스킵): %s", exc)

    # PostHog Insights URL (placeholder — 실제 프로젝트 ID 필요)
    posthog_insights_url = (
        f"{_POSTHOG_HOST}/experiments"
        f"?experiment_name={name}"
    )

    return {
        "data": {
            "experiment_name": name,
            "status": exp["status"],
            "days_running": days_running,
            "assignment_counts": assignment_counts,
            "newsletter_open_rate": newsletter_open_rate,
            "posthog_insights_url": posthog_insights_url,
            "note": "통계적 유의성은 PostHog Insights 대시보드에서 확인",
        }
    }
