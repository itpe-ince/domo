"""Unit tests — K-5 LLM 도슨트 서비스 (llm-docent-artwork).

Phase 9 K-5: compose_context, generate_docent, translate_docent_to_locales 검증.

Mock 전략:
  - LLMGatewayClient.generate_interview → AsyncMock
  - LLMGatewayClient.translate_text → AsyncMock
  - get_cached_translation / save_translation → AsyncMock
  - db.commit / db.refresh → AsyncMock

Test count: 12
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ─── Fixtures ─────────────────────────────────────────────────────────────────


def _make_post(
    *,
    title: str = "미지의 빛",
    genre: str = "회화",
    tags: list[str] | None = None,
    ai_caption: str | None = None,
    ai_docent_opted_out: bool = False,
    ai_docent_generated_at: datetime | None = None,
    ai_docent_text: str | None = None,
) -> MagicMock:
    p = MagicMock()
    p.id = uuid.uuid4()
    p.author_id = uuid.uuid4()
    p.title = title
    p.genre = genre
    p.tags = tags or ["추상", "아크릴"]
    p.ai_caption = ai_caption
    p.ai_docent_opted_out = ai_docent_opted_out
    p.ai_docent_generated_at = ai_docent_generated_at
    p.ai_docent_text = ai_docent_text
    p.ai_docent_translations = {}
    p.ai_docent_model_version = None
    return p


def _make_artist(
    *,
    display_name: str = "김작가",
    country_code: str = "KR",
    primary_genre: str = "회화",
    statement: str = "자연에서 영감을 받습니다.",
    genre_tags: list[str] | None = None,
) -> MagicMock:
    profile = MagicMock()
    profile.statement = statement
    profile.genre_tags = genre_tags or ["추상화", "아크릴"]

    artist = MagicMock()
    artist.display_name = display_name
    artist.country_code = country_code
    artist.artist_index_primary_genre = primary_genre
    artist.artist_profile = profile
    return artist


def _make_series(
    *,
    title: str = "빛의 연작",
    description: str = "자연광을 주제로 한 시리즈.",
) -> MagicMock:
    s = MagicMock()
    s.title = title
    s.description = description
    return s


def _make_db() -> AsyncMock:
    db = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    return db


def _settings_mock(*, has_api_key: bool = True) -> MagicMock:
    s = MagicMock()
    s.llm_gateway_api_key = "gw-test-key" if has_api_key else ""
    s.llm_gateway_url = "https://llm.example.com/v1"
    s.llm_model_name = "gemma4-e4b"
    return s


# ─── 1. compose_context: 시리즈 포함 ─────────────────────────────────────────


def test_compose_context_with_series():
    """시리즈 정보 포함 시 프롬프트에 시리즈 제목/설명 포함 확인."""
    from app.services.llm_docent import compose_context

    post = _make_post(title="오후의 해변")
    artist = _make_artist()
    series = _make_series(title="빛의 연작", description="자연광을 주제로 한 시리즈.")

    prompt = compose_context(post=post, artist=artist, series=series)

    assert "빛의 연작" in prompt
    assert "자연광을 주제로 한 시리즈" in prompt
    assert "오후의 해변" in prompt
    assert "김작가" in prompt


# ─── 2. compose_context: 시리즈 없음 ─────────────────────────────────────────


def test_compose_context_without_series():
    """시리즈 없을 때 프롬프트 생성 정상 동작 확인."""
    from app.services.llm_docent import compose_context

    post = _make_post()
    artist = _make_artist()

    prompt = compose_context(post=post, artist=artist, series=None)

    assert "미지의 빛" in prompt
    assert "김작가" in prompt
    # 시리즈 섹션 없음
    assert "시리즈:" not in prompt


# ─── 3. compose_context: K-3 caption 참고 ────────────────────────────────────


def test_compose_context_uses_caption():
    """K-3 caption_text가 프롬프트에 참고로 포함 확인."""
    from app.services.llm_docent import compose_context

    post = _make_post(ai_caption="푸른 하늘 아래 해변의 풍경을 담은 작품.")
    artist = _make_artist()

    prompt = compose_context(post=post, artist=artist, series=None)

    assert "AI 캡션 참고 (K-3)" in prompt
    assert "푸른 하늘 아래 해변의 풍경" in prompt


# ─── 4. generate_docent: Mock 모드 ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_generate_docent_mock_mode():
    """LLM is_mock=True → ai_docent_text=None 반환 (예외 없음)."""
    with patch("app.services.llm_docent.LLMGatewayClient") as mock_cls:
        client = MagicMock()
        client.is_mock = True
        mock_cls.return_value = client

        from app.services.llm_docent import generate_docent

        post = _make_post()
        artist = _make_artist()
        db = _make_db()

        result = await generate_docent(
            db=db,
            post_id=post.id,
            post=post,
            artist=artist,
            series=None,
        )

    assert result is None
    # DB commit 호출 없음
    db.commit.assert_not_called()


# ─── 5. generate_docent: 성공 ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_generate_docent_success():
    """LLM 호출 성공 → ai_docent_text 저장 + generated_at 기록."""
    docent_body = "이 작품은 후기 인상주의 계열의 회화로..."

    with patch("app.services.llm_docent.LLMGatewayClient") as mock_cls, \
         patch("app.services.llm_docent.get_cached_translation", new_callable=AsyncMock) as mock_cache_get, \
         patch("app.services.llm_docent.save_translation", new_callable=AsyncMock):

        client = AsyncMock()
        client.is_mock = False
        client.generate_interview = AsyncMock(return_value={
            "content": docent_body,
            "model": "gemma4-e4b",
            "usage_tokens": 800,
        })
        client.translate_text = AsyncMock(return_value="[MOCK en] " + docent_body[:40])
        mock_cls.return_value = client

        # 캐시 miss → LLM 번역
        mock_cache_get.return_value = None

        from app.services.llm_docent import generate_docent

        post = _make_post()
        artist = _make_artist()
        db = _make_db()

        result = await generate_docent(
            db=db,
            post_id=post.id,
            post=post,
            artist=artist,
            series=None,
        )

    assert result == docent_body
    assert post.ai_docent_text == docent_body
    assert post.ai_docent_model_version == "gemma4-e4b"
    assert post.ai_docent_generated_at is not None
    db.commit.assert_called()


# ─── 6. generate_docent: 24h idempotency ─────────────────────────────────────


@pytest.mark.asyncio
async def test_generate_docent_idempotency_24h():
    """24h 이내 재호출 → LLM 미호출, 기존 텍스트 반환."""
    existing_text = "기존 도슨트 텍스트"
    recent_time = datetime.now(timezone.utc) - timedelta(hours=1)

    with patch("app.services.llm_docent.LLMGatewayClient") as mock_cls:
        client = MagicMock()
        client.is_mock = False
        mock_cls.return_value = client

        from app.services.llm_docent import generate_docent

        post = _make_post(
            ai_docent_generated_at=recent_time,
            ai_docent_text=existing_text,
        )
        artist = _make_artist()
        db = _make_db()

        result = await generate_docent(
            db=db,
            post_id=post.id,
            post=post,
            artist=artist,
            series=None,
        )

    assert result == existing_text
    # LLM generate_interview 호출 없음
    client.generate_interview.assert_not_called()
    db.commit.assert_not_called()


# ─── 7. generate_docent: opted_out=True ──────────────────────────────────────


@pytest.mark.asyncio
async def test_generate_docent_opted_out():
    """opted_out=True → None 반환 (LLM 호출 없음)."""
    with patch("app.services.llm_docent.LLMGatewayClient") as mock_cls:
        client = MagicMock()
        client.is_mock = False
        mock_cls.return_value = client

        from app.services.llm_docent import generate_docent

        post = _make_post(ai_docent_opted_out=True)
        artist = _make_artist()
        db = _make_db()

        result = await generate_docent(
            db=db,
            post_id=post.id,
            post=post,
            artist=artist,
            series=None,
        )

    assert result is None
    client.generate_interview.assert_not_called()


# ─── 8. translate_docent: cache hit ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_translate_docent_cache_hit():
    """translation_cache hit → LLM 번역 미호출 확인 (L-F 재활용)."""
    with patch("app.services.llm_docent.LLMGatewayClient") as mock_cls, \
         patch("app.services.llm_docent.get_cached_translation", new_callable=AsyncMock) as mock_cache_get, \
         patch("app.services.llm_docent.save_translation", new_callable=AsyncMock) as mock_save:

        client = AsyncMock()
        client.translate_text = AsyncMock()
        mock_cls.return_value = client

        # 모든 locale 캐시 hit
        mock_cache_get.return_value = "cached translation text"

        from app.services.llm_docent import translate_docent_to_locales

        db = _make_db()
        result = await translate_docent_to_locales(
            db=db,
            docent_ko="한국어 도슨트 텍스트",
            model_version="gemma4-e4b",
        )

    # 4개 locale 모두 캐시에서 반환
    assert len(result) == 4
    assert all(v == "cached translation text" for v in result.values())
    # LLM translate 미호출
    client.translate_text.assert_not_called()
    # save_translation 미호출 (캐시 hit이므로)
    mock_save.assert_not_called()


# ─── 9. translate_docent: cache miss ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_translate_docent_cache_miss():
    """translation_cache miss → LLM 번역 후 cache 저장 확인."""
    with patch("app.services.llm_docent.LLMGatewayClient") as mock_cls, \
         patch("app.services.llm_docent.get_cached_translation", new_callable=AsyncMock) as mock_cache_get, \
         patch("app.services.llm_docent.save_translation", new_callable=AsyncMock) as mock_save:

        client = AsyncMock()
        client.translate_text = AsyncMock(return_value="translated text")
        mock_cls.return_value = client

        # 캐시 miss
        mock_cache_get.return_value = None

        from app.services.llm_docent import translate_docent_to_locales

        db = _make_db()
        result = await translate_docent_to_locales(
            db=db,
            docent_ko="한국어 도슨트 텍스트",
            model_version="gemma4-e4b",
        )

    # 4개 locale 번역 성공
    assert len(result) == 4
    # LLM translate 4회 호출 (en, ja, zh, es)
    assert client.translate_text.call_count == 4
    # save_translation 4회 호출
    assert mock_save.call_count == 4


# ─── 10. translate_docent: 일부 locale 번역 실패 ─────────────────────────────


@pytest.mark.asyncio
async def test_translate_partial_failure():
    """일부 locale 번역 실패 → 나머지 저장, 예외 없음 확인."""
    call_count = 0

    async def translate_side_effect(text: str, source_locale: str, target_locale: str) -> str:
        nonlocal call_count
        call_count += 1
        if target_locale == "ja":
            raise Exception("일본어 번역 실패 (시뮬레이션)")
        return f"[{target_locale}] translated"

    with patch("app.services.llm_docent.LLMGatewayClient") as mock_cls, \
         patch("app.services.llm_docent.get_cached_translation", new_callable=AsyncMock) as mock_cache_get, \
         patch("app.services.llm_docent.save_translation", new_callable=AsyncMock):

        client = AsyncMock()
        client.translate_text = AsyncMock(side_effect=translate_side_effect)
        mock_cls.return_value = client
        mock_cache_get.return_value = None

        from app.services.llm_docent import translate_docent_to_locales

        db = _make_db()
        # 예외 발생 없음
        result = await translate_docent_to_locales(
            db=db,
            docent_ko="한국어 도슨트",
            model_version="gemma4-e4b",
        )

    # ja 제외 3개만 성공
    assert "ja" not in result
    assert "en" in result
    assert "zh" in result
    assert "es" in result


# ─── 11. generate_docent: LLM 호출 HTTPStatusError → None 반환 ───────────────


@pytest.mark.asyncio
async def test_generate_docent_llm_error():
    """LLM 호출 HTTPStatusError → None 반환 (graceful)."""
    import httpx

    with patch("app.services.llm_docent.LLMGatewayClient") as mock_cls:
        client = AsyncMock()
        client.is_mock = False
        client.generate_interview = AsyncMock(
            side_effect=httpx.HTTPStatusError(
                "500 Internal Server Error",
                request=MagicMock(),
                response=MagicMock(status_code=500),
            )
        )
        mock_cls.return_value = client

        from app.services.llm_docent import generate_docent

        post = _make_post()
        artist = _make_artist()
        db = _make_db()

        result = await generate_docent(
            db=db,
            post_id=post.id,
            post=post,
            artist=artist,
            series=None,
        )

    assert result is None
    db.commit.assert_not_called()


# ─── 12. generate_docent: model_version 저장 확인 ────────────────────────────


@pytest.mark.asyncio
async def test_model_version_stored():
    """생성 성공 시 ai_docent_model_version 올바르게 저장 확인."""
    with patch("app.services.llm_docent.LLMGatewayClient") as mock_cls, \
         patch("app.services.llm_docent.get_cached_translation", new_callable=AsyncMock) as mock_cache_get, \
         patch("app.services.llm_docent.save_translation", new_callable=AsyncMock):

        client = AsyncMock()
        client.is_mock = False
        client.generate_interview = AsyncMock(return_value={
            "content": "도슨트 본문",
            "model": "gemma4-e4b-custom",
            "usage_tokens": 500,
        })
        client.translate_text = AsyncMock(return_value="translated")
        mock_cls.return_value = client
        mock_cache_get.return_value = None

        from app.services.llm_docent import generate_docent

        post = _make_post()
        artist = _make_artist()
        db = _make_db()

        await generate_docent(
            db=db,
            post_id=post.id,
            post=post,
            artist=artist,
            series=None,
        )

    assert post.ai_docent_model_version == "gemma4-e4b-custom"
