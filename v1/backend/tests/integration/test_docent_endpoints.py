"""Integration tests — K-5 도슨트 API 엔드포인트 (llm-docent-artwork).

Phase 9 K-5: docent endpoint 4개의 권한, 다국어, opt-out, 직접 작성 검증.

Strategy:
  - 함수 직접 호출 (FastAPI TestClient 없이 endpoint 함수 임포트)
  - AsyncMock DB + MagicMock Post/User
  - LLM Mock 모드: LLM_GATEWAY_API_KEY 미설정 상태 시뮬레이션

Test count: 9
  1. generate: 작가 본인만 가능 (cross-user 403)
  2. generate: opt_out=True 시 403
  3. generate: 24h 이내 중복 → 409
  4. generate: Mock 모드 → None 반환 (graceful)
  5. patch (직접 작성): artist_docent_text 저장 확인
  6. get (공개): 인증 없이 접근 가능, artist+ai 도슨트 반환
  7. get: locale=en → locale_docent=영어번역 확인
  8. get: opted_out=True → ai_docent_text null 반환
  9. opt-out 토글: True → False 정상 동작
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.errors import ApiError


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _make_user(uid: uuid.UUID | None = None, role: str = "artist") -> MagicMock:
    u = MagicMock()
    u.id = uid or uuid.uuid4()
    u.role = role
    u.display_name = "Test Artist"
    u.country_code = "KR"
    u.artist_index_primary_genre = "회화"
    profile = MagicMock()
    profile.statement = "자연에서 영감을 받습니다."
    profile.genre_tags = ["추상화"]
    u.artist_profile = profile
    return u


def _make_post(
    *,
    author_id: uuid.UUID | None = None,
    ai_docent_opted_out: bool = False,
    ai_docent_generated_at: datetime | None = None,
    ai_docent_text: str | None = None,
    ai_docent_translations: dict | None = None,
    artist_docent_text: str | None = None,
) -> MagicMock:
    p = MagicMock()
    p.id = uuid.uuid4()
    p.author_id = author_id or uuid.uuid4()
    p.title = "테스트 작품"
    p.genre = "회화"
    p.tags = ["추상"]
    p.ai_caption = None
    p.ai_docent_opted_out = ai_docent_opted_out
    p.ai_docent_generated_at = ai_docent_generated_at
    p.ai_docent_text = ai_docent_text
    p.ai_docent_translations = ai_docent_translations or {}
    p.artist_docent_text = artist_docent_text
    p.ai_docent_model_version = None
    p.media = []
    return p


def _make_db(*, post: MagicMock | None = None, artist: MagicMock | None = None) -> AsyncMock:
    db = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()

    # scalar_one_or_none 체인 설정
    result_mock = AsyncMock()
    result_mock.scalar_one_or_none = MagicMock(return_value=post)
    db.execute = AsyncMock(return_value=result_mock)

    return db


# ─── 1. generate: cross-user 403 ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_generate_docent_cross_user_forbidden():
    """다른 작가 포스트에 generate 요청 → 403 FORBIDDEN."""
    from app.api.posts import generate_post_docent, _assert_docent_author

    owner = _make_user()
    requester = _make_user()  # 다른 사용자
    post = _make_post(author_id=owner.id)

    with pytest.raises(ApiError) as exc_info:
        _assert_docent_author(post, requester)

    assert exc_info.value.status_code == 403
    assert exc_info.value.code == "FORBIDDEN"


# ─── 2. generate: opted_out=True → 403 ───────────────────────────────────────


@pytest.mark.asyncio
async def test_generate_docent_opted_out_403():
    """opted_out=True인 포스트에 generate 요청 → 403 DOCENT_OPTED_OUT."""
    artist = _make_user()
    post = _make_post(author_id=artist.id, ai_docent_opted_out=True)
    db = _make_db(post=post)

    with patch("app.api.posts._get_post_for_docent", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = post

        from app.api.posts import generate_post_docent

        with pytest.raises(ApiError) as exc_info:
            await generate_post_docent(
                post_id=post.id,
                user=artist,
                db=db,
            )

    assert exc_info.value.code == "DOCENT_OPTED_OUT"
    assert exc_info.value.status_code == 403


# ─── 3. generate: 24h 이내 중복 → 409 ───────────────────────────────────────


@pytest.mark.asyncio
async def test_generate_docent_24h_conflict():
    """24시간 이내 중복 생성 → 409 DOCENT_RECENTLY_GENERATED."""
    artist = _make_user()
    recent_time = datetime.now(timezone.utc) - timedelta(hours=2)
    post = _make_post(
        author_id=artist.id,
        ai_docent_generated_at=recent_time,
        ai_docent_text="기존 도슨트",
    )
    db = _make_db(post=post)

    with patch("app.api.posts._get_post_for_docent", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = post

        from app.api.posts import generate_post_docent

        with pytest.raises(ApiError) as exc_info:
            await generate_post_docent(
                post_id=post.id,
                user=artist,
                db=db,
            )

    assert exc_info.value.code == "DOCENT_RECENTLY_GENERATED"
    assert exc_info.value.status_code == 409


# ─── 4. generate: Mock 모드 → graceful None ───────────────────────────────────


@pytest.mark.asyncio
async def test_generate_docent_mock_mode_graceful():
    """LLM Gateway 미설정(Mock 모드) → ai_docent_text=null 반환 (예외 없음)."""
    artist = _make_user()
    post = _make_post(author_id=artist.id)
    db = _make_db(post=post)

    # 작가 조회 mock
    artist_result = AsyncMock()
    artist_result.scalar_one_or_none = MagicMock(return_value=artist)
    # 시리즈 멤버십 없음
    no_membership = AsyncMock()
    no_membership.scalar_one_or_none = MagicMock(return_value=None)

    db.execute = AsyncMock(side_effect=[
        # _get_post_for_docent → post
        AsyncMock(scalar_one_or_none=MagicMock(return_value=post)),
        # 작가 조회
        artist_result,
        # 시리즈 멤버십 조회
        no_membership,
    ])

    with patch("app.api.posts._get_post_for_docent", new_callable=AsyncMock) as mock_get, \
         patch("app.api.posts.generate_docent", new_callable=AsyncMock) as mock_gen:

        mock_get.return_value = post
        mock_gen.return_value = None  # Mock 모드 — None 반환

        from app.api.posts import generate_post_docent

        response = await generate_post_docent(
            post_id=post.id,
            user=artist,
            db=db,
        )

    assert response["data"]["ai_docent_text"] is None
    assert "비활성화" in response["data"]["message"]


# ─── 5. patch_artist_docent: 직접 작성 저장 확인 ─────────────────────────────


@pytest.mark.asyncio
async def test_patch_artist_docent_saves():
    """PATCH /docent → artist_docent_text DB 저장 확인."""
    from app.schemas.docent import DocentPatchRequest

    artist = _make_user()
    post = _make_post(author_id=artist.id)
    db = _make_db(post=post)

    with patch("app.api.posts._get_post_for_docent", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = post
        db.refresh = AsyncMock(side_effect=lambda p: setattr(p, "artist_docent_text", "작가의 말"))

        from app.api.posts import patch_artist_docent

        body = DocentPatchRequest(artist_docent_text="작가의 말")
        response = await patch_artist_docent(
            post_id=post.id,
            body=body,
            user=artist,
            db=db,
        )

    assert post.artist_docent_text == "작가의 말"
    db.commit.assert_called_once()
    assert "artist_docent_text" in response["data"]


# ─── 6. get_post_docent: 공개 접근 가능 ──────────────────────────────────────


@pytest.mark.asyncio
async def test_get_docent_public():
    """GET /docent 인증 없이 접근 가능 확인 + artist+ai 도슨트 반환."""
    post = _make_post(
        artist_docent_text="작가의 말입니다.",
        ai_docent_text="AI 생성 해설입니다.",
        ai_docent_translations={"en": "AI docent in English."},
    )
    db = _make_db()

    result_mock = AsyncMock()
    result_mock.scalar_one_or_none = MagicMock(return_value=post)
    db.execute = AsyncMock(return_value=result_mock)

    from app.api.posts import get_post_docent

    response = await get_post_docent(post_id=post.id, locale="ko", db=db)

    data = response["data"]
    assert data["artist_docent_text"] == "작가의 말입니다."
    assert data["ai_docent_text"] == "AI 생성 해설입니다."
    assert data["ai_docent_opted_out"] is False
    assert data["locale"] == "ko"


# ─── 7. get_post_docent: locale=en → 영어번역 반환 ───────────────────────────


@pytest.mark.asyncio
async def test_get_docent_locale_translation():
    """GET /docent?locale=en → locale_docent=영어번역 확인."""
    post = _make_post(
        ai_docent_text="한국어 도슨트",
        ai_docent_translations={"en": "English docent translation."},
    )
    db = _make_db()

    result_mock = AsyncMock()
    result_mock.scalar_one_or_none = MagicMock(return_value=post)
    db.execute = AsyncMock(return_value=result_mock)

    from app.api.posts import get_post_docent

    response = await get_post_docent(post_id=post.id, locale="en", db=db)

    data = response["data"]
    assert data["locale_docent"] == "English docent translation."
    assert data["locale"] == "en"


# ─── 8. get_post_docent: opted_out=True → ai null ────────────────────────────


@pytest.mark.asyncio
async def test_get_docent_opted_out():
    """opted_out=True → ai_docent_text null 반환 확인."""
    post = _make_post(
        ai_docent_opted_out=True,
        ai_docent_text="숨겨진 도슨트",
    )
    db = _make_db()

    result_mock = AsyncMock()
    result_mock.scalar_one_or_none = MagicMock(return_value=post)
    db.execute = AsyncMock(return_value=result_mock)

    from app.api.posts import get_post_docent

    response = await get_post_docent(post_id=post.id, locale="ko", db=db)

    data = response["data"]
    assert data["ai_docent_text"] is None
    assert data["ai_docent_opted_out"] is True
    assert data["locale_docent"] is None


# ─── 9. opt-out 토글 ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_opt_out_toggle():
    """PATCH /opt-out → opted_out true→false 토글 정상 동작."""
    from app.schemas.docent import DocentOptOutRequest

    artist = _make_user()
    post = _make_post(author_id=artist.id, ai_docent_opted_out=True)
    db = _make_db(post=post)

    with patch("app.api.posts._get_post_for_docent", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = post

        from app.api.posts import patch_docent_opt_out

        # 비활성화 → 활성화
        body = DocentOptOutRequest(opted_out=False)
        response = await patch_docent_opt_out(
            post_id=post.id,
            body=body,
            user=artist,
            db=db,
        )

    assert post.ai_docent_opted_out is False
    db.commit.assert_called_once()
    data = response["data"]
    assert data["ai_docent_opted_out"] is False
    assert "활성화" in data["message"]
