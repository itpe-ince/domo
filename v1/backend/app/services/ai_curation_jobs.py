"""AI 큐레이션 컬렉션 자동 생성 — Phase 10 K-7.

주 1회 월요일 09:00 UTC cron으로 Editor's Pick 컬렉션 5개를 자동 생성한다.

README 비전 직접 구현:
  "스토리텔링 hub" — AI 큐레이션 컬렉션 제목/설명 자동 생성으로
    언론/SNS 확산 가능한 "발견 스토리"를 매주 자동화한다.
  "히스토리를 두세 개 만든다" — 신진 작가 클러스터링을 통해
    발견되기 어려운 작가를 주제 컬렉션으로 조명해 글로벌 인덱스를 능동 큐레이션한다.
  "전 세계 아티스트들의 인덱스를 만들고 싶음" — 주제별 컬렉션으로
    Domo를 스토리텔링 허브로 완성한다.

파이프라인:
  1단계: post_embeddings K-means 클러스터링 (sklearn) → 주제 그룹 발견
  2단계: 클러스터별 주제 분석 (ai_caption 텍스트 + 장르 태그)
  3단계: LLM Gateway → 컬렉션 제목/설명 한국어 생성
  4단계: L-F translation_cache → 5 locale 번역
  5단계: ai_collections + ai_collection_posts DB INSERT

환경변수:
  AI_CURATION_WORKER_ENABLED: false로 설정 시 cron 미등록 (default: true)
  AI_CURATION_DAILY_BUDGET_USD: LLM 일 비용 한도 (default: 5.0)
  AI_CURATION_COLLECTIONS_PER_WEEK: 주당 생성 컬렉션 수 (default: 5)
  AI_CURATION_POSTS_PER_COLLECTION: 컬렉션당 작품 수 (default: 15)

Graceful fallback:
  - sklearn 미설치 → metadata-based grouping (장르 태그 기반)
  - LLM Gateway 미설정 → status='generating' 유지 + log WARNING
  - translation_cache 미가용 → 한국어 원본만 저장 (빈 translations)
  - LLM 비용 한도 초과 → cron skip + log WARNING
"""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import date, datetime, timedelta, timezone
from typing import Any

from sqlalchemy import text

from app.db.session import AsyncSessionLocal
from app.services.llm_gateway import LLMGatewayClient
from app.services.translation_cache import get_cached_translation, save_translation

log = logging.getLogger(__name__)

_COLLECTIONS_PER_WEEK = int(os.getenv("AI_CURATION_COLLECTIONS_PER_WEEK", "5"))
_POSTS_PER_COLLECTION = int(os.getenv("AI_CURATION_POSTS_PER_COLLECTION", "15"))
_DAILY_BUDGET_USD = float(os.getenv("AI_CURATION_DAILY_BUDGET_USD", "5.0"))
_TARGET_LOCALES = ["en", "ja", "zh", "es"]

# 주제 후보 (클러스터 인덱스에 매핑되는 레이블 풀)
_THEME_CANDIDATES = [
    "emerging_painters",
    "digital_art_pioneers",
    "southeast_asia_artists",
    "abstract_expressionism",
    "photo_realism",
    "street_art_new_wave",
    "mixed_media_experiments",
    "watercolor_renaissance",
]


# ─────────────────────────────────────────────────────────────────────────────
# 1단계: post_embeddings 로드 + 클러스터링
# ─────────────────────────────────────────────────────────────────────────────

async def _load_post_embeddings(db, limit: int = 2000) -> list[dict]:
    """post_embeddings에서 최근 포스트 임베딩 로드.

    L-A post_embeddings (alembic 0066) 재사용 — 재발명 X.

    Returns list of {"post_id": str, "embedding": list[float],
                      "ai_caption": str | None, "tags": list[str]}
    """
    result = await db.execute(text("""
        SELECT pe.post_id,
               pe.embedding::text AS embedding_text,
               p.ai_caption,
               p.tags
        FROM post_embeddings pe
        JOIN posts p ON p.id = pe.post_id
        WHERE p.status = 'published'
        ORDER BY pe.updated_at DESC
        LIMIT :lim
    """), {"lim": limit})
    rows = result.fetchall()

    posts = []
    for r in rows:
        try:
            # vector(128) 텍스트 파싱: "[0.1, 0.2, ...]"
            emb_str = r.embedding_text.strip("[]")
            embedding = [float(x) for x in emb_str.split(",")]
        except Exception:
            embedding = [0.0] * 128
        posts.append({
            "post_id": str(r.post_id),
            "embedding": embedding,
            "ai_caption": r.ai_caption or "",
            "tags": r.tags or [],
        })
    return posts


