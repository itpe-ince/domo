"""ML 임베딩 테이블 (user_embeddings, post_embeddings) + pgvector — Phase 9 L-A.

K-1 collaborative filtering 진입 조건.
pgvector 확장 + ivfflat ANN 인덱스 (vector_cosine_ops).

pgvector 미설치 환경 대응:
  - CREATE EXTENSION IF NOT EXISTS vector: 이미 설치된 경우 idempotent
  - vector 타입을 raw SQL로만 사용하므로 SQLAlchemy Vector 타입 의존 없음

Revision ID: 0066_pgvector_embeddings
Revises: 0065_auto_renew_enabled
Create Date: 2026-05-05
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0066_pgvector_embeddings"
down_revision: Union[str, None] = "0065_auto_renew_enabled"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # pgvector 확장 활성화 (PostgreSQL 16 호환, idempotent)
    # pgvector 미설치 시 이 명령이 실패하지만, 개발 환경에서는
    # docker-compose에서 ankane/pgvector 이미지 사용 권장
    try:
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    except Exception:  # noqa: BLE001
        # pgvector 미설치 환경: WARNING 로그만 남기고 계속 진행
        import logging
        logging.getLogger(__name__).warning(
            "pgvector extension not available — user_embeddings/post_embeddings "
            "tables will be created without vector type. "
            "Install pgvector to enable ANN search."
        )

    # user_embeddings: 사용자 행동 시퀀스 임베딩
    # vector(128): pgvector 설치 시 벡터 타입, 미설치 시 텍스트 타입 fallback
    try:
        op.execute("""
            CREATE TABLE IF NOT EXISTS user_embeddings (
                user_id      UUID         PRIMARY KEY
                                 REFERENCES users(id) ON DELETE CASCADE,
                embedding    vector(128),
                model_version VARCHAR(50)  NOT NULL DEFAULT 'minilm-v1',
                updated_at   TIMESTAMPTZ  NOT NULL DEFAULT now()
            )
        """)
    except Exception:  # noqa: BLE001
        # pgvector 미설치 시 FLOAT[] fallback으로 재시도
        op.execute("""
            CREATE TABLE IF NOT EXISTS user_embeddings (
                user_id      UUID         PRIMARY KEY
                                 REFERENCES users(id) ON DELETE CASCADE,
                embedding    FLOAT[],
                model_version VARCHAR(50)  NOT NULL DEFAULT 'minilm-v1',
                updated_at   TIMESTAMPTZ  NOT NULL DEFAULT now()
            )
        """)

    # post_embeddings: 작품 텍스트/메타 임베딩
    try:
        op.execute("""
            CREATE TABLE IF NOT EXISTS post_embeddings (
                post_id      UUID         PRIMARY KEY
                                 REFERENCES posts(id) ON DELETE CASCADE,
                embedding    vector(128),
                model_version VARCHAR(50)  NOT NULL DEFAULT 'minilm-v1',
                updated_at   TIMESTAMPTZ  NOT NULL DEFAULT now()
            )
        """)
    except Exception:  # noqa: BLE001
        op.execute("""
            CREATE TABLE IF NOT EXISTS post_embeddings (
                post_id      UUID         PRIMARY KEY
                                 REFERENCES posts(id) ON DELETE CASCADE,
                embedding    FLOAT[],
                model_version VARCHAR(50)  NOT NULL DEFAULT 'minilm-v1',
                updated_at   TIMESTAMPTZ  NOT NULL DEFAULT now()
            )
        """)

    # ivfflat ANN 인덱스 (코사인 거리 기준, K-1 ANN 검색용)
    # lists=100: ~1M 행 기준 권장값 (sqrt(rows)); 행 수 증가 시 조정 필요
    # pgvector 미설치 환경에서는 스킵 (graceful)
    try:
        op.execute("""
            CREATE INDEX IF NOT EXISTS ix_post_embeddings_ivfflat
                ON post_embeddings
                USING ivfflat (embedding vector_cosine_ops)
                WITH (lists = 100)
        """)
    except Exception:  # noqa: BLE001
        import logging
        logging.getLogger(__name__).warning(
            "ivfflat index on post_embeddings skipped (pgvector not available)"
        )

    try:
        op.execute("""
            CREATE INDEX IF NOT EXISTS ix_user_embeddings_ivfflat
                ON user_embeddings
                USING ivfflat (embedding vector_cosine_ops)
                WITH (lists = 100)
        """)
    except Exception:  # noqa: BLE001
        import logging
        logging.getLogger(__name__).warning(
            "ivfflat index on user_embeddings skipped (pgvector not available)"
        )

    # updated_at 빠른 조회 인덱스 (batch sweep stale 기준)
    op.create_index("ix_user_embeddings_updated_at", "user_embeddings", ["updated_at"])
    op.create_index("ix_post_embeddings_updated_at", "post_embeddings", ["updated_at"])


def downgrade() -> None:
    op.drop_index("ix_post_embeddings_updated_at", table_name="post_embeddings")
    op.drop_index("ix_user_embeddings_updated_at", table_name="user_embeddings")

    # ivfflat 인덱스 — pgvector 미설치 환경에서는 존재하지 않을 수 있음
    try:
        op.drop_index("ix_post_embeddings_ivfflat", table_name="post_embeddings")
    except Exception:  # noqa: BLE001
        pass

    try:
        op.drop_index("ix_user_embeddings_ivfflat", table_name="user_embeddings")
    except Exception:  # noqa: BLE001
        pass

    op.execute("DROP TABLE IF EXISTS post_embeddings")
    op.execute("DROP TABLE IF EXISTS user_embeddings")
    # pgvector 확장은 다른 테이블/기능이 사용할 수 있으므로 downgrade에서 DROP하지 않음
