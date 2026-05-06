"""Unit tests — artwork_caption_jobs.py (Phase 9 K-3).

테스트 범위:
  1.  test_generate_caption_success          — LLM Gateway mock → 캡션 생성 성공
  2.  test_generate_caption_mock_mode        — LLM_GATEWAY_API_KEY 미설정 → None, 예외 없음
  3.  test_generate_caption_timeout          — LLM 장애 → None 반환
  4.  test_vision_fallback_text_only         — VisionNotSupportedError → text-only fallback
  5.  test_generate_for_post_success         — 단일 포스트 캡션 생성 + DB 저장
  6.  test_generate_for_post_skip_override   — caption_override 존재 시 skip (force=False)
  7.  test_generate_for_post_force_override  — force=True → caption_override 무시 재생성
  8.  test_translation_cache_hit             — translation_cache hit → LLM 번역 호출 없음
  9.  test_translation_cache_miss_calls_llm  — cache miss → LLM 번역 + save_translation 호출
  10. test_all_5_locales_stored              — JSONB에 en/ja/zh/es 4개 locale 저장
  11. test_translation_partial_failure       — 특정 locale 실패 → "" 저장, 나머지 정상
  12. test_quick_sweep_processes_null        — ai_caption IS NULL 포스트 처리
  13. test_quick_sweep_idempotent            — 이미 캡션 있는 포스트 skip
  14. test_batch_sweep_stale_model           — stale_model_version 지정 시 해당 포스트만 재생성
  15. test_effective_caption_override_priority — caption_override 있으면 ai_caption 무시
  16. test_effective_caption_locale_fallback  — locale 번역 없으면 ai_caption(한국어) 반환
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.artwork_caption_jobs import (
    _translate_caption_to_all_locales,
    batch_sweep_once,
    generate_caption,
    generate_for_post,
    get_effective_caption,
    quick_sweep_once,
)


# ──────────────────────────────────────────────────────────────────────────────
# 헬퍼
# ──────────────────────────────────────────────────────────────────────────────

def _make_media(type_: str = "image", url: str = "http://cdn.example.com/art.jpg") -> MagicMock:
    m = MagicMock()
    m.type = type_
    m.url = url
    return m


def _make_post(
    ai_caption: str | None = None,
    ai_caption_locale_translations: dict | None = None,
    ai_caption_generated_at: datetime | None = None,
    ai_caption_model_version: str | None = None,
    caption_override: str | None = None,
    media: list | None = None,
    status: str = "published",
) -> MagicMock:
    post = MagicMock()
    post.id = uuid.uuid4()
    post.ai_caption = ai_caption
    post.ai_caption_locale_translations = ai_caption_locale_translations or {}
    post.ai_caption_generated_at = ai_caption_generated_at
    post.ai_caption_model_version = ai_caption_model_version
    post.caption_override = caption_override
    post.media = media or []
    post.status = status
    return post


def _make_db(post: MagicMock) -> AsyncMock:
    """AsyncSession mock — scalar_one_or_none()로 post 반환."""
    db = AsyncMock()
    execute_result = MagicMock()
    execute_result.scalar_one_or_none.return_value = post
    db.execute.return_value = execute_result
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    db.refresh = AsyncMock()
    return db


# ──────────────────────────────────────────────────────────────────────────────
# 1. generate_caption — LLM Gateway mock → 캡션 생성 성공
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_generate_caption_success():
    """LLM Gateway vision 호출 → 캡션 텍스트 반환."""
    expected_caption = "수채화 기법으로 표현된 작품입니다. 부드러운 색감과 자연스러운 구도가 인상적입니다."

    with patch("app.services.artwork_caption_jobs.LLMGatewayClient") as MockClient:
        mock_instance = MagicMock()
        mock_instance.is_mock = False
        mock_instance.generate_artwork_caption = AsyncMock(
            return_value={"content": expected_caption, "model": "gemma4-e4b", "usage_tokens": 150}
        )
        MockClient.return_value = mock_instance

        result = await generate_caption("http://cdn.example.com/art.jpg")

    assert result == expected_caption


# ──────────────────────────────────────────────────────────────────────────────
# 2. generate_caption — Mock 모드 → None 반환, 예외 없음
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_generate_caption_mock_mode():
    """LLM_GATEWAY_API_KEY 미설정 → None 반환, 예외 발생 없음."""
    with patch("app.services.artwork_caption_jobs.LLMGatewayClient") as MockClient:
        mock_instance = MagicMock()
        mock_instance.is_mock = True
        MockClient.return_value = mock_instance

        result = await generate_caption("http://cdn.example.com/art.jpg")

    assert result is None


# ──────────────────────────────────────────────────────────────────────────────
# 3. generate_caption — LLM 장애 → None 반환
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_generate_caption_timeout():
    """LLM Gateway 장애(Exception) → None 반환, 예외 전파 없음."""
    with patch("app.services.artwork_caption_jobs.LLMGatewayClient") as MockClient:
        mock_instance = MagicMock()
        mock_instance.is_mock = False
        mock_instance.generate_artwork_caption = AsyncMock(
            side_effect=Exception("Connection timeout")
        )
        MockClient.return_value = mock_instance

        result = await generate_caption("http://cdn.example.com/art.jpg")

    assert result is None


# ──────────────────────────────────────────────────────────────────────────────
# 4. generate_caption — VisionNotSupportedError → text-only fallback 시도
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_vision_fallback_text_only():
    """vision 미지원 → text-only fallback generate_interview 호출 확인."""
    from app.services.llm_gateway import VisionNotSupportedError

    fallback_caption = "이미지 URL을 기반으로 생성된 간단한 캡션입니다."

    with patch("app.services.artwork_caption_jobs.LLMGatewayClient") as MockClient:
        mock_instance = MagicMock()
        mock_instance.is_mock = False
        mock_instance.generate_artwork_caption = AsyncMock(
            side_effect=VisionNotSupportedError("vision not supported")
        )
        mock_instance.generate_interview = AsyncMock(
            return_value={"content": fallback_caption, "model": "gemma4-e4b", "usage_tokens": 80}
        )
        MockClient.return_value = mock_instance

        result = await generate_caption("http://cdn.example.com/art.jpg")

    assert result == fallback_caption
    mock_instance.generate_interview.assert_called_once()


# ──────────────────────────────────────────────────────────────────────────────
# 5. generate_for_post — 단일 포스트 캡션 생성 + DB 저장
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_generate_for_post_success():
    """이미지 포스트 → ai_caption + ai_caption_generated_at DB 저장 확인."""
    post = _make_post(media=[_make_media("image", "http://cdn.example.com/art.jpg")])
    db = _make_db(post)

    caption_text = "디지털 아트 작품입니다. 선명한 색채와 역동적인 구도가 특징입니다."
    translations = {"en": "A digital artwork.", "ja": "デジタルアート作品です。", "zh": "数字艺术作品。", "es": "Una obra de arte digital."}

    with (
        patch("app.services.artwork_caption_jobs.generate_caption", AsyncMock(return_value=caption_text)),
        patch("app.services.artwork_caption_jobs._translate_caption_to_all_locales", AsyncMock(return_value=translations)),
        patch("app.services.artwork_caption_jobs.LLMGatewayClient") as MockClient,
    ):
        mock_instance = MagicMock()
        mock_instance.model = "gemma4-e4b"
        MockClient.return_value = mock_instance

        result = await generate_for_post(db, post.id)

    assert result is True
    assert post.ai_caption == caption_text
    assert post.ai_caption_locale_translations == translations
    assert post.ai_caption_model_version == "gemma4-e4b"
    assert post.ai_caption_generated_at is not None
    db.commit.assert_called_once()


# ──────────────────────────────────────────────────────────────────────────────
# 6. generate_for_post — caption_override 존재 시 skip (force=False)
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_generate_for_post_skip_override():
    """caption_override 존재 + force=False → AI 캡션 생성 skip, False 반환."""
    post = _make_post(
        caption_override="작가가 직접 작성한 캡션",
        media=[_make_media("image")],
    )
    db = _make_db(post)

    with patch("app.services.artwork_caption_jobs.generate_caption") as mock_gen:
        result = await generate_for_post(db, post.id, force=False)

    assert result is False
    mock_gen.assert_not_called()


# ──────────────────────────────────────────────────────────────────────────────
# 7. generate_for_post — force=True → caption_override 무시하고 재생성
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_generate_for_post_force_override():
    """force=True → caption_override 있어도 AI 캡션 재생성 진행."""
    post = _make_post(
        caption_override="기존 수동 캡션",
        media=[_make_media("image")],
    )
    db = _make_db(post)

    new_caption = "AI가 새로 생성한 캡션입니다."

    with (
        patch("app.services.artwork_caption_jobs.generate_caption", AsyncMock(return_value=new_caption)),
        patch("app.services.artwork_caption_jobs._translate_caption_to_all_locales", AsyncMock(return_value={})),
        patch("app.services.artwork_caption_jobs.LLMGatewayClient") as MockClient,
    ):
        mock_instance = MagicMock()
        mock_instance.model = "gemma4-e4b"
        MockClient.return_value = mock_instance

        result = await generate_for_post(db, post.id, force=True)

    assert result is True
    assert post.ai_caption == new_caption


# ──────────────────────────────────────────────────────────────────────────────
# 8. translation cache hit → LLM 번역 호출 없음
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_translation_cache_hit():
    """translation_cache hit → LLM translate_text 호출 없음 확인."""
    db = AsyncMock()
    ko_text = "수채화 기법으로 표현된 작품입니다."

    mock_llm = MagicMock()
    mock_llm.model = "gemma4-e4b"
    mock_llm.translate_text = AsyncMock()

    with patch(
        "app.services.artwork_caption_jobs.get_cached_translation",
        AsyncMock(return_value="A work expressed in watercolor technique."),
    ):
        result = await _translate_caption_to_all_locales(db, ko_text, mock_llm)

    assert "en" in result
    assert result["en"] == "A work expressed in watercolor technique."
    # LLM 번역 호출 없음 (캐시 hit)
    mock_llm.translate_text.assert_not_called()


# ──────────────────────────────────────────────────────────────────────────────
# 9. translation cache miss → LLM 번역 + save_translation 호출
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_translation_cache_miss_calls_llm():
    """cache miss → LLM translate_text 호출 + save_translation 저장 확인."""
    db = AsyncMock()
    ko_text = "색채가 풍부한 추상 작품입니다."
    translated_en = "An abstract work rich in color."

    mock_llm = MagicMock()
    mock_llm.model = "gemma4-e4b"
    mock_llm.translate_text = AsyncMock(return_value=translated_en)

    with (
        patch("app.services.artwork_caption_jobs.get_cached_translation", AsyncMock(return_value=None)),
        patch("app.services.artwork_caption_jobs.save_translation", AsyncMock()) as mock_save,
    ):
        result = await _translate_caption_to_all_locales(db, ko_text, mock_llm)

    assert "en" in result
    assert result["en"] == translated_en
    # save_translation 호출 확인 (en 포함 4개 locale)
    assert mock_save.call_count == 4


# ──────────────────────────────────────────────────────────────────────────────
# 10. 5개 locale JSONB 저장 확인 (en/ja/zh/es)
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_all_5_locales_stored():
    """ai_caption_locale_translations JSONB에 en/ja/zh/es 4개 locale 모두 저장."""
    post = _make_post(media=[_make_media("image")])
    db = _make_db(post)

    ko_caption = "유화 기법의 풍경화입니다."
    all_translations = {
        "en": "A landscape painting in oil.",
        "ja": "油絵の風景画です。",
        "zh": "油画风景画。",
        "es": "Una pintura de paisaje al óleo.",
    }

    with (
        patch("app.services.artwork_caption_jobs.generate_caption", AsyncMock(return_value=ko_caption)),
        patch("app.services.artwork_caption_jobs._translate_caption_to_all_locales", AsyncMock(return_value=all_translations)),
        patch("app.services.artwork_caption_jobs.LLMGatewayClient") as MockClient,
    ):
        mock_instance = MagicMock()
        mock_instance.model = "gemma4-e4b"
        MockClient.return_value = mock_instance

        await generate_for_post(db, post.id)

    stored = post.ai_caption_locale_translations
    assert "en" in stored
    assert "ja" in stored
    assert "zh" in stored
    assert "es" in stored
    assert stored["en"] == "A landscape painting in oil."


# ──────────────────────────────────────────────────────────────────────────────
# 11. 특정 locale 번역 실패 → "" 저장, 나머지 locale 정상
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_translation_partial_failure():
    """특정 locale 번역 실패 → "" 기록, 나머지 locale 정상 저장."""
    db = AsyncMock()
    ko_text = "추상 표현주의 작품입니다."

    mock_llm = MagicMock()
    mock_llm.model = "gemma4-e4b"

    call_count = 0

    async def selective_translate(text, src, tgt):
        nonlocal call_count
        call_count += 1
        if tgt == "ja":
            raise Exception("Japanese translation failed")
        return f"[{tgt}] translated"

    mock_llm.translate_text = selective_translate

    with (
        patch("app.services.artwork_caption_jobs.get_cached_translation", AsyncMock(return_value=None)),
        patch("app.services.artwork_caption_jobs.save_translation", AsyncMock()),
    ):
        result = await _translate_caption_to_all_locales(db, ko_text, mock_llm)

    # ja: 빈 문자열, 나머지는 번역됨
    assert result.get("ja") == ""
    assert result.get("en") == "[en] translated"
    assert result.get("zh") == "[zh] translated"
    assert result.get("es") == "[es] translated"


# ──────────────────────────────────────────────────────────────────────────────
# 12. quick_sweep_once — ai_caption IS NULL 포스트 처리
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_quick_sweep_processes_null_captions():
    """ai_caption_generated_at IS NULL 이미지 포스트 → 처리 확인."""
    image_post = _make_post(media=[_make_media("image")])
    db = AsyncMock()
    execute_result = MagicMock()
    execute_result.scalars.return_value.all.return_value = [image_post]
    db.execute.return_value = execute_result
    db.commit = AsyncMock()

    with patch("app.services.artwork_caption_jobs.generate_for_post", AsyncMock(return_value=True)) as mock_gen:
        stats = await quick_sweep_once(db, batch_size=20)

    assert stats["processed"] >= 1
    mock_gen.assert_called_once_with(db, image_post.id)


# ──────────────────────────────────────────────────────────────────────────────
# 13. quick_sweep_once — 이미 캡션 있는 포스트는 재처리 없음 (idempotent)
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_quick_sweep_idempotent():
    """quick_sweep_once: 빈 결과(이미 캡션 있음) → processed=0."""
    db = AsyncMock()
    execute_result = MagicMock()
    execute_result.scalars.return_value.all.return_value = []  # 처리 대상 없음
    db.execute.return_value = execute_result

    with patch("app.services.artwork_caption_jobs.generate_for_post", AsyncMock()) as mock_gen:
        stats = await quick_sweep_once(db, batch_size=20)

    assert stats["processed"] == 0
    mock_gen.assert_not_called()


# ──────────────────────────────────────────────────────────────────────────────
# 14. batch_sweep_once — stale_model_version 지정 시 해당 포스트만 재생성
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_batch_sweep_stale_model():
    """stale_model_version 지정 → 해당 모델 포스트만 재생성 (force=True)."""
    stale_post = _make_post(
        ai_caption="오래된 캡션",
        ai_caption_model_version="old-model-v1",
        media=[_make_media("image")],
    )
    db = AsyncMock()
    execute_result = MagicMock()
    execute_result.scalars.return_value.all.return_value = [stale_post]
    db.execute.return_value = execute_result

    with patch("app.services.artwork_caption_jobs.generate_for_post", AsyncMock(return_value=True)) as mock_gen:
        stats = await batch_sweep_once(db, batch_size=100, stale_model_version="old-model-v1")

    assert stats["processed"] == 1
    assert stats["succeeded"] == 1
    # force=True로 호출 확인
    mock_gen.assert_called_once_with(db, stale_post.id, force=True)


# ──────────────────────────────────────────────────────────────────────────────
# 15. get_effective_caption — caption_override 우선
# ──────────────────────────────────────────────────────────────────────────────

def test_effective_caption_override_priority():
    """caption_override 존재 시 ai_caption 무시하고 override 반환."""
    post = _make_post(
        ai_caption="AI가 생성한 캡션",
        ai_caption_locale_translations={"en": "AI generated"},
        caption_override="작가가 직접 쓴 캡션",
    )

    result = get_effective_caption(post, locale="ko")
    assert result == "작가가 직접 쓴 캡션"

    result_en = get_effective_caption(post, locale="en")
    assert result_en == "작가가 직접 쓴 캡션"  # override가 locale 번역도 무시


# ──────────────────────────────────────────────────────────────────────────────
# 16. get_effective_caption — locale 번역 없으면 ai_caption(한국어) 반환
# ──────────────────────────────────────────────────────────────────────────────

def test_effective_caption_locale_fallback():
    """locale 번역 없을 때 ai_caption 한국어 원본으로 fallback."""
    post = _make_post(
        ai_caption="한국어 원본 캡션",
        ai_caption_locale_translations={},  # 번역 없음
        caption_override=None,
    )

    # ko: 원본 반환
    result_ko = get_effective_caption(post, locale="ko")
    assert result_ko == "한국어 원본 캡션"

    # en: 번역 없음 → ai_caption fallback
    result_en = get_effective_caption(post, locale="en")
    assert result_en == "한국어 원본 캡션"

    # 캡션 자체가 없을 때 빈 문자열
    empty_post = _make_post(ai_caption=None, ai_caption_locale_translations={})
    assert get_effective_caption(empty_post) == ""
