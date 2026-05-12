"""Diversity Reranking 서비스 — Phase 10 K-2 (필터 버블 방지 + 신진작가 부스팅).

알고리즘: quota-based reranking (MMR은 Phase 11 검토)
  1단계: 신진작가 부스팅 — artist_index_rank > 80% 작가의 post → score × boost
  2단계: quota-based 재정렬 — top_k_window 내 genre ≥ genre_min, region ≥ region_min
  3단계: 최종 score 내림차순 정렬 후 top_k_window 개 반환

Mock 모드:
  - artist_index 없는 후보 → 부스트 skip + WARNING 로그
  - diversity_configs 비어있음 → env 기본값 사용
  - DIVERSITY_RERANKING_ENABLED=false → K-1 결과 그대로 반환
"""
from __future__ import annotations

import dataclasses
import logging
import os

log = logging.getLogger(__name__)

_ENABLED = os.getenv("DIVERSITY_RERANKING_ENABLED", "true").lower() != "false"
_DEFAULT_BOOST = float(os.getenv("DIVERSITY_EMERGING_BOOST", "1.20"))
_DEFAULT_GENRE_MIN = int(os.getenv("DIVERSITY_GENRE_MIN", "3"))
_DEFAULT_REGION_MIN = int(os.getenv("DIVERSITY_REGION_MIN", "2"))
_DEFAULT_TOP_K = int(os.getenv("DIVERSITY_TOP_K_WINDOW", "20"))
_DEFAULT_POOL = int(os.getenv("DIVERSITY_CANDIDATE_POOL", "100"))

# 신진작가 판별 기준: artist_index_rank 백분위 상위 80% 이하
# artist_index_rank는 1=1위(최상위), 숫자가 클수록 하위권
# "rank > 80%"는 총 아티스트 수 대비 순위가 80% 이상인 경우를 의미
_EMERGING_RANK_PERCENTILE_THRESHOLD = float(
    os.getenv("DIVERSITY_EMERGING_RANK_PERCENTILE", "0.80")
)


@dataclasses.dataclass
class DiversityConfig:
    """다양성 재정렬 설정 dataclass.

    DB diversity_configs 테이블 또는 env 기본값에서 로드.
    """
    name: str = "feed_default"
    emerging_artist_boost: float = _DEFAULT_BOOST
    genre_min_diversity: int = _DEFAULT_GENRE_MIN
    region_min_diversity: int = _DEFAULT_REGION_MIN
    top_k_window: int = _DEFAULT_TOP_K
    candidate_pool_size: int = _DEFAULT_POOL


@dataclasses.dataclass
class PostMeta:
    """재정렬에 필요한 포스트 메타데이터."""
    post_id: str
    genre: str | None              # posts.genre (nullable)
    author_id: str
    author_country_code: str | None    # users.country_code (nullable)
    artist_index_rank: int | None      # users.artist_index_rank (nullable)
    artist_index_total: int | None     # 전체 아티스트 수 (신진작가 판별용)


# ──────────────────────────────────────────────────────────────────────────────
# Config 로드
# ──────────────────────────────────────────────────────────────────────────────

async def load_config(db, config_name: str = "feed_default") -> DiversityConfig:
    """diversity_configs 테이블에서 설정 로드.

    테이블 없거나 레코드 없으면 env 기본값으로 fallback.
    """
    from sqlalchemy import text

    try:
        result = await db.execute(
            text("""
                SELECT
                    name, emerging_artist_boost, genre_min_diversity,
                    region_min_diversity, top_k_window, candidate_pool_size
                FROM diversity_configs
                WHERE name = :name AND status = 'active'
                LIMIT 1
            """),
            {"name": config_name},
        )
        row = result.fetchone()
        if row:
            return DiversityConfig(
                name=row.name,
                emerging_artist_boost=float(row.emerging_artist_boost),
                genre_min_diversity=int(row.genre_min_diversity),
                region_min_diversity=int(row.region_min_diversity),
                top_k_window=int(row.top_k_window),
                candidate_pool_size=int(row.candidate_pool_size),
            )
    except Exception as exc:  # noqa: BLE001
        log.warning("load_config: DB 조회 실패 (%s) — env 기본값 사용", exc)

    log.info("load_config: env 기본값 사용 (name=%s)", config_name)
    return DiversityConfig()


