"""alembic 0072 — cohort_alerts 테이블 추가

Phase 9 L-F: Cohort retention 지표가 임계치 미달 시 Slack으로 자동 알림을 발송하고
중복 알림을 방지하는 이력 테이블.

UNIQUE INDEX on (cohort_date, metric_name) — 같은 날 같은 지표 중복 INSERT 차단.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers
revision: str = "0072_cohort_alerts"
down_revision: Union[str, None] = "0071_translation_cache"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "cohort_alerts",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        # 측정 대상 cohort 날짜 (어제)
        sa.Column("cohort_date", sa.Date(), nullable=False),
        # 지표 이름: d7_retention / d30_retention 등
        sa.Column("metric_name", sa.String(50), nullable=False),
        # 측정값 및 임계값 (0.0000 ~ 1.0000)
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("threshold", sa.Float(), nullable=False),
        # 알림 상태: pending → sent / skipped / error
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        # Slack API 응답 ts — 메시지 추적용 (nullable)
        sa.Column("slack_message_ts", sa.String(50), nullable=True),
        # 발송 실패 시 에러 메시지 (nullable)
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        # 실제 발송 시각 (nullable — pending/skipped/error 상태에서는 NULL)
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
    )

    # 특정 날짜 cohort 중복 알림 방지 UNIQUE 인덱스
    op.create_index(
        "uq_cohort_alerts_date_metric",
        "cohort_alerts",
        ["cohort_date", "metric_name"],
        unique=True,
    )

    # cooldown 조회용 (metric_name + created_at 최신순)
    op.create_index(
        "ix_cohort_alerts_metric_created",
        "cohort_alerts",
        ["metric_name", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_cohort_alerts_metric_created", table_name="cohort_alerts")
    op.drop_index("uq_cohort_alerts_date_metric", table_name="cohort_alerts")
    op.drop_table("cohort_alerts")
