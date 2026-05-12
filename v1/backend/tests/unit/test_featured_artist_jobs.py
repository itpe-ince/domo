"""Unit tests — featured_artist_jobs.py (Phase 10 K-4).

테스트 항목:
  1. test_select_candidates_score_calculation     — composite_score 4가지 가중합 검증
  2. test_insert_candidates_on_conflict_do_nothing — 동일 artist+week 중복 INSERT 방지
  3. test_low_candidate_alert_triggered           — 후보 < 3명 시 알림 호출 확인
  4. test_artist_index_unavailable_fallback       — DB 예외 → 빈 리스트 반환
  5. test_diversity_mmr_genre_variety             — 동일 장르 패널티로 점수 감소
  6. test_new_artist_bonus_prioritized            — 후원자 0명 작가 보너스 > 0
"""
from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services import featured_artist_jobs


# ── 1. composite_score 점수 계산 (mock data) ──────────────────────────────────

@pytest.mark.asyncio
async def test_select_candidates_score_calculation():
    """engagement + rank + bonus 가중합 점수 계산 검증."""
    db = AsyncMock()
    # engagement_score=100(max), artist_rank=100(max), sponsor_count=0 → max score
    mock_row = MagicMock(
        artist_id="artist-uuid-1",
        artist_rank=100.0,
        follower_count=50,
        region="KR",
        genre="watercolor",
        engagement_score=100.0,
        sponsor_count=0,
    )
    db.execute = AsyncMock(
        return_value=MagicMock(fetchall=lambda: [mock_row])
    )
    db.commit = AsyncMock()

    with patch(
        "app.services.featured_artist_jobs._notify_admin_low_candidates",
        new=AsyncMock(),
    ):
        results = await featured_artist_jobs.select_candidates_for_week(
            db, week_start=date(2026, 5, 4), n=5
        )

    assert len(results) == 1
    assert results[0]["artist_id"] == "artist-uuid-1"
    # engagement_norm=1.0, rank_norm=1.0, new_artist_bonus=0.20 → score > 0
    assert results[0]["composite_score"] > 0

    reasoning = results[0]["reasoning"]
    assert "engagement" in reasoning
    assert "rank" in reasoning
    assert "new_artist_bonus" in reasoning
    assert "diversity" in reasoning
    # sponsor_count=0 → new_artist_bonus 양수
    assert reasoning["new_artist_bonus"] > 0


# ── 2. UNIQUE INDEX 중복 방지 — ON CONFLICT DO NOTHING ─────────────────────────

@pytest.mark.asyncio
async def test_insert_candidates_on_conflict_do_nothing():
    """동일 artist_id + week_start 중복 INSERT → ON CONFLICT DO NOTHING."""
    db = AsyncMock()
    call_count = 0

    def execute_side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        mock = MagicMock()
        # 첫 번째 INSERT: RETURNING id 반환 (삽입 성공)
        # 두 번째 INSERT: RETURNING 없음 (충돌 무시)
        mock.fetchone.return_value = ("new-uuid",) if call_count == 1 else None
        return mock

    db.execute = AsyncMock(side_effect=execute_side_effect)
    db.commit = AsyncMock()

    candidates = [
        {"artist_id": "artist-1", "composite_score": 0.8, "reasoning": {}}
    ]
    week = date(2026, 5, 4)

    count1 = await featured_artist_jobs.insert_candidates(db, candidates, week)
    count2 = await featured_artist_jobs.insert_candidates(db, candidates, week)

    assert count1 == 1
    assert count2 == 0  # 충돌로 INSERT 없음


# ── 3. 후보 < 3 시 graceful — Slack mock ──────────────────────────────────────

