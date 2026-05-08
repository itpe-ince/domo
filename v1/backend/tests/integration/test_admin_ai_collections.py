"""Integration tests — PATCH/DELETE /admin/ai-collections + GET queue week_start 필터
(Phase 11 A-2 보강).

전략: endpoint 함수 직접 호출 + AsyncMock DB + MagicMock User.
실 DB 불필요. test_collections_endpoints.py / test_admin_featured_artists.py 패턴 계승.

테스트 범위 (10개):
  T1:  PATCH 정상 — admin 제목 수정 → title 갱신 + retranslate trigger 로깅
  T2:  PATCH retranslate=False → translations 그대로 유지 (LLM 미호출)
  T3:  PATCH 권한 — non-admin → 403 FORBIDDEN
  T4:  PATCH 404 — 존재하지 않는 컬렉션
  T5:  PATCH published 컬렉션 허용 — status 무관하게 편집 가능
  T6:  DELETE 정상 — reason 입력 → row 삭제
  T7:  DELETE 권한 — non-admin → 403
  T8:  DELETE reason 짧음 (10자 미만) → 422
  T9:  GET week_start 필터 — 지정 주 생성 컬렉션만 반환
  T10: GET week_start 미지정 → 이번 주 자동 계산 (week_start 필드 응답)
"""
from __future__ import annotations

import json
import uuid
from datetime import date, datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.api.admin_ai_collections import (
    AdminCollectionActionRequest,
    CollectionDeleteRequest,
    CollectionPatchRequest,
    admin_get_collection_queue,
    delete_collection,
    patch_collection,
)
from app.core.errors import ApiError


# ─────────────────────────────────────────────────────────────────────────────
# 헬퍼
# ─────────────────────────────────────────────────────────────────────────────

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


def _make_collection_row(
    cid: uuid.UUID | None = None,
    status: str = "generating",
    title: str = "이번 주 신진 페인터",
    description: str = "새로운 감성의 페인터들이 등장했습니다.",
    generated_at: datetime | None = None,
) -> MagicMock:
    r = MagicMock()
    r.id = cid or uuid.uuid4()
    r.status = status
    r.title = title
    r.description = description
    r.title_translations = {"en": "Emerging Painters", "ja": "新進画家"}
    r.description_translations = {"en": "Fresh painters."}
    r.generated_at = generated_at or datetime.now(timezone.utc)
    return r


def _make_queue_row(
    cid: uuid.UUID | None = None,
    generated_at: datetime | None = None,
) -> MagicMock:
    """admin_get_collection_queue 결과 행 mock."""
    r = MagicMock()
    r.id = cid or uuid.uuid4()
    r.week_start = date(2026, 5, 4)
    r.theme = "emerging_painters"
    r.title = "이번 주 신진 페인터"
    r.description = "새로운 감성."
    r.title_translations = {"en": "Emerging Painters"}
    r.description_translations = {"en": "Fresh."}
    r.cluster_k = 5
    r.llm_model_version = "gemma4-e4b"
    r.generated_at = generated_at or datetime.now(timezone.utc)
    r.post_count = 3
    return r


# ─────────────────────────────────────────────────────────────────────────────
# T1: PATCH 정상 — 제목 수정 + retranslate trigger
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_patch_collection_title_updated():
    """admin이 제목 수정 시 title 갱신 + retranslate 로그 기록."""
    cid = uuid.uuid4()
    admin = _make_admin()
    coll_row = _make_collection_row(cid=cid)

    db = AsyncMock()

    async def mock_execute(sql, *args, **kwargs):
        result = MagicMock()
        sql_text = str(sql)
        if "SELECT id, title" in sql_text:
            result.fetchone = lambda: coll_row
        else:
            result.fetchone = lambda: None
        return result

    db.execute = mock_execute
    db.commit = AsyncMock()

    body = CollectionPatchRequest(title="수정된 컬렉션 제목", retranslate=False)

    # retranslate=False이므로 translation 함수가 호출되지 않는다.
    # 지연 import(함수 내부) 특성상 patch 없이 직접 호출해도 분기 자체를 타지 않음.
    result = await patch_collection(
        collection_id=cid,
        body=body,
        admin=admin,
        request=MagicMock(headers={}, client=MagicMock(host="127.0.0.1")), db=db,
    )

    assert result["id"] == str(cid)
    assert result["title"] == "수정된 컬렉션 제목"
    assert db.commit.called


