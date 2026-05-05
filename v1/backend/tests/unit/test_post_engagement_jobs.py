"""Unit tests for G'-9 post-engagement-cache helpers.

4 test cases:
  1. empty posts → compute_engagement_score with 0 inputs → 0.0
  2. active posts engagement_score 계산 정확도 — weighted formula
  3. UPSERT idempotent — calling compute_engagement_score twice yields same result
  4. cache lookup feed_scoring 보강 — graceful degrade when cache=None vs cache hit
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from app.services.post_engagement_jobs import (
    WEIGHT_LIKES,
    WEIGHT_COMMENTS,
    WEIGHT_BOOKMARKS,
    WEIGHT_BIDS,
    WEIGHT_SHARES,
    compute_engagement_score,
)
from app.services.feed_scoring import compute_score


# ─── Test 1: empty inputs → score = 0.0 ──────────────────────────────────────


def test_empty_engagement_score_is_zero():
    """Zero counts → engagement_score = 0.0 (no-op for empty posts)."""
    score = compute_engagement_score(
        like_count=0,
        comment_count=0,
        bookmark_count=0,
        bid_count=0,
        share_count=0,
    )
    assert score == 0.0, f"Expected 0.0, got {score}"


# ─── Test 2: engagement_score 계산 정확도 ────────────────────────────────────


def test_engagement_score_formula_accuracy():
    """Verify weighted formula: likes×1 + comments×2 + bookmarks×1.5 + bids×5 + shares×3.

    Test case: likes=10, comments=5, bookmarks=3, bids=1, shares=2
    Expected: 10×1 + 5×2 + 3×1.5 + 1×5 + 2×3 = 10 + 10 + 4.5 + 5 + 6 = 35.5
    """
    score = compute_engagement_score(
        like_count=10,
        comment_count=5,
        bookmark_count=3,
        bid_count=1,
        share_count=2,
    )
    expected = (
        10 * WEIGHT_LIKES
        + 5 * WEIGHT_COMMENTS
        + 3 * WEIGHT_BOOKMARKS
        + 1 * WEIGHT_BIDS
        + 2 * WEIGHT_SHARES
    )
    assert score == pytest.approx(expected, abs=1e-6), (
        f"Expected {expected:.4f}, got {score:.4f}"
    )
    assert score == pytest.approx(35.5, abs=1e-6), (
        f"Expected 35.5 for canonical test case, got {score}"
    )


def test_engagement_score_bid_dominance():
    """bids (weight 5) should dominate when bid_count is high.

    1 bid (5 pts) > 4 likes (4 pts): score with 1 bid > score with 4 likes only.
    """
    score_bid = compute_engagement_score(0, 0, 0, 1, 0)
    score_likes = compute_engagement_score(4, 0, 0, 0, 0)
    assert score_bid > score_likes, (
        f"1 bid ({score_bid}) should score higher than 4 likes ({score_likes})"
    )


def test_engagement_score_share_weight():
    """shares (weight 3) > comments (weight 2) for same count."""
    score_shares = compute_engagement_score(0, 0, 0, 0, 1)   # 1 share = 3 pts
    score_comments = compute_engagement_score(0, 1, 0, 0, 0)  # 1 comment = 2 pts
    assert score_shares > score_comments


# ─── Test 3: UPSERT idempotent ───────────────────────────────────────────────


def test_engagement_score_idempotent():
    """Same inputs → same output every time (idempotency of pure function)."""
    kwargs = dict(
        like_count=7, comment_count=3, bookmark_count=2, bid_count=0, share_count=1
    )
    score_first = compute_engagement_score(**kwargs)
    score_second = compute_engagement_score(**kwargs)
    score_third = compute_engagement_score(**kwargs)

    assert score_first == score_second == score_third, (
        "compute_engagement_score must be deterministic (UPSERT-safe)"
    )

    # Verify the value is also correct
    expected = 7 * 1.0 + 3 * 2.0 + 2 * 1.5 + 0 * 5.0 + 1 * 3.0
    assert score_first == pytest.approx(expected, abs=1e-6)


# ─── Test 4: feed_scoring graceful degrade ───────────────────────────────────


def test_feed_scoring_cache_lookup_graceful_degrade():
    """G'-9 booster: cached_engagement_score=None → inline fallback (unchanged behaviour).

    cache hit (cached_engagement_score=X) → uses X for engagement_weight.
    cache miss (cached_engagement_score=None) → uses inline like_count+comment_count*2+...

    Both code paths must produce finite scores and not raise exceptions.
    """
    author_id = uuid.uuid4()
    viewer_id = uuid.uuid4()
    now = datetime(2026, 5, 4, 12, 0, 0, tzinfo=timezone.utc)
    created_at = datetime(2026, 5, 4, 6, 0, 0, tzinfo=timezone.utc)  # 6 hours ago

    base_kwargs = dict(
        author_id=author_id,
        viewer_id=viewer_id,
        created_at=created_at,
        like_count=5,
        comment_count=3,
        bluebird_count=1,
        is_followed=True,
        now=now,
    )

    # Cache miss (None) → inline fallback
    score_no_cache = compute_score(**base_kwargs, cached_engagement_score=None)
    assert isinstance(score_no_cache, float)
    assert score_no_cache > 0  # followed + recency + engagement > 0

    # Cache hit with a high engagement score → engagement_weight boosted
    score_cache_hit = compute_score(**base_kwargs, cached_engagement_score=50.0)
    assert isinstance(score_cache_hit, float)
    assert score_cache_hit > 0

    # Cache hit with 0 → inline lower score (more engagement than 0)
    score_cache_zero = compute_score(**base_kwargs, cached_engagement_score=0.0)
    assert isinstance(score_cache_zero, float)

    # High cache score should produce higher engagement component than 0 cache score
    assert score_cache_hit > score_cache_zero, (
        "Higher cached_engagement_score should produce higher overall score"
    )


def test_feed_scoring_cache_miss_matches_original():
    """When cached_engagement_score=None, compute_score output is identical to no-cache call.

    This verifies the graceful degrade path doesn't change existing behaviour.
    """
    author_id = uuid.uuid4()
    viewer_id = uuid.uuid4()
    now = datetime(2026, 5, 4, 12, 0, 0, tzinfo=timezone.utc)
    created_at = datetime(2026, 5, 3, 18, 0, 0, tzinfo=timezone.utc)  # 18 hours ago

    common = dict(
        author_id=author_id,
        viewer_id=viewer_id,
        created_at=created_at,
        like_count=8,
        comment_count=2,
        bluebird_count=0,
        is_followed=False,
        now=now,
    )

    # Without the new parameter (original call signature)
    score_original = compute_score(**common)
    # With explicit None (graceful degrade path)
    score_none = compute_score(**common, cached_engagement_score=None)

    assert score_original == pytest.approx(score_none, abs=1e-10), (
        f"cache miss must equal original: {score_original} vs {score_none}"
    )