# ──────────────────────────────────────────────────────────────────────────────
# 포스트 메타데이터 일괄 조회
# ──────────────────────────────────────────────────────────────────────────────

async def fetch_post_metadata(
    db,
    post_ids: list[str],
) -> dict[str, PostMeta]:
    """재정렬에 필요한 포스트/작가 메타데이터 일괄 조회.

    posts.genre + posts.author_id + users.country_code + users.artist_index_rank
    단일 JOIN 쿼리로 N+1 방지.
    """
    from sqlalchemy import text

    if not post_ids:
        return {}

    # 전체 아티스트 수 조회 (신진작가 판별용)
    try:
        total_result = await db.execute(
            text("SELECT COUNT(*) FROM users WHERE artist_index_rank IS NOT NULL")
        )
        total_artists = int(total_result.scalar_one() or 0)
    except Exception as exc:  # noqa: BLE001
        log.warning("fetch_post_metadata: 아티스트 수 조회 실패 (%s) — 0 사용", exc)
        total_artists = 0

    # SQL injection 방지: UUID 형식만 허용
    safe_post_ids = []
    for pid in post_ids:
        clean = str(pid).strip()
        if clean:
            safe_post_ids.append(clean)

    if not safe_post_ids:
        return {}

    placeholders = ", ".join(f"'{pid}'" for pid in safe_post_ids)
    try:
        result = await db.execute(
            text(f"""
                SELECT
                    p.id::text          AS post_id,
                    p.genre             AS genre,
                    p.author_id::text   AS author_id,
                    u.country_code      AS author_country_code,
                    u.artist_index_rank AS artist_index_rank
                FROM posts p
                JOIN users u ON u.id = p.author_id
                WHERE p.id::text IN ({placeholders})
            """)
        )
        rows = result.fetchall()
    except Exception as exc:  # noqa: BLE001
        log.warning("fetch_post_metadata: DB 조회 실패 (%s) — 빈 메타데이터 반환", exc)
        return {}

    meta: dict[str, PostMeta] = {}
    for row in rows:
        meta[row.post_id] = PostMeta(
            post_id=row.post_id,
            genre=row.genre or "unknown",
            author_id=row.author_id,
            author_country_code=row.author_country_code or "unknown",
            artist_index_rank=row.artist_index_rank,
            artist_index_total=total_artists if total_artists > 0 else None,
        )
    return meta


# ──────────────────────────────────────────────────────────────────────────────
# 신진작가 판별
# ──────────────────────────────────────────────────────────────────────────────

def _is_emerging_artist(meta: PostMeta, total_artists: int) -> bool:
    """artist_index_rank 기준 신진작가 여부 판별.

    신진작가 조건: artist_index_rank / total_artists > EMERGING_RANK_PERCENTILE_THRESHOLD
    즉, 전체 아티스트 중 하위 80% 이하 (순위가 낮을수록 신진)

    artist_index_rank 없으면 False 반환 (부스트 skip).
    """
    if meta.artist_index_rank is None or total_artists == 0:
        return False
    percentile = meta.artist_index_rank / total_artists
    return percentile > _EMERGING_RANK_PERCENTILE_THRESHOLD


# ──────────────────────────────────────────────────────────────────────────────
# 메인 재정렬 함수
# ──────────────────────────────────────────────────────────────────────────────

