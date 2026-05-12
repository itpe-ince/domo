"""Integration test — active_auction_end_at feed endpoint supply.

Phase 4 #11 auction-promotion-suite — AC-12 verification.

1 test case:
  - home_feed returns active_auction_end_at for a product post with an active auction
    whose end_at is within 1 hour (D-1h compact countdown scenario).
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.api.posts import home_feed


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_user(*, user_id: uuid.UUID | None = None) -> MagicMock:
    u = MagicMock()
    u.id = user_id or uuid.uuid4()
    u.role = "user"
    u.display_name = "Test User"
    u.avatar_url = None
    return u


def _make_product_post(
    *,
    post_id: uuid.UUID | None = None,
    author_id: uuid.UUID | None = None,
) -> MagicMock:
    """Build a minimal published product Post mock."""
    p = MagicMock()
    p.id = post_id or uuid.uuid4()
    p.author_id = author_id or uuid.uuid4()
    p.type = "product"
    p.title = "Product Post"
    p.content = "Some content"
    p.genre = "painting"
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
    p.created_at = datetime.now(UTC)
    p.media = []
    p.product = None
    p.visibility = "public"
    p.comments_enabled = True
    p.early_access_until = None
    p.early_access_tier = None
    # K-3 AI caption fields
    p.ai_caption = None
    p.ai_caption_locale_translations = {}
    p.ai_caption_model_version = None
    p.ai_caption_generated_at = None
    p.caption_override = None
    return p


# ---------------------------------------------------------------------------
# Test: home_feed includes active_auction_end_at in serialized post output
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_feed_includes_active_auction_end_at():
    """AC-12: feed serializes active_auction_end_at so frontend PostCard
    can show D-1h compact countdown.

    Arrange: trending feed returns one product post; DB auction query
    returns end_at = now + 45min (within 1h window).
    Assert: serialized post has active_auction_end_at != None.
    """
    viewer = _make_user()
    post = _make_product_post(author_id=uuid.uuid4())
    end_at = datetime.now(UTC) + timedelta(minutes=45)

    # Sequence of DB execute calls:
    # 1. Follow query (home_feed checks followee_ids)
    # 2. Author bulk query
    # 3. Trending posts query (followee_ids empty, all trending)
    # 4. _attach_active_auction_end_at query
    # (author bulk for trending is call 2 after trending query)

    follows_result = MagicMock()
    follows_result.all.return_value = []  # no followees → trending-only feed

    trending_result = MagicMock()
    trending_scalars = MagicMock()
    trending_scalars.all.return_value = [post]
    trending_result.scalars.return_value = trending_scalars

    authors_result = MagicMock()
    authors_result.scalars.return_value = [_make_user(user_id=post.author_id)]
    # authors_result needs .scalars().all() pattern
    authors_scalars = MagicMock()
    author_user = _make_user(user_id=post.author_id)
    author_user.id = post.author_id
    authors_scalars.all.return_value = [author_user]
    authors_result.scalars.return_value = authors_scalars

    # auction end_at result
    auction_rows = MagicMock()
    auction_rows.all.return_value = [(post.id, end_at)]

    # K-8: home_feed now looks up ml_experiment_assignments at the start
    experiment_result = MagicMock()
    experiment_result.fetchone.return_value = None  # no active experiment

    db = AsyncMock()
    execute_calls = [
        experiment_result, # K-8: ml_experiment lookup (no active experiment)
        follows_result,    # Follow.followee_id query
        trending_result,   # trending posts query
        authors_result,    # author bulk query
        auction_rows,      # _attach_active_auction_end_at
    ]
    db.execute = AsyncMock(side_effect=execute_calls)

    result = await home_feed(limit=20, following_only=False, user=viewer, db=db)

    assert "data" in result
    assert len(result["data"]) == 1
    item = result["data"][0]
    assert item["active_auction_end_at"] is not None, (
        "AC-12 FAIL: active_auction_end_at must be populated for product posts "
        "with an active auction so frontend PostCard can render D-1h countdown"
    )
