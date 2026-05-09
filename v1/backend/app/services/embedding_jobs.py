"""임베딩 batch cron worker — Phase 9 L-A (ML 임베딩 인프라).

R-5 격리 패턴 준수:
  - 별도 파일 (embedding_jobs.py)
  - AsyncSessionLocal 독립 사용
  - 개별 try/except DB rollback

동작:
  1. quick_sweep_once: 신규 user/post (임베딩 NULL) 즉시 처리 — 60초 주기
  2. batch_sweep_once: stale (updated_at < now() - 23h) 전체 갱신 — 86400초 주기

환경변수:
  EMBEDDING_WORKER_ENABLED: false로 설정 시 cron worker 등록 건너뜀 (main.py 제어)
  EMBEDDING_BATCH_SIZE: batch당 처리 건수 (default: 100)
  EMBEDDING_QUICK_INTERVAL_SECONDS: 신규 감지 주기 (default: 60초)
  EMBEDDING_BATCH_INTERVAL_SECONDS: 전체 batch 주기 (default: 86400초 = 24h)
"""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone

from sqlalchemy import text

from app.db.session import AsyncSessionLocal
from app.services import embedding_model
from app.services.cron_monitor import record_cron_run as _push_cron_status

log = logging.getLogger(__name__)

_BATCH_SIZE: int = int(os.getenv("EMBEDDING_BATCH_SIZE", "100"))
_QUICK_INTERVAL: int = int(os.getenv("EMBEDDING_QUICK_INTERVAL_SECONDS", "60"))
_BATCH_INTERVAL: int = int(os.getenv("EMBEDDING_BATCH_INTERVAL_SECONDS", "86400"))
_QUICK_SWEEP_LIMIT: int = 20  # 신규 감지 1회 최대 처리 건수


# ──────────────────────────────────────────────────────────────────────────────
# 단위 업데이트
# ──────────────────────────────────────────────────────────────────────────────

async def update_user_embedding(db, user_id: str) -> None:
    """단일 사용자 임베딩 계산 후 upsert.

    행동 시퀀스: behavioral_history 최근 200건 event_type 텍스트를 공백 join.
    behavioral_history 없을 시 "new_user" 텍스트 사용.
    모델 없을 시 zero vector (Mock 모드).

    Args:
        db: AsyncSession 인스턴스
        user_id: 대상 사용자 UUID 문자열
    """
    try:
        result = await db.execute(
            text("""
                SELECT event_type
                FROM behavioral_history
                WHERE user_id = :uid
                ORDER BY occurred_at DESC
                LIMIT 200
            """),
            {"uid": user_id},
        )
        rows = result.fetchall()
        sequence = " ".join(r.event_type for r in rows) if rows else "new_user"

        vectors = embedding_model.encode([sequence])
        vector = vectors[0]
        version = embedding_model.get_model_version()
        now = datetime.now(timezone.utc)

        await db.execute(
            text("""
                INSERT INTO user_embeddings (user_id, embedding, model_version, updated_at)
                VALUES (:uid, :emb::text::vector, :ver, :ts)
                ON CONFLICT (user_id) DO UPDATE
                    SET embedding     = EXCLUDED.embedding,
                        model_version = EXCLUDED.model_version,
                        updated_at    = EXCLUDED.updated_at
            """),
            {"uid": user_id, "emb": str(vector), "ver": version, "ts": now},
        )
        await db.commit()
        log.debug("update_user_embedding: user_id=%s done", user_id)
    except Exception as exc:  # noqa: BLE001
        log.warning("update_user_embedding: user_id=%s failed: %s", user_id, exc)
        try:
            await db.rollback()
        except Exception:  # noqa: BLE001
            pass