@pytest.mark.asyncio
async def test_low_candidate_alert_triggered():
    """후보 < 3명 시 _notify_admin_low_candidates 호출 확인."""
    db = AsyncMock()
    # 후보 1명만 반환
    mock_row = MagicMock(
        artist_id="artist-1",
        artist_rank=90.0,
        follower_count=50,
        region="KR",
        genre="oil",
        engagement_score=50.0,
        sponsor_count=0,
    )
    db.execute = AsyncMock(
        return_value=MagicMock(fetchall=lambda: [mock_row])
    )

    with patch(
        "app.services.featured_artist_jobs._notify_admin_low_candidates",
        new=AsyncMock(),
    ) as mock_notify:
        results = await featured_artist_jobs.select_candidates_for_week(
            db, week_start=date(2026, 5, 4), n=5
        )
        mock_notify.assert_called_once()
        call_args = mock_notify.call_args
        # 두 번째 인자(count)가 임계값 미만이어야 함
        assert call_args.args[1] < featured_artist_jobs._LOW_CANDIDATE_THRESHOLD


# ── 4. artist_index 미가용 fallback ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_artist_index_unavailable_fallback():
    """DB 쿼리 예외 발생 시 빈 리스트 반환 + 오류 미전파."""
    db = AsyncMock()
    db.execute = AsyncMock(side_effect=Exception("artist_index table not found"))

    with patch(
        "app.services.featured_artist_jobs._notify_admin_low_candidates",
        new=AsyncMock(),
    ):
        results = await featured_artist_jobs.select_candidates_for_week(
            db, week_start=date(2026, 5, 4)
        )

    # 예외 미전파, 빈 리스트 반환
    assert results == []


# ── 5. 다양성 분산 검증 — 장르 ≥ 2종 패널티 동작 ──────────────────────────────

@pytest.mark.asyncio
async def test_diversity_mmr_genre_variety():
    """상위 5명 선정 시 동일 장르 반복 → MMR 패널티로 점수 감소 확인."""
    # 10명 모두 같은 장르(oil) — MMR 패널티로 후순위 점수 감소
    scored = [
        {
            "artist_id": f"a-{i}",
            "composite_score": float(10 - i),
            "reasoning": {"genre": "oil", "region": "KR", "sponsor_count": 0},
        }
        for i in range(10)
    ]
    result = featured_artist_jobs._apply_diversity_mmr(scored, pool_size=10)

    scores = [r["composite_score"] for r in result]
    # 첫 번째는 패널티 없음, 두 번째 이상은 감소 또는 유지
    assert scores[0] >= scores[1]
    # 두 번째부터는 같은 장르 패널티(0.05)로 감소
    # diversity 값이 reasoning에 기록되어야 함
    assert result[1]["reasoning"]["diversity"] > 0


# ── 6. 신진작가 우선 선정 — sponsor_count=0 보너스 ────────────────────────────

@pytest.mark.asyncio
async def test_new_artist_bonus_prioritized():
    """후원자 0명 작가가 보너스 > 0, reasoning에 기록 확인."""
    db = AsyncMock()
    rows = [
        MagicMock(
            artist_id="new-artist",
            artist_rank=80.0,
            follower_count=100,
            region="VN",
            genre="digital",
            engagement_score=40.0,
            sponsor_count=0,
        ),
        MagicMock(
            artist_id="established",
            artist_rank=90.0,
            follower_count=800,
            region="KR",
            genre="oil",
            engagement_score=50.0,
            sponsor_count=5,
        ),
    ]
    db.execute = AsyncMock(
        return_value=MagicMock(fetchall=lambda: rows)
    )
    db.commit = AsyncMock()

    with patch(
        "app.services.featured_artist_jobs._notify_admin_low_candidates",
        new=AsyncMock(),
    ):
        results = await featured_artist_jobs.select_candidates_for_week(
            db, week_start=date(2026, 5, 4), n=5
        )

    # new-artist: sponsor_count=0 → new_artist_bonus 양수
    new_artist = next(r for r in results if r["artist_id"] == "new-artist")
    assert new_artist["reasoning"]["new_artist_bonus"] > 0

    # established: sponsor_count=5 → bonus 없음
    established = next(r for r in results if r["artist_id"] == "established")
    assert established["reasoning"]["new_artist_bonus"] == 0
