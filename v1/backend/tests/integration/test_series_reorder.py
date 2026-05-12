"""Integration-style tests for D-3: series-reorder-persistence.

POST /v1/series/{id}/reorder — persist dnd-kit order to PostSeriesMembership.order_index.

Strategy: direct endpoint function calls with MagicMock stand-ins for SQLAlchemy
model instances, AsyncMock for DB session. No real DB, no real network.

7 test cases:
  1. 200 happy path: 3 posts reordered successfully
  2. 403 non-owner
  3. 404 series not found
  4. 422 empty post_ids (schema validation)
  5. 422 duplicate post_ids
  6. 422 post_ids count mismatch (missing member)
  7. 422 post_ids contain non-member post
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.api.series import reorder_series_posts
from app.core.errors import ApiError
from app.models.series import PostSeriesMembership, Series
from app.schemas.series import SeriesReorderRequest


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _make_user(*, user_id: uuid.UUID | None = None, role: str = "artist") -> MagicMock:
    u = MagicMock()
    u.id = user_id or uuid.uuid4()
    u.role = role
    return u


def _make_series(*, series_id: uuid.UUID | None = None, author_id: uuid.UUID | None = None) -> MagicMock:
    s = MagicMock()
    s.id = series_id or uuid.uuid4()
    s.author_id = author_id or uuid.uuid4()
    s.updated_at = datetime.now(timezone.utc)
    return s


def _make_membership(series_id: uuid.UUID, post_id: uuid.UUID, order_index: int = 0) -> MagicMock:
    m = MagicMock(spec=PostSeriesMembership)
    m.series_id = series_id
    m.post_id = post_id
    m.order_index = order_index
    return m


def _make_db_with_series_and_memberships(
    series: MagicMock | None,
    memberships: list[MagicMock],
) -> AsyncMock:
    """DB mock that returns series on first execute() and memberships on second."""
    db = AsyncMock()

    series_result = MagicMock()
    series_result.scalar_one_or_none.return_value = series

    mem_scalars = MagicMock()
    mem_scalars.all.return_value = memberships
    mem_result = MagicMock()
    mem_result.scalars.return_value = mem_scalars

    # execute calls: [1] series lookup, [2] memberships lookup
    execute_results = iter([series_result, mem_result])

    async def _execute(stmt, *args, **kwargs):
        return next(execute_results)

    db.execute = _execute
    db.commit = AsyncMock()
    db.refresh = AsyncMock(side_effect=lambda obj: None)
    return db


# ---------------------------------------------------------------------------
# Test 1 — 200 happy path: 3 posts reordered
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_reorder_200_happy_path():
    user = _make_user()
    series = _make_series(author_id=user.id)

    p1, p2, p3 = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    memberships = [
        _make_membership(series.id, p1, order_index=0),
        _make_membership(series.id, p2, order_index=1),
        _make_membership(series.id, p3, order_index=2),
    ]
    db = _make_db_with_series_and_memberships(series, memberships)

    # Reorder: p3 first, then p1, then p2
    body = SeriesReorderRequest(post_ids=[p3, p1, p2])
    result = await reorder_series_posts(series.id, body, user, db, _rl=None)

    assert "data" in result
    data = result["data"]
    assert str(series.id) in str(data["series_id"])
    # ordered_post_ids should match input order
    assert [str(oid) for oid in data["ordered_post_ids"]] == [str(p3), str(p1), str(p2)]
    # Memberships must have been updated
    m_map = {m.post_id: m for m in memberships}
    assert m_map[p3].order_index == 0
    assert m_map[p1].order_index == 1
    assert m_map[p2].order_index == 2


# ---------------------------------------------------------------------------
# Test 2 — 403 non-owner
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_reorder_403_not_owner():
    owner_id = uuid.uuid4()
    other_user = _make_user()  # different id
    series = _make_series(author_id=owner_id)

    p1 = uuid.uuid4()
    memberships = [_make_membership(series.id, p1)]
    db = _make_db_with_series_and_memberships(series, memberships)

    body = SeriesReorderRequest(post_ids=[p1])
    with pytest.raises(ApiError) as exc_info:
        await reorder_series_posts(series.id, body, other_user, db, _rl=None)

    err = exc_info.value
    assert err.code == "SERIES_NOT_OWNER"
    assert err.status_code == 403


# ---------------------------------------------------------------------------
# Test 3 — 404 series not found
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_reorder_404_series_not_found():
    user = _make_user()
    # DB returns None for series lookup
    db = _make_db_with_series_and_memberships(series=None, memberships=[])

    body = SeriesReorderRequest(post_ids=[uuid.uuid4()])
    with pytest.raises(ApiError) as exc_info:
        await reorder_series_posts(uuid.uuid4(), body, user, db, _rl=None)

    err = exc_info.value
    assert err.code == "SERIES_NOT_FOUND"
    assert err.status_code == 404


# ---------------------------------------------------------------------------
# Test 4 — 422 empty post_ids (Pydantic schema validation: min_length=1)
# ---------------------------------------------------------------------------


def test_reorder_422_empty_post_ids():
    with pytest.raises(Exception):
        # Pydantic min_length=1 raises ValidationError for empty list
        SeriesReorderRequest(post_ids=[])


# ---------------------------------------------------------------------------
# Test 5 — 422 duplicate post_ids
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_reorder_422_duplicate_post_ids():
    user = _make_user()
    series = _make_series(author_id=user.id)

    p1 = uuid.uuid4()
    memberships = [_make_membership(series.id, p1)]
    db = _make_db_with_series_and_memberships(series, memberships)

    body = SeriesReorderRequest(post_ids=[p1, p1])  # duplicate
    with pytest.raises(ApiError) as exc_info:
        await reorder_series_posts(series.id, body, user, db, _rl=None)

    err = exc_info.value
    assert err.code == "DUPLICATE_POST_IDS"
    assert err.status_code == 422


# ---------------------------------------------------------------------------
# Test 6 — 422 count mismatch (missing member)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_reorder_422_count_mismatch():
    user = _make_user()
    series = _make_series(author_id=user.id)

    p1, p2, p3 = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    memberships = [
        _make_membership(series.id, p1),
        _make_membership(series.id, p2),
        _make_membership(series.id, p3),
    ]
    db = _make_db_with_series_and_memberships(series, memberships)

    # Only 2 of 3 posts provided
    body = SeriesReorderRequest(post_ids=[p1, p2])
    with pytest.raises(ApiError) as exc_info:
        await reorder_series_posts(series.id, body, user, db, _rl=None)

    err = exc_info.value
    assert err.code == "POST_IDS_INCOMPLETE"
    assert err.status_code == 422


# ---------------------------------------------------------------------------
# Test 7 — 422 non-member post included
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_reorder_422_non_member_post():
    user = _make_user()
    series = _make_series(author_id=user.id)

    p1, p2 = uuid.uuid4(), uuid.uuid4()
    stranger = uuid.uuid4()  # not in series
    memberships = [
        _make_membership(series.id, p1),
        _make_membership(series.id, p2),
    ]
    db = _make_db_with_series_and_memberships(series, memberships)

    # Same count but includes a non-member
    body = SeriesReorderRequest(post_ids=[p1, stranger])
    with pytest.raises(ApiError) as exc_info:
        await reorder_series_posts(series.id, body, user, db, _rl=None)

    err = exc_info.value
    assert err.code == "POST_NOT_IN_SERIES"
    assert err.status_code == 422
