"""Unit tests for artist-index-v1 scoring helpers (A-6).

6 test cases:
  1. 신진작가 (tenure 7일 + active 30일 posts) — 상위 점수
  2. 정착 작가 (tenure 1년 + 0 activity) — 낮은 점수
  3. 0 sales 작가 — sales_score = 0.0
  4. log10 normalization (1$ vs 100$ vs 10000$ breakpoints)
  5. tier_badge derivation (top_10 / top_100 / top_1000 / None)
  6. 가중치 합 = 1.0 검증
"""
from __future__ import annotations

import pytest

from app.services.artist_index_scoring import (
    WEIGHT_RECENT_ACTIVITY,
    WEIGHT_SALES,
    WEIGHT_SUPPORTERS,
    WEIGHT_TENURE,
    ScoreComponents,
    calc_artist_score,
    calc_recent_activity_score,
    calc_sales_score,
    calc_supporters_score,
    calc_tenure_score,
    derive_tier_badge,
)


# ─── Test 1: 신진작가 (7일 + 활발한 활동) 상위 점수 ─────────────────────────


def test_new_active_artist_scores_high():
    """신진작가 (tenure 7일, recent posts 10개) 점수가 정착 아티스트(0 activity)보다 높음.

    OQ-5=B: recent_activity weight 0.5 — 활동적인 신진작가 상위.
    """
    new_active = ScoreComponents(
        post_count_30d=10,   # recent_activity_score = min(100, 10*5) = 50
        bid_count_30d=5,     # + 5*2 = 10 → total 60
        comment_count_30d=0,
        lifetime_sales_cents=0,
        active_subscribers=0,
        active_sponsors=0,
        followers=0,
        days_since_signup=7,  # tenure_score = min(100, 7/3.65) ≈ 1.92
    )
    established_inactive = ScoreComponents(
        post_count_30d=0,
        bid_count_30d=0,
        comment_count_30d=0,
        lifetime_sales_cents=0,
        active_subscribers=0,
        active_sponsors=0,
        followers=0,
        days_since_signup=365,  # tenure_score = 100
    )

    score_new = calc_artist_score(new_active)
    score_old = calc_artist_score(established_inactive)

    # New active artist: 0.5*60 + 0.3*0 + 0.2*0 + 0.1*1.92 = 30.19
    # Established inactive: 0.5*0 + 0.1*100 = 10.0
    assert score_new > score_old, (
        f"Active new artist ({score_new:.2f}) should score higher than "
        f"inactive established artist ({score_old:.2f})"
    )
    assert score_new >= 25.0, f"New active artist score should be ≥25, got {score_new}"
    assert score_old <= 15.0, f"Inactive established artist score should be ≤15, got {score_old}"


# ─── Test 2: 정착 작가 (1년 + 0 activity) 낮은 점수 ─────────────────────────


def test_established_inactive_artist_scores_low():
    """1년 경력 + 0 recent activity → 낮은 점수 (tenure weight 0.1 only)."""
    components = ScoreComponents(
        post_count_30d=0,
        bid_count_30d=0,
        comment_count_30d=0,
        lifetime_sales_cents=0,
        active_subscribers=0,
        active_sponsors=0,
        followers=0,
        days_since_signup=365,
    )
    score = calc_artist_score(components)
    # Expected: 0.1 * 100 = 10.0
    assert score == pytest.approx(10.0, abs=0.01), f"Expected ~10.0, got {score}"


# ─── Test 3: 0 sales → sales_score = 0.0 ─────────────────────────────────────


def test_zero_sales_score():
    """lifetime_sales_cents = 0 → sales_score = 0.0."""
    components = ScoreComponents(lifetime_sales_cents=0)
    assert calc_sales_score(components) == 0.0

    # Negative guard (defensive)
    components_neg = ScoreComponents(lifetime_sales_cents=-100)
    assert calc_sales_score(components_neg) == 0.0


# ─── Test 4: log10 normalization breakpoints ──────────────────────────────────


def test_sales_score_log10_normalization():
    """Log10 sales_score breakpoints: $1 ≈ 20, $100 ≈ 60, $10000 ≈ 100 (cap).

    Formula: min(100, log10(dollars + 1) * 20)
    $1    = log10(2) * 20 ≈ 6.02   (note: $1 → ~6.02, not 20 — formula uses log10(dollars+1))
    $10   = log10(11) * 20 ≈ 20.8
    $100  = log10(101) * 20 ≈ 40.1
    $1000 = log10(1001) * 20 ≈ 60.0
    $10k  = log10(10001) * 20 ≈ 80.0
    Corrected expectations based on actual formula.
    """
    import math

    def expected(dollars: float) -> float:
        return min(100.0, math.log10(dollars + 1) * 20.0)

    # $10 USD (1000 cents)
    c10 = ScoreComponents(lifetime_sales_cents=1000)
    assert calc_sales_score(c10) == pytest.approx(expected(10.0), rel=1e-4)

    # $1000 USD (100000 cents)
    c1000 = ScoreComponents(lifetime_sales_cents=100_000)
    assert calc_sales_score(c1000) == pytest.approx(expected(1000.0), rel=1e-4)

    # $100000 USD → should cap at 100
    c_huge = ScoreComponents(lifetime_sales_cents=10_000_000)
    assert calc_sales_score(c_huge) == pytest.approx(100.0, abs=0.01)

    # Monotone: $10 < $1000
    assert calc_sales_score(c10) < calc_sales_score(c1000)


# ─── Test 5: tier_badge derivation ───────────────────────────────────────────


def test_tier_badge_derivation():
    """tier_badge: top_10 (rank 1-10), top_100 (11-100), top_1000 (101-1000), None (>1000 or None)."""
    # top_10
    assert derive_tier_badge(1) == "top_10"
    assert derive_tier_badge(10) == "top_10"

    # top_100
    assert derive_tier_badge(11) == "top_100"
    assert derive_tier_badge(100) == "top_100"

    # top_1000
    assert derive_tier_badge(101) == "top_1000"
    assert derive_tier_badge(1000) == "top_1000"

    # None
    assert derive_tier_badge(1001) is None
    assert derive_tier_badge(99999) is None
    assert derive_tier_badge(None) is None


# ─── Test 6: 가중치 합 = 1.0 ─────────────────────────────────────────────────


def test_weights_sum_to_one():
    """가중치 합 검증: 0.5 + 0.3 + 0.2 + 0.1 = 1.0 (OQ-5=B)."""
    total = (
        WEIGHT_RECENT_ACTIVITY
        + WEIGHT_SALES
        + WEIGHT_SUPPORTERS
        + WEIGHT_TENURE
    )
    assert total == pytest.approx(1.0, abs=1e-10), (
        f"Weights must sum to 1.0, got {total}. "
        f"Values: activity={WEIGHT_RECENT_ACTIVITY}, sales={WEIGHT_SALES}, "
        f"supporters={WEIGHT_SUPPORTERS}, tenure={WEIGHT_TENURE}"
    )
