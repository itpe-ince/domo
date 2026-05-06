"""번역 메모리 서비스 — Phase 9 L-F.

LLM Gateway 번역 결과를 DB(translation_cache 테이블)와 Redis(24h TTL)에 캐싱해
중복 번역 호출을 차단한다.

캐시 조회 흐름:
  1. Redis GET translation:{source_hash}:{source_lang}:{target_lang}
     └─ hit → 즉시 반환 (DB 접근 없음, 최속)
  ↓ miss
  2. DB SELECT WHERE source_hash=? AND source_lang=? AND target_lang=?
     └─ hit → hit_count++, last_used_at=now() → Redis SET(24h) → 반환
  ↓ miss
  3. LLM Gateway 호출
     └─ DB INSERT → Redis SET(24h) → 반환

설계 결정:
  - source_hash: SHA-256 hex 64자 (MD5 대비 충돌 확률 무시 가능 수준)
  - INSERT ON CONFLICT DO NOTHING: 동시 요청 시 안전
  - Mock 번역 결과는 model_version='mock-gateway'로 저장
    → 프로덕션 전환 시 DELETE WHERE model_version='mock-gateway'로 일괄 삭제 가능
"""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.translation_cache import TranslationCache
from app.services.cache import cache

log = logging.getLogger(__name__)

# Redis TTL: 24시간
_REDIS_TTL_SECONDS = 86400


def compute_source_hash(text: str) -> str:
    """SHA-256 hex digest 계산 (utf-8 인코딩).

    동일 텍스트는 항상 동일 해시를 반환한다 (deterministic).
    """
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _redis_key(source_hash: str, source_lang: str, target_lang: str) -> str:
    """Redis 키 형식: translation:{hash}:{source_lang}:{target_lang}"""
    return f"translation:{source_hash}:{source_lang}:{target_lang}"


async def get_cached_translation(
    db: AsyncSession,
    source_text: str,
    source_lang: str,
    target_lang: str,
) -> str | None:
    """번역 캐시 조회. Redis → DB 순으로 조회.

    Returns:
        번역 결과 문자열, 또는 캐시 miss 시 None.

    Side effects (DB hit 시):
        - hit_count 1 증가
        - last_used_at 현재 시각으로 갱신
    Side effects (Redis miss + DB hit 시):
        - Redis에 24h TTL로 캐싱
    """
    source_hash = compute_source_hash(source_text)

    # 1단계: Redis 조회
    redis_key = _redis_key(source_hash, source_lang, target_lang)
    redis_hit = await cache.get_json(redis_key, prefix="translation")
    if redis_hit is not None:
        log.debug(
            "translation_cache: Redis hit %s→%s hash=%s...",
            source_lang, target_lang, source_hash[:8],
        )
        return redis_hit.get("text")

    # 2단계: DB 조회
    result = await db.execute(
        select(TranslationCache).where(
            TranslationCache.source_hash == source_hash,
            TranslationCache.source_lang == source_lang,
            TranslationCache.target_lang == target_lang,
        )
    )
    row = result.scalar_one_or_none()

    if row is None:
        log.debug(
            "translation_cache: DB miss %s→%s hash=%s...",
            source_lang, target_lang, source_hash[:8],
        )
        return None

    # DB hit — hit_count++, last_used_at 갱신
    await db.execute(
        update(TranslationCache)
        .where(TranslationCache.id == row.id)
        .values(
            hit_count=TranslationCache.hit_count + 1,
            last_used_at=datetime.now(timezone.utc),
        )
    )
    await db.commit()

    # Redis에 24h TTL로 backfill
    await cache.set_json(
        redis_key,
        {"text": row.translated_text, "model": row.model_version},
        ttl_seconds=_REDIS_TTL_SECONDS,
        prefix="translation",
    )

    log.debug(
        "translation_cache: DB hit %s→%s hash=%s... hit_count=%d",
        source_lang, target_lang, source_hash[:8], row.hit_count + 1,
    )
    return row.translated_text


async def save_translation(
    db: AsyncSession,
    source_text: str,
    source_lang: str,
    target_lang: str,
    translated_text: str,
    model_version: str,
) -> None:
    """번역 결과를 DB + Redis에 저장.

    INSERT ON CONFLICT DO NOTHING — 동시 요청 시 중복 INSERT 안전.
    Redis에도 24h TTL로 캐싱.
    """
    source_hash = compute_source_hash(source_text)

    # DB INSERT (ON CONFLICT DO NOTHING)
    stmt = pg_insert(TranslationCache).values(
        source_hash=source_hash,
        source_lang=source_lang,
        target_lang=target_lang,
        source_text=source_text,
        translated_text=translated_text,
        model_version=model_version,
        hit_count=0,
        created_at=datetime.now(timezone.utc),
        last_used_at=datetime.now(timezone.utc),
    )
    stmt = stmt.on_conflict_do_nothing(
        index_elements=["source_hash", "source_lang", "target_lang"]
    )
    await db.execute(stmt)
    await db.commit()

    # Redis에 24h TTL로 캐싱
    redis_key = _redis_key(source_hash, source_lang, target_lang)
    await cache.set_json(
        redis_key,
        {"text": translated_text, "model": model_version},
        ttl_seconds=_REDIS_TTL_SECONDS,
        prefix="translation",
    )

    log.debug(
        "translation_cache: saved %s→%s hash=%s... model=%s",
        source_lang, target_lang, source_hash[:8], model_version,
    )


async def cleanup_old_cache_entries(db: AsyncSession, days: int = 90) -> int:
    """90일 이상 미사용 캐시 행 삭제. 삭제 건수 반환.

    gdpr_cron_loop 내에서 1일 1회 실행으로 통합한다 (cron 수 최소화).
    """
    from datetime import timedelta
    from sqlalchemy import delete as sa_delete

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    result = await db.execute(
        sa_delete(TranslationCache).where(TranslationCache.last_used_at < cutoff)
    )
    await db.commit()
    deleted = result.rowcount
    if deleted:
        log.info("translation_cache: cleanup removed %d rows (older than %d days)", deleted, days)
    return deleted
