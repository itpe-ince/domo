"""ML 임베딩 모델 싱글톤 로더 — Phase 9 L-A.

모델: sentence-transformers paraphrase-multilingual-MiniLM-L12-v2
  - KO/EN multilingual 지원
  - 128차원 출력 (pooled, normalized)
  - self-hosted ECS ML worker docker container

Mock 모드:
  EMBEDDING_MODEL_PATH 미설정 또는 모델 로드 실패 시 자동 활성화.
  → encode() 호출 시 zero vector(128) 반환 + WARNING 로그 출력
  → CI/CD, 로컬 개발 환경에서 ML 의존 없이 빌드·테스트 통과 보장

환경변수:
  EMBEDDING_MODEL_PATH: 모델 경로 (미설정 시 Mock 모드)
  EMBEDDING_WORKER_ENABLED: false로 설정 시 cron worker 등록 건너뜀 (main.py 제어)
"""
from __future__ import annotations

import logging
import os
from typing import Optional

log = logging.getLogger(__name__)

# 싱글톤 상태
_MODEL: Optional[object] = None
_MOCK_MODE: bool = False
_INITIALIZED: bool = False
_MODEL_VERSION: str = "minilm-v1"
_EMBED_DIM: int = 128


def _load_model() -> None:
    """최초 호출 시 1회 로드 (lazy init, singleton).

    EMBEDDING_MODEL_PATH 미설정 → Mock 모드 자동 활성화.
    sentence-transformers 패키지 미설치 → Mock 모드 fallback.
    """
    global _MODEL, _MOCK_MODE, _INITIALIZED

    _INITIALIZED = True
    model_path = os.getenv("EMBEDDING_MODEL_PATH", "").strip()

    if not model_path:
        log.warning(
            "EMBEDDING_MODEL_PATH not set — embedding_model running in MOCK MODE "
            "(zero vectors). Set EMBEDDING_MODEL_PATH to enable real embeddings."
        )
        _MOCK_MODE = True
        return

    try:
        from sentence_transformers import SentenceTransformer  # type: ignore
        _MODEL = SentenceTransformer(model_path)
        log.info(
            "Embedding model loaded from %s (dim=%d, version=%s)",
            model_path,
            _EMBED_DIM,
            _MODEL_VERSION,
        )
    except ImportError:
        log.warning(
            "sentence-transformers package not installed — falling back to MOCK MODE. "
            "Install sentence-transformers to enable real embeddings."
        )
        _MOCK_MODE = True
    except Exception as exc:  # noqa: BLE001
        log.warning(
            "Failed to load embedding model from %s: %s — falling back to MOCK MODE",
            model_path,
            exc,
        )
        _MOCK_MODE = True


def get_model_version() -> str:
    """현재 모델 식별자 반환."""
    return _MODEL_VERSION


def is_mock_mode() -> bool:
    """Mock 모드 여부 반환 (테스트 및 헬스체크용)."""
    if not _INITIALIZED:
        _load_model()
    return _MOCK_MODE


def encode(texts: list[str]) -> list[list[float]]:
    """텍스트 리스트 → 128차원 float 벡터 리스트.

    Mock 모드: zero vector [[0.0] * 128, ...] 반환.
    실제 모드: sentence-transformers encode + L2 normalize → 128차원 슬라이스.

    Args:
        texts: 인코딩할 텍스트 목록 (빈 리스트 OK)

    Returns:
        각 텍스트에 대한 128차원 float 리스트
    """
    global _MODEL, _MOCK_MODE

    # 최초 호출 시 lazy init
    if not _INITIALIZED:
        _load_model()

    if not texts:
        return []

    if _MOCK_MODE or _MODEL is None:
        # Mock 모드: zero vector 반환
        return [[0.0] * _EMBED_DIM for _ in texts]

    try:
        embeddings = _MODEL.encode(  # type: ignore[attr-defined]
            texts,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        # 128차원 슬라이스 (모델 출력이 더 클 경우 대비)
        return [list(map(float, e[:_EMBED_DIM])) for e in embeddings]
    except Exception as exc:  # noqa: BLE001
        log.warning("encode() failed: %s — returning zero vectors", exc)
        return [[0.0] * _EMBED_DIM for _ in texts]
