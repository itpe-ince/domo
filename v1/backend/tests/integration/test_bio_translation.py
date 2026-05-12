"""Integration tests for C-3 multi-language-story — bio translation endpoints.

Endpoints under test:
  POST /me/bio/translate?source_locale=ko  — auto-translate bio (LLM Mock mode)
  PATCH /me/bio/{locale}                   — manual edit one locale bio
  GET   /me/bio                            — list all locale bios
  GET   /users/{id}/bio?locale=en          — public bio by locale

Strategy: direct function calls with AsyncMock DB + MagicMock User.
Mock mode: LLM_GATEWAY_API_KEY not set → mock translations returned.

Test count: 5
  1. POST /me/bio/translate 200 — translates to all 5 locales (Mock mode)
  2. POST /me/bio/translate 422 — fails when User.bio is empty
  3. PATCH /me/bio/en 200       — manual edit sets is_machine_translated=False
  4. PATCH /me/bio/xx 422       — invalid locale rejected
  5. GET /users/{id}/bio 200    — public returns bio with locale fallback
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.api.me_bio import get_my_bio_translations, patch_my_bio_locale, translate_my_bio
from app.api.users import get_artist_bio_by_locale
from app.core.errors import ApiError
from app.schemas.bio import PatchBioRequest


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _make_user(bio: str | None = "나는 한국의 신진 작가입니다.") -> MagicMock:
    u = MagicMock()
    u.id = uuid.uuid4()
    u.role = "artist"
    u.bio = bio
    u.display_name = "Test Artist"
    return u


def _make_db() -> AsyncMock:
    db = AsyncMock()
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.add = MagicMock()
    return db


# ─── Test 1: POST /me/bio/translate — success (Mock mode) ────────────────────


@pytest.mark.asyncio
async def test_translate_my_bio_success():
    """POST /me/bio/translate returns 5 locale translations in Mock mode."""
    user = _make_user(bio="나는 한국의 신진 작가입니다.")
    db = _make_db()

    # translate_bio_to_all_locales upserts with pg_insert — mock execute to return None
    db.execute.return_value = AsyncMock()

    with patch("app.api.me_bio.translate_bio_to_all_locales") as mock_translate:
        mock_translate.return_value = {
            "ko": "나는 한국의 신진 작가입니다.",
            "en": "[MOCK en] 나는 한국의",
            "ja": "[MOCK ja] 나는 한국의",
            "zh": "[MOCK zh] 나는 한국의",
            "es": "[MOCK es] 나는 한국의",
        }
        result = await translate_my_bio(
            source_locale="ko",
            user=user,
            db=db,
            _rl=None,
        )

    assert result["data"]["translations"]["ko"] == "나는 한국의 신진 작가입니다."
    assert "en" in result["data"]["translations"]
    assert "ja" in result["data"]["translations"]
    assert "zh" in result["data"]["translations"]
    assert "es" in result["data"]["translations"]
    mock_translate.assert_awaited_once()


# ─── Test 2: POST /me/bio/translate — 422 when bio is empty ──────────────────


@pytest.mark.asyncio
async def test_translate_my_bio_empty_bio_422():
    """POST /me/bio/translate raises 422 when User.bio is empty."""
    user = _make_user(bio=None)
    db = _make_db()

    with pytest.raises(ApiError) as exc_info:
        await translate_my_bio(
            source_locale="ko",
            user=user,
            db=db,
            _rl=None,
        )
    assert exc_info.value.status_code == 422
    assert exc_info.value.code == "BIO_EMPTY"


# ─── Test 3: PATCH /me/bio/en — manual edit ──────────────────────────────────


@pytest.mark.asyncio
async def test_patch_my_bio_locale_success():
    """PATCH /me/bio/en saves manual edit and sets is_machine_translated=False."""
    user = _make_user()
    db = _make_db()
    body = PatchBioRequest(bio="I am an emerging Korean artist.")

    mock_row = MagicMock()
    mock_row.user_id = user.id
    mock_row.locale = "en"
    mock_row.bio = "I am an emerging Korean artist."
    mock_row.is_machine_translated = False
    mock_row.last_edited_at = datetime.now(timezone.utc)
    mock_row.last_translated_at = None

    with patch("app.api.me_bio.upsert_bio_locale") as mock_upsert:
        mock_upsert.return_value = mock_row
        result = await patch_my_bio_locale(
            locale="en",
            body=body,
            user=user,
            db=db,
        )

    assert result["data"]["locale"] == "en"
    assert result["data"]["is_machine_translated"] is False
    mock_upsert.assert_awaited_once_with(
        db=db,
        user_id=user.id,
        locale="en",
        bio_text="I am an emerging Korean artist.",
    )


# ─── Test 4: PATCH /me/bio/xx — invalid locale ───────────────────────────────


@pytest.mark.asyncio
async def test_patch_my_bio_invalid_locale_422():
    """PATCH /me/bio/xx raises 422 for unsupported locale."""
    user = _make_user()
    db = _make_db()
    body = PatchBioRequest(bio="test bio")

    with pytest.raises(ApiError) as exc_info:
        await patch_my_bio_locale(
            locale="xx",
            body=body,
            user=user,
            db=db,
        )
    assert exc_info.value.status_code == 422
    assert exc_info.value.code == "INVALID_LOCALE"


# ─── Test 5: GET /users/{id}/bio — public locale fallback ────────────────────


@pytest.mark.asyncio
async def test_get_artist_bio_by_locale_fallback():
    """GET /users/{id}/bio falls back to ko if requested locale not found."""
    user_id = uuid.uuid4()
    db = _make_db()

    mock_user = MagicMock()
    mock_user.id = user_id
    mock_user.bio = "나는 한국의 신진 작가입니다."

    # DB returns the user, then get_bio_for_locale returns ko text as fallback
    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = mock_user
    db.execute.return_value = user_result

    with patch("app.api.users.get_bio_for_locale", new_callable=AsyncMock) as mock_get:
        # get_bio_for_locale returns None for "en" (no translation stored)
        mock_get.return_value = None

        result = await get_artist_bio_by_locale(
            user_id=user_id,
            locale="en",
            db=db,
        )

    # Should fall back to User.bio (raw ko text)
    assert result["data"]["user_id"] == str(user_id)
    # bio falls back to user.bio which is set
    assert result["data"]["bio"] == "나는 한국의 신진 작가입니다."
