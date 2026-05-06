"""llm_docent: posts 테이블에 도슨트 컬럼 추가 — K-5

Phase 9 K-5: 작품 상세 페이지에 AI 도슨트(큐레이터 해설) 기능을 추가한다.
작가가 직접 작성한 해설(artist_docent_text)과 LLM이 생성한 해설(ai_docent_text)을
hybrid 방식으로 제공한다.

README 비전 "스토리텔링 hub"과 "AI 시대 작가의 정체성 재정의"를 직접 구현하는 migration.
K-3 AI 캡션(1~2문장)과 달리 K-5는 3~5문단 큐레이터 톤 해설을 제공한다.

주요 변경:
  - artist_docent_text TEXT NULL — 작가가 직접 작성한 해설 (우선 노출)
  - ai_docent_text TEXT NULL — LLM 생성 원본 해설 (한국어)
  - ai_docent_translations JSONB DEFAULT '{}' — 5 locale 번역 캐시
  - ai_docent_model_version VARCHAR(50) NULL — 생성 모델 식별자
  - ai_docent_generated_at TIMESTAMPTZ NULL — AI 도슨트 최초 생성 시각
  - ai_docent_opted_out BOOLEAN DEFAULT FALSE — 작가 AI 도슨트 비활성화

인덱스:
  - ix_posts_ai_docent_generated_at — IS NOT NULL partial (어드민/분석용)

Revision ID: 0079_llm_docent
Revises: 0078_ai_artwork_caption
Create Date: 2026-05-05
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = "0079_llm_docent"
down_revision: Union[str, None] = "0078_ai_artwork_caption"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 작가 직접 작성 해설 — AI 해설보다 항상 우선 노출
    op.add_column(
        "posts",
        sa.Column("artist_docent_text", sa.Text(), nullable=True),
    )

    # LLM 생성 원본 해설 (한국어) — K-3 caption_text와 목적이 다름 (3~5문단)
    op.add_column(
        "posts",
        sa.Column("ai_docent_text", sa.Text(), nullable=True),
    )

    # 5 locale 번역 캐시 JSONB — {"en": "...", "ja": "...", "zh": "...", "es": "..."}
    # L-F translation_cache가 원본 캐시를 담당하므로 denormalize 저장 (JOIN 없이 빠른 조회)
    op.add_column(
        "posts",
        sa.Column(
            "ai_docent_translations",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="{}",
            nullable=False,
        ),
    )

    # 생성에 사용된 모델 식별자 (예: gemma4-e4b)
    op.add_column(
        "posts",
        sa.Column("ai_docent_model_version", sa.String(50), nullable=True),
    )

    # AI 도슨트 최초 생성 시각 — 24h idempotency 체크용
    op.add_column(
        "posts",
        sa.Column(
            "ai_docent_generated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
        ),
    )

    # 작가 AI 도슨트 비활성화 플래그 — DEFAULT FALSE (신규 포스트는 기본 활성화)
    # 작가가 명시적으로 거부해야 비활성화 (opt-out 방식)
    op.add_column(
        "posts",
        sa.Column(
            "ai_docent_opted_out",
            sa.Boolean(),
            server_default=sa.text("FALSE"),
            nullable=False,
        ),
    )

    # AI 도슨트 생성된 포스트 조회용 partial 인덱스 (어드민/분석)
    op.create_index(
        "ix_posts_ai_docent_generated_at",
        "posts",
        ["ai_docent_generated_at"],
        postgresql_where=sa.text("ai_docent_generated_at IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "ix_posts_ai_docent_generated_at",
        table_name="posts",
        postgresql_where=sa.text("ai_docent_generated_at IS NOT NULL"),
    )
    op.drop_column("posts", "ai_docent_opted_out")
    op.drop_column("posts", "ai_docent_generated_at")
    op.drop_column("posts", "ai_docent_model_version")
    op.drop_column("posts", "ai_docent_translations")
    op.drop_column("posts", "ai_docent_text")
    op.drop_column("posts", "artist_docent_text")