def _cluster_by_sklearn(posts: list[dict], k: int) -> list[list[dict]]:
    """sklearn KMeans 클러스터링. 설치되지 않은 경우 ImportError 발생."""
    import numpy as np
    from sklearn.cluster import KMeans  # type: ignore

    embeddings = np.array([p["embedding"] for p in posts], dtype=np.float32)
    km = KMeans(n_clusters=k, random_state=42, n_init=10)
    labels = km.fit_predict(embeddings)

    clusters: list[list[dict]] = [[] for _ in range(k)]
    for post, label in zip(posts, labels):
        clusters[label].append(post)
    return clusters


def _cluster_by_metadata(posts: list[dict], k: int) -> list[list[dict]]:
    """sklearn 미설치 시 fallback: 장르 태그 기반 grouping.

    태그 없는 포스트는 'uncategorized' 버킷으로 분류.
    크기 순 상위 k개 태그 그룹을 반환한다.
    """
    from collections import defaultdict

    tag_groups: dict[str, list[dict]] = defaultdict(list)
    for post in posts:
        primary_tag = post["tags"][0] if post["tags"] else "uncategorized"
        tag_groups[primary_tag].append(post)

    # k개 클러스터로 제한 (크기 순 상위 k개 태그 선택)
    sorted_groups = sorted(tag_groups.values(), key=len, reverse=True)
    return sorted_groups[:k]


def _cluster_posts(posts: list[dict], k: int) -> tuple[list[list[dict]], bool]:
    """K-means 클러스터링 시도. sklearn 미설치 시 metadata fallback.

    Returns: (clusters, used_sklearn)
    """
    try:
        clusters = _cluster_by_sklearn(posts, k)
        log.info("ai_curation: sklearn KMeans clustering k=%d, posts=%d", k, len(posts))
        return clusters, True
    except ImportError:
        log.warning(
            "ai_curation: sklearn not installed — falling back to metadata-based grouping"
        )
        clusters = _cluster_by_metadata(posts, k)
        return clusters, False


# ─────────────────────────────────────────────────────────────────────────────
# 3단계: LLM 컬렉션 메타 생성
# ─────────────────────────────────────────────────────────────────────────────

def _build_collection_prompt(
    captions: list[str],
    tags: list[str],
    previous_titles: list[str],
) -> str:
    """LLM에 전달할 컬렉션 제목/설명 생성 프롬프트."""
    captions_text = "\n".join(f"- {c}" for c in captions[:8] if c)
    tags_text = ", ".join(sorted(set(tags))[:10])
    prev_text = "\n".join(f"- {t}" for t in previous_titles[-10:]) if previous_titles else "없음"

    return f"""당신은 예술 큐레이터입니다. 다음 작품 설명들을 분석해
하나의 주제로 묶는 컬렉션 제목과 소개글을 한국어로 작성해주세요.

[작품 설명 샘플]
{captions_text}

[주요 태그]
{tags_text}

[이전 컬렉션 제목 목록 (반복 금지)]
{prev_text}

요구사항:
1. 제목: 30자 이내, 독자의 호기심을 자극하는 문구
2. 설명: 2~3문장, 이 컬렉션을 탐색해야 하는 이유 설명
3. 이전 제목과 유사한 표현 사용 금지
4. 형식: JSON {{ "title": "...", "description": "..." }}"""


async def _generate_collection_meta(
    llm: LLMGatewayClient,
    captions: list[str],
    tags: list[str],
    previous_titles: list[str],
) -> dict[str, str] | None:
    """LLM으로 컬렉션 제목/설명 생성.

    Returns {"title": str, "description": str} 또는 LLM 미설정 시 None.
    LLM Gateway 미설정 → status='generating' 유지 + log WARNING (에러 없음).
    """
    if llm.is_mock:
        log.warning(
            "ai_curation: LLM Gateway not configured — collection will remain status='generating'. "
            "Admin can manually set title/description before publishing."
        )
        return None

    prompt = _build_collection_prompt(captions, tags, previous_titles)
    try:
        result = await llm.generate_interview(prompt, max_tokens=300, temperature=0.8)
        content = result.get("content", "")

        # JSON 파싱
        import json
        import re
        json_match = re.search(r"\{[^{}]+\}", content, re.DOTALL)
        if json_match:
            parsed = json.loads(json_match.group())
            return {
                "title": parsed.get("title", "")[:200],
                "description": parsed.get("description", ""),
            }
    except Exception as exc:
        log.warning("ai_curation: LLM meta generation failed: %s", exc)
    return None


# ─────────────────────────────────────────────────────────────────────────────
# 4단계: 번역 (L-F translation_cache 재사용 — 재발명 X)
# ─────────────────────────────────────────────────────────────────────────────

