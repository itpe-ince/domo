"""LLM 도슨트 서비스 — K-5 llm-docent-artwork.

작품 이미지 + 작가 bio + 시리즈 설명 + 장르 태그를 조합해 LLM에게 전달하고
큐레이터 톤의 3~5문단 해설(한국어)을 생성한다.

README 비전 연결:
  - "AI 세상으로 가면 갈수록 예술가들이 제일 먼저 굶어 죽음" — AI를 활용해 작가가
    먹고살 수 있는 플랫폼 구조 구축. 도슨트가 작품 스토리텔링을 자동화한다.
  - "히스토리를 두세 개 만든다" — LLM 도슨트와 AI 캡션으로 작품 스토리텔링 자동화.
    언론/SNS 확산 가속.

의존성:
  - LLMGatewayClient (app/services/llm_gateway.py) — LLM 호출
  - translation_cache (app/services/translation_cache.py) — 5 locale 번역 캐싱
  - Phase 6 artist_index 컨텍스트 (user.artist_index_primary_genre 등) 활용

Mock 모드:
  - LLM Gateway 미설정 시 ai_docent_text=None 반환 (예외 없음)
  - translation_cache 미가용 시 한국어 원본만 반환
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

import httpx

from app.services.llm_gateway import LLMGatewayClient
from app.services.translation_cache import get_cached_translation, save_translation

if TYPE_CHECKING:
    from app.models.post import Post
    from app.models.series import Series
    from app.models.user import User
    from sqlalchemy.ext.asyncio import AsyncSession

log = logging.getLogger(__name__)

# K-3 대비 K-5는 더 많은 컨텍스트와 긴 해설 (3~5문단, 200~350단어)
_MAX_TOKENS = 1500
_TEMPERATURE = 0.6

# 번역 대상 locale (ko는 원본이므로 제외)
_TARGET_LOCALES = ["en", "ja", "zh", "es"]

# 24h idempotency 윈도우
_IDEMPOTENCY_WINDOW_HOURS = 24

# 1포스트당 생성 제한 — 2회/일 (rate limit 별도 체크)
_RATE_LIMIT_PER_DAY = 2

# 큐레이터 톤 시스템 프롬프트
# "AI 시대 작가의 정체성 재정의" — AI가 보조하되 작가를 전면에 내세운다
_DOCENT_SYSTEM_PROMPT = (
    "You are a professional art museum docent and curator writing in Korean. "
    "Your commentary is scholarly yet accessible — you analyze artworks with "
    "specific references to technique, art history, and emotional resonance. "
    "Avoid marketing language and superlatives. Write 3~5 paragraphs (200~350 words). "
    "Your audience includes collectors, art students, and general viewers."
)


def compose_context(
    post: "Post",
    artist: "User",
    series: "Series | None",
) -> str:
    """도슨트 생성용 LLM 프롬프트 조립.

    K-3 AI 캡션(1~2문장)과 달리 K-5는 3~5문단의 예술사적·기법적 맥락 해설을 제공한다.
    K-3 caption이 있는 경우 "AI 캡션 참고"로 포함해 해설 품질을 높인다.

    포함 컨텍스트:
      - 작품 제목, 장르, 태그
      - K-3 AI 캡션 (ai_caption — 있는 경우 참고)
      - 작가 bio: display_name, country_code, artist_index_primary_genre
      - 작가 프로필: genre_tags, statement (ArtistProfile)
      - 시리즈 설명: series.title, series.description (있는 경우)

    Returns:
        LLM에 전달할 완성된 프롬프트 문자열.
    """
    genre = getattr(post, "genre", None) or "미분류"
    tags_list = getattr(post, "tags", None) or []
    tags = ", ".join(tags_list) if tags_list else "없음"

    # K-3 AI 캡션 참고 (있는 경우) — 해설 품질 향상
    caption = getattr(post, "ai_caption", None) or ""
    caption_context = f"AI 캡션 참고 (K-3): {caption}\n" if caption else ""

    artist_name = getattr(artist, "display_name", "") or "작가"
    country = getattr(artist, "country_code", "") or ""
    primary_genre = getattr(artist, "artist_index_primary_genre", "") or genre

    # ArtistProfile에서 statement, genre_tags 조회
    artist_profile = getattr(artist, "artist_profile", None)
    statement = ""
    genre_tags_str = ""
    if artist_profile:
        statement = getattr(artist_profile, "statement", "") or ""
        profile_genre_tags = getattr(artist_profile, "genre_tags", None) or []
        genre_tags_str = ", ".join(profile_genre_tags) if profile_genre_tags else ""

    # 시리즈 컨텍스트
    series_context = ""
    if series:
        series_title = getattr(series, "title", "") or ""
        series_desc = getattr(series, "description", "") or "없음"
        series_context = (
            f"시리즈: {series_title}\n"
            f"시리즈 설명: {series_desc}\n"
        )

    post_title = getattr(post, "title", "") or "무제"

    prompt = f"""다음 작품 정보를 바탕으로 전문 도슨트 스타일의 해설을 한국어로 작성해 주세요.

