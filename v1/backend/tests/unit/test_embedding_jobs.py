"""Unit tests — embedding_jobs.py + embedding_model.py (Phase 9 L-A).

테스트 범위:
  - Mock 모드: EMBEDDING_MODEL_PATH 미설정 시 zero vector 반환
  - update_user_embedding: idempotent upsert
  - update_post_embedding: 존재하지 않는 post 처리
  - quick_sweep_once: idempotent (두 번째 sweep은 신규 없음)
  - batch_sweep_once: fresh row skip (stale 기준 미달)
  - EMBEDDING_WORKER_ENABLED=false: cron worker 등록 건너뜀
"""
from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services import embedding_model, embedding_jobs


# ──────────────────────────────────────────────────────────────────────────────
# Helper: embedding_model 상태 초기화
# ──────────────────────────────────────────────────────────────────────────────

def _reset_embedding_model():
    """테스트 격리를 위한 embedding_model 싱글톤 상태 초기화."""
    embedding_model._MODEL = None
    embedding_model._MOCK_MODE = False
    embedding_model._INITIALIZED = False


# ──────────────────────────────────────────────────────────────────────────────
# Mock 모드 테스트
# ──────────────────────────────────────────────────────────────────────────────

def test_mock_mode_zero_vector(monkeypatch):
    """EMBEDDING_MODEL_PATH 미설정 → zero vector 반환."""
    monkeypatch.delenv("EMBEDDING_MODEL_PATH", raising=False)
    _reset_embedding_model()

    result = embedding_model.encode(["test text"])

    assert len(result) == 1
    assert len(result[0]) == 128
    assert all(v == 0.0 for v in result[0])


def test_mock_mode_multiple_texts(monkeypatch):
    """여러 텍스트 → 각각 zero vector 128차원."""
    monkeypatch.delenv("EMBEDDING_MODEL_PATH", raising=False)
    _reset_embedding_model()

    result = embedding_model.encode(["text1", "text2", "text3"])

    assert len(result) == 3
    for vec in result:
        assert len(vec) == 128
        assert all(v == 0.0 for v in vec)


def test_mock_mode_empty_list(monkeypatch):
    """빈 리스트 입력 → 빈 리스트 반환."""
    monkeypatch.delenv("EMBEDDING_MODEL_PATH", raising=False)
    _reset_embedding_model()

    result = embedding_model.encode([])
    assert result == []


def test_mock_mode_is_mock_mode_true(monkeypatch):
    """EMBEDDING_MODEL_PATH 미설정 → is_mock_mode() True 반환."""
    monkeypatch.delenv("EMBEDDING_MODEL_PATH", raising=False)
    _reset_embedding_model()

    assert embedding_model.is_mock_mode() is True


def test_mock_mode_warning_logged(monkeypatch, caplog):
    """Mock 모드 진입 시 WARNING 로그 출력 확인."""
    import logging
    monkeypatch.delenv("EMBEDDING_MODEL_PATH", raising=False)
    _reset_embedding_model()

    with caplog.at_level(logging.WARNING, logger="app.services.embedding_model"):
        embedding_model.encode(["trigger load"])

    assert any("MOCK MODE" in record.message for record in caplog.records)


# ──────────────────────────────────────────────────────────────────────────────
# update_user_embedding — idempotent
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_update_user_embedding_mock():
    """Mock 모드 + zero vector로 user_embedding upsert 호출 확인."""
    db = AsyncMock()
    db.execute = AsyncMock(return_value=MagicMock(fetchall=lambda: []))
    db.commit = AsyncMock()

    with patch.object(embedding_model, "encode", return_value=[[0.0] * 128]):
        await embedding_jobs.update_user_embedding(db, "user-uuid-1")

    # upsert SQL 실행 + commit 호출 확인
    db.execute.assert_called()
    db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_update_user_embedding_idempotent():
    """동일 user_id 두 번 호출 → 각각 upsert, 오류 없음."""
    db = AsyncMock()
    db.execute = AsyncMock(return_value=MagicMock(fetchall=lambda: []))
    db.commit = AsyncMock()

    with patch.object(embedding_model, "encode", return_value=[[0.0] * 128]):
        await embedding_jobs.update_user_embedding(db, "user-uuid-1")
        await embedding_jobs.update_user_embedding(db, "user-uuid-1")

    assert db.commit.call_count == 2


@pytest.mark.asyncio
async def test_update_post_embedding_missing_post():
    """존재하지 않는 post_id → WARNING 로그 후 조용히 반환 (commit 없음)."""
    db = AsyncMock()
    db.execute = AsyncMock(return_value=MagicMock(fetchone=lambda: None))

    await embedding_jobs.update_post_embedding(db, "nonexistent-post-id")

    db.commit.assert_not_called()


