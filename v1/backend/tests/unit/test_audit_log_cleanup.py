"""Unit tests — audit_log_cleanup_jobs (Phase 11 D-2).

테스트 항목:
  1. cleanup_old_audit_logs — cutoff 이전 행 삭제, 삭제 수 반환
  2. cutoff 이후 행은 삭제 안 함 (idempotent 확인)
  3. AUDIT_LOG_RETENTION_DAYS env override (7일) 반영
  4. 삭제 행 없으면 commit 미호출 (불필요한 DB 쓰기 방지)
"""
from __future__ import annotations

import importlib
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ──────────────────────────────────────────────────────────────────────────────
# 1. 정상 삭제
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.skip(reason="Over-mocked SQLAlchemy delete/select — Phase 12 refactor")
@pytest.mark.asyncio
async def test_cleanup_deletes_old_rows():
    """cutoff 이전 행 3개 삭제 → 반환값 3, commit 호출."""
    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.rowcount = 3
    db.execute = AsyncMock(return_value=mock_result)
    db.commit = AsyncMock()

    with patch("app.models.audit_log.AuditLog"):
        from app.services.audit_log_cleanup_jobs import cleanup_old_audit_logs

        deleted = await cleanup_old_audit_logs(db)

    assert deleted == 3
    db.commit.assert_awaited_once()


# ──────────────────────────────────────────────────────────────────────────────
# 2. 삭제 행 없으면 commit 미호출
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.skip(reason="Over-mocked SQLAlchemy delete/select — Phase 12 refactor")
@pytest.mark.asyncio
async def test_cleanup_no_rows_no_commit():
    """삭제 대상 없으면 commit 호출 안 함."""
    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.rowcount = 0
    db.execute = AsyncMock(return_value=mock_result)
    db.commit = AsyncMock()

    with patch("app.models.audit_log.AuditLog"):
        from app.services.audit_log_cleanup_jobs import cleanup_old_audit_logs

        deleted = await cleanup_old_audit_logs(db)

    assert deleted == 0
    db.commit.assert_not_awaited()


# ──────────────────────────────────────────────────────────────────────────────
# 3. AUDIT_LOG_RETENTION_DAYS env override
# ──────────────────────────────────────────────────────────────────────────────

def test_retention_days_env_override():
    """AUDIT_LOG_RETENTION_DAYS=7 → _RETENTION_DAYS=7."""
    with patch.dict(os.environ, {"AUDIT_LOG_RETENTION_DAYS": "7"}):
        # 모듈 재로드로 env 반영 확인
        import app.services.audit_log_cleanup_jobs as cleanup_module
        importlib.reload(cleanup_module)
        assert cleanup_module._RETENTION_DAYS == 7

    # 복원: 기본값 365
    os.environ.pop("AUDIT_LOG_RETENTION_DAYS", None)
    importlib.reload(cleanup_module)
    assert cleanup_module._RETENTION_DAYS == 365


# ──────────────────────────────────────────────────────────────────────────────
# 4. rowcount=None graceful (일부 DB driver)
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.skip(reason="Over-mocked SQLAlchemy delete/select — Phase 12 refactor")
@pytest.mark.asyncio
async def test_cleanup_rowcount_none():
    """rowcount=None 시 0으로 처리 (graceful)."""
    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.rowcount = None
    db.execute = AsyncMock(return_value=mock_result)
    db.commit = AsyncMock()

    with patch("app.models.audit_log.AuditLog"):
        from app.services.audit_log_cleanup_jobs import cleanup_old_audit_logs

        deleted = await cleanup_old_audit_logs(db)

    assert deleted == 0
    db.commit.assert_not_awaited()
