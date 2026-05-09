"""AI 작품 자동 캡션 서비스 — Phase 9 K-3.

LLM Gateway(vision 모델 gemma4-e4b)로 작품 이미지를 분석해 한국어 캡션을 생성하고,
L-F translation_cache를 통해 5 locale 번역을 저장한다.

주요 함수:
  generate_caption()      — vision 호출 (단일 image_url → str | None)
  generate_for_post()     — 단일 포스트 캡션 생성 + 5 locale 번역 저장
  quick_sweep_once()      — 미생성 포스트 일괄 처리 (60초 주기)
  batch_sweep_once()      — stale 캡션 재생성 (24h 주기)
  artwork_caption_cron_loop() — 21번째 cron worker (quick + batch 혼합)

설계 결정:
  - LLM_GATEWAY_API_KEY 미설정 → Mock 모드: ai_caption=NULL 저장, log warning
  - vision 미지원 → text-only fallback 시도 후 실패 시 NULL
  - translation_cache 재사용 (재발명 금지)
  - caption_override 존재 시 AI 캡션 skip (force=True 시 예외)
  - ai_caption_generated_at IS NULL → batch sweep 대상으로 자동 인식
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.models.post import Post
from app.services.cron_monitor import record_cron_run as _push_cron_status
from app.services.llm_gateway import LLMGatewayClient, VisionNotSupportedError
from app.services.translation_cache import get_cached_translation, save_translation

log = logging.getLogger(__name__)

# 번역 대상 locale (한국어 원본 제외)
TARGET_LOCALES = ["en", "ja", "zh", "es"]


def get_effective_caption(post: Post, locale: str = "ko") -> str:
    """caption_override 우선, 없으면 locale 번역 또는 ai_caption 반환.

    우선순위:
      1. caption_override (작가 수동 입력)
      2. ai_caption_locale_translations[locale] (locale 번역)
      3. ai_caption (한국어 원본 fallback)
      4. "" (캡션 없음)
    """
    if post.caption_override:
        return post.caption_override
    translations: dict = post.ai_caption_locale_translations or {}
    if locale != "ko" and locale in translations and translations[locale]:
        return translations[locale]
    return post.ai_caption or ""


async def generate_caption(
    image_url: str,
    locale: str = "ko",
) -> str | None:
    """tuzigroup LLM Gateway vision 모델 호출 → 캡션 텍스트 반환.

    LLM_GATEWAY_API_KEY 미설정(Mock 모드) 시 None 반환, log warning.
    vision 미지원 모델 → 이미지 URL만 전달한 text-only fallback으로 약식 캡션 시도.
    5초 timeout 초과 시 None 반환 (graceful).

    Args:
        image_url: 공개 접근 가능한 작품 이미지 URL.
        locale: 생성 언어 (기본 'ko' 한국어).

    Returns:
        생성된 캡션 텍스트 또는 None (실패/Mock 모드).
    """
    client = LLMGatewayClient()

    if client.is_mock:
        log.warning(
            "[ArtworkCaption] Mock mode — LLM_GATEWAY_API_KEY 미설정. "
            "image_url=%s, ai_caption=NULL 저장",
            image_url,
        )
        return None

    try:
        result = await client.generate_artwork_caption(image_url, locale=locale, max_tokens=300)
        return result.get("content")

    except VisionNotSupportedError:
        log.warning("[ArtworkCaption] vision 미지원 — text-only fallback 시도 image_url=%s", image_url)
        try:
            # text-only fallback: 이미지 URL만 포함한 프롬프트로 재시도
            fallback_prompt = (
                f"다음 이미지 URL을 참고해 작품 캡션을 한국어로 2문장 작성하세요: {image_url}"
            )
            result = await client.generate_interview(
                fallback_prompt,
                max_tokens=200,
                temperature=0.5,
            )
            caption = result.get("content")
            if caption:
                log.info("[ArtworkCaption] text-only fallback 성공 image_url=%s", image_url)
            return caption
        except Exception as fallback_exc:
            log.warning(
                "[ArtworkCaption] text-only fallback 실패: %s — ai_caption=NULL",
                fallback_exc,
            )
            return None

    except Exception as exc:
        log.warning(
            "[ArtworkCaption] caption 생성 실패: %s — ai_caption=NULL image_url=%s",
            exc,
            image_url,
        )
        return None


async def _translate_caption_to_all_locales(
    db: AsyncSession,
    ko_caption: str,
    llm_client: LLMGatewayClient,
) -> dict:
    """ko 원본 캡션 → 4 locale 번역 딕셔너리 반환.

    translation_cache 2-tier (Redis → DB) 조회 후 miss 시 LLM Gateway 번역 호출.
    번역 실패 locale은 빈 문자열("")로 기록 (원본 한국어 fallback은 프론트에서 처리).
    """
    translations: dict[str, str] = {}

    for target_lang in TARGET_LOCALES:
        try:
            # 1단계: translation_cache 조회 (Redis → DB)
            cached = await get_cached_translation(db, ko_caption, "ko", target_lang)
            if cached is not None:
                translations[target_lang] = cached
                log.debug(
                    "[ArtworkCaption] translation cache hit ko→%s", target_lang
                )
                continue

            # 2단계: LLM Gateway 번역 호출
            translated = await llm_client.translate_text(ko_caption, "ko", target_lang)
            await save_translation(
                db,
                ko_caption,
                "ko",
                target_lang,
                translated,
                llm_client.model,
            )
            translations[target_lang] = translated

        except Exception as exc:
            log.warning(
                "[ArtworkCaption] translation failed ko→%s: %s", target_lang, exc
            )
            translations[target_lang] = ""

    return translations


async def generate_for_post(
    db: AsyncSession,
    post_id: UUID,
    force: bool = False,
) -> bool:
    """단일 작품 포스트의 캡션 생성 + 5 locale 번역 저장.

    흐름:
      1. posts 테이블에서 post_id, media URL 조회
      2. caption_override가 있으면 AI 캡션 생성 skip (force=True 시 예외)
      3. generate_caption(image_url) 호출
      4. 성공 시 ai_caption, ai_caption_generated_at, ai_caption_model_version 저장
      5. 5 locale 번역: translation_cache 활용
      6. ai_caption_locale_translations JSONB 저장

    Args:
        db: AsyncSession
        post_id: 대상 Post UUID
        force: True 시 caption_override 무시하고 재생성

    Returns:
        True (캡션 생성 성공) / False (실패 또는 skip)
    """
    from sqlalchemy.orm import selectinload

    # post + media 조회
    result = await db.execute(
        select(Post)
        .where(Post.id == post_id)
        .options(selectinload(Post.media))
    )
    post = result.scalar_one_or_none()

    if not post:
        log.warning("[ArtworkCaption] post_id=%s not found", post_id)
        return False

    # caption_override 존재 시 skip (force=False 기본)
    if post.caption_override and not force:
        log.debug(
            "[ArtworkCaption] skip — caption_override exists post_id=%s", post_id
        )
        return False

    # 이미지 미디어 URL 추출
    image_url: str | None = None
    for media in (post.media or []):
        if media.type == "image" and media.url:
            image_url = media.url
            break

    if not image_url:
        log.debug(
            "[ArtworkCaption] skip — no image media post_id=%s", post_id
        )
        return False

    # LLM Gateway 캡션 생성
    ko_caption = await generate_caption(image_url, locale="ko")

    if ko_caption is None:
        # Mock 모드 또는 실패 — ai_caption=NULL 유지, generated_at도 NULL 유지
        log.info(
            "[ArtworkCaption] caption=None (mock/fail) post_id=%s", post_id
        )
        return False

    # 5 locale 번역
    client = LLMGatewayClient()
    try:
        locale_translations = await _translate_caption_to_all_locales(db, ko_caption, client)
    except Exception as cache_error:
        log.warning(
            "[ArtworkCaption] translation cache unavailable: %s — ko only", cache_error
        )
        locale_translations = {}

    # DB 저장
    post.ai_caption = ko_caption
    post.ai_caption_locale_translations = locale_translations
    post.ai_caption_model_version = client.model
    post.ai_caption_generated_at = datetime.now(timezone.utc)

    try:
        await db.commit()
        log.info(
            "[ArtworkCaption] saved post_id=%s model=%s",
            post_id,
            client.model,
        )
        return True
    except Exception as exc:
        await db.rollback()
        log.error("[ArtworkCaption] DB save failed post_id=%s: %s", post_id, exc)
        return False


async def quick_sweep_once(
    db: AsyncSession,
    batch_size: int = 20,
) -> dict:
    """ai_caption_generated_at IS NULL인 이미지 포스트를 batch_size개 처리.

    60초 주기 cron에서 호출. 한 번 실행당 최대 batch_size개 처리 후 반환.

    Returns:
        {"processed": int, "succeeded": int, "failed": int}
    """
    from sqlalchemy.orm import selectinload

    # ai_caption_generated_at IS NULL인 포스트 (캡션 미생성)
    result = await db.execute(
        select(Post)
        .where(Post.ai_caption_generated_at.is_(None))
        .options(selectinload(Post.media))
        .order_by(Post.created_at.asc())
        .limit(batch_size)
    )
    posts = list(result.scalars().all())

    processed = 0
    succeeded = 0
    failed = 0

    for post in posts:
        # 이미지 미디어가 있는 포스트만 처리
        has_image = any(m.type == "image" for m in (post.media or []))
        if not has_image:
            # 이미지 없는 포스트는 generated_at을 epoch로 마킹 (재처리 방지)
            post.ai_caption_generated_at = datetime(1970, 1, 1, tzinfo=timezone.utc)
            try:
                await db.commit()
            except Exception:
                await db.rollback()
            continue

        processed += 1
        ok = await generate_for_post(db, post.id)
        if ok:
            succeeded += 1
        else:
            failed += 1

    log.info(
        "[ArtworkCaption] quick_sweep_once processed=%d succeeded=%d failed=%d",
        processed,
        succeeded,
        failed,
    )
    return {"processed": processed, "succeeded": succeeded, "failed": failed}


async def batch_sweep_once(
    db: AsyncSession,
    batch_size: int = 100,
    stale_model_version: str | None = None,
) -> dict:
    """stale 캡션(모델 버전 변경된 작품) 재생성. 24h 주기 cron에서 호출.

    stale_model_version 지정 시: ai_caption_model_version = stale_model_version인 포스트 재생성.
    None 시: ai_caption_generated_at IS NULL인 포스트 처리 (quick_sweep 동일 대상).

    Returns:
        {"processed": int, "succeeded": int, "failed": int}
    """
    from sqlalchemy.orm import selectinload

    if stale_model_version is not None:
        result = await db.execute(
            select(Post)
            .where(Post.ai_caption_model_version == stale_model_version)
            .options(selectinload(Post.media))
            .order_by(Post.ai_caption_generated_at.asc())
            .limit(batch_size)
        )
    else:
        result = await db.execute(
            select(Post)
            .where(Post.ai_caption_generated_at.is_(None))
            .options(selectinload(Post.media))
            .order_by(Post.created_at.asc())
            .limit(batch_size)
        )

    posts = list(result.scalars().all())

    processed = 0
    succeeded = 0
    failed = 0

    for post in posts:
        has_image = any(m.type == "image" for m in (post.media or []))
        if not has_image:
            continue

        processed += 1
        # force=True: stale_model_version 재생성 시 caption_override 무시
        ok = await generate_for_post(db, post.id, force=stale_model_version is not None)
        if ok:
            succeeded += 1
        else:
            failed += 1

    log.info(
        "[ArtworkCaption] batch_sweep_once stale_model=%s processed=%d succeeded=%d failed=%d",
        stale_model_version,
        processed,
        succeeded,
        failed,
    )
    return {"processed": processed, "succeeded": succeeded, "failed": failed}


async def artwork_caption_cron_loop(
    quick_interval_seconds: int = 60,
    batch_interval_seconds: int = 86400,
) -> None:
    """21번째 cron. quick sweep(60s 주기) + batch sweep(24h 주기) 혼합 실행.

    - quick sweep: 미생성 신규 포스트 빠른 처리 (작가 UX)
    - batch sweep: stale 캡션 재생성 또는 야간 대량 소급 처리
    """
    from app.core.config import get_settings

    settings = get_settings()
    last_batch_at = datetime.min.replace(tzinfo=timezone.utc)

    while True:
        await _push_cron_status("artwork_caption", "running")
        async with AsyncSessionLocal() as db:
            try:
                await quick_sweep_once(db, batch_size=settings.caption_batch_size_quick)

                now = datetime.now(timezone.utc)
                if (now - last_batch_at).total_seconds() >= batch_interval_seconds:
                    await batch_sweep_once(db, batch_size=settings.caption_batch_size_batch)
                    last_batch_at = now

                await _push_cron_status("artwork_caption", "success")
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                log.error("[ArtworkCaptionCron] error: %s", exc, exc_info=True)
                await _push_cron_status("artwork_caption", "failed", error=str(exc)[:500])

        await asyncio.sleep(quick_interval_seconds)
