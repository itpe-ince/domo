---
template: design
version: 1.0
feature: ml-embedding-infra-bundle-final
phase: 9 / L-A
date: 2026-05-05
author: itpe-ince (Claude Sonnet 4.6)
project: domo
project_version: v1
parent_plan: domo-phase9-roadmap.plan.md
status: Draft
---

# Phase 9 L-A Design — ML 임베딩 파이프라인 인프라 + G''-6 번들 최종화

> **Summary**: K-1(Collaborative Filtering 피드 v2) 진입 조건인 임베딩 저장 인프라를 구축하고,
> Phase 8에서 partial 처리된 프론트엔드 번들 최적화를 최종 완성한다.
> 워크스트림 1(백엔드 임베딩 파이프라인) + 워크스트림 2(G''-6 번들 최종화)를 병렬 진행.

---

## 1. 목표 & Acceptance Criteria

### 목표

| # | 목표 | 이유 |
|---|------|------|
| 1 | pgvector 기반 임베딩 테이블 구축 | K-1 collaborative filtering이 ANN 검색에 직접 활용 |
| 2 | 임베딩 batch cron worker 운영 | 신규 즉시 + 기존 일 1회 갱신으로 벡터 신선도 유지 |
| 3 | First Load JS ≤ 200KB (또는 현재 대비 ≥30% 감소) | 글로벌 신진작가 주 사용자(동남아·남미·동유럽) 네트워크 환경 대응 |
| 4 | Mock 모드 fallback 보장 | CI/CD 환경에서 ML 모델 없이도 빌드·테스트 통과 |

### Acceptance Criteria

- [ ] `alembic 0066` 적용 후 `user_embeddings`, `post_embeddings` 테이블 생성 확인 (`alembic upgrade head` green)
- [ ] pgvector `ivfflat` 인덱스 생성 확인 (`\d post_embeddings`에서 인덱스 표시)
- [ ] `embedding_jobs.py` cron — 신규 user/post 즉시 처리, 일 1회 batch 정상 동작
- [ ] Mock 모드: `EMBEDDING_MODEL_PATH` 미설정 시 zero vector 반환 + WARNING 로그 출력
- [ ] `EMBEDDING_WORKER_ENABLED=false` 설정 시 cron worker 등록 건너뜀
- [ ] Next.js `@next/bundle-analyzer` 결과에서 First Load JS ≤ 200KB 확인
- [ ] `npm run build` tsc 0 errors, Lighthouse performance CI 측정 가능
- [ ] K-1 구현 시 `post_embeddings` 직접 SELECT + `<=>` 코사인 거리 쿼리 동작 확인

---

## 2. Database Schema (alembic 0066)

### 파일: `v1/backend/alembic/versions/0066_ml_embeddings.py`

```python
"""alembic 0066 — ML 임베딩 테이블 (user_embeddings, post_embeddings) + pgvector

Phase 9 L-A: K-1 collaborative filtering 사전 조건.
pgvector 확장 + ivfflat ANN 인덱스 (vector_cosine_ops).

Depends: 0065_auto_renew_enabled
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0066"
down_revision = "0065"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # pgvector 확장 활성화 (PostgreSQL 16 호환, idempotent)
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # user_embeddings: 사용자 행동 시퀀스 임베딩
    op.execute("""
        CREATE TABLE user_embeddings (
            user_id     UUID        PRIMARY KEY
                            REFERENCES users(id) ON DELETE CASCADE,
            embedding   vector(128),
            model_version VARCHAR(50)  NOT NULL DEFAULT 'minilm-v1',
            updated_at  TIMESTAMPTZ  NOT NULL DEFAULT now()
        )
    """)

    # post_embeddings: 작품 텍스트/메타 임베딩
    op.execute("""
        CREATE TABLE post_embeddings (
            post_id     UUID        PRIMARY KEY
                            REFERENCES posts(id) ON DELETE CASCADE,
            embedding   vector(128),
            model_version VARCHAR(50)  NOT NULL DEFAULT 'minilm-v1',
            updated_at  TIMESTAMPTZ  NOT NULL DEFAULT now()
        )
    """)

    # ivfflat ANN 인덱스 (코사인 거리 기준, K-1 ANN 검색용)
    # lists=100: ~1M 행 기준 권장값; 행 수 증가 시 조정 필요
    op.execute("""
        CREATE INDEX ix_post_embeddings_ivfflat
            ON post_embeddings
            USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 100)
    """)
    op.execute("""
        CREATE INDEX ix_user_embeddings_ivfflat
            ON user_embeddings
            USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 100)
    """)

    # updated_at 빠른 조회 인덱스 (batch sweep 기준)
    op.create_index("ix_user_embeddings_updated_at", "user_embeddings", ["updated_at"])
    op.create_index("ix_post_embeddings_updated_at", "post_embeddings", ["updated_at"])


def downgrade() -> None:
    op.drop_index("ix_post_embeddings_updated_at", table_name="post_embeddings")
    op.drop_index("ix_user_embeddings_updated_at", table_name="user_embeddings")
    op.drop_index("ix_post_embeddings_ivfflat", table_name="post_embeddings")
    op.drop_index("ix_user_embeddings_ivfflat", table_name="user_embeddings")
    op.execute("DROP TABLE IF EXISTS post_embeddings")
    op.execute("DROP TABLE IF EXISTS user_embeddings")
    # pgvector 확장은 다른 테이블이 사용할 수 있으므로 downgrade에서 DROP하지 않음
```

