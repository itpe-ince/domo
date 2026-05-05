"""feed_scoring.py — A-3 feed-algorithm-v1 personalized feed scoring helpers.

Implements SQL + Python hybrid (B-tier) approach:
  Step 1: SQL fast-path — fetch candidate posts (followed + recent + trending)
  Step 2: Python in-memory score calculation + sort + cursor

Score formula per post:
    score = followed_weight + recency_weight + engagement_weight + trending_weight - own_post_penalty

    followed_weight:    0.5 if author in viewer's followings else 0.0
    recency_weight:     0.3 * exp(-hours_since_post / 24)   # 24h half-life
    engagement_weight:  0.15 * (likes + comments * 2 + bluebird_count * 5) / max(1, age_days)
    trending_weight:    0.05 * (like_count + comment_count * 2 + bluebird_count * 3)
                               / sqrt(max(1, age_hours))
    own_post_penalty:   -1.0 if author_id == viewer_id else 0.0

Weights are hardcoded (Phase 6 tuning carry-over). PostHog feature flag controls A/B split
at the API layer, not here.

G'-9 booster: compute_score accepts an optional ``cached_engagement_score`` parameter.
When provided (from post_engagement_cache), it replaces inline like/comment subquery
aggregation in engagement_weight. Cache miss → caller passes None → graceful degrade
to existing inline like_count/comment_count fields.

R-5 cron isolation: this module has no lifespan import / no DB connection.
All DB access goes through callers in posts.py.
"""
from __future__ import annotations

import math
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone


# ─── Weight constants ────────────────────────────────────────────────────────

FOLLOWED_WEIGHT = 0.5
RECENCY_WEIGHT = 0.3
RECENCY_HALF_LIFE_HOURS = 24.0
ENGAGEMENT_WEIGHT = 0.15
TRENDING_WEIGHT = 0.05
OWN_POST_PENALTY = 1.0  # subtracted


# ─── Data class ──────────────────────────────────────────────────────────────


@dataclass(slots=True)
class ScoredPost:
    """Thin wrapper attaching a computed score to a post object.

    ``post`` is the SQLAlchemy Post ORM instance (caller responsibility to
    load media + product via selectinload before passing here).
    ``score`` is the final float score — higher = shown earlier.
    ``recommendation_reason`` is one of 'following' | 'trending' | None.
    """
    post: object  # app.models.post.Post — avoided circular import
    score: float
    recommendation_reason: str | None


# ─── Score computation ───────────────────────────────────────────────────────


def compute_score(
    *,
    author_id: uuid.UUID,
    viewer_id: uuid.UUID | None,
    created_at: datetime,
    like_count: int,
    comment_count: int,
    bluebird_count: int,
    is_followed: bool,
    now: datetime | None = None,
    cached_engagement_score: float | None = None,
) -> float:
    """Compute personalized feed score for a single post.

    Pure function — no DB access. All inputs must be pre-fetched.

    Parameters
    ----------
    author_id:      Post author UUID.
    viewer_id:      Authenticated viewer UUID, or None for anonymous.
    created_at:     UTC-aware post creation timestamp.
    like_count:     Denormalised like counter from Post model.
    comment_count:  Denormalised comment counter from Post model.
    bluebird_count: Denormalised Blue Bird sponsorship counter from Post model.
    is_followed:    True when the viewer follows the post author.
    now:            UTC-aware current time (injected for testing; defaults to utcnow).
    cached_engagement_score:
        G'-9 booster — pre-computed engagement score from post_engagement_cache.
        When provided (not None), replaces inline like_count/comment_count aggregation
        in engagement_weight calculation. Graceful degrade: caller passes None when
        cache miss → falls back to inline like_count + comment_count * 2 + bluebird_count * 5.

    Returns
    -------
    float: composite score (higher = shown first).
    """
    if now is None:
        now = datetime.now(timezone.utc)

    # Ensure both datetimes are timezone-aware for subtraction
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)

    delta_seconds = (now - created_at).total_seconds()
    age_hours = max(0.0, delta_seconds / 3600.0)
    age_days = max(0.0, delta_seconds / 86400.0)

    # followed_weight
    fw = FOLLOWED_WEIGHT if is_followed else 0.0

    # recency_weight: exponential decay with 24h half-life
    rw = RECENCY_WEIGHT * math.exp(-age_hours / RECENCY_HALF_LIFE_HOURS)

    # engagement_weight: G'-9 — use cached score when available; inline fallback when None
    if cached_engagement_score is not None:
        # cache hit: cached_engagement_score is already weighted; normalize by age
        ew = ENGAGEMENT_WEIGHT * cached_engagement_score / max(1.0, age_days)
    else:
        # cache miss (graceful degrade): original inline aggregation
        engagement_raw = like_count + comment_count * 2 + bluebird_count * 5
        ew = ENGAGEMENT_WEIGHT * engagement_raw / max(1.0, age_days)

    # trending_weight: inverse-sqrt of age (Wilson-score inspired)
    # Always uses inline counts (trending uses model counters, not 24h cache)
    trending_raw = like_count + comment_count * 2 + bluebird_count * 3
    tw = TRENDING_WEIGHT * trending_raw / math.sqrt(max(1.0, age_hours))

    # own_post_penalty
    penalty = OWN_POST_PENALTY if (viewer_id is not None and author_id == viewer_id) else 0.0

    return fw + rw + ew + tw - penalty


