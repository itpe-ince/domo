"""alembic 0081 — Diversity Reranking Config (diversity_configs)

Phase 10 K-2: 필터 버블 방지 + 신진작가 부스팅 설정 테이블.
- diversity_configs: 운영 중 튜닝 가능한 다양성 제약 파라미터 저장
- 초기 seed: 'feed_default' active 레코드 (Phase 10 K-2 OQ 수락값)

down_revision: 0079_llm_docent (현재 최신 revision)
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = "0081_diversity_config"
down_revision: str = "0080_ml_experiments"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # diversity_configs — 운영 중 튜닝 가능한 다양성 설정 테이블
    op.create_table(
        "diversity_configs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "name",
            sa.String(50),
            unique=True,
            nullable=False,
            comment="설정 식별자 (예: 'feed_default'). UNIQUE",
        ),
        sa.Column(
            "emerging_artist_boost",
            sa.Float,
            nullable=False,
            server_default="1.20",
            comment="신진작가 스코어 배수 (OQ 결정: 1.20)",
        ),
        sa.Column(
            "genre_min_diversity",
            sa.Integer,
            nullable=False,
            server_default="3",
            comment="top_k_window 내 최소 unique 장르 수 (OQ 결정: 3)",
        ),
        sa.Column(
            "region_min_diversity",
            sa.Integer,
            nullable=False,
            server_default="2",
            comment="top_k_window 내 최소 unique 지역 수 (OQ 결정: 2)",
        ),
        sa.Column(
            "top_k_window",
            sa.Integer,
            nullable=False,
            server_default="20",
            comment="다양성 제약 적용 window 크기 (최종 피드 노출 수)",
        ),
        sa.Column(
            "candidate_pool_size",
            sa.Integer,
            nullable=False,
            server_default="100",
            comment="K-1에서 가져올 후보 수 (reranking pool)",
        ),
        sa.Column(
            "status",
            sa.Enum("active", "archived", name="diversity_config_status_enum"),
            nullable=False,
            server_default="active",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    # 활성 config 빠른 조회 인덱스
    op.create_index(
        "ix_diversity_configs_name_status",
        "diversity_configs",
        ["name", "status"],
    )

    # 초기 seed: feed_default (Phase 10 K-2 OQ 수락값)
    op.execute(
        """
        INSERT INTO diversity_configs
            (name, emerging_artist_boost, genre_min_diversity, region_min_diversity,
             top_k_window, candidate_pool_size, status)
        VALUES
            ('feed_default', 1.20, 3, 2, 20, 100, 'active')
        """
    )


def downgrade() -> None:
    op.drop_index("ix_diversity_configs_name_status", table_name="diversity_configs")
    op.drop_table("diversity_configs")
    op.execute("DROP TYPE IF EXISTS diversity_config_status_enum")
