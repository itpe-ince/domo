"""alembic 0080 — ML A/B 테스트 인프라 (ml_experiments + ml_experiment_assignments)

Phase 10 K-8: PostHog Feature Flag 기반 A/B 테스트 영속화.
- ml_experiments: 실험 메타데이터 (이름, 상태, 분배 비율, 측정 지표)
- ml_experiment_assignments: 사용자별 variant 영속화 (재방문 일관성)

Depends: 0079_llm_docent (Phase 9 K-5)
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0080_ml_experiments"
down_revision: str = "0079_llm_docent"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── ml_experiments: 실험 메타데이터 ──────────────────────────────────────
    op.create_table(
        "ml_experiments",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.Column(
            "status",
            sa.Enum("draft", "running", "paused", "completed",
                    name="ml_experiment_status_enum"),
            nullable=False,
            server_default="draft",
        ),
        sa.Column(
            "variant_distribution",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text('\'{"v1": 0.5, "v2": 0.5}\''),
        ),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "ended_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column("target_metric", sa.String(50), nullable=True),
        sa.Column("hypothesis", sa.Text, nullable=True),
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
    # status + started_at 복합 인덱스 (running 실험 빠른 조회)
    op.create_index(
        "ix_ml_experiments_status_started",
        "ml_experiments",
        ["status", "started_at"],
    )

    # ── ml_experiment_assignments: 사용자별 variant 영속화 ────────────────────
    op.create_table(
        "ml_experiment_assignments",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "experiment_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ml_experiments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("variant", sa.String(20), nullable=False),
        sa.Column(
            "assigned_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    # UNIQUE: 사용자당 실험당 1개 variant만 (재방문 일관성 핵심 제약)
    op.create_unique_constraint(
        "uq_mea_experiment_user",
        "ml_experiment_assignments",
        ["experiment_id", "user_id"],
    )
    # 분석용 인덱스: experiment + variant 집계
    op.create_index(
        "ix_mea_experiment_variant",
        "ml_experiment_assignments",
        ["experiment_id", "variant"],
    )
    # cleanup 인덱스: assigned_at 기준 90일 보존 정책 적용
    op.create_index(
        "ix_mea_assigned_at",
        "ml_experiment_assignments",
        ["assigned_at"],
    )

    # ── seed: 초기 feed_v2_rollout 실험 데이터 삽입 ─────────────────────────
    op.execute(
        sa.text("""
            INSERT INTO ml_experiments (name, status, variant_distribution, target_metric, hypothesis)
            VALUES (
              'feed_v2_rollout',
              'running',
              '{"v1": 0.5, "v2": 0.5}',
              'feed_ctr',
              'ML 협업 필터링(v2) 피드가 룰 기반(v1) 피드 대비 CTR을 15% 이상 향상시킨다'
            )
        """)
    )


def downgrade() -> None:
    op.drop_index("ix_mea_assigned_at", table_name="ml_experiment_assignments")
    op.drop_index("ix_mea_experiment_variant", table_name="ml_experiment_assignments")
    op.drop_constraint("uq_mea_experiment_user", "ml_experiment_assignments",
                       type_="unique")
    op.drop_table("ml_experiment_assignments")

    op.drop_index("ix_ml_experiments_status_started", table_name="ml_experiments")
    op.drop_table("ml_experiments")
    op.execute("DROP TYPE IF EXISTS ml_experiment_status_enum")
