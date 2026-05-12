"""Unit tests for app.services.feed_scoring — A-3 feed-algorithm-v1.

5 tests:
  1. Score calculation accuracy — followed author + 24h-old post
  2. Own post penalty
  3. Recency decay — older posts score lower
  4. Trending boost — high engagement elevates score
  5. Cursor pagination — encode / decode / apply
"""
from __future__ import annotations

import math
import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from app.services.feed_scoring import (
    FOLLOWED_WEIGHT,
    OWN_POST_PENALTY,
    RECENCY_WEIGHT,
    apply_cursor,
    compute_score,
    decode_cursor,
    encode_cursor,
    score_posts,
    ScoredPost,
)


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _make_post(
    *,
    author_id: uuid.UUID | None = None,
    hours_old: float = 1.0,
    like_count: int = 0,
    comment_count: int = 0,
    bluebird_count: int = 0,
) -> SimpleNamespace:
    """Return a minimal fake Post (SimpleNamespace) with the fields scored."""
    now = datetime.now(timezone.utc)
    return SimpleNamespace(
        id=uuid.uuid4(),
        author_id=author_id or uuid.uuid4(),
        created_at=now - timedelta(hours=hours_old),
        like_count=like_count,
        comment_count=comment_count,
        bluebird_count=bluebird_count,
    )


# ─── Test 1: score accuracy — followed author, post 24h old ─────────────────


def test_score_followed_author_24h():
    viewer_id = uuid.uuid4()
    author_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    created_at = now - timedelta(hours=24)

    score = compute_score(
        author_id=author_id,
        viewer_id=viewer_id,
        created_at=created_at,
        like_count=0,
        comment_count=0,
        bluebird_count=0,
        is_followed=True,
        now=now,
    )

    # followed_weight + recency at 24h
    expected_followed = FOLLOWED_WEIGHT  # 0.5
    expected_recency = RECENCY_WEIGHT * math.exp(-24.0 / 24.0)  # 0.3 * e^{-1}
    expected_base = expected_followed + expected_recency

    assert score == pytest.approx(expected_base, rel=1e-6)
    assert score > 0


# ─── Test 2: own post penalty ────────────────────────────────────────────────


def test_own_post_penalty():
    viewer_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    created_at = now - timedelta(hours=1)

    score_own = compute_score(
        author_id=viewer_id,  # author == viewer → penalty
        viewer_id=viewer_id,
        created_at=created_at,
        like_count=0,
        comment_count=0,
        bluebird_count=0,
        is_followed=False,
        now=now,
    )
    score_other = compute_score(
        author_id=uuid.uuid4(),
        viewer_id=viewer_id,
        created_at=created_at,
        like_count=0,
        comment_count=0,
        bluebird_count=0,
        is_followed=False,
        now=now,
    )

    # Own post should score -OWN_POST_PENALTY lower than otherwise identical post
    assert score_own == pytest.approx(score_other - OWN_POST_PENALTY, rel=1e-6)
    # Own post score is negative (low engagement, early age, penalty applied)
    assert score_own < score_other


# ─── Test 3: recency decay — older posts score lower ─────────────────────────


def test_recency_decay():
    viewer_id = uuid.uuid4()
    author_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    score_1h = compute_score(
        author_id=author_id,
        viewer_id=viewer_id,
        created_at=now - timedelta(hours=1),
        like_count=0,
        comment_count=0,
        bluebird_count=0,
        is_followed=False,
        now=now,
    )
    score_48h = compute_score(
        author_id=author_id,
        viewer_id=viewer_id,
        created_at=now - timedelta(hours=48),
        like_count=0,
        comment_count=0,
        bluebird_count=0,
        is_followed=False,
        now=now,
    )
    score_168h = compute_score(
        author_id=author_id,
        viewer_id=viewer_id,
        created_at=now - timedelta(hours=168),
        like_count=0,
        comment_count=0,
        bluebird_count=0,
        is_followed=False,
        now=now,
    )

    # Scores should monotonically decrease as post age increases
    assert score_1h > score_48h > score_168h


# ─── Test 4: trending boost — high engagement elevates score ─────────────────


def test_trending_boost_high_engagement():
    viewer_id = uuid.uuid4()
    author_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    created_at = now - timedelta(hours=6)

    score_low = compute_score(
        author_id=author_id,
        viewer_id=viewer_id,
        created_at=created_at,
        like_count=0,
        comment_count=0,
        bluebird_count=0,
        is_followed=False,
        now=now,
    )
    score_high = compute_score(
        author_id=author_id,
        viewer_id=viewer_id,
        created_at=created_at,
        like_count=100,
        comment_count=50,
        bluebird_count=10,
        is_followed=False,
        now=now,
    )

    assert score_high > score_low
    # High engagement should be substantially boosted
    assert score_high > score_low + 1.0


# ─── Test 5: cursor pagination — encode / decode / apply ─────────────────────


def test_cursor_pagination():
    viewer_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    # Build 5 posts with decreasing ages so scores differ
    posts = [
        _make_post(hours_old=float(i + 1), like_count=max(0, 10 - i))
        for i in range(5)
    ]
    followee_ids: set[uuid.UUID] = set()  # no follows → scores based on recency+engagement

    scored = score_posts(posts=posts, viewer_id=viewer_id, followee_ids=followee_ids, now=now)

    # Scores must be in descending order
    scores = [s.score for s in scored]
    assert scores == sorted(scores, reverse=True)

    # Simulate page 1: take first 2
    page1 = scored[:2]
    last = page1[-1]
    cursor = encode_cursor(last.score, last.post.id)

    # Decode round-trip
    decoded = decode_cursor(cursor)
    assert decoded is not None
    cursor_score, cursor_id = decoded
    assert cursor_score == pytest.approx(last.score, rel=1e-9)
    assert cursor_id == last.post.id

    # Apply cursor → should return items after last of page 1
    page2 = apply_cursor(scored, cursor_score, cursor_id)
    assert len(page2) == len(scored) - 2
    # All page2 scores must be <= cursor_score
    for s in page2:
        assert s.score <= cursor_score + 1e-10

    # No overlap between page1 and page2
    page1_ids = {s.post.id for s in page1}
    page2_ids = {s.post.id for s in page2}
    assert page1_ids.isdisjoint(page2_ids)


# ─── Test 6 (bonus): invalid cursor gracefully returns None ──────────────────


def test_decode_cursor_invalid():
    assert decode_cursor("") is None
    assert decode_cursor("notvalid") is None
    assert decode_cursor("0x1p+0:not-a-uuid") is None