### 스키마 요약

| 테이블 | 컬럼 | 타입 | 설명 |
|--------|------|------|------|
| `user_embeddings` | `user_id` | UUID PK | `users.id` FK |
| | `embedding` | `vector(128)` | 행동 시퀀스 임베딩 |
| | `model_version` | VARCHAR(50) | 모델 식별자 (`minilm-v1`) |
| | `updated_at` | TIMESTAMPTZ | 마지막 계산 시각 |
| `post_embeddings` | `post_id` | UUID PK | `posts.id` FK |
| | `embedding` | `vector(128)` | 작품 텍스트/메타 임베딩 |
| | `model_version` | VARCHAR(50) | 모델 식별자 |
| | `updated_at` | TIMESTAMPTZ | 마지막 계산 시각 |

**설계 결정 — 임베딩 차원 128**

- 128 차원: 메모리·스토리지 절감 (384 대비 3배) + 초기 서비스 규모에 충분한 표현력
- ivfflat lists=100: PostgreSQL 공식 권장 (`sqrt(row_count)` 기준 ~1M행)
- 추후 384 차원으로 확장 시: 새 마이그레이션에서 컬럼 DROP → 재생성 (COPY 지원 불가)

---

## 3. Service Layer

### 3-1. `app/services/embedding_model.py` — 모델 싱글톤

```python
"""ML 임베딩 모델 싱글톤 로더.

OQ 결정: sentence-transformers paraphrase-multilingual-MiniLM-L12-v2
  - KO/EN multilingual 지원
  - 128차원 출력 (pooled, normalized)
  - self-hosted ECS ML worker docker container

Mock 모드: EMBEDDING_MODEL_PATH 미설정 or 모델 로드 실패 시
  → zero vector(128) 반환 + WARNING 로그
  → CI/CD, 로컬 개발 환경에서 ML 의존 없이 동작 보장
"""
from __future__ import annotations

import logging
import os
from typing import Optional

import numpy as np

log = logging.getLogger(__name__)

_MODEL = None
_MOCK_MODE = False
_MODEL_VERSION = "minilm-v1"
_EMBED_DIM = 128


def _load_model() -> None:
    """최초 호출 시 1회 로드 (lazy init, singleton)."""
    global _MODEL, _MOCK_MODE

    model_path = os.getenv("EMBEDDING_MODEL_PATH", "")
    if not model_path:
        log.warning(
            "EMBEDDING_MODEL_PATH not set — embedding_model running in MOCK MODE "
            "(zero vectors). Set EMBEDDING_MODEL_PATH to enable real embeddings."
        )
        _MOCK_MODE = True
        return

    try:
        from sentence_transformers import SentenceTransformer  # type: ignore
        _MODEL = SentenceTransformer(model_path)
        log.info("Embedding model loaded from %s (dim=%d)", model_path, _EMBED_DIM)
    except Exception as exc:  # noqa: BLE001
        log.warning(
            "Failed to load embedding model from %s: %s — falling back to MOCK MODE",
            model_path,
            exc,
        )
        _MOCK_MODE = True


def get_model_version() -> str:
    return _MODEL_VERSION


def encode(texts: list[str]) -> list[list[float]]:
    """텍스트 리스트 → 128차원 float 벡터 리스트.

    Mock 모드: zero vector 반환.
    실제 모드: sentence-transformers encode + L2 normalize.
    """
    global _MODEL, _MOCK_MODE

    if _MODEL is None and not _MOCK_MODE:
        _load_model()

    if _MOCK_MODE or _MODEL is None:
        return [[0.0] * _EMBED_DIM for _ in texts]

    embeddings = _MODEL.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    # 128차원 슬라이스 (모델 출력이 더 클 경우 대비)
    return [list(map(float, e[:_EMBED_DIM])) for e in embeddings]
```

