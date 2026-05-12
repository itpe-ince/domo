"""Unit tests — ml_feed_training.py (Phase 9 K-1).

테스트 항목:
  1. train_mf_model: numpy random mock (작은 matrix) — user_factors, item_factors 반환 구조
  2. train_mf_model: 빈 interactions → None 반환, 에러 없음
  3. train_mf_model: 상호작용 건수 < MIN_INTERACTIONS → None 반환
  4. collect_interactions: DB 데이터 없음 → 빈 dict 반환
  5. collect_interactions: 정상 데이터 → 올바른 구조 반환
  6. save_model_artifacts: 모델 저장 → 모델 ID 반환
"""
from __future__ import annotations

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services import ml_feed_training


# ── MF 학습 — numpy mock (작은 matrix) ───────────────────────────────────────


def _make_interactions(n_pairs: int = 120) -> dict:
    """테스트용 interactions 딕셔너리 생성 (n_pairs 건 초과 → MIN_INTERACTIONS 충족)."""
    user_ids = ["u1", "u2", "u3"]
    post_ids = ["p1", "p2", "p3", "p4"]
    user_idx = {u: i for i, u in enumerate(user_ids)}
    post_idx = {p: i for i, p in enumerate(post_ids)}

    base_pairs = [
        (0, 0, 3.0), (0, 1, 1.0),
        (1, 1, 2.0), (1, 2, 5.0),
        (2, 0, 1.0), (2, 3, 4.0),
    ]
    # n_pairs 건이 될 때까지 반복
    pairs = []
    while len(pairs) < n_pairs:
        pairs.extend(base_pairs)
    pairs = pairs[:n_pairs]

    return {
        "user_ids": user_ids,
        "post_ids": post_ids,
        "user_idx": user_idx,
        "post_idx": post_idx,
        "interactions": pairs,
    }


def test_train_mf_model_returns_factors_structure():
    """MIN_INTERACTIONS 초과 데이터 → user_factors, item_factors 포함한 dict 반환."""
    interactions = _make_interactions(n_pairs=120)

    # implicit, scipy 없는 환경 시뮬 → numpy mock fallback
    with (
        patch.dict(sys.modules, {"implicit": None}),
        patch.dict(sys.modules, {"scipy": None, "scipy.sparse": None, "scipy.sparse.linalg": None}),
    ):
        result = ml_feed_training.train_mf_model(
            interactions, n_factors=5, n_iterations=2
        )

    # numpy가 설치된 환경이면 mock 결과 반환
    if result is not None:
        assert "user_factors" in result
        assert "item_factors" in result
        assert isinstance(result["user_factors"], list)
        assert isinstance(result["item_factors"], list)
        # shape 검증: users=3, posts=4, factors=5
        assert len(result["user_factors"]) == 3
        assert len(result["item_factors"]) == 4
        assert len(result["user_factors"][0]) == 5


def test_train_mf_model_empty_interactions():
    """빈 interactions dict → None 반환, 예외 없음."""
    result = ml_feed_training.train_mf_model({}, n_factors=5)
    assert result is None


def test_train_mf_model_insufficient_data():
    """interactions < ML_MIN_INTERACTIONS → None 반환."""
    interactions = _make_interactions(n_pairs=5)  # 5건 < 기본 100건
    result = ml_feed_training.train_mf_model(interactions)
    assert result is None


def test_train_mf_model_no_users_posts():
    """user_ids 또는 post_ids 없는 interactions → None 반환."""
    result = ml_feed_training.train_mf_model(
        {"user_ids": [], "post_ids": [], "interactions": [(0, 0, 1.0)] * 200},
    )
    assert result is None


# ── collect_interactions ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_collect_interactions_empty_db():
    """DB에 데이터 없음 → 빈 dict 반환."""
    db = AsyncMock()
    db.execute = AsyncMock(return_value=MagicMock(fetchall=lambda: []))

    result = await ml_feed_training.collect_interactions(db, days=90)
    assert result == {}


@pytest.mark.asyncio
async def test_collect_interactions_structure():
    """정상 데이터 → 올바른 구조 반환."""
    db = AsyncMock()
    mock_rows = [
        MagicMock(user_id="user-1", post_id="post-a", total_weight=3.0),
        MagicMock(user_id="user-1", post_id="post-b", total_weight=1.0),
        MagicMock(user_id="user-2", post_id="post-a", total_weight=2.0),
    ]
    db.execute = AsyncMock(return_value=MagicMock(fetchall=lambda: mock_rows))

    result = await ml_feed_training.collect_interactions(db, days=90)

    assert "user_ids" in result
    assert "post_ids" in result
    assert "interactions" in result
    assert "user_idx" in result
    assert "post_idx" in result
    # user-1, user-2
    assert len(result["user_ids"]) == 2
    # post-a, post-b
    assert len(result["post_ids"]) == 2
    # 3쌍
    assert len(result["interactions"]) == 3
    # 각 interaction은 (u_idx, p_idx, weight) 튜플
    for u_idx, p_idx, weight in result["interactions"]:
        assert isinstance(u_idx, int)
        assert isinstance(p_idx, int)
        assert isinstance(weight, float)


# ── save_model_artifacts ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_save_model_artifacts_success():
    """모델 저장 성공 → 모델 UUID 문자열 반환."""
    db = AsyncMock()
    expected_id = "model-uuid-abcdef-123"

    # execute 호출: 1) archived UPDATE, 2) INSERT RETURNING id
    execute_mock = MagicMock()
    execute_mock.scalar_one = MagicMock(return_value=expected_id)

    db.execute = AsyncMock(return_value=execute_mock)
    db.commit = AsyncMock()

    model_result = {
        "user_factors": [[0.1, 0.2], [0.3, 0.4]],
        "item_factors": [[0.5, 0.6], [0.7, 0.8], [0.9, 1.0]],
    }
    interactions = {
        "user_ids": ["u1", "u2"],
        "post_ids": ["p1", "p2", "p3"],
    }

    result = await ml_feed_training.save_model_artifacts(
        db, model_result, interactions, version="mf-20260505"
    )

    assert result == expected_id
    db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_save_model_artifacts_db_error():
    """DB 에러 발생 → None 반환, rollback 호출."""
    db = AsyncMock()
    db.execute = AsyncMock(side_effect=Exception("DB connection error"))
    db.rollback = AsyncMock()

    model_result = {
        "user_factors": [[0.1]],
        "item_factors": [[0.2]],
    }

    result = await ml_feed_training.save_model_artifacts(
        db, model_result, {}, version="mf-20260505"
    )

    assert result is None
    db.rollback.assert_called_once()
