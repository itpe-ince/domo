"""ML Feed v2 학습 파이프라인 — Phase 9 K-1 (Collaborative Filtering).

OQ 결정:
  - 모델: Matrix Factorization (implicit 라이브러리 또는 numpy/scipy)
  - 학습 데이터: 최근 90일 implicit feedback (weight 합산)
  - 학습 주기: 일 1회 batch (새벽 3:00 UTC, 20번째 cron worker)
  - 모델 저장: ml_models 테이블 params JSONB (user_factors, item_factors)

Mock 모드:
  - implicit 라이브러리 미설치 → scipy SVD fallback → numpy random matrix + WARNING 로그
  - 빈 interaction 데이터 → 학습 스킵 + WARNING 로그
  - interaction < _MIN_INTERACTIONS 건 → 학습 스킵 + WARNING 로그

Interaction Weight 기준표:
  view (≥3초)  = 1.0  기본 관심 표현
  click        = 1.5  명시적 행동
  like         = 3.0  높은 engagement
  comment      = 4.0  가장 강한 engagement
  sponsor      = 5.0  최고 강도 (후원)
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any

from app.services.cron_monitor import record_cron_run as _push_cron_status

log = logging.getLogger(__name__)

_TRAINING_DAYS = int(os.getenv("ML_TRAINING_DAYS", "90"))
_MF_FACTORS = int(os.getenv("ML_MF_FACTORS", "50"))
_MF_ITERATIONS = int(os.getenv("ML_MF_ITERATIONS", "20"))
_MIN_INTERACTIONS = int(os.getenv("ML_MIN_INTERACTIONS", "100"))


# ──────────────────────────────────────────────────────────────────────────────
# 학습 데이터 수집
# ──────────────────────────────────────────────────────────────────────────────

async def collect_interactions(db, days: int = _TRAINING_DAYS) -> dict[str, Any]:
    """최근 N일 implicit feedback 집계.

    반환:
        {
            "user_ids": [uuid_str, ...],      # 정렬된 고유 사용자 ID
            "post_ids": [uuid_str, ...],      # 정렬된 고유 포스트 ID
            "user_idx": {uuid_str: int},      # user → matrix row index
            "post_idx": {uuid_str: int},      # post → matrix col index
            "interactions": [(u_idx, p_idx, weight_sum), ...],
        }
    데이터 없을 시 빈 dict {} 반환.
    """
    from sqlalchemy import text

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    result = await db.execute(
        text("""
            SELECT user_id::text, post_id::text, SUM(weight) AS total_weight
            FROM user_post_interactions
            WHERE created_at >= :cutoff
            GROUP BY user_id, post_id
            HAVING SUM(weight) > 0
            ORDER BY user_id, post_id
        """),
        {"cutoff": cutoff},
    )
    rows = result.fetchall()

    if not rows:
        log.warning("collect_interactions: 상호작용 데이터 없음 (cutoff=%s)", cutoff)
        return {}

    # 고유 사용자/포스트 인덱스 생성
    user_ids = sorted({r.user_id for r in rows})
    post_ids = sorted({r.post_id for r in rows})
    user_idx = {uid: i for i, uid in enumerate(user_ids)}
    post_idx = {pid: i for i, pid in enumerate(post_ids)}

    interactions = [
        (user_idx[r.user_id], post_idx[r.post_id], float(r.total_weight))
        for r in rows
    ]

    log.info(
        "collect_interactions: %d users, %d posts, %d pairs (cutoff=%s)",
        len(user_ids), len(post_ids), len(interactions), cutoff,
    )
    return {
        "user_ids": user_ids,
        "post_ids": post_ids,
        "user_idx": user_idx,
        "post_idx": post_idx,
        "interactions": interactions,
    }


# ──────────────────────────────────────────────────────────────────────────────
# Matrix Factorization 학습
# ──────────────────────────────────────────────────────────────────────────────

def train_mf_model(
    interactions: dict[str, Any],
    n_factors: int = _MF_FACTORS,
    n_iterations: int = _MF_ITERATIONS,
) -> dict[str, Any] | None:
    """Matrix Factorization 학습.

    1순위: implicit 라이브러리 (ALS 알고리즘, 성능 최적)
    2순위: scipy sparse + numpy SVD (fallback)
    3순위: numpy random matrix (mock, 추천 품질 없음)
    반환 없음(None): 데이터 없거나 numpy도 미설치

    반환: {"user_factors": [[float...]], "item_factors": [[float...]]}
           또는 None (학습 불가)
    """
    if not interactions:
        log.warning("train_mf_model: interaction 데이터 없음 — 학습 스킵")
        return None

    n_users = len(interactions.get("user_ids", []))
    n_posts = len(interactions.get("post_ids", []))
    pairs = interactions.get("interactions", [])

    if not pairs or len(pairs) < _MIN_INTERACTIONS:
        log.warning(
            "train_mf_model: 상호작용 %d건 < 최소 %d건 — 학습 스킵",
            len(pairs), _MIN_INTERACTIONS,
        )
        return None

    if n_users == 0 or n_posts == 0:
        log.warning("train_mf_model: 사용자(%d) 또는 포스트(%d) 없음 — 학습 스킵", n_users, n_posts)
        return None

    # implicit 라이브러리 시도 (ALS)
    try:
        import implicit  # type: ignore[import]
        import scipy.sparse as sp
        import numpy as np

        log.info("train_mf_model: implicit ALS 학습 시작 (users=%d, posts=%d)", n_users, n_posts)

        # CSR matrix: user × post
        rows_idx = [p[0] for p in pairs]
        cols_idx = [p[1] for p in pairs]
        data = [p[2] for p in pairs]
        user_post_matrix = sp.csr_matrix(
            (data, (rows_idx, cols_idx)), shape=(n_users, n_posts)
        )

        model = implicit.als.AlternatingLeastSquares(
            factors=n_factors,
            iterations=n_iterations,
            use_gpu=False,
        )
        model.fit(user_post_matrix)

        user_factors = model.user_factors.tolist()
        item_factors = model.item_factors.tolist()

        log.info(
            "train_mf_model: ALS 학습 완료 (factors=%d, iter=%d)", n_factors, n_iterations
        )
        return {"user_factors": user_factors, "item_factors": item_factors}

    except ImportError:
        log.warning("train_mf_model: implicit 라이브러리 미설치 — scipy SVD fallback 시도")

    # scipy SVD fallback
    try:
        import scipy.sparse as sp
        import numpy as np
        from scipy.sparse.linalg import svds

        rows_idx = [p[0] for p in pairs]
        cols_idx = [p[1] for p in pairs]
        data = [p[2] for p in pairs]
        mat = sp.csr_matrix(
            (data, (rows_idx, cols_idx)), shape=(n_users, n_posts), dtype=float
        )

        k = min(n_factors, min(n_users, n_posts) - 1)
        if k < 1:
            log.warning("train_mf_model: SVD k=%d < 1 — numpy mock으로 전환", k)
            raise ValueError("k too small")

        u, s, vt = svds(mat, k=k)
        user_factors = (u * s).tolist()
        item_factors = vt.T.tolist()

        log.info("train_mf_model: scipy SVD 학습 완료 (k=%d)", k)
        return {"user_factors": user_factors, "item_factors": item_factors}

    except ImportError:
        log.warning("train_mf_model: scipy 미설치 — numpy random mock 사용")
    except Exception as exc:  # noqa: BLE001
        log.warning("train_mf_model: scipy SVD 실패 (%s) — numpy random mock 사용", exc)

    # numpy mock (최후 수단 — 점수 의미 없음, 서비스 continuity용)
    try:
        import numpy as np

        user_factors = np.random.randn(n_users, n_factors).tolist()
        item_factors = np.random.randn(n_posts, n_factors).tolist()
        log.warning(
            "train_mf_model: MOCK MODE (random factors) — 추천 품질 없음 "
            "(users=%d, posts=%d, factors=%d)",
            n_users, n_posts, n_factors,
        )
        return {"user_factors": user_factors, "item_factors": item_factors}
    except ImportError:
        log.error("train_mf_model: numpy도 미설치 — 학습 완전 불가")
        return None


# ──────────────────────────────────────────────────────────────────────────────
# 모델 저장
# ──────────────────────────────────────────────────────────────────────────────

async def save_model_artifacts(
    db,
    model_result: dict[str, Any],
    interactions: dict[str, Any],
    version: str | None = None,
) -> str | None:
    """학습된 모델을 ml_models 테이블에 저장.

    기존 active 모델 → archived 처리 후 새 모델 active로 등록.
    params에 user_ids, post_ids 매핑 포함하여 추론 시 인덱스 순서 보장.
    반환: 새 모델 id (str) 또는 None (저장 실패)
    """
    from sqlalchemy import text

    if not version:
        version = datetime.now(timezone.utc).strftime("mf-%Y%m%d")

    now = datetime.now(timezone.utc)

    # params: user_factors, item_factors, user_id·post_id 매핑 포함
    params = {
        "user_factors": model_result["user_factors"],
        "item_factors": model_result["item_factors"],
        "user_ids": interactions.get("user_ids", []),
        "post_ids": interactions.get("post_ids", []),
    }

    try:
        # 기존 active 모델 archived 처리
        await db.execute(
            text("UPDATE ml_models SET status = 'archived' WHERE status = 'active'")
        )

        # 새 모델 INSERT
        result = await db.execute(
            text("""
                INSERT INTO ml_models (model_type, version, trained_at, params, status)
                VALUES ('mf', :ver, :ts, :params::jsonb, 'active')
                RETURNING id
            """),
            {"ver": version, "ts": now, "params": json.dumps(params)},
        )
        model_id = str(result.scalar_one())
        await db.commit()

        log.info(
            "save_model_artifacts: 모델 저장 완료 (id=%s, version=%s)", model_id, version
        )
        return model_id

    except Exception as exc:  # noqa: BLE001
        log.error("save_model_artifacts: 저장 실패 — %s", exc)
        try:
            await db.rollback()
        except Exception:  # noqa: BLE001
            pass
        return None


# ──────────────────────────────────────────────────────────────────────────────
# Cron loop — 일 1회 (새벽 3:00 UTC)
# ──────────────────────────────────────────────────────────────────────────────

async def ml_training_cron_loop(
    interval_seconds: int | None = None,
) -> None:
    """ML 학습 cron worker — R-5 격리 패턴.

    interval_seconds: 기본 86400 (24h). env ML_TRAINING_INTERVAL_SECONDS 우선.
    첫 실행은 interval 대기 후 시작 (새벽 3:00 UTC 타이밍은 배포 시각으로 조정).
    에러 발생 시 WARNING 로그 후 다음 주기까지 대기 (서버 재시작 불필요).
    """
    from app.db.session import AsyncSessionLocal

    _interval = interval_seconds or int(
        os.getenv("ML_TRAINING_INTERVAL_SECONDS", "86400")
    )

    log.info("ml_training_cron_loop: 시작 (interval=%ds)", _interval)
    while True:
        await asyncio.sleep(_interval)
        await _push_cron_status("ml_training", "running")
        async with AsyncSessionLocal() as db:
            try:
                log.info("ml_training_cron_loop: 학습 시작")
                interactions = await collect_interactions(db)
                if not interactions:
                    log.warning("ml_training_cron_loop: 데이터 없음 — 스킵")
                    await _push_cron_status("ml_training", "success")
                    continue

                model_result = train_mf_model(interactions)
                if model_result is None:
                    log.warning("ml_training_cron_loop: 학습 실패 — 스킵")
                    await _push_cron_status("ml_training", "success")
                    continue

                model_id = await save_model_artifacts(db, model_result, interactions)
                log.info("ml_training_cron_loop: 완료 (model_id=%s)", model_id)
                await _push_cron_status("ml_training", "success")

            except Exception as exc:  # noqa: BLE001
                log.warning("ml_training_cron_loop: 오류 — %s", exc)
                await _push_cron_status("ml_training", "failed", error=str(exc)[:500])