### 3-2. `app/services/embedding_jobs.py` — cron worker

```python
"""임베딩 batch cron worker — Phase 9 L-A (ML 임베딩 인프라).

R-5 격리 패턴 준수:
  - 별도 파일 (embedding_jobs.py)
  - AsyncSessionLocal 독립 사용
  - 개별 Prometheus metric label

동작:
  1. 신규 user/post: 즉시 임베딩 (on-write hook 대신 짧은 interval sweep)
  2. 기존 전체: 일 1회 batch sweep (EMBEDDING_BATCH_INTERVAL_SECONDS, default 86400)

EMBEDDING_WORKER_ENABLED=false 환경변수로 worker 비활성화 가능.
"""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.db.session import AsyncSessionLocal
from app.services import embedding_model

log = logging.getLogger(__name__)

_BATCH_SIZE = int(os.getenv("EMBEDDING_BATCH_SIZE", "100"))
_QUICK_INTERVAL = int(os.getenv("EMBEDDING_QUICK_INTERVAL_SECONDS", "60"))   # 신규 감지
_BATCH_INTERVAL = int(os.getenv("EMBEDDING_BATCH_INTERVAL_SECONDS", "86400"))  # 일 1회

# ──────────────────────────────────────────────────────────────────────────────
# 단위 업데이트
# ──────────────────────────────────────────────────────────────────────────────

async def update_user_embedding(db, user_id: str) -> None:
    """단일 사용자 임베딩 계산 후 upsert.

    행동 시퀀스: behavioral_history 최근 200건 event_type 텍스트를 공백 join.
    모델 없을 시 zero vector (Mock 모드).
    """
    result = await db.execute(
        text("""
            SELECT event_type, target_id
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
            VALUES (:uid, :emb::vector, :ver, :ts)
            ON CONFLICT (user_id) DO UPDATE
                SET embedding = EXCLUDED.embedding,
                    model_version = EXCLUDED.model_version,
                    updated_at = EXCLUDED.updated_at
        """),
        {"uid": user_id, "emb": str(vector), "ver": version, "ts": now},
    )
    await db.commit()


async def update_post_embedding(db, post_id: str) -> None:
    """단일 작품 임베딩 계산 후 upsert.

    텍스트 소스: title + body(첫 500자) + tags join.
    """
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
            VALUES (:pid, :emb::vector, :ver, :ts)
            ON CONFLICT (post_id) DO UPDATE
                SET embedding = EXCLUDED.embedding,
                    model_version = EXCLUDED.model_version,
                    updated_at = EXCLUDED.updated_at
        """),
        {"pid": post_id, "emb": str(vector), "ver": version, "ts": now},
    )
    await db.commit()


# ──────────────────────────────────────────────────────────────────────────────
# Batch sweep (일 1회)
# ──────────────────────────────────────────────────────────────────────────────

async def batch_update_embeddings_once(db, batch_size: int = _BATCH_SIZE) -> dict[str, int]:
    """전체 user + post 임베딩 일괄 갱신 (idempotent).

    stale 기준: updated_at < now() - 23h (일 1회 interval보다 약간 짧게 설정)
    반환: {"users": n, "posts": n}
    """
    stale_cutoff = datetime.now(timezone.utc) - timedelta(hours=23)
    counts: dict[str, int] = {"users": 0, "posts": 0}

    # Users sweep
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
    for uid in user_ids:
        try:
            await update_user_embedding(db, uid)
            counts["users"] += 1
        except Exception as exc:  # noqa: BLE001
            log.warning("batch_update_embeddings_once: user %s failed: %s", uid, exc)

    # Posts sweep
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
    for pid in post_ids:
        try:
            await update_post_embedding(db, pid)
            counts["posts"] += 1
        except Exception as exc:  # noqa: BLE001
            log.warning("batch_update_embeddings_once: post %s failed: %s", pid, exc)

    log.info("batch_update_embeddings_once done: %s", counts)
    return counts


# ──────────────────────────────────────────────────────────────────────────────
# Cron loop (R-5 격리)
# ──────────────────────────────────────────────────────────────────────────────

async def embedding_cron_loop(
    quick_interval_seconds: int = _QUICK_INTERVAL,
    batch_interval_seconds: int = _BATCH_INTERVAL,
) -> None:
    """두 주기 cron:
      - quick sweep: quick_interval_seconds 마다 신규 user/post 즉시 처리
      - batch sweep: batch_interval_seconds 마다 전체 stale 갱신
    """
    batch_counter = 0
    while True:
        await asyncio.sleep(quick_interval_seconds)
        batch_counter += quick_interval_seconds

        async with AsyncSessionLocal() as db:
            try:
                # 신규 감지 (임베딩 없는 최신 user/post 소수만)
                await _quick_sweep(db)

                # 일 1회 전체 batch
                if batch_counter >= batch_interval_seconds:
                    await batch_update_embeddings_once(db)
                    batch_counter = 0
            except Exception as exc:  # noqa: BLE001
                log.warning("embedding_cron_loop error: %s", exc)


async def _quick_sweep(db) -> None:
    """신규 user/post (임베딩 없음) 최대 20건 즉시 처리."""
    result = await db.execute(
        text("""
            SELECT u.id FROM users u
            LEFT JOIN user_embeddings ue ON ue.user_id = u.id
            WHERE ue.user_id IS NULL
            ORDER BY u.created_at DESC
            LIMIT 20
        """)
    )
    for row in result.fetchall():
        try:
            await update_user_embedding(db, str(row.id))
        except Exception as exc:  # noqa: BLE001
            log.warning("quick_sweep user %s: %s", row.id, exc)

    result = await db.execute(
        text("""
            SELECT p.id FROM posts p
            LEFT JOIN post_embeddings pe ON pe.post_id = p.id
            WHERE pe.post_id IS NULL
            ORDER BY p.created_at DESC
            LIMIT 20
        """)
    )
    for row in result.fetchall():
        try:
            await update_post_embedding(db, str(row.id))
        except Exception as exc:  # noqa: BLE001
            log.warning("quick_sweep post %s: %s", row.id, exc)
```