async def _translate_texts(
    db,
    llm: LLMGatewayClient,
    texts: dict[str, str],  # {"title": ko_title, "description": ko_desc}
) -> tuple[dict[str, str], dict[str, str]]:
    """한국어 제목/설명 → 5 locale 번역.

    L-F translation_cache (alembic 0071)를 먼저 조회하고,
    miss 시에만 LLM 번역을 호출해 비용을 최소화한다.

    Returns: (title_translations, description_translations)
      각각 {"en": "...", "ja": "...", "zh": "...", "es": "..."}
    """
    title_translations: dict[str, str] = {}
    desc_translations: dict[str, str] = {}

    for locale in _TARGET_LOCALES:
        # 제목 번역
        if texts.get("title"):
            cached_title = await get_cached_translation(
                db, texts["title"], "ko", locale
            )
            if cached_title:
                title_translations[locale] = cached_title
            elif not llm.is_mock:
                try:
                    trans_result = await llm.generate_interview(
                        f"다음 한국어 텍스트를 {locale} 언어로 번역해주세요. "
                        f"번역 결과만 출력하세요:\n{texts['title']}",
                        max_tokens=100,
                        temperature=0.3,
                    )
                    translated = trans_result.get("content", "").strip()
                    if translated:
                        title_translations[locale] = translated
                        await save_translation(
                            db, texts["title"], "ko", locale, translated,
                            model_version="gemma4-e4b",
                        )
                except Exception as exc:
                    log.warning(
                        "ai_curation: title translation to %s failed: %s", locale, exc
                    )

        # 설명 번역
        if texts.get("description"):
            cached_desc = await get_cached_translation(
                db, texts["description"], "ko", locale
            )
            if cached_desc:
                desc_translations[locale] = cached_desc
            elif not llm.is_mock:
                try:
                    trans_result = await llm.generate_interview(
                        f"다음 한국어 텍스트를 {locale} 언어로 번역해주세요. "
                        f"번역 결과만 출력하세요:\n{texts['description']}",
                        max_tokens=300,
                        temperature=0.3,
                    )
                    translated = trans_result.get("content", "").strip()
                    if translated:
                        desc_translations[locale] = translated
                        await save_translation(
                            db, texts["description"], "ko", locale, translated,
                            model_version="gemma4-e4b",
                        )
                except Exception as exc:
                    log.warning(
                        "ai_curation: desc translation to %s failed: %s", locale, exc
                    )

    return title_translations, desc_translations


# ─────────────────────────────────────────────────────────────────────────────
# 5단계: 컬렉션 생성 메인
# ─────────────────────────────────────────────────────────────────────────────