async def update_post_embedding(db, post_id: str) -> None:
    """단일 작품 임베딩 계산 후 upsert.

    텍스트 소스: title + body(첫 500자) + tags join.
    post를 찾을 수 없는 경우 WARNING 로그 후 조용히 반환.

    Args:
        db: AsyncSession 인스턴스
        post_id: 대상 작품 UUID 문자열
    """
    try:
        result = await db.execute(
            text("""
                SELECT title, body, tags
                FROM posts
                WHERE id = :pid
            """),
            {"pid": post_id},
        )
        row = result.fetchone()
        if row is None:
            log.warning("update_post_embedding: post %s not found, skip", post_id)
            return

        tags_str = " ".join(row.tags or []) if row.tags else ""
        body_snippet = (row.body or "")[:500]
        text_input = f"{row.title or ''} {body_snippet} {tags_str}".strip() or "untitled"

        vectors = embedding_model.encode([text_input])
        vector = vectors[0]
        version = embedding_model.get_model_version()
        now = datetime.now(timezone.utc)

        await db.execute(
            text("""
                INSERT INTO post_embeddings (post_id, embedding, model_version, updated_at)
                VALUES (:pid, :emb::text::vector, :ver, :ts)
                ON CONFLICT (post_id) DO UPDATE
                    SET embedding     = EXCLUDED.embedding,
                        model_version = EXCLUDED.model_version,
                        updated_at    = EXCLUDED.updated_at
            """),
            {"pid": post_id, "emb": str(vector), "ver": version, "ts": now},
        )
        await db.commit()
        log.debug("update_post_embedding: post_id=%s done", post_id)
    except Exception as exc:  # noqa: BLE001
        log.warning("update_post_embedding: post_id=%s failed: %s", post_id, exc)
        try:
            await db.rollback()
        except Exception:  # noqa: BLE001
            pass


# ──────────────────────────────────────────────────────────────────────────────
# Quick sweep (신규 감지, 60초 주기)
# ──────────────────────────────────────────────────────────────────────────────

async def quick_sweep_once(db, batch_size: int = _QUICK_SWEEP_LIMIT) -> dict[str, int]:
    """신규 user/post (임베딩 NULL) 최대 batch_size건 즉시 처리.

    idempotent: 이미 embedding이 있는 row는 SELECT에서 제외.

    Args:
        db: AsyncSession 인스턴스
        batch_size: 1회 sweep 최대 처리 건수 (default: 20)

    Returns:
        {"users": n, "posts": n} — 처리된 건수
    """
    counts: dict[str, int] = {"users": 0, "posts": 0}

    # 임베딩 없는 신규 users
    try:
        result = await db.execute(
            text("""
                SELECT u.id FROM users u
                LEFT JOIN user_embeddings ue ON ue.user_id = u.id
                WHERE ue.user_id IS NULL
                ORDER BY u.created_at DESC
                LIMIT :lim
            """),
            {"lim": batch_size},
        )
        user_ids = [str(r.id) for r in result.fetchall()]
    except Exception as exc:  # noqa: BLE001
        log.warning("quick_sweep_once: user query failed: %s", exc)
        user_ids = []

    for uid in user_ids:
        await update_user_embedding(db, uid)
        counts["users"] += 1

    # 임베딩 없는 신규 posts
    try:
        result = await db.execute(
            text("""
                SELECT p.id FROM posts p
                LEFT JOIN post_embeddings pe ON pe.post_id = p.id
                WHERE pe.post_id IS NULL
                ORDER BY p.created_at DESC
                LIMIT :lim
            """),
            {"lim": batch_size},
        )
        post_ids = [str(r.id) for r in result.fetchall()]
    except Exception as exc:  # noqa: BLE001
        log.warning("quick_sweep_once: post query failed: %s", exc)
        post_ids = []

    for pid in post_ids:
        await update_post_embedding(db, pid)
        counts["posts"] += 1

    if counts["users"] or counts["posts"]:
        log.info("quick_sweep_once done: %s", counts)
    return counts


# ──────────────────────────────────────────────────────────────────────────────
# Batch sweep (전체 stale 갱신, 86400초 주기)
# ──────────────────────────────────────────────────────────────────────────────

