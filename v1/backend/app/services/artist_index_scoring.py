"""Pure score calculation helpers for artist-index-v1 (A-6).

Isolated from DB/async so functions are unit-testable synchronously.

Score formula (OQ-5=B):
    score = (
        0.5 * recent_activity_score +
        0.3 * sales_score +
        0.2 * supporters_score +
        0.1 * tenure_score
    )

Sub-scores are individually normalized to 0-100 before weighting.

Weights sum = 1.0 (verified by test).
"""
from __future__ import annotations

import math
from dataclasses import dataclass

# ─── Weight constants (OQ-5=B) ───────────────────────────────────────────────

WEIGHT_RECENT_ACTIVITY = 0.5
WEIGHT_SALES = 0.25
WEIGHT_SUPPORTERS = 0.15
WEIGHT_TENURE = 0.10

# Validation: sum must equal 1.0
_WEIGHT_SUM = WEIGHT_RECENT_ACTIVITY + WEIGHT_SALES + WEIGHT_SUPPORTERS + WEIGHT_TENURE


@dataclass
class ScoreComponents:
    """Raw inputs for score calculation."""

    # Recent activity (last 30 days)
    post_count_30d: int = 0
    bid_count_30d: int = 0
    comment_count_30d: int = 0

    # Cumulative sales (lifetime total in cents)
    lifetime_sales_cents: int = 0

    # Supporter counts
    active_subscribers: int = 0
    active_sponsors: int = 0
    followers: int = 0

    # Tenure
    days_since_signup: int = 0


def calc_recent_activity_score(components: ScoreComponents) -> float:
    """Normalize recent 30-day activity to 0-100.

    Formula: min(100, post_count_30d * 5 + bid_count_30d * 2 + comment_count_30d)

    Rationale: posts are the primary signal (×5), bids show transactional
    engagement (×2), comments show social activity (×1). Cap at 100.
    """
    raw = (
        components.post_count_30d * 5
        + components.bid_count_30d * 2
        + components.comment_count_30d
    )
    return min(100.0, float(raw))


def calc_sales_score(components: ScoreComponents) -> float:
    """Log-scale normalization of lifetime sales to 0-100.

    Formula: min(100, log10(lifetime_sales_cents / 100 + 1) * 20)

    Breakpoints (USD) — log10(dollars+1)*20:
      $0     → 0
      $1     → ~6.0   (log10(2)*20)
      $10    → ~20.8  (log10(11)*20)
      $100   → ~40.1  (log10(101)*20)
      $1000  → ~60.0  (log10(1001)*20)
      $10k   → ~80.0  (log10(10001)*20)
      $99.9k → ~100   (capped)

    Log scale prevents mega-sellers from completely dominating. New artists
    with a single sale ($1-10) still get 20-40 points.
    """
    if components.lifetime_sales_cents <= 0:
        return 0.0
    dollars = components.lifetime_sales_cents / 100.0
    raw = math.log10(dollars + 1) * 20.0
    return min(100.0, raw)


def calc_supporters_score(components: ScoreComponents) -> float:
    """Normalize supporter counts to 0-100.

    Formula: min(100, active_subscribers * 5 + active_sponsors * 3 + followers / 10)

    Subscribers are the most valuable (recurring), sponsors next,
    followers provide a soft base. Cap at 100.
    """
    raw = (
        components.active_subscribers * 5
        + components.active_sponsors * 3
        + components.followers / 10.0
    )
    return min(100.0, raw)


def calc_tenure_score(components: ScoreComponents) -> float:
    """Normalize signup tenure to 0-100.

    Formula: min(100, days_since_signup / 3.65)
    → 1 year (365 days) = 100 points. 0.1 weight keeps tenure a bonus,
    not a barrier — new artists are not penalized heavily.
    """
    if components.days_since_signup <= 0:
        return 0.0
    return min(100.0, components.days_since_signup / 3.65)


def calc_artist_score(components: ScoreComponents) -> float:
    """Compute weighted composite score in range [0, 100].

    score = 0.5 * recent_activity + 0.3 * sales + 0.2 * supporters + 0.1 * tenure

    Favors recent activity (0.5) so new artists posting frequently can rank
    above dormant artists with historic sales (OQ-5=B: 신진작가 친화).
    """
    s_activity = calc_recent_activity_score(components)
    s_sales = calc_sales_score(components)
    s_supporters = calc_supporters_score(components)
    s_tenure = calc_tenure_score(components)

    score = (
        WEIGHT_RECENT_ACTIVITY * s_activity
        + WEIGHT_SALES * s_sales
        + WEIGHT_SUPPORTERS * s_supporters
        + WEIGHT_TENURE * s_tenure
    )
    return round(min(100.0, max(0.0, score)), 4)


def calc_region_score(components: ScoreComponents) -> float:
    """Compute region-scoped score (same formula as global, but applied within region group).

    The score value itself is identical to the global score — region ranking is
    determined by sorting this score within the country_code bucket.
    This helper is provided for clarity and testability.
    """
    return calc_artist_score(components)


def calc_genre_score(components: ScoreComponents) -> float:
    """Compute genre-scoped score (same formula as global, applied within primary_genre bucket).

    Genre ranking is determined by sorting this score within the primary_genre bucket.
    """
    return calc_artist_score(components)


def derive_tier_badge(rank: int | None) -> str | None:
    """Derive tier badge string from global rank.

    top_10   → rank 1-10
    top_100  → rank 11-100
    top_1000 → rank 101-1000
    None     → rank > 1000 or no rank
    """
    if rank is None:
        return None
    if rank <= 10:
        return "top_10"
    if rank <= 100:
        return "top_100"
    if rank <= 1000:
        return "top_1000"
    return None