# ─── Batch scoring ───────────────────────────────────────────────────────────


def score_posts(
    posts: list,
    viewer_id: uuid.UUID | None,
    followee_ids: set[uuid.UUID],
    now: datetime | None = None,
    engagement_cache: dict | None = None,
) -> list[ScoredPost]:
    """Score and sort a list of Post ORM instances.

    Parameters
    ----------
    posts:            List of app.models.post.Post ORM instances.
    viewer_id:        Authenticated viewer UUID, or None.
    followee_ids:     Set of UUIDs that the viewer follows.
    now:              UTC-aware current time (injected for testing).
    engagement_cache: G'-9 booster — optional dict mapping post_id (UUID or str)
                      to pre-computed engagement_score from post_engagement_cache.
                      When provided, hit posts use cached score; miss posts fall back
                      to inline aggregation. Pass None to disable (original behaviour).

    Returns
    -------
    List of ScoredPost sorted by score DESC (highest score first).
    """
    if now is None:
        now = datetime.now(timezone.utc)

    scored: list[ScoredPost] = []
    for post in posts:
        is_followed = post.author_id in followee_ids  # type: ignore[attr-defined]

        # G'-9: look up cached engagement score (cache hit → use cache; miss → None → inline)
        cached_score: float | None = None
        if engagement_cache is not None:
            pid = post.id  # type: ignore[attr-defined]
            # Accept both UUID and str keys
            cached_score = engagement_cache.get(pid) or engagement_cache.get(str(pid))

        score = compute_score(
            author_id=post.author_id,  # type: ignore[attr-defined]
            viewer_id=viewer_id,
            created_at=post.created_at,  # type: ignore[attr-defined]
            like_count=post.like_count or 0,  # type: ignore[attr-defined]
            comment_count=post.comment_count or 0,  # type: ignore[attr-defined]
            bluebird_count=post.bluebird_count or 0,  # type: ignore[attr-defined]
            is_followed=is_followed,
            now=now,
            cached_engagement_score=cached_score,
        )
        reason: str | None
        if is_followed:
            reason = "following"
        elif score > 0:
            reason = "trending"
        else:
            reason = None

        scored.append(ScoredPost(post=post, score=score, recommendation_reason=reason))

    scored.sort(key=lambda s: s.score, reverse=True)
    return scored


# ─── Cursor encoding / decoding ───────────────────────────────────────────────


def encode_cursor(score: float, post_id: uuid.UUID) -> str:
    """Encode a composite (score, post_id) cursor for pagination.

    Format: ``{score_hex}:{post_id}``
    score_hex uses IEEE 754 double hex repr to avoid float formatting ambiguity.
    """
    score_hex = score.hex()
    return f"{score_hex}:{post_id}"


def decode_cursor(cursor: str) -> tuple[float, uuid.UUID] | None:
    """Decode a cursor string into (score, post_id).

    Returns None on any parse error (caller falls back to no cursor).
    """
    try:
        score_part, id_part = cursor.split(":", 1)
        score = float.fromhex(score_part)
        post_id = uuid.UUID(id_part)
        return score, post_id
    except (ValueError, AttributeError):
        return None


# ─── Slice with cursor ────────────────────────────────────────────────────────


def apply_cursor(
    scored: list[ScoredPost],
    cursor_score: float,
    cursor_id: uuid.UUID,
) -> list[ScoredPost]:
    """Return items after the cursor position (exclusive).

    Items are considered "after" the cursor when:
      - score < cursor_score, OR
      - score == cursor_score AND post_id < cursor_id (UUID lexicographic)

    This is consistent with the ordering produced by score_posts().
    """
    result = []
    for s in scored:
        post_id: uuid.UUID = s.post.id  # type: ignore[attr-defined]
        if s.score < cursor_score:
            result.append(s)
        elif s.score == cursor_score and post_id < cursor_id:
            result.append(s)
    return result