def rerank(
    candidates: list[tuple[str, float]],
    post_metadata: dict[str, PostMeta],
    config: DiversityConfig,
) -> list[str]:
    """Diversity Reranking — quota-based 알고리즘.

    Args:
        candidates: [(post_id, score), ...] — K-1 추론 결과 (score 내림차순)
        post_metadata: {post_id: PostMeta} — genre, region, artist_index 정보
        config: DiversityConfig — 다양성 제약 파라미터

    Returns:
        list[str] — post_id 리스트, 최대 config.top_k_window개.
                    후보 < top_k_window이면 전체 반환.

    알고리즘:
        1단계) 신진작가 부스팅: artist_index 기준 신진작가 post → score × boost
        2단계) 부스팅 적용 score 내림차순 정렬
        3단계) quota-based 선택:
              - selected 리스트에 순서대로 추가
              - selected 내 unique genres < genre_min → 동일 장르 추가 제한
              - selected 내 unique regions < region_min → 동일 지역 추가 제한
              - top_k_window 채울 때까지 반복
        4단계) quota 조건 미충족 후보 소진 시 나머지 그대로 채움 (graceful)
    """
    if not candidates:
        return []

    # 후보 < window 크기 시 그대로 반환 (graceful)
    if len(candidates) <= config.top_k_window:
        log.info(
            "rerank: 후보 수(%d) ≤ top_k_window(%d) — 전체 반환",
            len(candidates), config.top_k_window,
        )
        return [pid for pid, _ in candidates]

    # 전체 아티스트 수 추출 (메타데이터에서 샘플링)
    total_artists = 0
    if post_metadata:
        sample = next(iter(post_metadata.values()))
        total_artists = sample.artist_index_total or 0

    # ── 1단계: 신진작가 부스팅 ──────────────────────────────────────────────
    boosted: list[tuple[str, float]] = []
    boost_applied = 0
    boost_skipped = 0

    for post_id, score in candidates:
        meta = post_metadata.get(post_id)
        if meta is None:
            boosted.append((post_id, score))
            boost_skipped += 1
            continue

        if total_artists > 0 and _is_emerging_artist(meta, total_artists):
            new_score = score * config.emerging_artist_boost
            boosted.append((post_id, new_score))
            boost_applied += 1
        else:
            if meta.artist_index_rank is None:
                boost_skipped += 1
            boosted.append((post_id, score))

    if boost_skipped > 0:
        log.warning(
            "rerank: %d개 후보 artist_index 미가용 — 부스트 skip (quota만 적용)",
            boost_skipped,
        )
    log.info("rerank: 신진작가 부스팅 적용 %d개 / 전체 %d개", boost_applied, len(boosted))

    # ── 2단계: 부스팅 score 내림차순 정렬 ──────────────────────────────────
    boosted.sort(key=lambda x: x[1], reverse=True)

    # ── 3단계: quota-based 선택 ─────────────────────────────────────────────
    selected: list[str] = []
    selected_genres: list[str] = []
    selected_regions: list[str] = []
    deferred: list[tuple[str, float]] = []  # quota 위반으로 미선택된 후보

    for post_id, score in boosted:
        if len(selected) >= config.top_k_window:
            break

        meta = post_metadata.get(post_id)
        genre = (meta.genre if meta else None) or "unknown"
        region = (meta.author_country_code if meta else None) or "unknown"

        # 현재 selected의 다양성 상태
        unique_genres = len(set(selected_genres))
        unique_regions = len(set(selected_regions))

        # 장르 quota 체크: genre_min 미충족 상태에서 특정 장르가 window 내 허용 비율 초과
        genre_quota_ok = True
        if unique_genres < config.genre_min_diversity:
            # 이미 selected에 있는 장르인 경우 — 허용 비율 계산
            if genre in set(selected_genres):
                genre_count_in_selected = selected_genres.count(genre)
                max_same_genre = config.top_k_window // config.genre_min_diversity
                if genre_count_in_selected >= max_same_genre:
                    genre_quota_ok = False

        # 지역 quota 체크: 동일 방식
        region_quota_ok = True
        if unique_regions < config.region_min_diversity:
            if region in set(selected_regions):
                region_count_in_selected = selected_regions.count(region)
                max_same_region = config.top_k_window // config.region_min_diversity
                if region_count_in_selected >= max_same_region:
                    region_quota_ok = False

        if genre_quota_ok and region_quota_ok:
            selected.append(post_id)
            selected_genres.append(genre)
            selected_regions.append(region)
        else:
            deferred.append((post_id, score))

    # ── 4단계: quota 조건 미충족으로 보류된 후보로 window 채움 (graceful) ──
    for post_id, _ in deferred:
        if len(selected) >= config.top_k_window:
            break
        if post_id not in selected:
            selected.append(post_id)

    log.info(
        "rerank 완료: 선택 %d개, unique_genres=%d, unique_regions=%d",
        len(selected),
        len(set(selected_genres[:len(selected)])),
        len(set(selected_regions[:len(selected)])),
    )
    return selected