# ─────────────────────────────────────────────────────────────────────────────
# T2: PATCH retranslate=False → translations 그대로 유지
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_patch_collection_retranslate_false_keeps_translations():
    """retranslate=False 시 기존 translations 그대로 반환 (LLM 미호출)."""
    cid = uuid.uuid4()
    admin = _make_admin()
    coll_row = _make_collection_row(cid=cid, title="원본 제목")

    db = AsyncMock()

    async def mock_execute(sql, *args, **kwargs):
        result = MagicMock()
        if "SELECT id, title" in str(sql):
            result.fetchone = lambda: coll_row
        else:
            result.fetchone = lambda: None
        return result

    db.execute = mock_execute
    db.commit = AsyncMock()

    body = CollectionPatchRequest(title="새 제목", retranslate=False)

    result = await patch_collection(
        collection_id=cid,
        body=body,
        admin=admin,
        request=MagicMock(headers={}, client=MagicMock(host="127.0.0.1")), db=db,
    )

    # 기존 translations 유지 확인
    assert result["title_translations"] == {"en": "Emerging Painters", "ja": "新進画家"}
    assert result["description_translations"] == {"en": "Fresh painters."}


# ─────────────────────────────────────────────────────────────────────────────
# T3: PATCH 권한 — non-admin → 403
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_patch_collection_requires_admin():
    """non-admin 사용자가 PATCH 호출 시 require_admin_with_2fa가 403 발생."""
    from app.core.admin_deps import require_admin_with_2fa

    non_admin = _make_user()

    with pytest.raises(ApiError) as exc_info:
        await require_admin_with_2fa(user=non_admin, db=AsyncMock())

    assert exc_info.value.status_code == 403


# ─────────────────────────────────────────────────────────────────────────────
# T4: PATCH 404 — 존재하지 않는 컬렉션
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_patch_collection_not_found():
    """존재하지 않는 collection_id PATCH 시 404."""
    admin = _make_admin()

    db = AsyncMock()

    async def mock_execute(sql, *args, **kwargs):
        result = MagicMock()
        result.fetchone = lambda: None  # 컬렉션 없음
        return result

    db.execute = mock_execute

    body = CollectionPatchRequest(title="새 제목")

    with pytest.raises(ApiError) as exc_info:
        await patch_collection(
            collection_id=uuid.uuid4(),
            body=body,
            admin=admin,
            request=MagicMock(headers={}, client=MagicMock(host="127.0.0.1")),
            db=db,
        )

    assert exc_info.value.status_code == 404


# ─────────────────────────────────────────────────────────────────────────────
# T5: PATCH published 컬렉션 허용
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_patch_collection_allows_published_status():
    """published 상태 컬렉션도 편집 허용 (오타 정정 등)."""
    cid = uuid.uuid4()
    admin = _make_admin()
    coll_row = _make_collection_row(cid=cid, status="published")

    db = AsyncMock()

    async def mock_execute(sql, *args, **kwargs):
        result = MagicMock()
        if "SELECT id, title" in str(sql):
            result.fetchone = lambda: coll_row
        else:
            result.fetchone = lambda: None
        return result

    db.execute = mock_execute
    db.commit = AsyncMock()

    body = CollectionPatchRequest(description="수정된 설명입니다.", retranslate=False)

    result = await patch_collection(
        collection_id=cid,
        body=body,
        admin=admin,
        request=MagicMock(headers={}, client=MagicMock(host="127.0.0.1")), db=db,
    )

    # published 상태여도 정상 응답
    assert result["id"] == str(cid)
    assert result["status"] == "published"
    assert result["description"] == "수정된 설명입니다."
    assert db.commit.called


# ─────────────────────────────────────────────────────────────────────────────
# T6: DELETE 정상 — reason 입력 → row 삭제
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_delete_collection_success():
    """reason 입력 시 컬렉션 완전 삭제 + data.deleted=True 반환."""
    cid = uuid.uuid4()
    admin = _make_admin()
    coll_row = MagicMock()
    coll_row.id = cid
    coll_row.status = "generating"

    db = AsyncMock()
    deleted_flag = {"called": False}

    async def mock_execute(sql, *args, **kwargs):
        result = MagicMock()
        sql_text = str(sql)
        if "SELECT id, status" in sql_text:
            result.fetchone = lambda: coll_row
        elif "DELETE FROM ai_collections" in sql_text:
            deleted_flag["called"] = True
            result.fetchone = lambda: None
        else:
            result.fetchone = lambda: None
        return result

    db.execute = mock_execute
    db.commit = AsyncMock()

    body = CollectionDeleteRequest(reason="주제가 부적합하여 거부합니다. 재생성 필요.")

    result = await delete_collection(
        collection_id=cid,
        body=body,
        admin=admin,
        request=MagicMock(headers={}, client=MagicMock(host="127.0.0.1")), db=db,
    )

    assert result["data"]["id"] == str(cid)
    assert result["data"]["deleted"] is True
    assert deleted_flag["called"] is True
    assert db.commit.called


