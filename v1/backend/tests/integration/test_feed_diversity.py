"""Integration tests — /api/feed?algo=v2 diversity reranking (Phase 10 K-2).

전략: AsyncMock DB + 엔드포인트 함수 직접 호출 (실제 DB 불필요).
기존 test_feed_api_v2.py 패턴 동일.

테스트 항목:
  1. /api/feed?algo=v2 응답 형식 동일 (diversity 활성 상태)
  2. DIVERSITY_RERANKING_ENABLED=false 시 비활성 (K-1 결과 그대로 반환)
  3. GET /admin/diversity-config → 목록 반환 (admin 전용)
  4. PATCH /admin/diversity-config/feed_default → 수정 즉시 반영
  5. PATCH — emerging_artist_boost > 2.0 → 422 Validation Error
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.api.admin_diversity import (
    list_diversity_configs,
    patch_diversity_config,
    DiversityConfigPatch,
)
from app.core.errors import ApiError


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _make_admin() -> MagicMock:
    u = MagicMock()
    u.id = uuid.uuid4()
    u.role = "admin"
    u.totp_enabled_at = datetime.now(timezone.utc)
    return u


def _make_row(**kwargs) -> MagicMock:
    """다양성 설정 DB row mock 생성."""
    row = MagicMock()
    row.id = kwargs.get("id", uuid.uuid4())
    row.name = kwargs.get("name", "feed_default")
    row.emerging_artist_boost = kwargs.get("emerging_artist_boost", 1.20)
    row.genre_min_diversity = kwargs.get("genre_min_diversity", 3)
    row.region_min_diversity = kwargs.get("region_min_diversity", 2)
    row.top_k_window = kwargs.get("top_k_window", 20)
    row.candidate_pool_size = kwargs.get("candidate_pool_size", 100)
    row.status = kwargs.get("status", "active")
    row.created_at = kwargs.get("created_at", datetime.now(timezone.utc))
    row.updated_at = kwargs.get("updated_at", datetime.now(timezone.utc))
    return row


# ─── Feed v2 + Diversity 통합 ─────────────────────────────────────────────────
#
# ADR (Phase 12 A-1 결정): test_feed_v2_diversity_applied, test_feed_v2_diversity_disabled_fallback 제거
#
# 제거 이유:
#   - `_personalized_feed_v2` 내부 함수는 존재하지 않음 (Phase 10 K-2 구현 시 ml_feed_inference 내부에 통합됨)
#   - diversity 로직은 `tests/unit/test_diversity_reranking.py`의 unit tests가 충분히 커버
#   - 존재하지 않는 내부 함수를 patch하는 것은 의미 없는 검증 (항상 pass)
#   - 추후 `_personalized_feed_v2`가 독립 함수로 분리된다면 이 파일에 새로운 테스트 추가
#
# 대체 커버리지:
#   - tests/unit/test_diversity_reranking.py — diversity reranking 알고리즘 unit 검증
#   - tests/unit/test_ml_feed_inference.py — ml_feed_inference 통합 검증


# ─── Admin Diversity Config API ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_admin_diversity_config_get_list():
    """GET /admin/diversity-config → 설정 목록 반환."""
    admin = _make_admin()
    db = AsyncMock()

    mock_row = _make_row()
    mock_result = MagicMock()
    mock_result.fetchall.return_value = [mock_row]
    db.execute.return_value = mock_result

    result = await list_diversity_configs(admin=admin, db=db)

    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0].name == "feed_default"
    assert result[0].emerging_artist_boost == 1.20
    assert result[0].genre_min_diversity == 3
    assert result[0].region_min_diversity == 2


@pytest.mark.asyncio
async def test_admin_diversity_config_get_empty():
    """GET /admin/diversity-config — 설정 없음 → 빈 리스트 반환."""
    admin = _make_admin()
    db = AsyncMock()

    mock_result = MagicMock()
    mock_result.fetchall.return_value = []
    db.execute.return_value = mock_result

    result = await list_diversity_configs(admin=admin, db=db)

    assert isinstance(result, list)
    assert len(result) == 0


@pytest.mark.asyncio
async def test_admin_diversity_config_patch_success():
    """PATCH /admin/diversity-config/feed_default → 수정 즉시 반영."""
    admin = _make_admin()
    db = AsyncMock()

    updated_row = _make_row(emerging_artist_boost=1.25)

    # 첫 execute: 존재 확인 / 두 번째: UPDATE / 세 번째: SELECT 결과
    check_mock = MagicMock()
    check_mock.fetchone.return_value = MagicMock(id=uuid.uuid4())

    select_mock = MagicMock()
    select_mock.fetchone.return_value = updated_row

    db.execute.side_effect = [check_mock, MagicMock(), select_mock]

    body = DiversityConfigPatch(emerging_artist_boost=1.25)
    result = await patch_diversity_config(name="feed_default", body=body, admin=admin, request=MagicMock(headers={}, client=MagicMock(host="127.0.0.1")), db=db)

    assert result.emerging_artist_boost == 1.25
    assert db.commit.called


@pytest.mark.asyncio
async def test_admin_diversity_config_patch_not_found():
    """PATCH /admin/diversity-config/nonexistent → 404 Not Found."""
    admin = _make_admin()
    db = AsyncMock()

    check_mock = MagicMock()
    check_mock.fetchone.return_value = None  # 존재하지 않음
    db.execute.return_value = check_mock

    body = DiversityConfigPatch(emerging_artist_boost=1.25)

    with pytest.raises(ApiError) as exc_info:
        await patch_diversity_config(name="nonexistent", body=body, admin=admin, request=MagicMock(headers={}, client=MagicMock(host="127.0.0.1")), db=db)

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_admin_diversity_config_patch_no_fields():
    """PATCH 본문 필드 없음 → 400 Validation Error."""
    admin = _make_admin()
    db = AsyncMock()

    body = DiversityConfigPatch()  # 모든 필드 None

    with pytest.raises(ApiError) as exc_info:
        await patch_diversity_config(name="feed_default", body=body, admin=admin, request=MagicMock(headers={}, client=MagicMock(host="127.0.0.1")), db=db)

    assert exc_info.value.status_code == 400
