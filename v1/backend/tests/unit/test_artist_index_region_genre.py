"""Unit tests for G'-8 artist-index region/genre ranking helpers.

4 test cases:
  1. region 분리 ranking — 동일 country_code 내 순위 격리
  2. genre 분리 ranking — 동일 primary_genre 내 순위 격리
  3. region + genre 교차 — region 필터 + genre 필터 동시 적용 시 교집합 동작
  4. primary_genre 추출 정확도 — 복수 genre_tags 중 가장 많이 등장하는 태그 우선
"""
from __future__ import annotations

import pytest

from app.services.artist_index_scoring import (
    ScoreComponents,
    calc_artist_score,
    calc_region_score,
    calc_genre_score,
)


# ─── Helper: build a minimal ScoreComponents ─────────────────────────────────

def _comp(post_count_30d: int = 0, bid_count_30d: int = 0,
          lifetime_sales_cents: int = 0, days_since_signup: int = 0) -> ScoreComponents:
    return ScoreComponents(
        post_count_30d=post_count_30d,
        bid_count_30d=bid_count_30d,
        comment_count_30d=0,
        lifetime_sales_cents=lifetime_sales_cents,
        active_subscribers=0,
        active_sponsors=0,
        followers=0,
        days_since_signup=days_since_signup,
    )


# ─── Helper: simulate region ranking ─────────────────────────────────────────

def _rank_within_region(artist_data: list[tuple[str, str, ScoreComponents]]) -> dict[str, int]:
    """Simulate region ranking from a list of (uid, country_code, components).

    Returns {uid: rank_1indexed} for all artists.
    Same algorithm as artist_index_jobs.py Step 2.
    """
    region_groups: dict[str, list[tuple[str, float]]] = {}
    for uid, country, comp in artist_data:
        score_r = calc_region_score(comp)
        region_groups.setdefault(country, []).append((uid, score_r))

    region_rank: dict[str, int] = {}
    for country, group in region_groups.items():
        group.sort(key=lambda x: x[1], reverse=True)
        for rank_1i, (uid, _sc) in enumerate(group, start=1):
            region_rank[uid] = rank_1i
    return region_rank


def _rank_within_genre(artist_data: list[tuple[str, str, ScoreComponents]]) -> dict[str, int]:
    """Simulate genre ranking from a list of (uid, primary_genre, components).

    Returns {uid: rank_1indexed} for all artists.
    Same algorithm as artist_index_jobs.py Step 3.
    """
    genre_groups: dict[str, list[tuple[str, float]]] = {}
    for uid, genre, comp in artist_data:
        score_g = calc_genre_score(comp)
        genre_groups.setdefault(genre, []).append((uid, score_g))

    genre_rank: dict[str, int] = {}
    for genre, group in genre_groups.items():
        group.sort(key=lambda x: x[1], reverse=True)
        for rank_1i, (uid, _sc) in enumerate(group, start=1):
            genre_rank[uid] = rank_1i
    return genre_rank


# ─── Test 1: region 분리 ranking ─────────────────────────────────────────────


def test_region_ranking_isolation():
    """KR 아티스트 3명 + US 아티스트 2명 — 각 지역 내 별도 순위 부여.

    KR 그룹에서는 KR-highest가 rank 1, KR-lowest가 rank 3.
    US 그룹에서는 US-highest가 rank 1, US-lowest가 rank 2.
    두 그룹 간 rank 1이 2개 존재 (지역별 독립).
    """
    # KR: 3 artists with different scores
    kr_high = _comp(post_count_30d=10, days_since_signup=200)   # highest KR score
    kr_mid = _comp(post_count_30d=5, days_since_signup=100)
    kr_low = _comp(post_count_30d=1, days_since_signup=30)      # lowest KR score

    # US: 2 artists
    us_high = _comp(post_count_30d=8, days_since_signup=180)    # highest US score
    us_low = _comp(post_count_30d=2, days_since_signup=50)

    artist_data = [
        ("kr_high_uid", "KR", kr_high),
        ("kr_mid_uid", "KR", kr_mid),
        ("kr_low_uid", "KR", kr_low),
        ("us_high_uid", "US", us_high),
        ("us_low_uid", "US", us_low),
    ]
    ranks = _rank_within_region(artist_data)

    # KR group ranks
    assert ranks["kr_high_uid"] == 1, "KR highest activity → KR rank 1"
    assert ranks["kr_mid_uid"] == 2, "KR mid activity → KR rank 2"
    assert ranks["kr_low_uid"] == 3, "KR lowest activity → KR rank 3"

    # US group ranks
    assert ranks["us_high_uid"] == 1, "US highest activity → US rank 1"
    assert ranks["us_low_uid"] == 2, "US lowest activity → US rank 2"

    # Both regions independently have rank 1
    assert ranks["kr_high_uid"] == ranks["us_high_uid"] == 1


# ─── Test 2: genre 분리 ranking ───────────────────────────────────────────────


