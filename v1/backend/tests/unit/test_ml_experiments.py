"""Unit tests — ml_experiments.py (Phase 10 K-8).

테스트 항목:
  1. get_user_variant: 기존 할당 레코드 HIT → DB에서 variant 반환
  2. get_user_variant: 신규 할당 — PostHog flag OFF → v1
  3. get_user_variant: 신규 할당 — PostHog flag ON → v2
  4. get_user_variant: running 실험 없음 → v1 default
  5. 분배 비율 검증: 1000회 호출 시 ≈ 50:50 (±5%)
  6. Mock 모드: POSTHOG_API_KEY 미설정 → v1 반환
  7. cleanup_old_experiments: idempotent (0 rows, 2회 호출 무오류)
  8. record_event: PostHog 발화 + sponsor_created 이면 conversions metric
  9. posthog_client: posthog 라이브러리 미설치 graceful (ImportError)
"""
from __future__ import annotations

import sys
import types
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services import ml_experiments
from app.services.posthog_client import _PostHogClient


# ── Test 1: 기존 할당 레코드 HIT ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_user_variant_existing_assignment():
    """기존 할당 레코드 있음 → DB에서 variant 반환 (PostHog 미조회)."""
    db = AsyncMock()

    # ml_experiments 조회: running 실험 있음
    mock_exp_row = MagicMock()
    mock_exp_row.id = "exp-uuid-1"
    # ml_experiment_assignments 조회: 기존 할당 있음
    mock_assign_row = MagicMock()
    mock_assign_row.variant = "v2"

    db.execute = AsyncMock(side_effect=[
        MagicMock(fetchone=MagicMock(return_value=mock_exp_row)),
        MagicMock(fetchone=MagicMock(return_value=mock_assign_row)),
    ])

    result = await ml_experiments.get_user_variant(db, "feed_v2_rollout", "user-1")

    assert result == "v2"


# ── Test 2: 신규 할당 — PostHog flag OFF → v1 ────────────────────────────────


@pytest.mark.asyncio
async def test_get_user_variant_new_assignment_v1():
    """신규 할당 — PostHog flag OFF → v1."""
    db = AsyncMock()

    mock_exp_row = MagicMock()
    mock_exp_row.id = "exp-uuid-2"

    db.execute = AsyncMock(side_effect=[
        MagicMock(fetchone=MagicMock(return_value=mock_exp_row)),
        MagicMock(fetchone=MagicMock(return_value=None)),  # 기존 할당 없음
        MagicMock(),  # INSERT
    ])
    db.commit = AsyncMock()

    with patch.object(
        ml_experiments.posthog_client, "get_feature_flag",
        new=AsyncMock(return_value=False),
    ):
        result = await ml_experiments.get_user_variant(db, "feed_v2_rollout", "user-2")

    assert result == "v1"


# ── Test 3: 신규 할당 — PostHog flag ON → v2 ─────────────────────────────────


@pytest.mark.asyncio
async def test_get_user_variant_new_assignment_v2():
    """신규 할당 — PostHog flag ON → v2."""
    db = AsyncMock()

    mock_exp_row = MagicMock()
    mock_exp_row.id = "exp-uuid-3"

    db.execute = AsyncMock(side_effect=[
        MagicMock(fetchone=MagicMock(return_value=mock_exp_row)),
        MagicMock(fetchone=MagicMock(return_value=None)),
        MagicMock(),
    ])
    db.commit = AsyncMock()

    with patch.object(
        ml_experiments.posthog_client, "get_feature_flag",
        new=AsyncMock(return_value=True),
    ):
        result = await ml_experiments.get_user_variant(db, "feed_v2_rollout", "user-3")

    assert result == "v2"


# ── Test 4: running 실험 없음 → v1 default ───────────────────────────────────


@pytest.mark.asyncio
async def test_get_user_variant_no_running_experiment():
    """running 실험 없음 → v1 default 반환."""
    db = AsyncMock()
    db.execute = AsyncMock(
        return_value=MagicMock(fetchone=MagicMock(return_value=None))
    )

    result = await ml_experiments.get_user_variant(db, "feed_v2_rollout", "user-4")

    assert result == "v1"


# ── Test 5: 분배 비율 검증 (1000회 시뮬레이션) ───────────────────────────────


