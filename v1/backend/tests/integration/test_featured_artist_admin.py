"""Integration tests — Admin Featured Artist 후보 검수 큐 API (Phase 10 K-4).

테스트 항목:
  1. GET /admin/featured-artist/candidates — non-admin → 403 Forbidden
  2. approve → publish 워크플로우 (pending→approved→published + featured_artists INSERT)
  3. reject 워크플로우 (pending→rejected + reason 저장, reasoning JSONB에 reject_reason)
  4. approve 동시성 — 같은 후보 두 번 approve 시도 → 두 번째 409 Conflict

전략: endpoint 함수 직접 호출 + AsyncMock DB + MagicMock User.
실제 DB 불필요. test_admin_experiments.py 패턴 동일.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.api.admin_featured_artist import (
    approve_candidate,
    list_candidates,
    publish_candidate,
    reject_candidate,
    PublishRequest,
    RejectRequest,
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


def _make_candidate_row(
    candidate_id: uuid.UUID | None = None,
    artist_id: uuid.UUID | None = None,
    status: str = "pending",
    reasoning: dict | None = None,
) -> MagicMock:
    """featured_artist_candidates DB row mock."""
    row = MagicMock()
    row.id = candidate_id or uuid.uuid4()
    row.artist_id = artist_id or uuid.uuid4()
    row.week_start = date(2026, 5, 4)
    row.composite_score = 0.76
    row.reasoning = reasoning or {
        "engagement": 0.85,
        "rank": 0.72,
        "diversity": 0.03,
        "new_artist_bonus": 0.20,
        "sponsor_count": 0,
        "follower_count": 87,
        "region": "KR",
        "genre": "watercolor",
    }
    row.status = status
    row.admin_id = None
    row.reviewed_at = None
    row.published_at = None
    row.created_at = datetime(2026, 5, 4, 9, 0, 0, tzinfo=timezone.utc)
    # display_name, avatar_url, follower_count for list query join
    row.artist_name = "이서연"
    row.artist_avatar_url = "https://cdn.example.com/avatar.jpg"
    row.follower_count = 87
    return row


def _make_fa_row(fa_id: uuid.UUID | None = None) -> MagicMock:
    """featured_artists INSERT RETURNING row mock."""
    row = MagicMock()
    row.id = fa_id or uuid.uuid4()
    return row


# ── Test 1: GET candidates — non-admin 403 ────────────────────────────────────

@pytest.mark.asyncio
async def test_get_candidates_non_admin_forbidden():
    """non-admin → require_admin_with_2fa가 403 ApiError 발생."""
    from app.core.admin_deps import require_admin

    non_admin = _make_user()

    with pytest.raises(ApiError) as exc_info:
        await require_admin(user=non_admin)

    assert exc_info.value.status_code == 403


# ── Test 2: approve → publish 워크플로우 ──────────────────────────────────────

@pytest.mark.asyncio
async def test_approve_then_publish_workflow():
    """pending → approved → published 워크플로우 + featured_artists INSERT 확인."""
    admin = _make_admin()
    candidate_id = uuid.uuid4()
    artist_id = uuid.uuid4()
    fa_id = uuid.uuid4()

    # ── Step A: approve
    db_approve = AsyncMock()
    pending_row = MagicMock()
    pending_row.id = candidate_id
    pending_row.status = "pending"

    db_approve.execute = AsyncMock(
        return_value=MagicMock(fetchone=MagicMock(return_value=pending_row))
    )
    db_approve.commit = AsyncMock()

    approve_result = await approve_candidate(
        candidate_id=str(candidate_id),
        admin=admin,
        request=MagicMock(headers={}, client=MagicMock(host="127.0.0.1")),
        db=db_approve,
    )

    assert approve_result["data"]["status"] == "approved"
    assert approve_result["data"]["id"] == str(candidate_id)
    assert approve_result["data"]["admin_id"] == str(admin.id)
    assert db_approve.commit.called

    # ── Step B: publish
    db_publish = AsyncMock()
    approved_row = MagicMock()
    approved_row.id = candidate_id
    approved_row.artist_id = artist_id
    approved_row.status = "approved"

    fa_row = _make_fa_row(fa_id)

    db_publish.execute = AsyncMock(
        side_effect=[
            # SELECT candidate
            MagicMock(fetchone=MagicMock(return_value=approved_row)),
            # INSERT INTO featured_artists RETURNING id
            MagicMock(fetchone=MagicMock(return_value=fa_row)),
            # UPDATE featured_artist_candidates
            MagicMock(),
        ]
    )
    db_publish.commit = AsyncMock()

    publish_result = await publish_candidate(
        candidate_id=str(candidate_id),
        body=PublishRequest(notes="주간 자동 선정"),
        admin=admin,
        request=MagicMock(headers={}, client=MagicMock(host="127.0.0.1")),
        db=db_publish,
    )

    assert publish_result["data"]["status"] == "published"
    assert publish_result["data"]["id"] == str(candidate_id)
    # featured_artists 테이블 INSERT 확인
    assert publish_result["data"]["featured_artist_id"] == str(fa_id)
    assert publish_result["data"]["published_at"] is not None
    assert db_publish.commit.called


# ── Test 3: reject 워크플로우 ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_reject_workflow_saves_reason():
    """pending → rejected + reason 저장 + reasoning JSONB에 reject_reason 키 확인."""
    admin = _make_admin()
    candidate_id = uuid.uuid4()

    db = AsyncMock()
    pending_row = MagicMock()
    pending_row.id = candidate_id
    pending_row.status = "pending"
    pending_row.reasoning = {
        "engagement": 0.85,
        "rank": 0.72,
        "diversity": 0.03,
        "new_artist_bonus": 0.20,
    }

    db.execute = AsyncMock(
        side_effect=[
            # SELECT candidate
            MagicMock(fetchone=MagicMock(return_value=pending_row)),
            # UPDATE
            MagicMock(),
        ]
    )
    db.commit = AsyncMock()

    reject_body = RejectRequest(reason="프로필 이미지 부적절")
    result = await reject_candidate(
        candidate_id=str(candidate_id),
        body=reject_body,
        admin=admin,
        request=MagicMock(headers={}, client=MagicMock(host="127.0.0.1")),
        db=db,
    )

    assert result["data"]["status"] == "rejected"
    assert result["data"]["id"] == str(candidate_id)
    assert result["data"]["reviewed_at"] is not None

    # DB UPDATE 호출 시 reasoning에 reject_reason이 포함되었는지 확인
    update_call = db.execute.call_args_list[1]
    update_params = update_call.args[1]  # SQL 파라미터 dict
    import json

    updated_reasoning = json.loads(update_params["reasoning"])
    assert "reject_reason" in updated_reasoning
    assert updated_reasoning["reject_reason"] == "프로필 이미지 부적절"


# ── Test 4: approve 중복 시도 → 409 Conflict ──────────────────────────────────

@pytest.mark.asyncio
async def test_approve_already_approved_returns_409():
    """이미 approved 상태인 후보를 다시 approve 시도 → 409 Conflict."""
    admin = _make_admin()
    candidate_id = uuid.uuid4()

    db = AsyncMock()
    # 이미 approved 상태
    already_approved_row = MagicMock()
    already_approved_row.id = candidate_id
    already_approved_row.status = "approved"

    db.execute = AsyncMock(
        return_value=MagicMock(fetchone=MagicMock(return_value=already_approved_row))
    )
    db.commit = AsyncMock()

    with pytest.raises(ApiError) as exc_info:
        await approve_candidate(
            candidate_id=str(candidate_id),
            admin=admin,
            request=MagicMock(headers={}, client=MagicMock(host="127.0.0.1")),
            db=db,
        )

    assert exc_info.value.status_code == 409
    # commit 호출 없음 (상태 변경 없음)
    db.commit.assert_not_called()