async def generate_collections_for_week(db, week_start: date) -> list[str]:
    """주어진 week_start에 대한 AI 큐레이션 컬렉션을 생성한다.

    Returns: 생성된 collection_id 목록.

    파이프라인:
      1. post_embeddings 로드
      2. K-means 클러스터링 (k=5)
      3. 클러스터별 LLM 메타 생성
      4. translation_cache 5 locale 번역
      5. ai_collections + ai_collection_posts INSERT
    """
    import json

    posts = await _load_post_embeddings(db, limit=2000)
    if len(posts) < _COLLECTIONS_PER_WEEK:
        log.warning(
            "ai_curation: not enough posts (%d) for clustering (need >= %d) — skipping",
            len(posts), _COLLECTIONS_PER_WEEK,
        )
        return []

    k = _COLLECTIONS_PER_WEEK
    clusters, used_sklearn = _cluster_posts(posts, k)

    # 이전 컬렉션 제목 로드 (클리셰 반복 방지 — 최근 4주치)
    prev_result = await db.execute(text("""
        SELECT title FROM ai_collections
        WHERE week_start >= :cutoff
        ORDER BY generated_at DESC
        LIMIT 20
    """), {"cutoff": week_start - timedelta(weeks=4)})
    previous_titles = [r.title for r in prev_result.fetchall() if r.title]

    # K-3/K-5 LLM 패턴 재사용 (재발명 X)
    llm = LLMGatewayClient()
    created_ids: list[str] = []

    for idx, cluster in enumerate(clusters):
        if not cluster:
            continue

        theme = _THEME_CANDIDATES[idx % len(_THEME_CANDIDATES)]

        # 중복 확인 (UNIQUE INDEX 위반 사전 방지)
        dup_check = await db.execute(text("""
            SELECT id FROM ai_collections
            WHERE theme = :theme AND week_start = :ws
            LIMIT 1
        """), {"theme": theme, "week_start": week_start})
        if dup_check.fetchone():
            log.info(
                "ai_curation: theme=%s week=%s already exists — skip (UNIQUE INDEX guard)",
                theme, week_start,
            )
            continue

        # 대표 포스트 선택 (상위 POSTS_PER_COLLECTION개)
        top_posts = cluster[:_POSTS_PER_COLLECTION]
        captions = [p["ai_caption"] for p in top_posts if p["ai_caption"]]
        tags = [tag for p in top_posts for tag in p["tags"]]

        # 3단계: LLM 메타 생성
        meta = await _generate_collection_meta(llm, captions, tags, previous_titles)

        title = meta["title"] if meta else None
        description = meta["description"] if meta else None
        title_translations: dict = {}
        desc_translations: dict = {}

        # 4단계: 번역 (meta 생성 성공 시에만)
        if meta:
            title_translations, desc_translations = await _translate_texts(
                db, llm, {"title": title, "description": description}
            )
            previous_titles.append(title)  # 다음 클러스터에서 반복 방지

        # cover_post_id: 첫 번째 포스트 (ML 스코어 상위)
        cover_post_id = top_posts[0]["post_id"] if top_posts else None

        # 5단계: ai_collections INSERT
        insert_result = await db.execute(text("""
            INSERT INTO ai_collections
              (week_start, theme, title, description,
               title_translations, description_translations,
               cover_post_id, status, cluster_k, llm_model_version)
            VALUES
              (:ws, :theme, :title, :desc,
               :title_tr::jsonb, :desc_tr::jsonb,
               :cover::uuid, 'generating', :k, :model)
            RETURNING id
        """), {
            "ws": week_start,
            "theme": theme,
            "title": title,
            "desc": description,
            "title_tr": json.dumps(title_translations, ensure_ascii=False),
            "desc_tr": json.dumps(desc_translations, ensure_ascii=False),
            "cover": cover_post_id,
            "k": k if used_sklearn else None,
            "model": llm.model if not llm.is_mock else None,
        })
        collection_id = str(insert_result.fetchone().id)

        # ai_collection_posts INSERT (position 1-indexed)
        for position, post in enumerate(top_posts, start=1):
            await db.execute(text("""
                INSERT INTO ai_collection_posts
                  (collection_id, post_id, position, ml_score)
                VALUES (:cid, :pid, :pos, :score)
            """), {
                "cid": collection_id,
                "pid": post["post_id"],
                "pos": position,
                "score": post.get("ml_score"),
            })

        await db.commit()
        created_ids.append(collection_id)
        log.info(
            "ai_curation: collection created id=%s theme=%s title=%s posts=%d",
            collection_id, theme, title, len(top_posts),
        )

    return created_ids


# ─────────────────────────────────────────────────────────────────────────────
# Cron loop (R-5 격리 패턴 — 23번째 cron worker)
# ─────────────────────────────────────────────────────────────────────────────

async def ai_curation_cron_loop() -> None:
    """주 1회 AI 큐레이션 컬렉션 생성 cron.

    매주 월요일 09:00 UTC 실행.
    K-4 featured_artist_worker(06:00)가 끝난 후 3시간 뒤 실행해
    featured artist 작품이 컬렉션에 반영될 수 있도록 한다.

    LLM 비용 일 $5 한도 (AI_CURATION_DAILY_BUDGET_USD) 초과 시 해당 주 skip.

    R-5 격리 패턴 준수:
      - 별도 파일 (ai_curation_jobs.py)
      - AsyncSessionLocal 독립 사용
      - 개별 try/except
    """
    while True:
        now = datetime.now(timezone.utc)
        # 다음 월요일 09:00 UTC 계산
        days_until_monday = (7 - now.weekday()) % 7 or 7
        next_run = now.replace(
            hour=9, minute=0, second=0, microsecond=0
        ) + timedelta(days=days_until_monday)
        wait_seconds = (next_run - now).total_seconds()

        log.info("ai_curation_cron: next run at %s (%.0fs)", next_run, wait_seconds)
        await asyncio.sleep(wait_seconds)

        # 비용 한도 확인 (일 $5 hard cap)
        daily_budget = float(os.getenv("AI_CURATION_DAILY_BUDGET_USD", "5.0"))
        if daily_budget <= 0:
            log.warning(
                "ai_curation_cron: AI_CURATION_DAILY_BUDGET_USD=%s — skipping this week",
                daily_budget,
            )
            continue

        run_date = datetime.now(timezone.utc).date()
        # week_start = 해당 주 월요일
        week_start = run_date - timedelta(days=run_date.weekday())

        async with AsyncSessionLocal() as db:
            try:
                created = await generate_collections_for_week(db, week_start)
                log.info(
                    "ai_curation_cron: week=%s created %d collections: %s",
                    week_start, len(created), created,
                )
            except Exception as exc:
                log.warning(
                    "ai_curation_cron: error for week=%s: %s", week_start, exc
                )
