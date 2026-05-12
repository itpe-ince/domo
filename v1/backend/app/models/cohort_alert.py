"""CohortAlert 모델 — Phase 9 L-F Cohort Retention 알림 이력.

D7/D30 retention 지표 임계치 미달 시 Slack 알림을 발송하고 이력을 저장한다.
UNIQUE INDEX on (cohort_date, metric_name) — 같은 날 같은 지표 중복 알림 차단.

status 흐름:
  pending → sent      (Slack 발송 성공)
  pending → skipped   (24h cooldown — 이미 sent 이력 존재, 또는 SLACK_WEBHOOK_URL 미설정)
  pending → error     (Slack 발송 실패)
"""
from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, Index, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CohortAlert(Base):
    """Cohort retention 알림 이력 테이블."""

    __tablename__ = "cohort_alerts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # 측정 대상 cohort 날짜 (어제)
    cohort_date: Mapped[date] = mapped_column(Date, nullable=False)

    # 지표 이름: d7_retention / d30_retention
    metric_name: Mapped[str] = mapped_column(String(50), nullable=False)

    # 측정값 및 임계값 (0.0 ~ 1.0)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    threshold: Mapped[float] = mapped_column(Float, nullable=False)

    # 알림 상태: pending / sent / skipped / error
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending", server_default="pending"
    )

    # Slack API 응답 ts — 메시지 추적용 (nullable)
    slack_message_ts: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # 발송 실패 시 에러 메시지 (nullable)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # 실제 발송 시각 (nullable — pending/skipped/error 상태에서는 NULL)
    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        # 같은 날 같은 지표 중복 알림 방지
        UniqueConstraint(
            "cohort_date", "metric_name",
            name="uq_cohort_alerts_date_metric",
        ),
        # cooldown 조회용 (metric_name + created_at 최신순)
        Index("ix_cohort_alerts_metric_created", "metric_name", "created_at"),
    )