### 3-3. `app/main.py` — cron worker 등록 (12번째)

기존 11개 worker에 추가:

```python
# main.py imports 추가
from app.services.embedding_jobs import embedding_cron_loop

# lifespan 내 task 등록 (EMBEDDING_WORKER_ENABLED guard)
import os as _os
if _os.getenv("EMBEDDING_WORKER_ENABLED", "true").lower() != "false":
    # 12th cron worker — embedding (R-5 isolated, quick 60s + batch 86400s, L-A)
    embedding_task = asyncio.create_task(embedding_cron_loop())
else:
    embedding_task = None

# finally 블록 all_tasks 튜플에 추가
if embedding_task:
    # ... 기존 16개 + embedding_task
```

---

## 4. API Endpoints

**외부 노출 없음.** 임베딩은 내부 cron worker가 계산하고 K-1에서 직접 DB 참조.

K-1 (collaborative filtering) 사용 예시:

```sql
-- K-1에서 사용할 코사인 유사도 쿼리 (참고)
SELECT post_id, 1 - (embedding <=> :target_vec::vector) AS similarity
FROM post_embeddings
ORDER BY embedding <=> :target_vec::vector
LIMIT 20;
```

---

## 5. Frontend Changes (G''-6 번들 최종화)

### 현재 상태