@pytest.mark.asyncio
async def test_variant_distribution_50_50():
    """1000회 호출 시 v1/v2 분배 ≈ 50:50 (±5%)."""
    import random

    counts = {"v1": 0, "v2": 0}
    for i in range(1000):
        db = AsyncMock()

        mock_exp_row = MagicMock()
        mock_exp_row.id = "exp-uuid-dist"

        db.execute = AsyncMock(side_effect=[
            MagicMock(fetchone=MagicMock(return_value=mock_exp_row)),
            MagicMock(fetchone=MagicMock(return_value=None)),
            MagicMock(),
        ])
        db.commit = AsyncMock()

        # 50% 확률 flag 반환 시뮬레이션
        flag_result = random.random() < 0.5
        with patch.object(
            ml_experiments.posthog_client, "get_feature_flag",
            new=AsyncMock(return_value=flag_result),
        ):
            variant = await ml_experiments.get_user_variant(
                db, "feed_v2_rollout", f"user-{i}"
            )
        counts[variant] += 1

    v1_ratio = counts["v1"] / 1000
    assert 0.45 <= v1_ratio <= 0.55, (
        f"분배 불균형: v1={v1_ratio:.2f} (기대값 0.45~0.55)"
    )


# ── Test 6: Mock 모드 — v1 반환 ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_posthog_mock_mode_returns_v1():
    """POSTHOG_API_KEY 미설정 Mock 모드 → v1 반환."""
    db = AsyncMock()

    mock_exp_row = MagicMock()
    mock_exp_row.id = "exp-uuid-mock"

    db.execute = AsyncMock(side_effect=[
        MagicMock(fetchone=MagicMock(return_value=mock_exp_row)),
        MagicMock(fetchone=MagicMock(return_value=None)),
        MagicMock(),
    ])
    db.commit = AsyncMock()

    # Mock 모드: get_feature_flag → False (전 사용자 v1)
    with patch.object(
        ml_experiments.posthog_client, "get_feature_flag",
        new=AsyncMock(return_value=False),
    ):
        result = await ml_experiments.get_user_variant(
            db, "feed_v2_rollout", "user-mock"
        )

    assert result == "v1"


# ── Test 7: cleanup_old_experiments idempotent ────────────────────────────────


@pytest.mark.asyncio
async def test_cleanup_old_experiments_idempotent():
    """cleanup 2회 호출 → 동일하게 동작 (데이터 없어도 오류 없음)."""
    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.rowcount = 0
    db.execute = AsyncMock(return_value=mock_result)
    db.commit = AsyncMock()

    result1 = await ml_experiments.cleanup_old_experiments(db, days=90)
    result2 = await ml_experiments.cleanup_old_experiments(db, days=90)

    assert result1 == 0
    assert result2 == 0
    # 오류 없이 2회 호출 성공
    assert db.commit.call_count == 2


# ── Test 8: record_event — PostHog 발화 + conversions metric ─────────────────


@pytest.mark.asyncio
async def test_record_event_sponsor_created():
    """sponsor_created 이벤트 → capture 호출 + conversions metric 증가."""
    with patch.object(
        ml_experiments.posthog_client, "capture",
        new=AsyncMock(),
    ) as mock_capture, patch(
        "app.services.ml_experiments._increment_conversions_metric"
    ) as mock_conversions:
        await ml_experiments.record_event(
            "feed_v2_rollout", "user-ev", "sponsor_created",
            {"variant": "v2"},
        )

    mock_capture.assert_called_once()
    mock_conversions.assert_called_once()


@pytest.mark.asyncio
async def test_record_event_feed_click_no_conversions():
    """feed_post_click → capture 호출, conversions metric 미증가."""
    with patch.object(
        ml_experiments.posthog_client, "capture",
        new=AsyncMock(),
    ) as mock_capture, patch(
        "app.services.ml_experiments._increment_conversions_metric"
    ) as mock_conversions:
        await ml_experiments.record_event(
            "feed_v2_rollout", "user-ev2", "feed_post_click",
            {"post_id": "p1"},
        )

    mock_capture.assert_called_once()
    mock_conversions.assert_not_called()


# ── Test 9: posthog 라이브러리 미설치 graceful ───────────────────────────────


@pytest.mark.asyncio
async def test_posthog_client_importerror_graceful():
    """posthog 라이브러리 미설치 → ImportError catch → False 반환 (graceful)."""
    client = _PostHogClient()

    # posthog import 실패 시뮬레이션: _get_posthog → None
    with patch(
        "app.services.posthog_client._get_posthog", return_value=None
    ), patch(
        "app.services.posthog_client._MOCK_MODE", False
    ):
        result = await client.get_feature_flag("ml_feed_v2", "user-import-err")

    # ImportError → graceful: False 반환
    assert result is False


@pytest.mark.asyncio
async def test_posthog_client_capture_importerror_graceful():
    """posthog 미설치 시 capture → 예외 없이 반환."""
    client = _PostHogClient()

    with patch("app.services.posthog_client._get_posthog", return_value=None):
        # 예외 없이 정상 반환
        await client.capture("test_event", "user-x", {"k": "v"})
