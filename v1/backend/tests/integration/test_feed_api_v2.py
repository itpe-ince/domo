"""Integration tests — /api/feed v2 ML 피드 엔드포인트 (Phase 9 K-1).

전략: AsyncMock DB + endpoint 함수 직접 호출 (실제 DB 불필요).
기존 test_personalized_feed.py 패턴 동일.

테스트 항목:
  1. algo=v1 → 기존 피드 응답 형식 동일 (회귀 없음)
  2. algo=v2 → ML 피드 응답 (cold user fallback 포함, 200 OK + 형식 동일)
  3. algo=auto + ML_FEED_V2_ENABLED=false → v1 동작 (기본 safe rollout)
  4. algo=v2, cold user (interaction 0건) → fallback 200 OK
  5. _resolve_ml_algo: 각 algo 값 → bool 반환 검증
  6. POST /feed/interaction → 201 Created (성공) 또는 404 (post 미존재)
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.api.posts import _resolve_ml_algo


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _make_user(role: str = "user") -> MagicMock:
    u = MagicMock()
    u.id = uuid.uuid4()
    u.email = "test@domo.test"
    u.role = role
    u.display_name = "Test User"
    u.avatar_url = None
    u.status = "active"
    u.sponsor_validity_days = None
    return u


def _make_post_orm(
    *,
    post_id: uuid.UUID | None = None,
    author_id: uuid.UUID | None = None,
    hours_old: float = 1.0,
) -> MagicMock:
    now = datetime.now(timezone.utc)
    p = MagicMock()
    p.id = post_id or uuid.uuid4()
    p.author_id = author_id or uuid.uuid4()
    p.type = "general"
    p.title = "Test Post"
    p.content = "Content"
    p.genre = None
    p.tags = []
    p.language = "ko"
    p.like_count = 0
    p.comment_count = 0
    p.view_count = 0
    p.bluebird_count = 0
    p.status = "published"
    p.digital_art_check = "not_required"
    p.scheduled_at = None
    p.location_name = None
    p.location_lat = None
    p.location_lng = None
    p.created_at = now - timedelta(hours=hours_old)
    p.media = []
    p.product = None
    p.visibility = "public"
    p.comments_enabled = True
    p.early_access_until = None
    p.early_access_tier = None
    p.author = None
    p._active_auction_end_at = None
    return p


# ─── _resolve_ml_algo 단위 검증 ──────────────────────────────────────────────


def test_resolve_ml_algo_v2_always_true():
    """algo=v2 → 항상 ML 사용."""
    user = _make_user()
    assert _resolve_ml_algo("v2", user) is True
    assert _resolve_ml_algo("v2", None) is True


def test_resolve_ml_algo_v1_always_false():
    """algo=v1 → 항상 기존 룰 기반."""
    user = _make_user()
    assert _resolve_ml_algo("v1", user) is False


def test_resolve_ml_algo_default_always_false():
    """algo=default → 항상 기존 룰 기반."""
    user = _make_user()
    assert _resolve_ml_algo("default", user) is False


def test_resolve_ml_algo_auto_no_user():
    """algo=auto + 비로그인 사용자 → False."""
    assert _resolve_ml_algo("auto", None) is False


def test_resolve_ml_algo_auto_flag_off():
    """algo=auto + ML_FEED_V2_ENABLED=false → False."""
    user = _make_user()
    with patch.dict("os.environ", {"ML_FEED_V2_ENABLED": "false"}):
        assert _resolve_ml_algo("auto", user) is False


def test_resolve_ml_algo_auto_flag_on():
    """algo=auto + ML_FEED_V2_ENABLED=true → True."""
    user = _make_user()
    with patch.dict("os.environ", {"ML_FEED_V2_ENABLED": "true"}):
        assert _resolve_ml_algo("auto", user) is True


# ─── home_feed: algo=v1 회귀 없음 ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_feed_algo_v1_returns_data():
    """algo=v1 → 기존 _personalized_feed_v1 호출, 응답 형식 동일."""
    from app.api.posts import home_feed

    user = _make_user()
    db = AsyncMock()

    expected_result = {
        "data": [],
        "pagination": {"next_cursor": None, "has_more": False},
    }

    with patch("app.api.posts._personalized_feed_v1", new_callable=AsyncMock, return_value=expected_result):
        result = await home_feed(
            limit=5,
            following_only=False,
            algo="v1",
            cursor=None,
            user=user,
            db=db,
        )

    assert "data" in result
    assert "pagination" in result
    assert isinstance(result["data"], list)


# ─── home_feed: algo=v2 cold user fallback ───────────────────────────────────


@pytest.mark.asyncio
async def test_feed_algo_v2_cold_user_fallback():
    """algo=v2 + interaction 0건 cold user → fallback 피드 반환 (200 OK, 리스트)."""
    from app.api.posts import home_feed

    user = _make_user()
    db = AsyncMock()

    # ML inference에서 cold user fallback으로 빈 리스트 반환
    with (
        patch(
            "app.services.ml_feed_inference.get_recommendations",
            new_callable=AsyncMock, return_value=[],
        ),
        patch(
            "app.api.posts._personalized_feed_v1",
            new_callable=AsyncMock,
            return_value={
                "data": [],
                "pagination": {"next_cursor": None, "has_more": False},
            },
        ),
    ):
        result = await home_feed(
            limit=5,
            following_only=False,
            algo="v2",
            cursor=None,
            user=user,
            db=db,
        )

    assert "data" in result
    assert "pagination" in result
    assert isinstance(result["data"], list)


@pytest.mark.asyncio
async def test_feed_algo_v2_with_ml_results():
    """algo=v2 + ML 추천 결과 있음 → ML 결과 반환, algo_used='v2' 메타 포함."""
    from app.api.posts import home_feed

    user = _make_user()
    author_id = uuid.uuid4()
    db = AsyncMock()
    post = _make_post_orm(author_id=author_id)
    post.author = _make_user()

    with (
        patch(
            "app.services.ml_feed_inference.get_recommendations",
            new_callable=AsyncMock,
            return_value=[str(post.id)],
        ),
        patch(
            "app.api.posts._load_posts_by_ids",
            new_callable=AsyncMock,
            return_value=[post],
        ),
        patch("app.api.posts._attach_active_auction_end_at", new_callable=AsyncMock),
        patch("app.api.posts._serialize_post", return_value={
            "id": str(post.id),
            "type": "general",
            "author": {"id": str(author_id), "display_name": "Test User", "role": "user"},
            "created_at": "2026-05-05T00:00:00Z",
        }),
    ):
        result = await home_feed(
            limit=5,
            following_only=False,
            algo="v2",
            cursor=None,
            user=user,
            db=db,
        )

    assert "data" in result
    assert "pagination" in result
    assert result.get("algo_used") == "v2"
    assert len(result["data"]) == 1
    assert "id" in result["data"][0]


# ─── home_feed: algo=auto + flag off → v1 동작 ───────────────────────────────


@pytest.mark.asyncio
async def test_feed_algo_auto_flag_off_uses_v1_default():
    """algo=auto + ML_FEED_V2_ENABLED=false → 기존 default 경로 사용."""
    from app.api.posts import home_feed

    user = _make_user()
    db = AsyncMock()

    follow_result = MagicMock()
    follow_result.all.return_value = []
    db.execute = AsyncMock(return_value=follow_result)

    scalars_mock = MagicMock()
    scalars_mock.scalars.return_value.all.return_value = []

    db.execute = AsyncMock(return_value=scalars_mock)

    with (
        patch.dict("os.environ", {"ML_FEED_V2_ENABLED": "false"}),
        patch("app.api.posts._attach_active_auction_end_at", new_callable=AsyncMock),
    ):
        result = await home_feed(
            limit=5,
            following_only=False,
            algo="auto",
            cursor=None,
            user=user,
            db=db,
        )

    assert "data" in result
    assert "pagination" in result
    # K-8: auto + flag off 시 algo_used='v1' (v2 아님)
    assert result.get("algo_used") != "v2"


# ─── record_feed_interaction ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_record_feed_interaction_post_not_found():
    """POST /feed/interaction + 존재하지 않는 post_id → 404."""
    from app.api.posts import record_feed_interaction, FeedInteractionIn
    from app.core.errors import ApiError

    user = _make_user()
    db = AsyncMock()

    # post 존재 확인 쿼리 → None 반환
    db.execute = AsyncMock(return_value=MagicMock(fetchone=lambda: None))

    with pytest.raises(ApiError) as exc_info:
        await record_feed_interaction(
            body=FeedInteractionIn(post_id=str(uuid.uuid4()), interaction_type="view"),
            user=user,
            db=db,
            _rl=None,
        )

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_record_feed_interaction_success():
    """POST /feed/interaction + 유효한 post_id → 201 OK."""
    from app.api.posts import record_feed_interaction, FeedInteractionIn

    user = _make_user()
    db = AsyncMock()
    post_id = str(uuid.uuid4())

    # post 존재 확인 → row 반환
    db.execute = AsyncMock(return_value=MagicMock(fetchone=lambda: MagicMock()))
    db.commit = AsyncMock()

    result = await record_feed_interaction(
        body=FeedInteractionIn(post_id=post_id, interaction_type="like"),
        user=user,
        db=db,
        _rl=None,
    )

    assert result == {"data": {"ok": True}}
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_record_feed_interaction_invalid_type():
    """POST /feed/interaction + 잘못된 interaction_type → 422."""
    from app.api.posts import record_feed_interaction, FeedInteractionIn
    from app.core.errors import ApiError

    user = _make_user()
    db = AsyncMock()

    # invalid_type은 _INTERACTION_WEIGHTS에 없음
    with pytest.raises(ApiError) as exc_info:
        await record_feed_interaction(
            body=FeedInteractionIn(post_id=str(uuid.uuid4()), interaction_type="invalid_type"),
            user=user,
            db=db,
            _rl=None,
        )

    assert exc_info.value.status_code == 422