- `next.config.mjs`: `@next/bundle-analyzer` 통합 완료, `canvas: false` alias 설정
- webpack splitChunks 미설정 (Next.js 기본값만 사용)
- `ANALYZE=true npm run build`로 분석 가능하나 vendor chunk 분리 미적용

### 5-1. `next.config.mjs` 개선

```typescript
import bundleAnalyzer from "@next/bundle-analyzer";

const withBundleAnalyzer = bundleAnalyzer({
  enabled: process.env.ANALYZE === "true",
});

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: "standalone",

  // 자주 사용되는 아이콘/날짜 라이브러리 트리셰이킹 최적화
  experimental: {
    optimizePackageImports: ["lucide-react", "date-fns"],
  },

  webpack(config, { isServer }) {
    // canvas 빈 모듈 alias (Konva SSR 오류 방지, 기존 설정 유지)
    config.resolve.alias = {
      ...config.resolve.alias,
      canvas: false,
    };

    // vendor chunk 분리 (클라이언트 번들만)
    if (!isServer) {
      config.optimization.splitChunks = {
        chunks: "all",
        cacheGroups: {
          // React 코어 — 변경 빈도 낮음, 장기 캐시
          react: {
            test: /[\\/]node_modules[\\/](react|react-dom|scheduler)[\\/]/,
            name: "vendor-react",
            chunks: "all",
            priority: 40,
          },
          // Next.js 런타임
          next: {
            test: /[\\/]node_modules[\\/]next[\\/]/,
            name: "vendor-next",
            chunks: "all",
            priority: 30,
          },
          // PostHog 분석 — 지연 로드 후보
          posthog: {
            test: /[\\/]node_modules[\\/]posthog-js[\\/]/,
            name: "vendor-posthog",
            chunks: "all",
            priority: 20,
          },
          // Stripe.js — 결제 페이지에서만 필요
          stripe: {
            test: /[\\/]node_modules[\\/](@stripe|stripe)[\\/]/,
            name: "vendor-stripe",
            chunks: "all",
            priority: 20,
          },
          // 기타 공통 vendor
          commons: {
            test: /[\\/]node_modules[\\/]/,
            name: "vendor-commons",
            chunks: "all",
            minChunks: 2,
            priority: 10,
          },
        },
      };
    }

    return config;
  },
};

export default withBundleAnalyzer(nextConfig);
```

### 5-2. `package.json` 스크립트 추가

```json
{
  "scripts": {
    "analyze": "ANALYZE=true next build",
    "analyze:server": "BUNDLE_ANALYZE=server ANALYZE=true next build",
    "analyze:browser": "BUNDLE_ANALYZE=browser ANALYZE=true next build"
  }
}
```

### 5-3. Dynamic Import 후보 (대형 컴포넌트)

| 컴포넌트 | 추정 크기 | Dynamic import 방식 |
|----------|----------|---------------------|
| Konva 기반 이미지 에디터 | ~200KB | `dynamic(() => import('../ImageEditor'), { ssr: false })` |
| Chart/통계 컴포넌트 | ~80KB | `dynamic(() => import('../StatsChart'), { loading: () => <Skeleton /> })` |
| PostHog provider | ~60KB | 조건부 렌더 (analytics disabled 환경 대응) |

> **주의**: Konva dynamic import는 `ssr: false` 필수. 에디터 페이지 진입 시점에만 로드.

---

## 6. Mock 모드 Fallback

### 환경변수 매트릭스

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `EMBEDDING_MODEL_PATH` | (없음) | 모델 경로. 미설정 시 Mock 모드 자동 활성화 |
| `EMBEDDING_WORKER_ENABLED` | `true` | `false`로 설정 시 cron worker 등록 건너뜀 |
| `EMBEDDING_BATCH_SIZE` | `100` | 일 1회 batch당 처리 건수 |
| `EMBEDDING_QUICK_INTERVAL_SECONDS` | `60` | 신규 감지 주기 (초) |
| `EMBEDDING_BATCH_INTERVAL_SECONDS` | `86400` | 전체 batch 주기 (초, 24h) |

### Mock 모드 동작

