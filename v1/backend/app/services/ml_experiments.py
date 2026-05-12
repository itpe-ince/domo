"""ML A/B 테스트 서비스 — Phase 10 K-8.

주요 기능:
  - get_user_variant(): 사용자 variant 조회 또는 생성 (PostHog flag 결과 영속화)
  - record_event(): PostHog 이벤트 발화 + Prometheus metric 갱신
  - cleanup_old_experiments(): 90일 이전 completed 실험 assignments 정리

Mock 모드:
  - POSTHOG_API_KEY 미설정 → 모든 사용자 v1 + WARNING 로그
  - ml_experiments 테이블에 running 실험 없음 → variant='v1' (default)

L-B 통합:
  - newsletter_events 테이블은 K-8 results endpoint에서 보조 지표로만 활용.
  - 재발명 없이 기존 L-B 인프라 그대로 사용.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.posthog_client import posthog_client

log = logging.getLogger(__name__)

# 환경변수 기반 설정 (기본값: design §7)
_EXPERIMENT_NAME = os.getenv("ML_AB_EXPERIMENT_NAME", "feed_v2_rollout")
_POSTHOG_FLAG_KEY = os.getenv("ML_AB_FLAG_KEY", "ml_feed_v2")
_DEFAULT_VARIANT = "v1"  # POSTHOG_API_KEY 미설정 시 전 사용자 v1


async def get_user_variant(
    db: AsyncSession,
    experiment_name: str,
    user_id: str,
) -> str:
    """사용자의 실험 variant 반환. 없으면 PostHog flag 조회 후 DB 영속화.

    반환: 'v1' 또는 'v2'
    우선순위:
      1. ml_experiment_assignments 기존 레코드 (재방문 일관성)
      2. PostHog feature flag 조회 (신규 할당)
      3. Mock fallback → 'v1' (POSTHOG_API_KEY 미설정)
    """
    # 1. running 실험 조회
    exp_result = await db.execute(
        text("""
            SELECT id FROM ml_experiments
            WHERE name = :name AND status = 'running'
            LIMIT 1
        """),
        {"name": experiment_name},
    )
    exp_row = exp_result.fetchone()
    if exp_row is None:
        log.debug(
            "get_user_variant: running 실험 없음 ('%s') → v1 default",
            experiment_name,
        )
        return _DEFAULT_VARIANT

    experiment_id = str(exp_row.id)

    # 2. 기존 할당 확인 (재방문 일관성)
    assign_result = await db.execute(
        text("""
            SELECT variant FROM ml_experiment_assignments
            WHERE experiment_id = :exp_id AND user_id = :uid
            LIMIT 1
        """),
        {"exp_id": experiment_id, "uid": user_id},
    )
    assign_row = assign_result.fetchone()
    if assign_row is not None:
        log.debug(
            "get_user_variant: 기존 할당 HIT (user=%s, variant=%s)",
            user_id, assign_row.variant,
        )
        return assign_row.variant

    # 3. PostHog feature flag 조회 → variant 결정
    flag_on = await posthog_client.get_feature_flag(_POSTHOG_FLAG_KEY, user_id)
    variant = "v2" if flag_on else "v1"

    # 4. DB 영속화 (race condition 안전: ON CONFLICT DO NOTHING)
    try:
        await db.execute(
            text("""
                INSERT INTO ml_experiment_assignments (experiment_id, user_id, variant)
                VALUES (:exp_id, :uid, :variant)
                ON CONFLICT ON CONSTRAINT uq_mea_experiment_user DO NOTHING
            """),
            {"exp_id": experiment_id, "uid": user_id, "variant": variant},
        )
        await db.commit()
    except Exception as exc:  # noqa: BLE001
        log.warning(
            "get_user_variant: INSERT 실패 (%s) — variant=%s 반환",
            exc, variant,
        )
        await db.rollback()

    # Prometheus metric 갱신
    _increment_assignments_metric(variant)

    log.info(
        "get_user_variant: 신규 할당 (user=%s, experiment=%s, variant=%s)",
        user_id, experiment_name, variant,
    )
    return variant


async def record_event(
    experiment_name: str,
    user_id: str,
    event_type: str,
    metadata: dict[str, Any] | None = None,
) -> None:
    """PostHog 이벤트 발화 + Prometheus metric 갱신.

    event_type: 'feed_post_click' | 'sponsor_created' | 'session_end' | ...
    비동기 fire-and-forget: 실패해도 응답 지연 없음.
    """
    props = {"experiment": experiment_name, "user_id": user_id}
    if metadata:
        props.update(metadata)

    try:
        await posthog_client.capture(event_type, user_id, props)
        _increment_events_metric(event_type)
        if event_type == "sponsor_created":
            _increment_conversions_metric()
    except Exception as exc:  # noqa: BLE001
        log.warning("record_event: PostHog 발화 실패 (%s)", exc)


async def cleanup_old_experiments(db: AsyncSession, days: int = 90) -> int:
    """90일 이전 ml_experiment_assignments 정리.

    completed 상태 실험의 assignments만 삭제.
    running/paused 실험은 보존 (데이터 보호).
    반환: 삭제된 레코드 수
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    try:
        result = await db.execute(
            text("""
                DELETE FROM ml_experiment_assignments mea
                USING ml_experiments me
                WHERE mea.experiment_id = me.id
                  AND me.status = 'completed'
                  AND mea.assigned_at < :cutoff
            """),
            {"cutoff": cutoff},
        )
        await db.commit()
        deleted = result.rowcount
        log.info(
            "cleanup_old_experiments: %d 레코드 삭제 (cutoff=%s)",
            deleted, cutoff,
        )
        return deleted
    except Exception as exc:  # noqa: BLE001
        log.warning("cleanup_old_experiments: 실패 (%s)", exc)
        await db.rollback()
        return 0


# ── Prometheus metric helpers ─────────────────────────────────────────────────
# app.core.metrics 모듈에서 ML_AB_* 메트릭을 import.
# prometheus_client 미설치 시 graceful (no-op stubs).


def _increment_assignments_metric(variant: str) -> None:
    """ml_ab_test_assignments_total{variant=...} +1."""
    try:
        from app.core.metrics import ML_AB_ASSIGNMENTS  # type: ignore[attr-defined]
        ML_AB_ASSIGNMENTS.labels(variant=variant).inc()
    except Exception:  # noqa: BLE001
        pass  # metrics 미등록 또는 prometheus_client 미설치 시 무시


def _increment_events_metric(event_type: str) -> None:
    """ml_ab_test_events_total{event_type=...} +1."""
    try:
        from app.core.metrics import ML_AB_EVENTS  # type: ignore[attr-defined]
        ML_AB_EVENTS.labels(event_type=event_type).inc()
    except Exception:  # noqa: BLE001
        pass


def _increment_conversions_metric() -> None:
    """ml_ab_test_conversions_total +1."""
    try:
        from app.core.metrics import ML_AB_CONVERSIONS  # type: ignore[attr-defined]
        ML_AB_CONVERSIONS.inc()
    except Exception:  # noqa: BLE001
        pass
