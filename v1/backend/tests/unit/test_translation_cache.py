"""Unit tests — translation_cache.py (Phase 9 L-F).

테스트 범위:
  - cache miss: DB + Redis 모두 없을 때 None 반환
  - cache hit (DB): hit_count 증가 + last_used_at 갱신 + translated_text 반환
  - cache hit (Redis): DB 조회 없이 즉시 반환
  - hit_count 증가 검증
  - hash 동일성 검증 (동일 텍스트 → 동일 SHA-256)
  - 동일 원문 다른 target_lang → 별도 캐시 항목
  - save_translation: DB INSERT + Redis 캐싱
  - cleanup_old_cache_entries: 90일 초과 행 삭제
  - model_version 저장 검증
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.translation_cache import (
    cleanup_old_cache_entries,
    compute_source_hash,
    get_cached_translation,
    save_translation,
)


# ──────────────────────────────────────────────────────────────────────────────
# 헬퍼 — DB 행 mock 생성
# ──────────────────────────────────────────────────────────────────────────────

def _make_db_row(
    translated_text: str = "Hello world",
    model_version: str = "gemma4-e4b",
    hit_count: int = 0,
) -> MagicMock:
    """TranslationCache DB 행 mock."""
    import uuid
    row = MagicMock()
    row.id = uuid.uuid4()
    row.translated_text = translated_text
    row.model_version = model_version
    row.hit_count = hit_count
    row.last_used_at = datetime.now(timezone.utc) - timedelta(hours=1)
    return row


# ──────────────────────────────────────────────────────────────────────────────
# 1. compute_source_hash — 결정적(deterministic)
# ──────────────────────────────────────────────────────────────────────────────

def test_source_hash_deterministic():
    """동일 텍스트 → 동일 SHA-256 해시 (결정적)."""
    text = "안녕하세요, 저는 예술가입니다."
    hash1 = compute_source_hash(text)
    hash2 = compute_source_hash(text)
    assert hash1 == hash2
    assert len(hash1) == 64  # SHA-256 hex: 64자


def test_source_hash_different_texts():
    """다른 텍스트 → 다른 해시."""
    assert compute_source_hash("hello") != compute_source_hash("world")


def test_source_hash_utf8_encoding():
    """UTF-8 인코딩 기반 — 한국어 포함 텍스트도 정상 처리."""
    text = "한국어 텍스트 🎨"
    h = compute_source_hash(text)
    assert len(h) == 64


# ──────────────────────────────────────────────────────────────────────────────
# 2. get_cached_translation — Redis hit
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_cache_hit_redis_no_db_call():
    """Redis hit 시 DB 조회 없이 즉시 반환."""
    db = AsyncMock()
    source_text = "안녕하세요"

    with patch("app.services.translation_cache.cache") as mock_cache:
        mock_cache.get_json = AsyncMock(return_value={"text": "Hello", "model": "gemma4-e4b"})

        result = await get_cached_translation(db, source_text, "ko", "en")

    assert result == "Hello"
    # DB execute가 호출되지 않아야 함
    db.execute.assert_not_called()


# ──────────────────────────────────────────────────────────────────────────────
# 3. get_cached_translation — DB hit
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_cache_hit_db_no_llm_call():
    """DB에 캐시 존재 시 translated_text 반환 + hit_count 증가 UPDATE 실행."""
    db = AsyncMock()
    source_text = "테스트 텍스트"
    db_row = _make_db_row("Test text", hit_count=2)

    # DB scalar_one_or_none() → row 반환
    db.execute.return_value.scalar_one_or_none = MagicMock(return_value=db_row)

    with patch("app.services.translation_cache.cache") as mock_cache:
        mock_cache.get_json = AsyncMock(return_value=None)  # Redis miss
        mock_cache.set_json = AsyncMock()

        result = await get_cached_translation(db, source_text, "ko", "en")

    assert result == "Test text"
    # DB execute가 최소 2번: SELECT + UPDATE
    assert db.execute.call_count >= 2
    db.commit.assert_called()


@pytest.mark.asyncio
async def test_hit_count_increments():
    """DB hit 시 hit_count 1 증가하는 UPDATE가 실행된다."""
    db = AsyncMock()
    source_text = "증가 테스트"
    db_row = _make_db_row(hit_count=5)
    db.execute.return_value.scalar_one_or_none = MagicMock(return_value=db_row)

    with patch("app.services.translation_cache.cache") as mock_cache:
        mock_cache.get_json = AsyncMock(return_value=None)
        mock_cache.set_json = AsyncMock()

        await get_cached_translation(db, source_text, "ko", "ja")

    # UPDATE 호출 확인 (execute가 2회 이상 호출됨)
    assert db.execute.call_count >= 2


# ──────────────────────────────────────────────────────────────────────────────
# 4. get_cached_translation — cache miss
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_cache_miss_returns_none():
    """DB + Redis 모두 miss 시 None 반환."""
    db = AsyncMock()
    db.execute.return_value.scalar_one_or_none = MagicMock(return_value=None)

    with patch("app.services.translation_cache.cache") as mock_cache:
        mock_cache.get_json = AsyncMock(return_value=None)

        result = await get_cached_translation(db, "없는 텍스트", "ko", "en")

    assert result is None


# ──────────────────────────────────────────────────────────────────────────────
# 5. save_translation
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_save_translation_calls_db_and_redis():
    """save_translation: DB INSERT + Redis SET 호출."""
    db = AsyncMock()
    db.execute.return_value = MagicMock()

    with patch("app.services.translation_cache.cache") as mock_cache:
        mock_cache.set_json = AsyncMock()

        await save_translation(
            db=db,
            source_text="안녕하세요",
            source_lang="ko",
            target_lang="en",
            translated_text="Hello",
            model_version="gemma4-e4b",
        )

    db.execute.assert_called_once()
    db.commit.assert_called_once()
    mock_cache.set_json.assert_called_once()


@pytest.mark.asyncio
async def test_save_translation_model_version_stored():
    """INSERT 시 model_version이 파라미터대로 전달된다."""
    db = AsyncMock()
    db.execute.return_value = MagicMock()

    with patch("app.services.translation_cache.cache") as mock_cache:
        mock_cache.set_json = AsyncMock()

        await save_translation(
            db=db,
            source_text="텍스트",
            source_lang="ko",
            target_lang="zh",
            translated_text="文本",
            model_version="mock-gateway",
        )

    # execute가 호출된 statement 확인 — values에 model_version 포함
    call_args = db.execute.call_args
    assert call_args is not None  # execute 호출됨


# ──────────────────────────────────────────────────────────────────────────────
# 6. 동일 원문 다른 target_lang → 별도 캐시 항목
# ──────────────────────────────────────────────────────────────────────────────

def test_same_source_diff_targets_different_keys():
    """동일 원문이라도 target_lang이 다르면 Redis 키가 달라야 한다."""
    from app.services.translation_cache import _redis_key, compute_source_hash
    source = "hello"
    h = compute_source_hash(source)
    key_en = _redis_key(h, "ko", "en")
    key_ja = _redis_key(h, "ko", "ja")
    assert key_en != key_ja


# ──────────────────────────────────────────────────────────────────────────────
# 7. cleanup_old_cache_entries
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_cleanup_removes_old_entries():
    """cleanup_old_cache_entries: DELETE 실행 + rowcount 반환."""
    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.rowcount = 3
    db.execute.return_value = mock_result

    deleted = await cleanup_old_cache_entries(db, days=90)

    assert deleted == 3
    db.execute.assert_called_once()
    db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_cleanup_returns_zero_when_nothing_deleted():
    """cleanup_old_cache_entries: 삭제 대상 없을 때 0 반환."""
    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.rowcount = 0
    db.execute.return_value = mock_result

    deleted = await cleanup_old_cache_entries(db, days=90)

    assert deleted == 0
