"""ML Feed v2 추론 서비스 — Phase 9 K-1 (Collaborative Filtering) + Phase 10 K-2 (Diversity Reranking).

추론 흐름:
  1. Redis cache 조회 (ml_feed:{user_id}) → HIT → 즉시 반환
  2. MISS → interaction count 확인
     - < _COLD_USER_THRESHOLD 건 → Cold User fallback (chronological)
  3. ml_models active 조회
     - 없음 → Mock fallback (chronological)
  4. MF 점수 계산 (user_factor @ item_factors.T) — K-2: 후보 풀 100개로 확장
  5. pgvector cosine 보정 (0.3 가중치) — L-A user_embeddings + post_embeddings 활용
  6. [K-2] Diversity Reranking — 신진작가 부스팅 + quota-based 다양성 제약
  7. 최종 정렬 → Redis SET (5분 TTL) → 반환

성능 목표:
  - cache hit: ≤ 200ms
  - cold (DB 직접): ≤ 1s

최종 스코어 공식 (K-1):
  final_score = 0.7 * mf_score + 0.3 * cosine_similarity

K-2 추가 처리:
  DIVERSITY_RERANKING_ENABLED=true 시 → 후보 100개 확장 후 diversity reranking
  DIVERSITY_RERANKING_ENABLED=false 시 → 기존 K-1 동작 그대로 (top_k 반환)
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any

from app.services.cache import cache

log = logging.getLogger(__name__)

_CACHE_TTL = int(os.getenv("ML_FEED_CACHE_TTL_SECONDS", "300"))       # 5분
_COLD_USER_THRESHOLD = int(os.getenv("ML_COLD_USER_THRESHOLD", "5"))   # cold user 기준
_DEFAULT_TOP_K = int(os.getenv("ML_FEED_TOP_K", "20"))                 # 추천 포스트 수

# K-2 Diversity Reranking 제어
_DIVERSITY_ENABLED = os.getenv("DIVERSITY_RERANKING_ENABLED", "true").lower() != "false"
_CANDIDATE_POOL = int(os.getenv("DIVERSITY_CANDIDATE_POOL", "100"))     # reranking 후보 풀


def _cache_key(user_id: str) -> str:
    """ml_feed:{user_id} 캐시 키 생성."""
    return f"ml_feed:{user_id}"


# ──────────────────────────────────────────────────────────────────────────────
# 메인 추론 함수
# ──────────────────────────────────────────────────────────────────────────────

async def get_recommendations(
    db,
    user_id: str,
    top_k: int = _DEFAULT_TOP_K,
) -> list[str]:
    """사용자 맞춤 포스트 ID 리스트 반환 (ML 스코어 + K-2 Diversity Reranking).

    반환: post_id (str) 리스트, top_k개.
    fallback 시: chronological post_id 리스트 (동일 형식).
    에러 시: 빈 리스트 [] (상위 레이어에서 v1 fallback 처리).

    K-2 변경사항:
      - DIVERSITY_RERANKING_ENABLED=true 시: 후보 _CANDIDATE_POOL(100)개 확장 후 reranking
      - DIVERSITY_RERANKING_ENABLED=false 시: 기존 top_k 그대로 반환 (K-1 동작 보존)
    """
    key = _cache_key(user_id)

    # 1. Redis cache hit 확인
    cached = await cache.get_json(key, prefix="ml_feed")
    if cached is not None:
        log.debug("get_recommendations: cache HIT (user=%s)", user_id)
        return cached  # type: ignore[return-value]

    # 2. interaction count 확인 (cold user 판별)
    interaction_count = await _get_interaction_count(db, user_id)
    if interaction_count < _COLD_USER_THRESHOLD:
        log.info(
            "get_recommendations: cold user (user=%s, interactions=%d) → fallback",
            user_id, interaction_count,
        )
        return await _chronological_fallback(db, top_k)

    # 3. 활성 모델 조회
    model_params = await _load_active_model(db)
    if model_params is None:
        log.warning("get_recommendations: 활성 모델 없음 → fallback (user=%s)", user_id)
        return await _chronological_fallback(db, top_k)

    # 4. MF 점수 + pgvector 보정 계산 (K-2: diversity 활성 시 후보 풀 확장)
    candidate_pool = _CANDIDATE_POOL if _DIVERSITY_ENABLED else top_k
    try:
        post_ids_with_scores = await _compute_mf_scores_with_scores(
            db, user_id, model_params, top_k=candidate_pool
        )
    except Exception as exc:  # noqa: BLE001
        log.warning(
            "get_recommendations: MF 점수 계산 실패 (%s) → fallback (user=%s)", exc, user_id
        )
        return await _chronological_fallback(db, top_k)

    # 5. K-2 Diversity Reranking 적용
    if _DIVERSITY_ENABLED and post_ids_with_scores:
        try:
            from app.services.diversity_reranking import (
                fetch_post_metadata,
                load_config,
                rerank,
            )
            config = await load_config(db)
            candidate_post_ids = [pid for pid, _ in post_ids_with_scores]
            post_metadata = await fetch_post_metadata(db, candidate_post_ids)
            post_ids = rerank(
                candidates=post_ids_with_scores,
                post_metadata=post_metadata,
                config=config,
            )
            log.info(
                "get_recommendations: diversity reranking 완료 (user=%s, before=%d, after=%d)",
                user_id, len(post_ids_with_scores), len(post_ids),
            )
        except Exception as exc:  # noqa: BLE001
            log.warning(
                "get_recommendations: diversity reranking 실패 (%s) — K-1 결과 사용",
                exc,
            )
            # 안전 fallback: K-1 score 원본 top_k 반환
            post_ids = [pid for pid, _ in post_ids_with_scores[:top_k]]
    else:
        # DIVERSITY_RERANKING_ENABLED=false 또는 후보 없음: K-1 결과 그대로 반환
        post_ids = [pid for pid, _ in post_ids_with_scores[:top_k]]

    # 6. Redis SET (5분 TTL) — 개인화된 결과만 캐시 (chronological fallback은 캐시 안 함)
    await cache.set_json(key, post_ids, ttl_seconds=_CACHE_TTL, prefix="ml_feed")

    return post_ids


async def _get_interaction_count(db, user_id: str) -> int:
    """사용자의 총 상호작용 건수 조회."""
    from sqlalchemy import text

    result = await db.execute(
        text("SELECT COUNT(*) FROM user_post_interactions WHERE user_id = :uid"),
        {"uid": user_id},
    )
    return int(result.scalar_one() or 0)


async def _load_active_model(db) -> dict[str, Any] | None:
    """ml_models에서 가장 최신 active 모델의 params 반환."""
    from sqlalchemy import text

    result = await db.execute(
        text("""
            SELECT params FROM ml_models
            WHERE status = 'active'
            ORDER BY trained_at DESC
            LIMIT 1
        """)
    )
    row = result.fetchone()
    if row is None or not row.params:
        return None
    # JSONB는 dict로 반환, 문자열이면 파싱
    return row.params if isinstance(row.params, dict) else json.loads(row.params)


async def _compute_mf_scores_with_scores(
    db,
    user_id: str,
    model_params: dict[str, Any],
    top_k: int,
) -> list[tuple[str, float]]:
    """MF 점수 + pgvector cosine 보정으로 최종 (post_id, score) 튜플 리스트 계산.

    K-2 Diversity Reranking을 위해 score를 함께 반환.
    final_score = 0.7 * mf_score + 0.3 * cosine_similarity
    """
    result = await _compute_mf_scores(db, user_id, model_params, top_k)
    # _compute_mf_scores는 post_id 리스트 반환 — score 없이 순위만 있음
    # K-2용: score를 역순위 기반으로 부여 (최상위 = top_k, 최하위 = 1)
    total = len(result)
    return [(pid, float(total - i)) for i, pid in enumerate(result)]


async def _compute_mf_scores(
    db,
    user_id: str,
    model_params: dict[str, Any],
    top_k: int,
) -> list[str]:
    """MF 점수 + pgvector cosine 보정으로 최종 포스트 ID 리스트 계산.

    final_score = 0.7 * mf_score + 0.3 * cosine_similarity
    """
    from sqlalchemy import text

    try:
        import numpy as np
    except ImportError:
        log.warning("_compute_mf_scores: numpy 미설치 → chronological fallback")
        return await _chronological_fallback(db, top_k)

    user_ids: list[str] = model_params.get("user_ids", [])
    post_ids: list[str] = model_params.get("post_ids", [])

    if not user_ids or not post_ids:
        log.info("_compute_mf_scores: 모델 파라미터 비어있음 → fallback (user=%s)", user_id)
        return await _chronological_fallback(db, top_k)

    user_factors_raw = model_params.get("user_factors", [])
    item_factors_raw = model_params.get("item_factors", [])

    if not user_factors_raw or not item_factors_raw:
        log.info("_compute_mf_scores: factors 없음 → fallback (user=%s)", user_id)
        return await _chronological_fallback(db, top_k)

    user_factors = np.array(user_factors_raw, dtype=float)
    item_factors = np.array(item_factors_raw, dtype=float)

    if user_id not in user_ids:
        log.info("_compute_mf_scores: 모델에 user_id 없음 → fallback (user=%s)", user_id)
        return await _chronological_fallback(db, top_k)

    u_idx = user_ids.index(user_id)

    if u_idx >= len(user_factors):
        log.info("_compute_mf_scores: user_idx 범위 초과 → fallback (user=%s)", user_id)
        return await _chronological_fallback(db, top_k)

    user_vec = user_factors[u_idx]  # (n_factors,)

    # MF 점수: item_factors @ user_vec → (n_posts,)
    mf_scores = item_factors @ user_vec

    # pgvector cosine 보정: L-A user_embeddings <=> post_embeddings
    cosine_scores = np.zeros(len(post_ids))
    try:
        # 사용자 임베딩 조회 (L-A user_embeddings 테이블)
        ue_result = await db.execute(
            text("SELECT embedding::text FROM user_embeddings WHERE user_id = :uid"),
            {"uid": user_id},
        )
        ue_row = ue_result.fetchone()
        if ue_row and ue_row.embedding:
            # pgvector 문자열 파싱: [0.1,0.2,...] 형태
            emb_str = ue_row.embedding.strip()
            if emb_str.startswith("[") and emb_str.endswith("]"):
                emb_str = emb_str[1:-1]
            user_emb_vec = np.array(
                [float(x) for x in emb_str.split(",") if x.strip()],
                dtype=float,
            )

            # 포스트 임베딩 배치 조회 — 성능: 상위 200개 MF 후보만 cosine 계산
            candidate_post_ids = post_ids
            candidate_indices = list(range(len(post_ids)))
            if len(candidate_post_ids) > 200:
                top200_idx = np.argsort(mf_scores)[-200:][::-1]
                candidate_post_ids = [post_ids[i] for i in top200_idx]
                candidate_indices = list(top200_idx)

            # IN 절 배치 쿼리 (N+1 방지)
            placeholders = ", ".join(f"'{pid}'" for pid in candidate_post_ids)
            vec_literal = "[" + ",".join(str(v) for v in user_emb_vec.tolist()) + "]"
            pe_result = await db.execute(
                text(f"""
                    SELECT post_id::text,
                           1 - (embedding <=> '{vec_literal}'::vector) AS similarity
                    FROM post_embeddings
                    WHERE post_id IN ({placeholders})
                """)
            )
            post_id_to_cosine = {
                pe_row.post_id: float(pe_row.similarity or 0)
                for pe_row in pe_result.fetchall()
            }
            for i, pid in zip(candidate_indices, candidate_post_ids):
                if pid in post_id_to_cosine:
                    cosine_scores[i] = post_id_to_cosine[pid]

    except Exception as exc:  # noqa: BLE001
        log.warning(
            "_compute_mf_scores: pgvector 보정 실패 (%s) — MF 점수만 사용 (user=%s)",
            exc, user_id,
        )

    # 최종 스코어: 0.7 * MF + 0.3 * cosine
    final_scores = 0.7 * mf_scores + 0.3 * cosine_scores

    # top_k 정렬 (내림차순)
    top_indices = np.argsort(final_scores)[-top_k:][::-1]
    result_post_ids = [post_ids[i] for i in top_indices if i < len(post_ids)]

    return result_post_ids


async def _chronological_fallback(db, top_k: int) -> list[str]:
    """최신순 published 공개 포스트 ID 리스트 반환 (fallback).

    cold user, 모델 미준비, 에러 등 모든 fallback 케이스에서 호출.
    """
    from sqlalchemy import text

    result = await db.execute(
        text("""
            SELECT id::text FROM posts
            WHERE status = 'published'
              AND visibility = 'public'
            ORDER BY created_at DESC
            LIMIT :lim
        """),
        {"lim": top_k},
    )
    return [str(r.id) for r in result.fetchall()]


# ──────────────────────────────────────────────────────────────────────────────
# Cache invalidation
# ──────────────────────────────────────────────────────────────────────────────

async def invalidate_user_feed_cache(user_id: str) -> None:
    """사용자 피드 캐시 무효화 (interaction 발생 시 호출 가능).

    interaction 기록 후 호출하면 다음 요청에서 신선한 추천 반환.
    """
    await cache.delete(_cache_key(user_id), reason="interaction_update")