async def batch_sweep_once(db, batch_size: int = _BATCH_SIZE) -> dict[str, int]:
    """전체 user + post 임베딩 일괄 갱신 (idempotent).

    stale 기준: updated_at < now() - 23h
    (일 1회 interval 86400s보다 약간 짧게 설정하여 누락 방지)

    Args:
        db: AsyncSession 인스턴스
        batch_size: 1회 batch 최대 처리 건수 (default: 100)

    Returns:
        {"users": n, "posts": n} — 처리된 건수
    """
    stale_cutoff = datetime.now(timezone.utc) - timedelta(hours=23)
    counts: dict[str, int] = {"users": 0, "posts": 0}

    # Stale or missing users
    try:
        result = await db.execute(
            text("""
                SELECT u.id FROM users u
                LEFT JOIN user_embeddings ue ON ue.user_id = u.id
                WHERE ue.user_id IS NULL OR ue.updated_at < :cutoff
                ORDER BY u.created_at
                LIMIT :lim
            """),
            {"cutoff": stale_cutoff, "lim": batch_size},
        )
        user_ids = [str(r.id) for r in result.fetchall()]
    except Exception as exc:  # noqa: BLE001
        log.warning("batch_sweep_once: user query failed: %s", exc)
        user_ids = []

    for uid in user_ids:
        try:
            await update_user_embedding(db, uid)
            counts["users"] += 1
        except Exception as exc:  # noqa: BLE001
            log.warning("batch_sweep_once: user %s failed: %s", uid, exc)

    # Stale or missing posts
    try:
        result = await db.execute(
            text("""
                SELECT p.id FROM posts p
                LEFT JOIN post_embeddings pe ON pe.post_id = p.id
                WHERE pe.post_id IS NULL OR pe.updated_at < :cutoff
                ORDER BY p.created_at
                LIMIT :lim
            """),
            {"cutoff": stale_cutoff, "lim": batch_size},
        )
        post_ids = [str(r.id) for r in result.fetchall()]
    except Exception as exc:  # noqa: BLE001
        log.warning("batch_sweep_once: post query failed: %s", exc)
        post_ids = []

    for pid in post_ids:
        try:
            await update_post_embedding(db, pid)
            counts["posts"] += 1
        except Exception as exc:  # noqa: BLE001
            log.warning("batch_sweep_once: post %s failed: %s", pid, exc)

    log.info("batch_sweep_once done: %s", counts)
    return counts


# ──────────────────────────────────────────────────────────────────────────────
# Cron loop (R-5 격리)
# ──────────────────────────────────────────────────────────────────────────────

async def embedding_cron_loop(
    quick_interval_seconds: int = _QUICK_INTERVAL,
    batch_interval_seconds: int = _BATCH_INTERVAL,
) -> None:
    """두 주기 cron loop — R-5 격리 패턴.

    - quick sweep: quick_interval_seconds(60s) 마다 신규 user/post 즉시 처리
    - batch sweep: batch_interval_seconds(86400s) 마다 전체 stale 갱신

    EMBEDDING_WORKER_ENABLED=false 시 main.py에서 이 함수 자체를 등록하지 않음.

    Args:
        quick_interval_seconds: 신규 감지 주기 (초, default: 60)
        batch_interval_seconds: 전체 batch 주기 (초, default: 86400)
    """
    log.info(
        "embedding_cron_loop started (quick=%ss, batch=%ss)",
        quick_interval_seconds,
        batch_interval_seconds,
    )
    batch_counter: int = 0

    while True:
        await asyncio.sleep(quick_interval_seconds)
        batch_counter += quick_interval_seconds

        await _push_cron_status("embedding", "running")
        try:
            async with AsyncSessionLocal() as db:
                # 신규 감지: 임베딩 없는 최신 user/post 소수만 즉시 처리
                await quick_sweep_once(db)

                # 일 1회 전체 batch sweep
                if batch_counter >= batch_interval_seconds:
                    await batch_sweep_once(db)
                    batch_counter = 0
            await _push_cron_status("embedding", "success")
        except Exception as exc:  # noqa: BLE001
            log.warning("embedding_cron_loop error: %s", exc)
            await _push_cron_status("embedding", "failed", error=str(exc)[:500])