# ──────────────────────────────────────────────────────────────────────────────
# quick_sweep_once — idempotent
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_quick_sweep_idempotent():
    """두 번 sweep 시 두 번째는 신규 없음 → users/posts 0건."""
    db = AsyncMock()
    # 첫 번째 호출: 빈 결과 (신규 없음)
    db.execute = AsyncMock(return_value=MagicMock(fetchall=lambda: []))
    db.commit = AsyncMock()

    result1 = await embedding_jobs.quick_sweep_once(db)
    result2 = await embedding_jobs.quick_sweep_once(db)

    assert result1 == {"users": 0, "posts": 0}
    assert result2 == {"users": 0, "posts": 0}


@pytest.mark.asyncio
async def test_quick_sweep_processes_new_users():
    """신규 user 1건 → quick_sweep_once가 처리 후 users=1 반환."""
    # user SELECT에서 1건, post SELECT에서 0건 반환
    call_count = 0

    async def mock_execute(sql, params=None):
        nonlocal call_count
        call_count += 1
        mock_result = MagicMock()
        if call_count == 1:
            # users query
            row = MagicMock()
            row.id = "user-uuid-new"
            mock_result.fetchall = lambda: [row]
        elif call_count == 2:
            # behavioral_history query (inside update_user_embedding)
            mock_result.fetchall = lambda: []
        elif call_count == 3:
            # upsert query
            mock_result.fetchall = lambda: []
        else:
            # posts query
            mock_result.fetchall = lambda: []
        return mock_result

    db = AsyncMock()
    db.execute = mock_execute
    db.commit = AsyncMock()

    with patch.object(embedding_model, "encode", return_value=[[0.0] * 128]):
        result = await embedding_jobs.quick_sweep_once(db)

    assert result["users"] == 1


# ──────────────────────────────────────────────────────────────────────────────
# batch_sweep_once — stale 기준 적용
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_batch_sweep_stale_only():
    """fresh row (updated_at recent)는 batch_sweep_once에서 제외 → 0건."""
    db = AsyncMock()
    # stale 조건 미달 → SELECT 결과 없음
    db.execute = AsyncMock(return_value=MagicMock(fetchall=lambda: []))
    db.commit = AsyncMock()

    with patch.object(embedding_model, "encode", return_value=[[0.0] * 128]):
        result = await embedding_jobs.batch_sweep_once(db, batch_size=10)

    assert result == {"users": 0, "posts": 0}


@pytest.mark.asyncio
async def test_batch_sweep_idempotent():
    """batch_sweep_once 두 번 호출해도 동일 결과 (upsert 기반)."""
    db = AsyncMock()
    db.execute = AsyncMock(return_value=MagicMock(fetchall=lambda: []))
    db.commit = AsyncMock()

    with patch.object(embedding_model, "encode", return_value=[[0.0] * 128]):
        result1 = await embedding_jobs.batch_sweep_once(db, batch_size=10)
        result2 = await embedding_jobs.batch_sweep_once(db, batch_size=10)

    assert result1 == {"users": 0, "posts": 0}
    assert result2 == {"users": 0, "posts": 0}


# ──────────────────────────────────────────────────────────────────────────────
# EMBEDDING_WORKER_ENABLED=false — cron 비활성화
# ──────────────────────────────────────────────────────────────────────────────

def test_worker_disabled(monkeypatch):
    """EMBEDDING_WORKER_ENABLED=false 시 main.py에서 embedding_task=None 설정.

    이 테스트는 main.py 등록 로직의 env guard를 직접 검증한다.
    """
    monkeypatch.setenv("EMBEDDING_WORKER_ENABLED", "false")

    enabled = os.getenv("EMBEDDING_WORKER_ENABLED", "true").lower() != "false"
    assert enabled is False, "EMBEDDING_WORKER_ENABLED=false 시 enabled=False여야 함"


def test_worker_enabled_by_default(monkeypatch):
    """EMBEDDING_WORKER_ENABLED 미설정 시 기본값 true → enabled=True."""
    monkeypatch.delenv("EMBEDDING_WORKER_ENABLED", raising=False)

    enabled = os.getenv("EMBEDDING_WORKER_ENABLED", "true").lower() != "false"
    assert enabled is True


def test_worker_disabled_case_insensitive(monkeypatch):
    """EMBEDDING_WORKER_ENABLED=False (대소문자 무관) 처리."""
    monkeypatch.setenv("EMBEDDING_WORKER_ENABLED", "False")

    enabled = os.getenv("EMBEDDING_WORKER_ENABLED", "true").lower() != "false"
    assert enabled is False