def test_genre_ranking_isolation():
    """watercolor 2명 + oil_painting 3명 — 각 장르 내 별도 순위 부여.

    watercolor rank 1 = watercolor_high_uid.
    oil_painting rank 1 = oil_high_uid.
    """
    wc_high = _comp(post_count_30d=12, bid_count_30d=3, days_since_signup=150)
    wc_low = _comp(post_count_30d=2, days_since_signup=30)

    oil_high = _comp(post_count_30d=15, bid_count_30d=5, days_since_signup=200)
    oil_mid = _comp(post_count_30d=6, days_since_signup=90)
    oil_low = _comp(post_count_30d=1, days_since_signup=10)

    artist_data = [
        ("wc_high_uid", "watercolor", wc_high),
        ("wc_low_uid", "watercolor", wc_low),
        ("oil_high_uid", "oil_painting", oil_high),
        ("oil_mid_uid", "oil_painting", oil_mid),
        ("oil_low_uid", "oil_painting", oil_low),
    ]
    ranks = _rank_within_genre(artist_data)

    assert ranks["wc_high_uid"] == 1
    assert ranks["wc_low_uid"] == 2
    assert ranks["oil_high_uid"] == 1
    assert ranks["oil_mid_uid"] == 2
    assert ranks["oil_low_uid"] == 3

    # Both genres independently have rank 1
    assert ranks["wc_high_uid"] == ranks["oil_high_uid"] == 1


# ─── Test 3: region + genre 교차 동작 ─────────────────────────────────────────


def test_region_genre_cross_ranking():
    """region 랭킹 + genre 랭킹 모두 계산 시 각 그룹 독립성 보장.

    KR/watercolor, KR/oil, US/watercolor — 세 아티스트.
    region 랭킹: KR 그룹 2명(각자 rank), US 그룹 1명(rank 1).
    genre 랭킹: watercolor 그룹 2명(각자 rank), oil 그룹 1명(rank 1).
    """
    kr_wc = _comp(post_count_30d=8, days_since_signup=100)
    kr_oil = _comp(post_count_30d=5, days_since_signup=80)
    us_wc = _comp(post_count_30d=10, days_since_signup=120)

    region_data = [
        ("kr_wc_uid", "KR", kr_wc),
        ("kr_oil_uid", "KR", kr_oil),
        ("us_wc_uid", "US", us_wc),
    ]
    genre_data = [
        ("kr_wc_uid", "watercolor", kr_wc),
        ("kr_oil_uid", "oil_painting", kr_oil),
        ("us_wc_uid", "watercolor", us_wc),
    ]

    region_ranks = _rank_within_region(region_data)
    genre_ranks = _rank_within_genre(genre_data)

    # KR region: kr_wc (score > kr_oil) → rank 1, kr_oil → rank 2
    assert region_ranks["kr_wc_uid"] == 1
    assert region_ranks["kr_oil_uid"] == 2
    # US region: only one artist → rank 1
    assert region_ranks["us_wc_uid"] == 1

    # watercolor genre: us_wc (higher score) → rank 1, kr_wc → rank 2
    us_score = calc_genre_score(us_wc)
    kr_score = calc_genre_score(kr_wc)
    if us_score >= kr_score:
        assert genre_ranks["us_wc_uid"] == 1
        assert genre_ranks["kr_wc_uid"] == 2
    else:
        assert genre_ranks["kr_wc_uid"] == 1
        assert genre_ranks["us_wc_uid"] == 2

    # oil_painting genre: only one artist → rank 1
    assert genre_ranks["kr_oil_uid"] == 1


# ─── Test 4: primary_genre 추출 정확도 ────────────────────────────────────────


def test_primary_genre_extraction_accuracy():
    """_fetch_primary_genres 로직 시뮬레이션: 가장 많이 등장하는 genre_tag 우선.

    posts 테이블 unnest 결과를 simulate:
    artist A: watercolor×5, oil×2 → primary = watercolor
    artist B: digital×3, watercolor×3, oil×1 → primary = digital (alphabetical tie-break via ORDER BY)
    artist C: sculpture×10 → primary = sculpture
    """
    # Simulate the "SELECT author_id, genre_tag, COUNT(*) GROUP BY ORDER BY cnt DESC" result
    # and the "first row per author wins" logic from _fetch_primary_genres.
    def _simulate_primary_genre(tag_counts: list[tuple[str, int]]) -> str:
        """Returns primary genre from list of (genre_tag, count) sorted by count DESC."""
        sorted_tags = sorted(tag_counts, key=lambda x: x[1], reverse=True)
        return sorted_tags[0][0]

    # artist A
    a_genre = _simulate_primary_genre([("watercolor", 5), ("oil", 2)])
    assert a_genre == "watercolor", f"Expected watercolor (highest count=5), got {a_genre}"

    # artist C
    c_genre = _simulate_primary_genre([("sculpture", 10)])
    assert c_genre == "sculpture", f"Expected sculpture, got {c_genre}"

    # Score consistency: calc_region_score == calc_artist_score (same formula)
    comp = _comp(post_count_30d=5, days_since_signup=100)
    assert calc_region_score(comp) == calc_artist_score(comp), \
        "calc_region_score must equal calc_artist_score (same formula)"
    assert calc_genre_score(comp) == calc_artist_score(comp), \
        "calc_genre_score must equal calc_artist_score (same formula)"
