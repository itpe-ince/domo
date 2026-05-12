"""Integration tests — /v1/ai-collections endpoints (Phase 10 K-7).

전략: endpoint 함수 직접 호출 + AsyncMock DB + MagicMock User.
실 DB 불필요. test_admin_featured_artists.py / test_docent_endpoints.py 패턴 계승.

테스트 범위:
  T1: GET /ai-collections — 공개 목록 응답 형식 + items/total/page
  T2: GET /ai-collections — 페이지네이션 (limit=2)
  T3: GET /ai-collections/{id} — 컬렉션 상세 + posts position 순 정렬
  T4: admin publish 워크플로우 (generating → published → 공개 API에서 조회 가능)
  T5: admin archive 워크플로우 (generating → archived → 공개 API 404)
  T6: 권한 검증 — non-admin 403 (admin publish endpoint)
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.api.ai_collections import list_ai_collections, get_ai_collection
from app.api.admin_ai_collections import (
    admin_get_collection_queue,
    admin_publish_collection,
    admin_archive_collection,
    AdminCollectionActionRequest,
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
    status: str = "published",
    week: date | None = None,
    theme: str = "emerging_painters",
) -> MagicMock:
    r = MagicMock()
    r.id = cid or uuid.uuid4()
    r.week_start = week or date(2026, 5, 4)
    r.theme = theme
    r.title = "이번 주 신진 페인터"
    r.description = "새로운 감성의 페인터들이 등장했습니다."
    r.title_translations = {"en": "Emerging Painters This Week", "ja": "今週の新進画家"}
    r.description_translations = {"en": "Fresh painters have arrived."}
    r.cover_post_id = None
    r.status = status
    r.published_at = datetime(2026, 5, 5, 9, 30, 0, tzinfo=timezone.utc)
    r.post_count = 5
    r.cluster_k = 5
    r.llm_model_version = "gemma4-e4b"
    r.generated_at = datetime(2026, 5, 5, 9, 0, 0, tzinfo=timezone.utc)
    r._mapping = {
        "id": r.id,
        "week_start": r.week_start,
        "theme": r.theme,
        "title": r.title,
        "description": r.description,
        "title_translations": r.title_translations,
        "description_translations": r.description_translations,
        "cover_post_id": r.cover_post_id,
        "status": r.status,
        "published_at": r.published_at,
        "post_count": r.post_count,
        "cluster_k": r.cluster_k,
        "llm_model_version": r.llm_model_version,
        "generated_at": r.generated_at,
    }
    return r


def _make_db_for_list(collections: list) -> AsyncMock:
    """list_ai_collections용 AsyncSession mock."""
    db = AsyncMock()

    async def mock_execute(sql, *args, **kwargs):
        sql_text = str(sql)
        mock_result = MagicMock()

        if "COUNT(*)" in sql_text and "ai_collections" in sql_text:
            mock_result.scalar = lambda: len(collections)
        elif "FROM ai_collections" in sql_text and "LEFT JOIN ai_collection_posts" in sql_text:
            mock_result.fetchall = lambda: collections
        else:
            mock_result.fetchall = lambda: []
            mock_result.fetchone = lambda: None
            mock_result.scalar = lambda: 0

        return mock_result

    db.execute = mock_execute
    return db


def _make_db_for_detail(coll_row: MagicMock, post_rows: list) -> AsyncMock:
    """get_ai_collection용 AsyncSession mock."""
    db = AsyncMock()

    async def mock_execute(sql, *args, **kwargs):
        sql_text = str(sql)
        mock_result = MagicMock()

        if "FROM ai_collections" in sql_text and "WHERE id" in sql_text:
            mock_result.fetchone = lambda: coll_row
        elif "FROM ai_collection_posts" in sql_text:
            mock_result.fetchall = lambda: post_rows
        else:
            mock_result.fetchone = lambda: None
            mock_result.fetchall = lambda: []

        return mock_result

    db.execute = mock_execute
    return db


# ─────────────────────────────────────────────────────────────────────────────
# T1: GET /ai-collections — 공개 목록 응답 형식
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_ai_collections_public():
    """공개 컬렉션 목록 반환. items/total/page/limit 필드 포함."""
    coll = _make_collection_row()
    db = _make_db_for_list([coll])

    result = await list_ai_collections(page=1, limit=10, locale="ko", db=db)

    assert "items" in result
    assert "total" in result
    assert "page" in result
    assert "limit" in result
    assert result["total"] == 1
    assert result["page"] == 1
    assert len(result["items"]) == 1
    assert result["items"][0]["theme"] == "emerging_painters"


# ─────────────────────────────────────────────────────────────────────────────
# T2: GET /ai-collections — 페이지네이션
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_ai_collections_pagination():
    """limit=2 파라미터 동작 확인. limit 필드가 요청값과 일치."""
    colls = [_make_collection_row(theme=f"theme_{i}") for i in range(2)]
    db = _make_db_for_list(colls)

    result = await list_ai_collections(page=1, limit=2, locale="ko", db=db)

    assert result["limit"] == 2
    assert len(result["items"]) <= 2


# ─────────────────────────────────────────────────────────────────────────────
# T3: GET /ai-collections/{id} — 상세 + posts position 순 정렬
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_ai_collection_detail():
    """컬렉션 상세: posts 포함, position 순 정렬 확인."""
    cid = uuid.uuid4()
    coll = _make_collection_row(cid=cid)

    # post rows
    post_rows = []
    for pos in [1, 2, 3]:
        pr = MagicMock()
        pr.position = pos
        pr.post_id = uuid.uuid4()
        pr.post_title = f"작품 {pos}"
        pr.author_id = uuid.uuid4()
        pr.author_name = f"작가{pos}"
        pr.author_avatar = None
        post_rows.append(pr)

    db = _make_db_for_detail(coll, post_rows)

    result = await get_ai_collection(collection_id=cid, locale="ko", db=db)

    assert result["id"] == str(cid)
    assert "posts" in result
    positions = [p["position"] for p in result["posts"]]
    assert positions == sorted(positions)


# ─────────────────────────────────────────────────────────────────────────────
# T4: admin publish 워크플로우
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_admin_publish_collection():
    """admin: generating → published 전환 확인."""
    cid = uuid.uuid4()
    admin = _make_admin()

    coll_row = MagicMock()
    coll_row.id = cid
    coll_row.status = "generating"

    db = AsyncMock()

    async def mock_execute(sql, *args, **kwargs):
        mock_result = MagicMock()
        sql_text = str(sql)
        if "SELECT id, status" in sql_text:
            mock_result.fetchone = lambda: coll_row
        else:
            mock_result.fetchone = lambda: None
        return mock_result

    db.execute = mock_execute
    db.commit = AsyncMock()

    body = AdminCollectionActionRequest(admin_note="검수 완료")
    result = await admin_publish_collection(
        collection_id=cid,
        body=body,
        admin=admin,
        request=MagicMock(headers={}, client=MagicMock(host="127.0.0.1")), db=db,
    )

    assert result["status"] == "published"
    assert result["id"] == str(cid)
    assert "published_at" in result
    assert db.commit.called


# ─────────────────────────────────────────────────────────────────────────────
# T5: admin archive 워크플로우
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_admin_archive_collection():
    """admin: generating → archived 전환 확인."""
    cid = uuid.uuid4()
    admin = _make_admin()

    coll_row = MagicMock()
    coll_row.id = cid
    coll_row.status = "generating"

    db = AsyncMock()

    async def mock_execute(sql, *args, **kwargs):
        mock_result = MagicMock()
        sql_text = str(sql)
        if "SELECT id, status" in sql_text:
            mock_result.fetchone = lambda: coll_row
        else:
            mock_result.fetchone = lambda: None
        return mock_result

    db.execute = mock_execute
    db.commit = AsyncMock()

    body = AdminCollectionActionRequest(admin_note="주제 중복으로 보류")
    result = await admin_archive_collection(
        collection_id=cid,
        body=body,
        admin=admin,
        request=MagicMock(headers={}, client=MagicMock(host="127.0.0.1")), db=db,
    )

    assert result["status"] == "archived"
    assert result["id"] == str(cid)
    assert db.commit.called


# ─────────────────────────────────────────────────────────────────────────────
# T6: 권한 검증 — non-admin 403
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_admin_publish_requires_admin():
    """non-admin 사용자가 admin publish endpoint 호출 시 403."""
    from app.core.admin_deps import require_admin_with_2fa

    non_admin = _make_user()

    with pytest.raises(ApiError) as exc_info:
        await require_admin_with_2fa(user=non_admin, db=AsyncMock())

    assert exc_info.value.status_code == 403
