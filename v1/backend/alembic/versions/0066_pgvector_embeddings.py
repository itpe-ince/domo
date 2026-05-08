"""ML 임베딩 테이블 (user_embeddings, post_embeddings) + pgvector — Phase 9 L-A.

K-1 collaborative filtering 진입 조건.
pgvector 확장 + ivfflat ANN 인덱스 (vector_cosine_ops).

pgvector 미설치 환경 대응:
  - SAVEPOINT(begin_nested)로 EXTENSION/vector 타입/ivfflat 시도를 격리
  - 실패 시 transaction abort 없이 FLOAT[] fallback으로 진행
  - PostgreSQL은 트랜잭션 내 SQL 실패 시 abort 상태가 되므로 SAVEPOINT 필수

Revision ID: 0066_pgvector_embeddings
Revises: 0065_auto_renew_enabled
Create Date: 2026-05-05
"""
from __future__ import annotations

import logging
from typing import Sequence, Union

from alembic import op

revision: str = "0066_pgvector_embeddings"
down_revision: Union[str, None] = "0065_auto_renew_enabled"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

log = logging.getLogger(__name__)


def _try_create_extension() -> bool:
    """SAVEPOINT 안에서 pgvector EXTENSION 생성 시도.

    Returns:
        True: 설치 가능 (이미 설치되어 있거나 새로 설치됨)
        False: 미설치 (FLOAT[] fallback 필요)
    """
    bind = op.get_bind()
    try:
        with bind.begin_nested():
            bind.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS vector")
        return True
    except Exception:  # noqa: BLE001
        log.warning(
            "pgvector extension not available — user_embeddings/post_embeddings "
            "tables will be created with FLOAT[] fallback. "
            "Install pgvector (e.g. pgvector/pgvector:pg16 docker image) for ANN search."
        )
        return False


def upgrade() -> None:
    pgvector_ok = _try_create_extension()
    embedding_type = "vector(128)" if pgvector_ok else "FLOAT[]"

    # user_embeddings: 사용자 행동 시퀀스 임베딩
    op.execute(f"""
        CREATE TABLE IF NOT EXISTS user_embeddings (
            user_id      UUID         PRIMARY KEY
                             REFERENCES users(id) ON DELETE CASCADE,
            embedding    {embedding_type},
            model_version VARCHAR(50)  NOT NULL DEFAULT 'minilm-v1',
            updated_at   TIMESTAMPTZ  NOT NULL DEFAULT now()
        )
    """)

    # post_embeddings: 작품 텍스트/메타 임베딩
    op.execute(f"""
        CREATE TABLE IF NOT EXISTS post_embeddings (
            post_id      UUID         PRIMARY KEY
                             REFERENCES posts(id) ON DELETE CASCADE,
            embedding    {embedding_type},
            model_version VARCHAR(50)  NOT NULL DEFAULT 'minilm-v1',
            updated_at   TIMESTAMPTZ  NOT NULL DEFAULT now()
        )
    """)

    # ivfflat ANN 인덱스 (pgvector 가용 시만)
    # lists=100: ~1M 행 기준 권장값 (sqrt(rows)); 행 수 증가 시 조정 필요
    if pgvector_ok:
        bind = op.get_bind()
        for table_name in ("post_embeddings", "user_embeddings"):
            try:
                with bind.begin_nested():
                    bind.exec_driver_sql(f"""
                        CREATE INDEX IF NOT EXISTS ix_{table_name}_ivfflat
                            ON {table_name}
                            USING ivfflat (embedding vector_cosine_ops)
                            WITH (lists = 100)
                    """)
            except Exception:  # noqa: BLE001
                log.warning(
                    "ivfflat index on %s skipped (vector_cosine_ops 연산자 없음 — pgvector 버전 확인)",
                    table_name,
                )

    # updated_at 빠른 조회 인덱스 (batch sweep stale 기준)
    op.create_index("ix_user_embeddings_updated_at", "user_embeddings", ["updated_at"])
    op.create_index("ix_post_embeddings_updated_at", "post_embeddings", ["updated_at"])


def downgrade() -> None:
    op.drop_index("ix_post_embeddings_updated_at", table_name="post_embeddings")
    op.drop_index("ix_user_embeddings_updated_at", table_name="user_embeddings")

    # ivfflat 인덱스 — pgvector 미설치 환경에서는 존재하지 않을 수 있음
    bind = op.get_bind()
    for index_name, table_name in (
        ("ix_post_embeddings_ivfflat", "post_embeddings"),
        ("ix_user_embeddings_ivfflat", "user_embeddings"),
    ):
        try:
            with bind.begin_nested():
                bind.exec_driver_sql(f"DROP INDEX IF EXISTS {index_name}")
        except Exception:  # noqa: BLE001
            pass

    op.execute("DROP TABLE IF EXISTS post_embeddings")
    op.execute("DROP TABLE IF EXISTS user_embeddings")
    # pgvector 확장은 다른 테이블/기능이 사용할 수 있으므로 downgrade에서 DROP하지 않음
