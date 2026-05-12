"""alembic 0071 — translation_cache 테이블 추가

Phase 9 L-F: tuzigroup LLM Gateway 번역 결과를 DB에 영구 저장해
중복 번역 호출을 차단하는 번역 메모리 테이블.

source_hash UNIQUE INDEX로 O(1) cache lookup 지원.
last_used_at 인덱스로 90일 미사용 캐시 cleanup cron 지원.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers
revision: str = "0071_translation_cache"
down_revision: Union[str, None] = "0070_cognitive_simple_mode"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # uuid_generate_v4() 사용을 위한 uuid-ossp extension 활성화 (멱등)
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    op.create_table(
        "translation_cache",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
            nullable=False,
        ),
        # SHA-256 hex digest of source_text (utf-8 인코딩)
        sa.Column("source_hash", sa.String(64), nullable=False),
        sa.Column("source_lang", sa.String(5), nullable=False),
        sa.Column("target_lang", sa.String(5), nullable=False),
        # 원문 전체 — 해시 충돌 방지 + 모델 변경 시 내용 검증용
        sa.Column("source_text", sa.Text(), nullable=False),
        sa.Column("translated_text", sa.Text(), nullable=False),
        # LLM 모델 식별자 — 모델 업그레이드 시 구 버전 캐시 일괄 invalidate 가능
        sa.Column("model_version", sa.String(50), nullable=False),
        # cache hit 누적 횟수 (0 = 최초 번역, LLM 호출 직후 INSERT)
        sa.Column(
            "hit_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        # TTL cleanup cron 기준 컬럼 — hit 시마다 갱신
        sa.Column(
            "last_used_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    # cache lookup 기본 UNIQUE 인덱스 (source_hash, source_lang, target_lang)
    op.create_index(
        "uq_translation_cache_hash_langs",
        "translation_cache",
        ["source_hash", "source_lang", "target_lang"],
        unique=True,
    )

    # 90일 cleanup cron용 last_used_at 인덱스
    op.create_index(
        "ix_translation_cache_last_used_at",
        "translation_cache",
        ["last_used_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_translation_cache_last_used_at", table_name="translation_cache")
    op.drop_index("uq_translation_cache_hash_langs", table_name="translation_cache")
    op.drop_table("translation_cache")
