"""Unit tests — ml_feed_inference.py (Phase 9 K-1).

테스트 항목:
  1. cache HIT → DB 조회 없이 즉시 반환
  2. cache MISS → 계산 후 Redis SET 호출 경로 검증
  3. cold user fallback (interaction < 5건)
  4. 모델 미준비 시 fallback
  5. _chronological_fallback 반환 구조 검증
  6. _get_interaction_count: DB 조회 검증
  7. _load_active_model: active 모델 반환 / None 반환
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services import ml_feed_inference


# ── Cache hit/miss ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_recommendations_cache_hit():
    """Redis cache HIT → DB 조회 없이 즉시 반환."""
    db = AsyncMock()
    expected = ["post-uuid-1", "post-uuid-2", "post-uuid-3"]

    with patch.object(ml_feed_inference.cache, "get_json", return_value=expected):
        result = await ml_feed_inference.get_recommendations(db, "user-uuid-1", top_k=3)

    assert result == expected
    # cache hit 시 DB execute 호출 없음
    db.execute.assert_not_called()


@pytest.mark.asyncio
async def test_get_recommendations_cache_miss_cold_user_no_cache_write():
    """cache MISS + cold user → chronological fallback, Redis SET 미호출."""
    db = AsyncMock()

    with (
        patch.object(ml_feed_inference.cache, "get_json", return_value=None),
        patch.object(ml_feed_inference.cache, "set_json", new_callable=AsyncMock) as mock_set,
        patch.object(
            ml_feed_inference, "_get_interaction_count", new_callable=AsyncMock, return_value=2
        ),
        patch.object(
            ml_feed_inference, "_chronological_fallback",
            new_callable=AsyncMock, return_value=["post-a"],
        ),
    ):
        result = await ml_feed_inference.get_recommendations(db, "cold-user", top_k=5)

    assert result == ["post-a"]
    # cold user fallback: 개인화 없으므로 캐시 미저장
    mock_set.assert_not_called()


# ── Cold user fallback ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_cold_user_fallback_threshold():
    """interaction < 5건 사용자 → _chronological_fallback 호출."""
    db = AsyncMock()
    chronological_posts = ["post-a", "post-b", "post-c"]

    with (
        patch.object(ml_feed_inference.cache, "get_json", return_value=None),
        patch.object(
            ml_feed_inference, "_get_interaction_count", new_callable=AsyncMock, return_value=4
        ),
        patch.object(
            ml_feed_inference, "_chronological_fallback",
            new_callable=AsyncMock, return_value=chronological_posts,
        ) as mock_fallback,
    ):
        result = await ml_feed_inference.get_recommendations(db, "cold-user", top_k=5)

    mock_fallback.assert_awaited_once()
    assert result == chronological_posts


@pytest.mark.asyncio
async def test_warm_user_no_fallback():
    """interaction >= 5건 사용자 → cold user fallback 호출 안 함."""
    db = AsyncMock()

    with (
        patch.object(ml_feed_inference.cache, "get_json", return_value=None),
        patch.object(
            ml_feed_inference, "_get_interaction_count", new_callable=AsyncMock, return_value=10
        ),
        patch.object(
            ml_feed_inference, "_load_active_model", new_callable=AsyncMock, return_value=None
        ),
        patch.object(
            ml_feed_inference, "_chronological_fallback",
            new_callable=AsyncMock, return_value=["post-x"],
        ) as mock_fallback,
    ):
        result = await ml_feed_inference.get_recommendations(db, "warm-user", top_k=5)

    # 모델 미준비로 fallback 호출되지만, cold user fallback 아님
    mock_fallback.assert_awaited_once()
    assert result == ["post-x"]


# ── 모델 미준비 fallback ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_mock_mode_no_active_model():
    """ml_models active 없음 → chronological fallback."""
    db = AsyncMock()
    fallback_posts = ["post-x", "post-y"]

    with (
        patch.object(ml_feed_inference.cache, "get_json", return_value=None),
        patch.object(
            ml_feed_inference, "_get_interaction_count", new_callable=AsyncMock, return_value=10
        ),
        patch.object(
            ml_feed_inference, "_load_active_model", new_callable=AsyncMock, return_value=None
        ),
        patch.object(
            ml_feed_inference, "_chronological_fallback",
            new_callable=AsyncMock, return_value=fallback_posts,
        ),
    ):
        result = await ml_feed_inference.get_recommendations(db, "user-1")

    assert result == fallback_posts


@pytest.mark.asyncio
async def test_mf_exception_falls_back():
    """MF 점수 계산 중 예외 → chronological fallback."""
    db = AsyncMock()
    fallback_posts = ["post-fb"]

    with (
        patch.object(ml_feed_inference.cache, "get_json", return_value=None),
        patch.object(
            ml_feed_inference, "_get_interaction_count", new_callable=AsyncMock, return_value=20
        ),
        patch.object(
            ml_feed_inference, "_load_active_model",
            new_callable=AsyncMock, return_value={"user_ids": [], "post_ids": [], "user_factors": [], "item_factors": []},
        ),
        patch.object(
            ml_feed_inference, "_compute_mf_scores",
            new_callable=AsyncMock, side_effect=RuntimeError("MF error"),
        ),
        patch.object(
            ml_feed_inference, "_chronological_fallback",
            new_callable=AsyncMock, return_value=fallback_posts,
        ),
    ):
        result = await ml_feed_inference.get_recommendations(db, "user-1")

    assert result == fallback_posts


# ── top_k 정렬 검증 ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_recommendations_top_k_respected():
    """ML 성공 시 top_k개 이하 포스트 반환."""
    db = AsyncMock()
    ml_posts = [f"post-{i}" for i in range(20)]

    with (
        patch.object(ml_feed_inference.cache, "get_json", return_value=None),
        patch.object(
            ml_feed_inference, "_get_interaction_count", new_callable=AsyncMock, return_value=30
        ),
        patch.object(
            ml_feed_inference, "_load_active_model",
            new_callable=AsyncMock, return_value={"some": "params"},
        ),
        patch.object(
            ml_feed_inference, "_compute_mf_scores",
            new_callable=AsyncMock, return_value=ml_posts,
        ),
        patch.object(ml_feed_inference.cache, "set_json", new_callable=AsyncMock),
    ):
        result = await ml_feed_inference.get_recommendations(db, "user-1", top_k=20)

    assert len(result) == 20
    assert result == ml_posts


# ── _chronological_fallback ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_chronological_fallback_structure():
    """_chronological_fallback: 반환 형식 str 리스트 확인."""
    db = AsyncMock()
    mock_rows = [
        MagicMock(id="post-uuid-1"),
        MagicMock(id="post-uuid-2"),
    ]
    db.execute = AsyncMock(return_value=MagicMock(fetchall=lambda: mock_rows))

    result = await ml_feed_inference._chronological_fallback(db, top_k=2)

    assert len(result) == 2
    assert all(isinstance(pid, str) for pid in result)
    assert result[0] == "post-uuid-1"
    assert result[1] == "post-uuid-2"


@pytest.mark.asyncio
async def test_chronological_fallback_empty_db():
    """DB에 포스트 없음 → 빈 리스트 반환."""
    db = AsyncMock()
    db.execute = AsyncMock(return_value=MagicMock(fetchall=lambda: []))

    result = await ml_feed_inference._chronological_fallback(db, top_k=10)
    assert result == []


# ── _get_interaction_count ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_interaction_count_zero():
    """신규 사용자 → interaction count 0."""
    db = AsyncMock()
    db.execute = AsyncMock(return_value=MagicMock(scalar_one=lambda: 0))

    count = await ml_feed_inference._get_interaction_count(db, "new-user-uuid")
    assert count == 0


@pytest.mark.asyncio
async def test_get_interaction_count_positive():
    """기존 사용자 → interaction count > 0."""
    db = AsyncMock()
    db.execute = AsyncMock(return_value=MagicMock(scalar_one=lambda: 42))

    count = await ml_feed_inference._get_interaction_count(db, "user-uuid")
    assert count == 42


# ── _load_active_model ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_load_active_model_none_when_no_model():
    """ml_models에 active 모델 없음 → None 반환."""
    db = AsyncMock()
    db.execute = AsyncMock(return_value=MagicMock(fetchone=lambda: None))

    result = await ml_feed_inference._load_active_model(db)
    assert result is None


@pytest.mark.asyncio
async def test_load_active_model_returns_dict():
    """ml_models active 모델 존재 → params dict 반환."""
    db = AsyncMock()
    params_dict = {
        "user_factors": [[0.1, 0.2]],
        "item_factors": [[0.3, 0.4]],
        "user_ids": ["u1"],
        "post_ids": ["p1"],
    }
    mock_row = MagicMock()
    mock_row.params = params_dict
    db.execute = AsyncMock(return_value=MagicMock(fetchone=lambda: mock_row))

    result = await ml_feed_inference._load_active_model(db)
    assert result is not None
    assert "user_factors" in result
    assert "item_factors" in result
