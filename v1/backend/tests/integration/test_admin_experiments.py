"""Integration tests — Admin Experiments API (Phase 10 K-8 + Phase 12 A-2).

테스트 항목:
  [K-8 기존 — 6개]
  1. GET /admin/experiments — non-admin → 403 Forbidden
  2. GET /admin/experiments — admin → 200 OK + data 리스트 반환
  3. POST /admin/experiments — 실험 생성 → 201 Created
  4. POST /admin/experiments — 동일 name 중복 → 409 Conflict
  5. GET /admin/experiments/{name}/results — 200 OK + 기대 형식
  6. GET /admin/experiments/{name}/results — 존재하지 않는 실험 → 404

  [A-2 신규 — 10개]
  7.  PATCH 정상 — draft → running (started_at 자동 갱신)
  8.  PATCH 정상 — running → paused
  9.  PATCH 정상 — paused → running (재개)
  10. PATCH 정상 — running → completed (ended_at 자동 갱신)
  11. PATCH 차단 — completed → running (400 IMMUTABLE)
  12. PATCH 차단 — paused → draft (400 INVALID_TRANSITION)
  13. PATCH 검증 — variant_distribution 합 != 1.0 (422)
  14. PATCH 검증 — 기존 assignment 있는 variant 키 삭제 (400 ASSIGNMENTS_EXIST)
  15. PATCH 권한 — non-admin (403)
  16. audit_log 기록 검증 (action="admin.experiment_patch")

전략: endpoint 함수 직접 호출 + AsyncMock DB + MagicMock User.
실제 DB 불필요. test_admin_featured_artists.py 패턴 동일.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.api.admin_experiments import (
    ExperimentCreateRequest,
    ExperimentPatchRequest,
    create_or_update_experiment,
    get_experiment_results,
    list_experiments,
    patch_experiment,
)
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


def _make_exp_row(
    name: str = "feed_v2_rollout",
    status: str = "running",
    variant_distribution: dict | None = None,
    started_at: datetime | None = None,
    ended_at: datetime | None = None,
) -> MagicMock:
    """실험 DB row mock."""
    row = MagicMock()
    exp_id = uuid.uuid4()
    dist = variant_distribution or {"v1": 0.5, "v2": 0.5}
    s_at = started_at or datetime(2026, 5, 1, tzinfo=timezone.utc)

    row.id = exp_id
    row.name = name
    row.status = status
    row.variant_distribution = dist
    row.started_at = s_at
    row.ended_at = ended_at
    row.target_metric = "feed_ctr"
    row.hypothesis = "ML 피드가 CTR을 15% 향상"
    row.created_at = datetime(2026, 5, 1, tzinfo=timezone.utc)
    row.updated_at = datetime(2026, 5, 5, tzinfo=timezone.utc)
    # _mapping: dict-like access 지원
    row._mapping = {
        "id": exp_id,
        "name": name,
        "status": status,
        "variant_distribution": dist,
        "started_at": s_at,
        "ended_at": ended_at,
        "target_metric": "feed_ctr",
        "hypothesis": "ML 피드가 CTR을 15% 향상",
        "created_at": datetime(2026, 5, 1, tzinfo=timezone.utc),
        "updated_at": datetime(2026, 5, 5, tzinfo=timezone.utc),
    }
    return row


def _make_admin_2fa() -> MagicMock:
    """2FA 완료된 admin mock (require_admin_with_2fa 통과용)."""
    return _make_admin()


def _make_request() -> MagicMock:
    """FastAPI Request mock."""
    req = MagicMock()
    req.headers = {}
    req.client = MagicMock(host="127.0.0.1")
    return req


def _make_patch_db(
    exp_row: MagicMock,
    updated_row: MagicMock,
    assign_counts: list[MagicMock] | None = None,
) -> AsyncMock:
    """PATCH endpoint용 DB mock.

    순서: 1) SELECT (실험 조회) → 2) _get_assignment_counts (변경 전) →
          3) UPDATE RETURNING → 4) _get_assignment_counts (응답용)
    """
    ac = assign_counts or []
    db = AsyncMock()
    db.execute = AsyncMock(side_effect=[
        MagicMock(fetchone=MagicMock(return_value=exp_row)),    # 1. SELECT
        MagicMock(fetchall=MagicMock(return_value=ac)),          # 2. 삭제 키 검증용 (또는 스킵)
        MagicMock(fetchone=MagicMock(return_value=updated_row)), # 3. UPDATE RETURNING
        MagicMock(fetchall=MagicMock(return_value=ac)),          # 4. 응답용 assignment_counts
    ])
    db.commit = AsyncMock()
    return db


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

    result = await create_or_update_experiment(body=body, admin=admin, request=MagicMock(headers={}, client=MagicMock(host="127.0.0.1")), db=db)

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
        await create_or_update_experiment(body=body, admin=admin, request=MagicMock(headers={}, client=MagicMock(host="127.0.0.1")), db=db)

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


# ── Phase 12 A-2 Tests: PATCH /admin/experiments/{name} ──────────────────────


# ── Test 7: PATCH 정상 — draft → running (started_at 자동 갱신) ──────────────


@pytest.mark.asyncio
async def test_patch_draft_to_running():
    """PATCH 정상 — draft → running: started_at 자동 갱신."""
    admin = _make_admin_2fa()
    exp_row = _make_exp_row(status="draft", started_at=None)
    # 갱신 후 row (status=running, started_at=now)
    updated_row = _make_exp_row(
        status="running",
        started_at=datetime(2026, 5, 8, tzinfo=timezone.utc),
    )

    db = AsyncMock()
    db.execute = AsyncMock(side_effect=[
        MagicMock(fetchone=MagicMock(return_value=exp_row)),      # SELECT
        MagicMock(fetchone=MagicMock(return_value=updated_row)),  # UPDATE RETURNING
        MagicMock(fetchall=MagicMock(return_value=[])),           # assignment_counts
    ])
    db.commit = AsyncMock()

    body = ExperimentPatchRequest(status="running")

    with patch("app.api.admin_experiments.record_audit", new_callable=AsyncMock), \
         patch("app.api.admin_experiments._sync_posthog_flag", new_callable=AsyncMock):
        result = await patch_experiment(
            name="feed_v2_rollout",
            body=body,
            request=_make_request(),
            admin=admin,
            db=db,
        )

    data = result["data"]
    assert data["status"] == "running"
    assert data["started_at"] is not None


# ── Test 8: PATCH 정상 — running → paused ────────────────────────────────────


@pytest.mark.asyncio
async def test_patch_running_to_paused():
    """PATCH 정상 — running → paused."""
    admin = _make_admin_2fa()
    exp_row = _make_exp_row(status="running")
    updated_row = _make_exp_row(status="paused")

    db = AsyncMock()
    db.execute = AsyncMock(side_effect=[
        MagicMock(fetchone=MagicMock(return_value=exp_row)),
        MagicMock(fetchone=MagicMock(return_value=updated_row)),
        MagicMock(fetchall=MagicMock(return_value=[])),
    ])
    db.commit = AsyncMock()

    body = ExperimentPatchRequest(status="paused")

    with patch("app.api.admin_experiments.record_audit", new_callable=AsyncMock), \
         patch("app.api.admin_experiments._sync_posthog_flag", new_callable=AsyncMock):
        result = await patch_experiment(
            name="feed_v2_rollout",
            body=body,
            request=_make_request(),
            admin=admin,
            db=db,
        )

    assert result["data"]["status"] == "paused"


# ── Test 9: PATCH 정상 — paused → running (재개) ─────────────────────────────


@pytest.mark.asyncio
async def test_patch_paused_to_running_resumes():
    """PATCH 정상 — paused → running: 재개."""
    admin = _make_admin_2fa()
    exp_row = _make_exp_row(status="paused")
    updated_row = _make_exp_row(status="running")

    db = AsyncMock()
    db.execute = AsyncMock(side_effect=[
        MagicMock(fetchone=MagicMock(return_value=exp_row)),
        MagicMock(fetchone=MagicMock(return_value=updated_row)),
        MagicMock(fetchall=MagicMock(return_value=[])),
    ])
    db.commit = AsyncMock()

    body = ExperimentPatchRequest(status="running")

    with patch("app.api.admin_experiments.record_audit", new_callable=AsyncMock), \
         patch("app.api.admin_experiments._sync_posthog_flag", new_callable=AsyncMock):
        result = await patch_experiment(
            name="feed_v2_rollout",
            body=body,
            request=_make_request(),
            admin=admin,
            db=db,
        )

    assert result["data"]["status"] == "running"


# ── Test 10: PATCH 정상 — running → completed (ended_at 자동 갱신) ───────────


@pytest.mark.asyncio
async def test_patch_running_to_completed_sets_ended_at():
    """PATCH 정상 — running → completed: ended_at 자동 갱신."""
    admin = _make_admin_2fa()
    exp_row = _make_exp_row(status="running")
    updated_row = _make_exp_row(
        status="completed",
        ended_at=datetime(2026, 5, 8, tzinfo=timezone.utc),
    )

    db = AsyncMock()
    db.execute = AsyncMock(side_effect=[
        MagicMock(fetchone=MagicMock(return_value=exp_row)),
        MagicMock(fetchone=MagicMock(return_value=updated_row)),
        MagicMock(fetchall=MagicMock(return_value=[])),
    ])
    db.commit = AsyncMock()

    body = ExperimentPatchRequest(status="completed")

    with patch("app.api.admin_experiments.record_audit", new_callable=AsyncMock), \
         patch("app.api.admin_experiments._sync_posthog_flag", new_callable=AsyncMock):
        result = await patch_experiment(
            name="feed_v2_rollout",
            body=body,
            request=_make_request(),
            admin=admin,
            db=db,
        )

    data = result["data"]
    assert data["status"] == "completed"
    assert data["ended_at"] is not None


# ── Test 11: PATCH 차단 — completed → running (400 IMMUTABLE) ────────────────


@pytest.mark.asyncio
async def test_patch_completed_to_running_blocked():
    """PATCH 차단 — completed → running: 400 IMMUTABLE."""
    admin = _make_admin_2fa()
    exp_row = _make_exp_row(status="completed")

    db = AsyncMock()
    db.execute = AsyncMock(
        return_value=MagicMock(fetchone=MagicMock(return_value=exp_row))
    )

    body = ExperimentPatchRequest(status="running")

    with pytest.raises(ApiError) as exc_info:
        await patch_experiment(
            name="feed_v2_rollout",
            body=body,
            request=_make_request(),
            admin=admin,
            db=db,
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.code == "IMMUTABLE"


# ── Test 12: PATCH 차단 — paused → draft (400 INVALID_TRANSITION) ────────────


@pytest.mark.asyncio
async def test_patch_paused_to_draft_blocked():
    """PATCH 차단 — paused → draft: 400 INVALID_TRANSITION."""
    admin = _make_admin_2fa()
    exp_row = _make_exp_row(status="paused")

    db = AsyncMock()
    db.execute = AsyncMock(
        return_value=MagicMock(fetchone=MagicMock(return_value=exp_row))
    )

    body = ExperimentPatchRequest(status="draft")

    with pytest.raises(ApiError) as exc_info:
        await patch_experiment(
            name="feed_v2_rollout",
            body=body,
            request=_make_request(),
            admin=admin,
            db=db,
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.code == "INVALID_TRANSITION"


# ── Test 13: PATCH 검증 — variant_distribution 합 != 1.0 (422) ───────────────


@pytest.mark.asyncio
async def test_patch_invalid_distribution_sum():
    """PATCH 검증 — variant_distribution 합 != 1.0: 422."""
    admin = _make_admin_2fa()
    exp_row = _make_exp_row(status="running")

    db = AsyncMock()
    db.execute = AsyncMock(
        return_value=MagicMock(fetchone=MagicMock(return_value=exp_row))
    )

    body = ExperimentPatchRequest(
        variant_distribution={"v1": 0.6, "v2": 0.6}  # 합 = 1.2
    )

    with pytest.raises(ApiError) as exc_info:
        await patch_experiment(
            name="feed_v2_rollout",
            body=body,
            request=_make_request(),
            admin=admin,
            db=db,
        )

    assert exc_info.value.status_code == 422
    assert exc_info.value.code == "VALIDATION_ERROR"


# ── Test 14: PATCH 검증 — 기존 assignment 있는 variant 키 삭제 차단 ───────────


@pytest.mark.asyncio
async def test_patch_remove_variant_with_assignments_blocked():
    """PATCH 검증 — 기존 assignment 있는 variant 키 삭제: 400 ASSIGNMENTS_EXIST."""
    admin = _make_admin_2fa()
    # 기존 분배: v1, v2
    exp_row = _make_exp_row(
        status="running",
        variant_distribution={"v1": 0.5, "v2": 0.5},
    )

    # v1 에 3명 배정된 상태
    assign_v1 = MagicMock()
    assign_v1.variant = "v1"
    assign_v1.cnt = 3

    db = AsyncMock()
    db.execute = AsyncMock(side_effect=[
        # SELECT 실험
        MagicMock(fetchone=MagicMock(return_value=exp_row)),
        # _get_assignment_counts (v1 삭제 차단 검증용)
        MagicMock(fetchall=MagicMock(return_value=[assign_v1])),
    ])

    # v1 제거 — v2만 1.0으로 전달
    body = ExperimentPatchRequest(variant_distribution={"v2": 1.0})

    with pytest.raises(ApiError) as exc_info:
        await patch_experiment(
            name="feed_v2_rollout",
            body=body,
            request=_make_request(),
            admin=admin,
            db=db,
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.code == "ASSIGNMENTS_EXIST"


# ── Test 15: PATCH 권한 — non-admin (403) ────────────────────────────────────


@pytest.mark.asyncio
async def test_patch_non_admin_forbidden():
    """PATCH 권한 — non-admin: require_admin_with_2fa가 403 발생."""
    from app.core.admin_deps import require_admin_with_2fa

    non_admin = _make_user()
    db = AsyncMock()
    # WebauthnCredential count 조회 → 0
    db.execute = AsyncMock(
        return_value=MagicMock(scalar_one=MagicMock(return_value=0))
    )

    with pytest.raises(ApiError) as exc_info:
        await require_admin_with_2fa(user=non_admin, db=db)

    assert exc_info.value.status_code == 403


# ── Test 16: audit_log 기록 검증 ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_patch_audit_log_recorded():
    """audit_log — status 변경 시 action="admin.experiment_patch" 기록 확인."""
    admin = _make_admin_2fa()
    exp_row = _make_exp_row(status="running")
    updated_row = _make_exp_row(status="paused")

    db = AsyncMock()
    db.execute = AsyncMock(side_effect=[
        MagicMock(fetchone=MagicMock(return_value=exp_row)),
        MagicMock(fetchone=MagicMock(return_value=updated_row)),
        MagicMock(fetchall=MagicMock(return_value=[])),
    ])
    db.commit = AsyncMock()

    body = ExperimentPatchRequest(status="paused")

    captured_calls: list[dict] = []

    async def mock_record_audit(db, actor, action, target_type, metadata, request):
        captured_calls.append({
            "action": action,
            "metadata": metadata,
        })

    with patch("app.api.admin_experiments.record_audit", side_effect=mock_record_audit), \
         patch("app.api.admin_experiments._sync_posthog_flag", new_callable=AsyncMock):
        await patch_experiment(
            name="feed_v2_rollout",
            body=body,
            request=_make_request(),
            admin=admin,
            db=db,
        )

    assert len(captured_calls) == 1
    call = captured_calls[0]
    assert call["action"] == "admin.experiment_patch"
    assert call["metadata"]["name"] == "feed_v2_rollout"
    assert call["metadata"]["prev_status"] == "running"
    assert call["metadata"]["new_status"] == "paused"
