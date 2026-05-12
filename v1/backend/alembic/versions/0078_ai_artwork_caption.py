"""alembic 0078 — AI 작품 자동 캡션 컬럼 추가 (K-3)

Phase 9 K-3: posts 테이블에 AI 생성 캡션 관련 5개 컬럼 추가.
LLM Gateway(vision 모델)로 작품 이미지를 분석해 자동 캡션을 생성하고
5 locale 번역을 JSONB로 저장한다.

주요 변경:
  - ai_caption TEXT NULL — LLM 생성 원본 캡션 (한국어)
  - ai_caption_locale_translations JSONB DEFAULT '{}' — 5 locale 번역 JSON
  - ai_caption_model_version VARCHAR(50) NULL — 캡션 생성 모델 식별자
  - ai_caption_generated_at TIMESTAMPTZ NULL — 캡션 생성 시각
  - caption_override TEXT NULL — 작가 수동 입력 캡션 (AI 캡션보다 우선)

인덱스:
  - ix_posts_ai_caption_generated_at — NULL 포함 partial (batch sweep 효율화)
  - ix_posts_ai_caption_model_version — NOT NULL partial (stale 재생성 스캔)
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = "0078_ai_artwork_caption"
down_revision: Union[str, None] = "0073_ml_feed_v2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 5개 컬럼 추가 — 모두 NULL 허용으로 하위 호환 유지
    op.add_column("posts", sa.Column("ai_caption", sa.Text(), nullable=True))
    op.add_column(
        "posts",
        sa.Column(
            "ai_caption_locale_translations",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="{}",
            nullable=False,
        ),
    )
    op.add_column(
        "posts",
        sa.Column("ai_caption_model_version", sa.String(50), nullable=True),
    )
    op.add_column(
        "posts",
        sa.Column(
            "ai_caption_generated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
        ),
    )
    op.add_column("posts", sa.Column("caption_override", sa.Text(), nullable=True))

    # batch sweep용 인덱스 — ai_caption_generated_at IS NULL인 포스트 고속 스캔
    op.create_index(
        "ix_posts_ai_caption_generated_at",
        "posts",
        ["ai_caption_generated_at"],
        postgresql_where=sa.text("ai_caption_generated_at IS NULL"),
    )

    # stale 캡션 재생성용 인덱스 — 특정 모델 버전 스캔
    op.create_index(
        "ix_posts_ai_caption_model_version",
        "posts",
        ["ai_caption_model_version"],
        postgresql_where=sa.text("ai_caption_model_version IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "ix_posts_ai_caption_model_version",
        table_name="posts",
        postgresql_where=sa.text("ai_caption_model_version IS NOT NULL"),
    )
    op.drop_index(
        "ix_posts_ai_caption_generated_at",
        table_name="posts",
        postgresql_where=sa.text("ai_caption_generated_at IS NULL"),
    )
    op.drop_column("posts", "caption_override")
    op.drop_column("posts", "ai_caption_generated_at")
    op.drop_column("posts", "ai_caption_model_version")
    op.drop_column("posts", "ai_caption_locale_translations")
    op.drop_column("posts", "ai_caption")