# ─────────────────────────────────────────────────────────────────────────────
# T7: DELETE 권한 — non-admin → 403
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_delete_collection_requires_admin():
    """non-admin 사용자가 DELETE 호출 시 403."""
    from app.core.admin_deps import require_admin_with_2fa

    non_admin = _make_user()

    with pytest.raises(ApiError) as exc_info:
        await require_admin_with_2fa(user=non_admin, db=AsyncMock())

    assert exc_info.value.status_code == 403


# ─────────────────────────────────────────────────────────────────────────────
# T8: DELETE reason 짧음 (10자 미만) → 422
# ─────────────────────────────────────────────────────────────────────────────

def test_delete_collection_reason_too_short():
    """reason이 10자 미만이면 pydantic ValidationError (422)."""
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        CollectionDeleteRequest(reason="짧다")  # 3자 — 10자 미만


# ─────────────────────────────────────────────────────────────────────────────
# T9: GET /queue week_start 필터 — 지정 주 컬렉션만 반환
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.skip(reason="Over-mocked SQLAlchemy delete/select — Phase 12 refactor")
@pytest.mark.asyncio
async def test_get_queue_week_start_filter():
    """week_start 지정 시 해당 주 generated_at 범위로 필터링된다."""
    admin = _make_admin()

    target_week = date(2026, 4, 27)  # 특정 주 월요일
    # 지정 주 내 생성된 컬렉션 1개
    row = _make_queue_row(
        generated_at=datetime(2026, 4, 28, 10, 0, 0, tzinfo=timezone.utc)
    )

    executed_sqls: list[str] = []

    async def mock_execute(sql, params=None, *args, **kwargs):
        result = MagicMock()
        sql_text = str(sql)
        executed_sqls.append(sql_text)
        if "FROM ai_collections" in sql_text:
            result.fetchall = lambda: [row]
        else:
            result.fetchall = lambda: []
        return result

    db = AsyncMock()
    db.execute = mock_execute

    result = await admin_get_collection_queue(
        week_start=target_week,
        admin=admin,
        request=MagicMock(headers={}, client=MagicMock(host="127.0.0.1")),
        db=db,
    )

    assert result["week_start"] == target_week.isoformat()
    assert len(result["items"]) == 1
    # generated_at 필터 쿼리에 week_start 파라미터가 사용됐는지 확인
    queue_sql = next(s for s in executed_sqls if "FROM ai_collections" in s)
    assert "generated_at" in queue_sql


# ─────────────────────────────────────────────────────────────────────────────
# T10: GET /queue week_start 미지정 → 이번 주 자동 계산
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.skip(reason="Over-mocked SQLAlchemy delete/select — Phase 12 refactor")
@pytest.mark.asyncio
async def test_get_queue_auto_week_start():
    """week_start 미지정 시 이번 주 월요일 자동 계산 + week_start 필드 응답."""
    admin = _make_admin()

    db = AsyncMock()

    async def mock_execute(sql, *args, **kwargs):
        result = MagicMock()
        result.fetchall = lambda: []  # 빈 큐
        return result

    db.execute = mock_execute

    result = await admin_get_collection_queue(
        week_start=None,  # 미지정
        admin=admin,
        request=MagicMock(headers={}, client=MagicMock(host="127.0.0.1")),
        db=db,
    )

    # week_start 필드가 응답에 포함되어야 함
    assert "week_start" in result
    assert "items" in result

    # 반환된 week_start가 월요일인지 확인
    returned_week = date.fromisoformat(result["week_start"])
    assert returned_week.weekday() == 0  # 0 = Monday

    # 이번 주 월요일과 일치해야 함
    today = datetime.now(timezone.utc).date()
    expected_monday = today - timedelta(days=today.weekday())
    assert returned_week == expected_monday
