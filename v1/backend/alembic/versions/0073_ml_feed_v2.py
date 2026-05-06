"""alembic 0073 — ML Feed v2 (user_post_interactions + ml_models)

Phase 9 K-1: Collaborative Filtering 피드 v2 사전 조건.
- user_post_interactions: implicit feedback 수집 (view/like/comment/sponsor/click)
- ml_models: 학습된 MF 모델 메타데이터 + params JSONB 저장

Depends: 0072_cohort_alerts (L-F), 0066_pgvector_embeddings (L-A)
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0073_ml_feed_v2"
down_revision = "0072_cohort_alerts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # user_post_interactions — implicit feedback 원본 로그
    op.create_table(
        "user_post_interactions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "post_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("posts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "interaction_type",
            sa.Enum(
                "view", "like", "comment", "sponsor", "click",
                name="interaction_type_enum",
            ),
            nullable=False,
        ),
        sa.Column(
            "weight",
            sa.Float,
            nullable=False,
            server_default="1.0",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    # 인덱스: 사용자별 최신 순 조회 (학습 데이터 수집)
    op.create_index(
        "ix_upi_user_id_created_at",
        "user_post_interactions",
        ["user_id", sa.text("created_at DESC")],
    )
    # 인덱스: 포스트별 최신 순 조회 (인기도 집계)
    op.create_index(
        "ix_upi_post_id_created_at",
        "user_post_interactions",
        ["post_id", sa.text("created_at DESC")],
    )
    # 인덱스: 학습 데이터 기간 필터 (90일 슬라이딩 윈도우)
    op.create_index(
        "ix_upi_created_at",
        "user_post_interactions",
        ["created_at"],
    )

    # ml_models — 학습된 모델 메타데이터
    op.create_table(
        "ml_models",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "model_type",
            sa.Enum("mf", "two_tower", name="ml_model_type_enum"),
            nullable=False,
            server_default="mf",
        ),
        sa.Column("version", sa.String(50), nullable=False),
        sa.Column(
            "trained_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("params", postgresql.JSONB, nullable=True),
        sa.Column(
            "status",
            sa.Enum("training", "active", "archived", name="ml_model_status_enum"),
            nullable=False,
            server_default="training",
        ),
    )
    # 활성 모델 빠른 조회 인덱스
    op.create_index(
        "ix_ml_models_status_trained_at",
        "ml_models",
        ["status", sa.text("trained_at DESC")],
    )


def downgrade() -> None:
    op.drop_index("ix_ml_models_status_trained_at", table_name="ml_models")
    op.drop_table("ml_models")
    op.execute("DROP TYPE IF EXISTS ml_model_status_enum")
    op.execute("DROP TYPE IF EXISTS ml_model_type_enum")

    op.drop_index("ix_upi_created_at", table_name="user_post_interactions")
    op.drop_index("ix_upi_post_id_created_at", table_name="user_post_interactions")
    op.drop_index("ix_upi_user_id_created_at", table_name="user_post_interactions")
    op.drop_table("user_post_interactions")
    op.execute("DROP TYPE IF EXISTS interaction_type_enum")
