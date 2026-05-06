"""Unit tests — diversity_reranking.py (Phase 10 K-2).

테스트 항목:
  1. 신진작가 부스트 적용 (mock artist_index_rank=85% → score × 1.20)
  2. 장르 quota (top-20 ≥ 3 unique genres 강제)
  3. 지역 quota (top-20 ≥ 2 unique regions 강제)
  4. 부스트 + quota 통합 안정성
  5. 후보 < top_k_window 시 graceful (모든 후보 반환)
  6. artist_index 미가용 시 quota만 적용 + WARNING
  7. rerank 후보 없음 시 빈 리스트 반환
  8. 신진작가 판별 — rank/total > 0.80 → True
  9. 신진작가 판별 — rank/total ≤ 0.80 → False
  10. 신진작가 판별 — rank=None → False (부스트 skip)
  11. 신진작가 판별 — total_artists=0 → False (division by zero 방지)
"""
from __future__ import annotations

import pytest

from app.services.diversity_reranking import (
    DiversityConfig,
    PostMeta,
    _is_emerging_artist,
    rerank,
)


# ── 신진작가 판별 ──────────────────────────────────────────────────────────────

def test_is_emerging_artist_true():
    """rank/total > 0.80 → 신진작가."""
    meta = PostMeta(
        post_id="p1", genre="oil", author_id="a1",
        author_country_code="KR",
        artist_index_rank=850, artist_index_total=1000,
    )
    assert _is_emerging_artist(meta, total_artists=1000) is True


def test_is_emerging_artist_false_top_artist():
    """rank/total ≤ 0.80 → 신진작가 아님."""
    meta = PostMeta(
        post_id="p1", genre="oil", author_id="a1",
        author_country_code="KR",
        artist_index_rank=100, artist_index_total=1000,
    )
    assert _is_emerging_artist(meta, total_artists=1000) is False


def test_is_emerging_artist_null_rank():
    """artist_index_rank=None → 신진작가 아님 (부스트 skip)."""
    meta = PostMeta(
        post_id="p1", genre="oil", author_id="a1",
        author_country_code="KR",
        artist_index_rank=None, artist_index_total=1000,
    )
    assert _is_emerging_artist(meta, total_artists=1000) is False


def test_is_emerging_artist_zero_total():
    """total_artists=0 → 신진작가 아님 (division by zero 방지)."""
    meta = PostMeta(
        post_id="p1", genre="oil", author_id="a1",
        author_country_code="KR",
        artist_index_rank=50, artist_index_total=0,
    )
    assert _is_emerging_artist(meta, total_artists=0) is False


# ── 신진작가 부스팅 적용 ────────────────────────────────────────────────────────

def test_rerank_applies_emerging_boost():
    """신진작가 post → score × 1.20 적용 후 상위 노출."""
    config = DiversityConfig(
        emerging_artist_boost=1.20,
        genre_min_diversity=1,   # 장르 제약 최소화
        region_min_diversity=1,  # 지역 제약 최소화
        top_k_window=3,
        candidate_pool_size=10,
    )
    # emerging artist (rank=900/1000 > 80%)의 post는 boost 후 상위 이동
    # 후보 수 > top_k_window 가 되도록 추가 candidate 포함 (early return 방지)
    meta = {
        "post-emerging": PostMeta("post-emerging", "oil", "a1", "KR", 900, 1000),
        "post-top":      PostMeta("post-top", "watercolor", "a2", "US", 50, 1000),
        "post-mid":      PostMeta("post-mid", "digital", "a3", "VN", 400, 1000),
        "post-extra":    PostMeta("post-extra", "ink", "a4", "JP", 200, 1000),
    }
    candidates = [
        ("post-top",      10.0),   # 상위 아티스트, score 높음
        ("post-emerging",  8.5),   # 신진작가: boost 적용 → 8.5 × 1.20 = 10.2
        ("post-mid",       7.0),
        ("post-extra",     6.0),  # extra candidate to exceed top_k_window
    ]
    result = rerank(candidates, meta, config)

    # post-emerging(score 10.2) > post-top(10.0) → 신진작가가 1위
    assert result[0] == "post-emerging", f"Expected post-emerging at [0], got: {result}"


# ── 장르 quota ─────────────────────────────────────────────────────────────────

def test_rerank_genre_quota_top20():
    """top-K 내 unique genres ≥ 3 보장."""
    config = DiversityConfig(
        emerging_artist_boost=1.0,  # 부스팅 없음 (신진작가 무시)
        genre_min_diversity=3,
        region_min_diversity=1,
        top_k_window=6,
        candidate_pool_size=20,
    )
    # 후보: oil 4개(높은 score), watercolor 2개, digital 2개
    meta = {}
    candidates = []
    for i in range(4):
        pid = f"oil-{i}"
        meta[pid] = PostMeta(pid, "oil", f"a{i}", "KR", None, 0)
        candidates.append((pid, 10.0 - i))
    for i in range(2):
        pid = f"wc-{i}"
        meta[pid] = PostMeta(pid, "watercolor", f"b{i}", "JP", None, 0)
        candidates.append((pid, 5.0 - i))
    for i in range(2):
        pid = f"dig-{i}"
        meta[pid] = PostMeta(pid, "digital", f"c{i}", "US", None, 0)
        candidates.append((pid, 3.0 - i))

    result = rerank(candidates, meta, config)

    selected_genres = [meta[pid].genre for pid in result if pid in meta]
    assert len(set(selected_genres)) >= 3, f"genres: {set(selected_genres)}"


