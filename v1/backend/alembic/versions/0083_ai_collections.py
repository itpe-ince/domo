"""alembic 0083 — AI 큐레이션 컬렉션 (ai_collections, ai_collection_posts)

Phase 10 K-7: Editor's Pick 자동 생성.
LLM 큐레이션 컬렉션 + 작품 M:N 매핑 테이블.

README 비전 "스토리텔링 hub"와 "히스토리를 두세 개 만든다"를 직접 구현:
  - AI가 매주 주제별 컬렉션 5개를 자동 생성해 Domo를 스토리텔링 허브로 완성
  - 신진 작가 클러스터링으로 발견되기 어려운 작가를 주제 컬렉션으로 조명

down_revision: 0082 (K-4 featured_artist_candidates)
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0083_ai_collections"
down_revision = "0082"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ai_collection_status ENUM 타입 생성
    op.execute("""
        CREATE TYPE ai_collection_status AS ENUM
            ('generating', 'published', 'archived')
    """)

    # ai_collections: 주제별 AI 큐레이션 컬렉션
    op.create_table(
        "ai_collections",
        sa.Column("id", postgresql.UUID(as_uuid=True),
                  server_default=sa.text("uuid_generate_v4()"), primary_key=True),
        sa.Column("week_start", sa.Date(), nullable=False,
                  comment="해당 주 월요일 날짜 (ISO week 기준)"),
        sa.Column("theme", sa.VARCHAR(100), nullable=False,
                  comment="주제 식별자 예: emerging_painters, digital_art_pioneers"),
        sa.Column("title", sa.VARCHAR(200), nullable=True,
                  comment="LLM 생성 한국어 원본 제목 (≤ 30자)"),
        sa.Column("description", sa.TEXT(), nullable=True,
                  comment="LLM 생성 한국어 원본 설명 (2~3문장)"),
        sa.Column("title_translations", postgresql.JSONB(), nullable=False,
                  server_default=sa.text("'{}'::jsonb"),
                  comment='5 locale 번역 {"en": "...", "ja": "...", "zh": "...", "es": "..."}'),
        sa.Column("description_translations", postgresql.JSONB(), nullable=False,
                  server_default=sa.text("'{}'::jsonb"),
                  comment="5 locale 설명 번역"),
        sa.Column("cover_post_id", postgresql.UUID(as_uuid=True), nullable=True,
                  comment="대표 작품 ID (썸네일 소스)"),
        sa.Column("status", postgresql.ENUM(
            "generating", "published", "archived",
            name="ai_collection_status", create_type=False,
        ), nullable=False, server_default="generating"),
        sa.Column("cluster_k", sa.Integer(), nullable=True,
                  comment="KMeans k값 (클러스터링에 사용된 k)"),
        sa.Column("llm_model_version", sa.VARCHAR(50), nullable=True,
                  comment="컬렉션 생성에 사용한 LLM 모델 식별자"),
        sa.Column("admin_note", sa.TEXT(), nullable=True,
                  comment="admin 검수 메모"),
        sa.Column("generated_at", postgresql.TIMESTAMPTZ(), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("published_at", postgresql.TIMESTAMPTZ(), nullable=True),
        sa.ForeignKeyConstraint(
            ["cover_post_id"], ["posts.id"], ondelete="SET NULL"
        ),
    )

    # UNIQUE: 같은 주제는 같은 주에 1개만 (중복 생성 방지)
    op.create_index(
        "uq_ai_collections_theme_week",
        "ai_collections",
        ["theme", "week_start"],
        unique=True,
    )
    # 공개 목록 정렬 인덱스 (status, published_at DESC)
    op.create_index(
        "ix_ai_collections_status_published",
        "ai_collections",
        ["status", "published_at"],
        postgresql_ops={"published_at": "DESC NULLS LAST"},
    )
    # 생성일 인덱스 (admin 검수 큐 정렬)
    op.create_index(
        "ix_ai_collections_generated_at",
        "ai_collections",
        ["generated_at"],
    )

    # ai_collection_posts: 컬렉션-작품 M:N 매핑
    op.create_table(
        "ai_collection_posts",
        sa.Column("id", postgresql.UUID(as_uuid=True),
                  server_default=sa.text("uuid_generate_v4()"), primary_key=True),
        sa.Column("collection_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("post_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False,
                  comment="컬렉션 내 노출 순서 (1-indexed)"),
        sa.Column("ml_score", sa.Float(), nullable=True,
                  comment="클러스터링 시 ML 스코어 (대표성 지표)"),
        sa.ForeignKeyConstraint(
            ["collection_id"], ["ai_collections.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["post_id"], ["posts.id"], ondelete="CASCADE"
        ),
    )

    # 컬렉션별 position 정렬 인덱스
    op.create_index(
        "ix_ai_collection_posts_collection_position",
        "ai_collection_posts",
        ["collection_id", "position"],
    )
    # post 역방향 인덱스 (특정 작품이 포함된 컬렉션 조회)
    op.create_index(
        "ix_ai_collection_posts_post_id",
        "ai_collection_posts",
        ["post_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_ai_collection_posts_post_id", "ai_collection_posts")
    op.drop_index("ix_ai_collection_posts_collection_position", "ai_collection_posts")
    op.drop_table("ai_collection_posts")

    op.drop_index("ix_ai_collections_generated_at", "ai_collections")
    op.drop_index("ix_ai_collections_status_published", "ai_collections")
    op.drop_index("uq_ai_collections_theme_week", "ai_collections")
    op.drop_table("ai_collections")

    op.execute("DROP TYPE IF EXISTS ai_collection_status")