---
[작품 정보]
제목: {post_title}
장르: {genre}
태그: {tags}
{caption_context}
[작가 정보]
이름: {artist_name}
국가: {country}
주요 장르: {primary_genre}
장르 태그: {genre_tags_str or "없음"}
작가 소개: {statement or "없음"}

{series_context}---

요청 사항:
1. 작품의 예술사적 맥락과 장르적 특성을 1문단으로 서술하세요.
2. 사용된 기법 또는 시각적 특성을 1문단으로 분석하세요.
3. 작품이 전달하는 감정이나 주제를 1문단으로 해석하세요.
4. 선택적으로 작가의 작품 세계와의 연결점을 1문단으로 추가하세요.
5. 관람자에게 감상 포인트를 제안하는 문단으로 마무리하세요.
6. 총 3~5문단, 200~350단어로 유지하세요.
7. "훌륭한", "멋진", "대단한" 같은 마케팅 표현은 사용하지 마세요.
"""
    return prompt.strip()


async def translate_docent_to_locales(
    db: "AsyncSession",
    docent_ko: str,
    model_version: str,
) -> dict[str, str]:
    """한국어 도슨트를 4개 locale (en, ja, zh, es)로 번역.

    L-F translation_cache 활용 (재발명 금지):
      - 캐시 hit → LLM 재호출 없음 (번역 비용 절감)
      - 캐시 miss → LLM 번역 후 translation_cache 저장

    Returns:
        {"en": "...", "ja": "...", "zh": "...", "es": "..."} 형태.
        번역 실패한 locale은 결과에서 제외 (한국어 원본이 항상 저장됨).
    """
    client = LLMGatewayClient()
    translations: dict[str, str] = {}

    for target_lang in _TARGET_LOCALES:
        try:
            # L-F translation_cache — Redis → DB 순으로 조회
            cached = await get_cached_translation(
                db=db,
                source_text=docent_ko,
                source_lang="ko",
                target_lang=target_lang,
            )
            if cached is not None:
                log.debug(
                    "llm_docent: translation_cache hit ko→%s", target_lang
                )
                translations[target_lang] = cached
                continue

            # 캐시 miss → LLM 번역 호출
            translated = await client.translate_text(
                text=docent_ko,
                source_locale="ko",
                target_locale=target_lang,
            )
            translations[target_lang] = translated

            # translation_cache 저장 (Redis + DB)
            await save_translation(
                db=db,
                source_text=docent_ko,
                source_lang="ko",
                target_lang=target_lang,
                translated_text=translated,
                model_version=model_version,
            )
            log.debug(
                "llm_docent: translated ko→%s model=%s", target_lang, model_version
            )

        except Exception as exc:
            # 일부 locale 번역 실패 → 해당 locale 제외, 나머지 저장
            # 한국어 원본은 항상 저장됨 (번역 실패가 도슨트 자체를 막지 않음)
            log.warning(
                "llm_docent: translation failed ko→%s error=%s (skipping)",
                target_lang,
                exc,
            )
            continue

    return translations


async def generate_docent(
    db: "AsyncSession",
    post_id: uuid.UUID,
    post: "Post",
    artist: "User",
    series: "Series | None",
) -> str | None:
    """AI 도슨트 생성 진입점.

    README 비전 "스토리텔링 hub" — AI가 작가의 콘텐츠 해설 부담을 보조한다.

    흐름:
      1. opt_out 체크 → True이면 None 반환
      2. 24h idempotency 체크 → 기존 텍스트 반환
      3. compose_context → LLM 프롬프트 조립
      4. LLM Mock 모드 → None 반환 (graceful)
      5. LLM 호출 (max 10초 timeout)
      6. translate_docent_to_locales → 5 locale 번역
      7. DB 갱신 (ai_docent_text, translations, model_version, generated_at)

    Args:
        db: AsyncSession
        post_id: 포스트 UUID (로깅용)
        post: Post 모델 인스턴스 (side effect: 컬럼 갱신)
        artist: 작가 User 모델 인스턴스
        series: Series 모델 인스턴스 (없으면 None)

    Returns:
        생성된 한국어 도슨트 텍스트.
        LLM Gateway 미설정 시 None.
        24h 이내 재호출 시 기존 텍스트.

    Side effects:
        - post.ai_docent_text 갱신
        - post.ai_docent_translations 갱신 (5 locale)
        - post.ai_docent_model_version 갱신
        - post.ai_docent_generated_at 갱신 (최초 생성 시각 — 재생성 시 overwrite)
    """
    # 1. opt_out 체크 — 작가가 AI 도슨트를 비활성화한 경우
    if getattr(post, "ai_docent_opted_out", False):
        log.info("llm_docent: opted_out=True post=%s — skip", post_id)
        return None

    # 2. 24h idempotency 체크 — 최근 24시간 이내 생성된 도슨트가 있으면 재호출 없음
    generated_at = getattr(post, "ai_docent_generated_at", None)
    if generated_at is not None:
        now = datetime.now(timezone.utc)
        # datetime이 timezone-naive인 경우 대비
        if generated_at.tzinfo is None:
            generated_at = generated_at.replace(tzinfo=timezone.utc)
        age = now - generated_at
        if age < timedelta(hours=_IDEMPOTENCY_WINDOW_HOURS):
            log.info(
                "llm_docent: idempotency hit post=%s generated_at=%s — skip",
                post_id,
                generated_at.isoformat(),
            )
            return getattr(post, "ai_docent_text", None)

    # 3. LLM Mock 모드 체크 — API KEY 미설정 시 graceful fallback
    client = LLMGatewayClient()
    if client.is_mock:
        log.info(
            "llm_docent: Mock mode (LLM_GATEWAY_API_KEY not set) post=%s — return None",
            post_id,
        )
        return None

    # 4. compose_context → 프롬프트 조립
    prompt = compose_context(post=post, artist=artist, series=series)

    # 5. LLM 호출
    try:
        result = await client.generate_interview(
            prompt=prompt,
            max_tokens=_MAX_TOKENS,
            temperature=_TEMPERATURE,
        )
    except (httpx.HTTPStatusError, httpx.RequestError) as exc:
        # LLM 호출 실패 → graceful NULL (작가에게 "생성 실패" 메시지 표시)
        log.error(
            "llm_docent: LLM 호출 실패 post=%s error=%s", post_id, exc
        )
        return None

    docent_ko: str = result["content"]
    model_version: str = result.get("model", "unknown")

    # 6. 5 locale 번역 (L-F translation_cache 활용)
    translations = await translate_docent_to_locales(
        db=db,
        docent_ko=docent_ko,
        model_version=model_version,
    )

    # 7. DB 갱신 (side effect)
    now = datetime.now(timezone.utc)
    post.ai_docent_text = docent_ko  # type: ignore[assignment]
    post.ai_docent_translations = translations  # type: ignore[assignment]
    post.ai_docent_model_version = model_version  # type: ignore[assignment]
    # OQ-K-5-1=overwrite: 재생성 시 마지막 생성본이 최신 (이력 불필요)
    # 단, generated_at은 최초 생성 시각 유지 → 재생성 시에도 overwrite 허용
    post.ai_docent_generated_at = now  # type: ignore[assignment]

    await db.commit()
    await db.refresh(post)

    log.info(
        "llm_docent: 도슨트 생성 완료 post=%s model=%s locales=%s",
        post_id,
        model_version,
        list(translations.keys()),
    )
    return docent_ko
