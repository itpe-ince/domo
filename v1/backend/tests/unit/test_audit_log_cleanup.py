"""Unit tests — audit_log_cleanup_jobs (Phase 11 D-2).

Phase 12 A-1 refactor:
  - 카테고리 1 (SQLAlchemy over-mock) → freezegun + real DB (testcontainers)
  - @pytest.mark.skip 제거
  - AsyncMock db.execute rowcount 대신 실제 PostgreSQL DELETE rowcount 검증
  - cleanup_old_audit_logs 내부 commit()은 patch (real_db_session은 BEGIN 상태이므로)

테스트 항목:
  1. cleanup_old_audit_logs — cutoff 이전 행 삭제, rowcount 반환 (실제 DB)
  2. 삭제 대상 없을 때 rowcount=0 (실제 DB)
  3. 빈 테이블에서 rowcount graceful → 0 반환 (실제 DB)
  4. AUDIT_LOG_RETENTION_DAYS env override (7일) — 모듈 reload로 검증
"""
from __future__ import annotations

import importlib
import os
from contextlib import contextmanager
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from freezegun import freeze_time


# ──────────────────────────────────────────────────────────────────────────────
# 1. 정상 삭제 — cutoff 이전 3행 INSERT → cleanup → deleted=3
# ──────────────────────────────────────────────────────────────────────────────

@freeze_time("2026-05-08 12:00:00")
@pytest.mark.asyncio
async def test_cleanup_deletes_old_rows(real_db_session):
    """cutoff(365일) 이전 audit_log 3건 INSERT → cleanup 실행 → deleted=3.

    freeze_time으로 현재 시각을 2026-05-08로 고정.
    cutoff = 2025-05-08. 366일 전 행 3건 → 모두 삭제됨.
    cleanup_old_audit_logs 내부 commit()은 patch (real_db_session BEGIN 상태 보호).
    """
    from app.models.audit_log import AuditLog
    from app.services.audit_log_cleanup_jobs import cleanup_old_audit_logs

    # 366일 전 날짜 — cutoff(365일 전) 이전 확실
    old_date = datetime(2025, 5, 7, 0, 0, 0, tzinfo=timezone.utc)

    for _ in range(3):
        real_db_session.add(AuditLog(
            action="user.login",
            actor_id=None,
            actor_role=None,
            target_type="user",
            status="success",
            created_at=old_date,
        ))
    await real_db_session.flush()

    # real_db_session은 BEGIN 상태이므로 내부 commit() patch (이중 트랜잭션 방지)
    with patch.object(real_db_session, "commit", new_callable=AsyncMock):
        deleted = await cleanup_old_audit_logs(real_db_session)

    assert deleted == 3
    # rollback은 real_db_session fixture가 자동 처리


# ──────────────────────────────────────────────────────────────────────────────
# 2. 삭제 대상 없으면 deleted=0 — 최근 행만 있을 때
# ──────────────────────────────────────────────────────────────────────────────

@freeze_time("2026-05-08 12:00:00")
@pytest.mark.asyncio
async def test_cleanup_no_rows_no_commit(real_db_session):
    """최근 행(오늘 생성)만 있을 때 cleanup → deleted=0.

    cutoff(365일 전) 이후 날짜 행은 삭제되지 않아야 한다.
    deleted=0이면 commit 미호출 — commit mock으로 검증.
    """
    from app.models.audit_log import AuditLog
    from app.services.audit_log_cleanup_jobs import cleanup_old_audit_logs

    # 오늘 날짜 행 → cutoff 이후 → 삭제 안 됨
    recent_date = datetime(2026, 5, 8, 6, 0, 0, tzinfo=timezone.utc)
    real_db_session.add(AuditLog(
        action="user.login",
        actor_id=None,
        actor_role=None,
        target_type="user",
        status="success",
        created_at=recent_date,
    ))
    await real_db_session.flush()

    mock_commit = AsyncMock()
    with patch.object(real_db_session, "commit", mock_commit):
        deleted = await cleanup_old_audit_logs(real_db_session)

    assert deleted == 0
    # deleted=0이면 commit 미호출 (cleanup_old_audit_logs 로직: if deleted: await db.commit())
    mock_commit.assert_not_awaited()


# ──────────────────────────────────────────────────────────────────────────────
# 3. 빈 테이블 — rowcount=0, `or 0` 로직 검증
# ──────────────────────────────────────────────────────────────────────────────

@freeze_time("2026-05-08 12:00:00")
@pytest.mark.asyncio
async def test_cleanup_rowcount_none(real_db_session):
    """빈 테이블 상태에서 cleanup → deleted=0 (`result.rowcount or 0` 로직).

    asyncpg는 rowcount=0 반환. or 0 처리도 동일하게 0이어야 함.
    """
    from app.services.audit_log_cleanup_jobs import cleanup_old_audit_logs

    # 행 미삽입 상태 → DELETE 결과 rowcount=0
    with patch.object(real_db_session, "commit", new_callable=AsyncMock):
        deleted = await cleanup_old_audit_logs(real_db_session)

    assert deleted == 0


# ──────────────────────────────────────────────────────────────────────────────
# 4. AUDIT_LOG_RETENTION_DAYS env override (모듈 reload — env 전용)
# ──────────────────────────────────────────────────────────────────────────────

@contextmanager
def _patch_env(env_vars: dict):
    """환경변수 임시 설정 후 복원하는 컨텍스트 매니저."""
    old = {k: os.environ.get(k) for k in env_vars}
    os.environ.update(env_vars)
    try:
        yield
    finally:
        for k, v in old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def test_retention_days_env_override():
    """AUDIT_LOG_RETENTION_DAYS=7 → _RETENTION_DAYS=7."""
    with _patch_env({"AUDIT_LOG_RETENTION_DAYS": "7"}):
        import app.services.audit_log_cleanup_jobs as cleanup_module
        importlib.reload(cleanup_module)
        assert cleanup_module._RETENTION_DAYS == 7

    # 복원: 기본값 365
    os.environ.pop("AUDIT_LOG_RETENTION_DAYS", None)
    importlib.reload(cleanup_module)  # type: ignore[possibly-undefined]
    assert cleanup_module._RETENTION_DAYS == 365  # type: ignore[possibly-undefined]
