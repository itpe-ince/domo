"""Integration tests — Admin Experiments API (Phase 10 K-8).

테스트 항목:
  1. GET /admin/experiments — non-admin → 403 Forbidden
  2. GET /admin/experiments — admin → 200 OK + data 리스트 반환
  3. POST /admin/experiments — 실험 생성 → 201 Created
  4. POST /admin/experiments — 동일 name 중복 → 409 Conflict
  5. GET /admin/experiments/{name}/results — 200 OK + 기대 형식
  6. GET /admin/experiments/{name}/results — 존재하지 않는 실험 → 404

전략: endpoint 함수 직접 호출 + AsyncMock DB + MagicMock User.
실제 DB 불필요. test_admin_featured_artists.py 패턴 동일.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.api.admin_experiments import (
    create_or_update_experiment,
    get_experiment_results,
    list_experiments,
)
from app.api.admin_experiments import ExperimentCreateRequest
from app.core.errors import ApiError


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_admin() -> MagicMock:
    u = MagicMock()
    u.id = uuid.uuid4()
    u.role = "admin"
    u.totp_enabled_at = datetime.now(timezone.utc)
    return u


def _make_user() -> MagicMock:
    u = MagicMock()
    u.id = uuid.uuid4()
    u.role = "user"
    return u


def _make_exp_row(name: str = "feed_v2_rollout", status: str = "running") -> MagicMock:
    """실험 DB row mock."""
    row = MagicMock()
    exp_id = uuid.uuid4()
    row.id = exp_id
    row.name = name
    row.status = status
    row.variant_distribution = {"v1": 0.5, "v2": 0.5}
    row.started_at = datetime(2026, 5, 1, tzinfo=timezone.utc)
    row.ended_at = None
    row.target_metric = "feed_ctr"
    row.hypothesis = "ML 피드가 CTR을 15% 향상"
    row.created_at = datetime(2026, 5, 1, tzinfo=timezone.utc)
    row.updated_at = datetime(2026, 5, 5, tzinfo=timezone.utc)
    # _mapping: dict-like access 지원
    row._mapping = {
        "id": exp_id,
        "name": name,
        "status": status,
        "variant_distribution": {"v1": 0.5, "v2": 0.5},
        "started_at": datetime(2026, 5, 1, tzinfo=timezone.utc),
        "ended_at": None,
        "target_metric": "feed_ctr",
        "hypothesis": "ML 피드가 CTR을 15% 향상",
        "created_at": datetime(2026, 5, 1, tzinfo=timezone.utc),
        "updated_at": datetime(2026, 5, 5, tzinfo=timezone.utc),
    }
    return row


# ── Test 1: GET 권한 검증 — non-admin 403 ────────────────────────────────────


@pytest.mark.asyncio
async def test_get_experiments_non_admin_forbidden():
    """non-admin → require_admin가 403 ApiError 발생."""
    from app.core.admin_deps import require_admin

    non_admin = _make_user()
    db = AsyncMock()

    with pytest.raises(ApiError) as exc_info:
        await require_admin(user=non_admin)

    assert exc_info.value.status_code == 403


# ── Test 2: GET /admin/experiments — admin 200 OK ────────────────────────────


@pytest.mark.asyncio
async def test_get_experiments_admin_success():
    """admin → 200 OK + data 리스트 반환."""
    admin = _make_admin()
    db = AsyncMock()

    exp_row = _make_exp_row()
    # assignment counts 조회: v1=100, v2=98
    assign_row_v1 = MagicMock()
    assign_row_v1.variant = "v1"
    assign_row_v1.cnt = 100
    assign_row_v2 = MagicMock()
    assign_row_v2.variant = "v2"
    assign_row_v2.cnt = 98

    db.execute = AsyncMock(side_effect=[
        # list_experiments 쿼리
        MagicMock(fetchall=MagicMock(return_value=[exp_row])),
        # _get_assignment_counts 쿼리
        MagicMock(fetchall=MagicMock(return_value=[assign_row_v1, assign_row_v2])),
    ])

    result = await list_experiments(admin=admin, db=db)

    assert "data" in result
    assert isinstance(result["data"], list)
    assert len(result["data"]) == 1
    assert result["data"][0]["assignment_counts"] == {"v1": 100, "v2": 98}


# ── Test 3: POST 실험 생성 → 201 Created ─────────────────────────────────────


@pytest.mark.asyncio
async def test_post_experiment_create():
    """실험 생성 → 201 Created + data 반환."""
    admin = _make_admin()
    db = AsyncMock()

    new_exp_row = _make_exp_row(name="feed_v2_test", status="draft")

    db.execute = AsyncMock(side_effect=[
        # 기존 실험 존재 확인: 없음
        MagicMock(fetchone=MagicMock(return_value=None)),
        # INSERT RETURNING
        MagicMock(fetchone=MagicMock(return_value=new_exp_row)),
    ])
    db.commit = AsyncMock()

    body = ExperimentCreateRequest(
        name="feed_v2_test",
        status="draft",
        variant_distribution={"v1": 0.5, "v2": 0.5},
        target_metric="feed_ctr",
        hypothesis="테스트 가설",
    )

    result = await create_or_update_experiment(body=body, admin=admin, db=db)

    assert result["data"]["name"] == "feed_v2_test"


# ── Test 4: POST 동일 name 중복 → 409 ────────────────────────────────────────


@pytest.mark.asyncio
async def test_post_experiment_duplicate_409():
    """동일 name 중복 생성 → 409 Conflict."""
    admin = _make_admin()
    db = AsyncMock()

    existing_row = MagicMock()
    existing_row.id = uuid.uuid4()

    db.execute = AsyncMock(
        return_value=MagicMock(fetchone=MagicMock(return_value=existing_row))
    )

    body = ExperimentCreateRequest(
        name="feed_v2_rollout",
        status="draft",
        variant_distribution={"v1": 0.5, "v2": 0.5},
    )

    with pytest.raises(ApiError) as exc_info:
        await create_or_update_experiment(body=body, admin=admin, db=db)

    assert exc_info.value.status_code == 409


# ── Test 5: GET results → 200 OK + 기대 형식 ─────────────────────────────────


@pytest.mark.asyncio
async def test_get_experiment_results_success():
    """results endpoint → 200 OK + 기대 형식."""
    admin = _make_admin()
    db = AsyncMock()

    exp_row = _make_exp_row()
    assign_row_v1 = MagicMock()
    assign_row_v1.variant = "v1"
    assign_row_v1.cnt = 1234
    assign_row_v2 = MagicMock()
    assign_row_v2.variant = "v2"
    assign_row_v2.cnt = 1198

    db.execute = AsyncMock(side_effect=[
        # get experiment
        MagicMock(fetchone=MagicMock(return_value=exp_row)),
        # assignment counts
        MagicMock(fetchall=MagicMock(return_value=[assign_row_v1, assign_row_v2])),
        # newsletter open rate (스킵 대비)
        MagicMock(fetchall=MagicMock(return_value=[])),
    ])

    result = await get_experiment_results(
        name="feed_v2_rollout", admin=admin, db=db
    )

    data = result["data"]
    assert "experiment_name" in data
    assert "assignment_counts" in data
    assert "posthog_insights_url" in data
    assert data["experiment_name"] == "feed_v2_rollout"
    assert data["assignment_counts"] == {"v1": 1234, "v2": 1198}


# ── Test 6: GET results — 존재하지 않는 실험 → 404 ───────────────────────────


@pytest.mark.asyncio
async def test_get_experiment_results_not_found():
    """존재하지 않는 실험 → 404 Not Found."""
    admin = _make_admin()
    db = AsyncMock()

    db.execute = AsyncMock(
        return_value=MagicMock(fetchone=MagicMock(return_value=None))
    )

    with pytest.raises(ApiError) as exc_info:
        await get_experiment_results(
            name="nonexistent_experiment", admin=admin, db=db
        )

    assert exc_info.value.status_code == 404