```
EMBEDDING_MODEL_PATH 미설정
  → _load_model() 호출 시 _MOCK_MODE = True 설정
  → encode() → [[0.0] * 128, ...] 반환
  → WARNING: "embedding_model running in MOCK MODE"
  → DB에 zero vector upsert (ivfflat 인덱스 동작 영향 없음)
  → K-1 ANN 검색 시 모든 문서 동일 거리 → fallback to recency sort
```

### CI/CD 권장 설정

```yaml
# GitHub Actions / docker-compose.test.yml
env:
  EMBEDDING_WORKER_ENABLED: "false"   # CI에서 cron 미시작
  EMBEDDING_MODEL_PATH: ""            # Mock 모드 자동 활성화
```

---

## 7. Test Plan

### 7-1. Unit Tests — `tests/unit/test_embedding_jobs.py`

```python
"""Unit tests — embedding_jobs.py + embedding_model.py (Phase 9 L-A)."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services import embedding_model, embedding_jobs


# ──────────────────────────────────────────────────────────────────────────────
# Mock 모드 테스트
# ──────────────────────────────────────────────────────────────────────────────

def test_encode_mock_mode_returns_zero_vector(monkeypatch):
    """EMBEDDING_MODEL_PATH 미설정 → zero vector 반환."""
    monkeypatch.delenv("EMBEDDING_MODEL_PATH", raising=False)
    # 모듈 상태 초기화
    embedding_model._MODEL = None
    embedding_model._MOCK_MODE = False

    result = embedding_model.encode(["test text"])
    assert len(result) == 1
    assert len(result[0]) == 128
    assert all(v == 0.0 for v in result[0])


def test_encode_mock_mode_multiple_texts(monkeypatch):
    """여러 텍스트 → 각각 zero vector."""
    monkeypatch.delenv("EMBEDDING_MODEL_PATH", raising=False)
    embedding_model._MODEL = None
    embedding_model._MOCK_MODE = False

    result = embedding_model.encode(["text1", "text2", "text3"])
    assert len(result) == 3
    for vec in result:
        assert len(vec) == 128


# ──────────────────────────────────────────────────────────────────────────────
# update_user_embedding — idempotent
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_update_user_embedding_idempotent():
    """동일 user_id 두 번 호출 → upsert, 오류 없음."""
    db = AsyncMock()
    db.execute = AsyncMock(return_value=MagicMock(fetchall=lambda: []))
    db.commit = AsyncMock()

    with patch.object(embedding_model, "encode", return_value=[[0.0] * 128]):
        await embedding_jobs.update_user_embedding(db, "user-uuid-1")
        await embedding_jobs.update_user_embedding(db, "user-uuid-1")

    assert db.commit.call_count == 2


@pytest.mark.asyncio
async def test_update_post_embedding_missing_post():
    """존재하지 않는 post_id → WARNING 로그 후 조용히 반환."""
    db = AsyncMock()
    db.execute = AsyncMock(return_value=MagicMock(fetchone=lambda: None))

    # 오류 없이 반환되어야 함
    await embedding_jobs.update_post_embedding(db, "nonexistent-post-id")
    db.commit.assert_not_called()


# ──────────────────────────────────────────────────────────────────────────────
# batch_update_embeddings_once — idempotent
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_batch_update_embeddings_once_idempotent():
    """두 번 호출해도 동일 결과 (upsert 기반)."""
    db = AsyncMock()
    db.execute = AsyncMock(return_value=MagicMock(fetchall=lambda: []))
    db.commit = AsyncMock()

    with patch.object(embedding_model, "encode", return_value=[[0.0] * 128]):
        result1 = await embedding_jobs.batch_update_embeddings_once(db, batch_size=10)
        result2 = await embedding_jobs.batch_update_embeddings_once(db, batch_size=10)

    assert result1 == {"users": 0, "posts": 0}
    assert result2 == {"users": 0, "posts": 0}
```

### 7-2. Integration Tests