# ── 지역 quota ─────────────────────────────────────────────────────────────────

def test_rerank_region_quota_top20():
    """top-K 내 unique regions ≥ 2 보장."""
    config = DiversityConfig(
        emerging_artist_boost=1.0,
        genre_min_diversity=1,
        region_min_diversity=2,
        top_k_window=6,
        candidate_pool_size=20,
    )
    # 후보: KR 작가 5명 + VN 작가 2명
    meta = {}
    candidates = []
    for i in range(5):
        pid = f"kr-{i}"
        meta[pid] = PostMeta(pid, "oil", f"a{i}", "KR", None, 0)
        candidates.append((pid, 10.0 - i))
    for i in range(2):
        pid = f"vn-{i}"
        meta[pid] = PostMeta(pid, "watercolor", f"b{i}", "VN", None, 0)
        candidates.append((pid, 3.0 - i))

    result = rerank(candidates, meta, config)

    selected_regions = [meta[pid].author_country_code for pid in result if pid in meta]
    assert len(set(selected_regions)) >= 2, f"regions: {set(selected_regions)}"


# ── 부스팅 + quota 통합 안정성 ─────────────────────────────────────────────────

def test_rerank_boost_and_quota_combined():
    """부스팅 + quota 동시 적용 시 top-K 내 다양성 + 신진작가 보장."""
    config = DiversityConfig(
        emerging_artist_boost=1.20,
        genre_min_diversity=3,
        region_min_diversity=2,
        top_k_window=5,
        candidate_pool_size=20,
    )
    meta = {
        "p1": PostMeta("p1", "oil",       "a1", "KR", 900, 1000),  # emerging
        "p2": PostMeta("p2", "oil",       "a2", "KR", 50, 1000),   # top artist
        "p3": PostMeta("p3", "watercolor","a3", "VN", 850, 1000),  # emerging
        "p4": PostMeta("p4", "digital",   "a4", "US", 10, 1000),   # top artist
        "p5": PostMeta("p5", "oil",       "a5", "JP", 920, 1000),  # emerging
        "p6": PostMeta("p6", "sketch",    "a6", "KR", 600, 1000),  # mid
    }
    candidates = [
        ("p2", 10.0), ("p4", 9.0), ("p1", 8.0),
        ("p3", 7.0), ("p5", 6.0), ("p6", 5.0),
    ]
    result = rerank(candidates, meta, config)

    assert len(result) == 5
    selected_genres = {meta[pid].genre for pid in result}
    selected_regions = {meta[pid].author_country_code for pid in result}
    assert len(selected_genres) >= 3, f"genres: {selected_genres}"
    assert len(selected_regions) >= 2, f"regions: {selected_regions}"


# ── 후보 < top_k_window graceful ───────────────────────────────────────────────

def test_rerank_fewer_candidates_than_window():
    """후보 수 < top_k_window → 전체 후보 그대로 반환."""
    config = DiversityConfig(top_k_window=20, candidate_pool_size=100)
    meta = {"p1": PostMeta("p1", "oil", "a1", "KR", None, 0)}
    candidates = [("p1", 5.0)]

    result = rerank(candidates, meta, config)
    assert result == ["p1"]


def test_rerank_empty_candidates():
    """후보 없음 → 빈 리스트 반환."""
    config = DiversityConfig()
    result = rerank([], {}, config)
    assert result == []


# ── artist_index 미가용 시 quota만 적용 ────────────────────────────────────────

def test_rerank_no_artist_index_quota_only():
    """artist_index_rank=None → 부스트 skip, quota-based 정렬은 정상 동작."""
    config = DiversityConfig(
        emerging_artist_boost=1.20,
        genre_min_diversity=2,
        region_min_diversity=2,
        top_k_window=4,
        candidate_pool_size=10,
    )
    meta = {
        "p1": PostMeta("p1", "oil",       "a1", "KR", None, 0),
        "p2": PostMeta("p2", "oil",       "a2", "KR", None, 0),
        "p3": PostMeta("p3", "watercolor","a3", "VN", None, 0),
        "p4": PostMeta("p4", "digital",   "a4", "US", None, 0),
        "p5": PostMeta("p5", "oil",       "a5", "KR", None, 0),
    }
    candidates = [
        ("p1", 10.0), ("p2", 9.0), ("p3", 8.0), ("p4", 7.0), ("p5", 6.0),
    ]
    result = rerank(candidates, meta, config)

    # 부스트 없이 quota만: genre/region 다양성 충족 확인
    assert len(result) == 4
    selected_genres = {meta[pid].genre for pid in result}
    selected_regions = {meta[pid].author_country_code for pid in result}
    assert len(selected_genres) >= 2, f"genres: {selected_genres}"
    assert len(selected_regions) >= 2, f"regions: {selected_regions}"


def test_rerank_no_metadata_graceful():
    """post_metadata 전혀 없음(빈 dict) → 부스트 skip + quota는 'unknown'으로 처리."""
    config = DiversityConfig(
        emerging_artist_boost=1.20,
        genre_min_diversity=1,
        region_min_diversity=1,
        top_k_window=3,
        candidate_pool_size=10,
    )
    candidates = [("p1", 10.0), ("p2", 9.0), ("p3", 8.0), ("p4", 7.0)]
    result = rerank(candidates, {}, config)

    # 메타데이터 없어도 3개 반환 (graceful)
    assert len(result) == 3