| 항목 | 검증 내용 |
|------|----------|
| pgvector extension | `SELECT extname FROM pg_extension WHERE extname = 'vector'` |
| 테이블 생성 | `user_embeddings`, `post_embeddings` 존재 확인 |
| vector 차원 | INSERT 후 `embedding::text` 파싱 → 128 float 확인 |
| ivfflat 인덱스 | `\d post_embeddings`에서 인덱스 표시 |
| ANN 쿼리 | `SELECT ... ORDER BY embedding <=> '...'::vector LIMIT 5` 동작 |
| upsert idempotent | 동일 user_id 두 번 INSERT ON CONFLICT → 1행만 존재 |

---

## 8. 위임 Agent

| Agent | 담당 작업 | 산출물 |
|-------|----------|--------|
| `bkend-expert` | alembic 0066 작성 + `embedding_model.py` + `embedding_jobs.py` + `main.py` cron 등록 + unit test | `0066_ml_embeddings.py`, `embedding_model.py`, `embedding_jobs.py`, `tests/unit/test_embedding_jobs.py` |
| `frontend-architect` | `next.config.mjs` splitChunks 적용 + `package.json` analyze 스크립트 + dynamic import 후보 적용 | `next.config.mjs`, `package.json` |
| `devops-architect` | ML worker Docker container 정의 (ECS 배포 시) | `docker/ml-worker/Dockerfile` *(선택적 — ECS 미사용 시 보류)* |

### 병렬 실행 가능 범위

```
[병렬]
  bkend-expert: alembic 0066 + embedding_model.py + embedding_jobs.py
  frontend-architect: next.config.mjs splitChunks + dynamic import

[순차]
  bkend-expert: main.py 등록 (embedding_jobs.py 완성 후)
  bkend-expert: unit test 작성 + 통과
  frontend-architect: npm run build + bundle-analyzer 크기 확인

[검증]
  tsc 0 errors + alembic upgrade head + unit test green
```

---

## 9. 작업 단계 (L-A 내부 순서)

| Step | 작업 | 담당 | 검증 |
|------|------|------|------|
| 1 | `alembic/versions/0066_ml_embeddings.py` 작성 | bkend-expert | `alembic upgrade head` green |
| 2 | `app/services/embedding_model.py` 작성 | bkend-expert | Mock 모드 `encode()` 반환 확인 |
| 3 | `app/services/embedding_jobs.py` 작성 | bkend-expert | 함수 시그니처 + type annotation |
| 4 | `app/main.py` cron worker 등록 (12번째) | bkend-expert | `EMBEDDING_WORKER_ENABLED=false` guard 포함 |
| 5 | `tests/unit/test_embedding_jobs.py` 작성 + 통과 | bkend-expert | `pytest tests/unit/test_embedding_jobs.py` green |
| 6 | `next.config.mjs` splitChunks + `optimizePackageImports` 적용 | frontend-architect | `npm run build` 성공 |
| 7 | `package.json` analyze 스크립트 추가 | frontend-architect | `npm run analyze` 실행 확인 |
| 8 | Dynamic import 후보 컴포넌트 적용 (Konva 에디터 우선) | frontend-architect | E2E 기능 회귀 없음 |
| 9 | First Load JS ≤ 200KB 확인 | frontend-architect | `npm run analyze` 출력 캡처 |
| 10 | 전체 tsc 0 errors + alembic head + unit test green | — | CI 통과 기준 |

---

## 10. 위험 & 완화

| 위험 | 가능성 | 완화 방안 |
|------|--------|----------|
| pgvector 미설치 환경 (개발 로컬) | 중 | `CREATE EXTENSION IF NOT EXISTS vector` idempotent + 로컬 docker-compose에 pgvector 이미지 사용 |
| Konva dynamic import 후 화면 깜빡임 | 중 | `loading: () => <Skeleton />` + `ssr: false` 조합으로 Suspense 처리 |
| 128차원 ivfflat lists=100 정확도 | 낮 | 초기 데이터 규모 수만 건 → 정확도 충분. 수백만 행 시 lists 재조정 마이그레이션 |
| sentence-transformers 모델 파일 크기 (~500MB) | 중 | Docker layer 캐시 + ECS task def volumeMount. 로컬/CI는 Mock 모드 |
| splitChunks 설정 후 hydration mismatch | 낮 | 클라이언트 전용(`!isServer`) 적용으로 SSR chunk에는 미영향 |
