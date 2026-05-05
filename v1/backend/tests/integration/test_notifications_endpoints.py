"""Integration-style endpoint tests for notifications UX audit — D-4.

Strategy: direct endpoint function calls with MagicMock for SQLAlchemy model
instances, AsyncMock for DB session. No real DB, no real network.
Mirrors test_artist_tier_release_endpoints.py pattern.

12 test cases:
  list_notifications (4):
    1. 200 returns all notifications for authenticated user
    2. 200 unread_only=true filters read items
    3. 200 types=auction expands category to type list
    4. 200 types=like,comment (explicit CSV) filters correctly

  unread_count (1):
    5. 200 returns correct unread count

  mark_all_read (2):
    6. 200 marks unread items and returns rowcount
    7. 200 idempotent — second call returns updated=0

  mark_read (2):
    8. 200 single notification mark-read
    9. 403 cross-user attempt raises FORBIDDEN

  mark_read_by_type (3):
    10. 200 category slug expanded and updated
    11. 200 explicit CSV updated
    12. 422 empty types string raises INVALID_INPUT
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.errors import ApiError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _make_user(*, user_id: uuid.UUID | None = None) -> MagicMock:
    u = MagicMock()
    u.id = user_id or uuid.uuid4()
    return u


def _make_notification(
    *,
    notif_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
    type_: str = "like",
    is_read: bool = False,
    link: str | None = None,
) -> MagicMock:
    n = MagicMock()
    n.id = notif_id or uuid.uuid4()
    n.user_id = user_id or uuid.uuid4()
    n.type = type_
    n.title = "Test notification"
    n.body = "body text"
    n.link = link
    n.is_read = is_read
    n.created_at = _now()
    return n


def _make_db(*, scalars_all: list | None = None, scalar_one: object = None, scalar: int = 0):
    db = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = scalars_all or []
    result.scalar_one_or_none.return_value = scalar_one
    db.execute.return_value = result
    db.scalar.return_value = scalar
    # simulate rowcount for UPDATE
    result.rowcount = 0
    return db


# ---------------------------------------------------------------------------
# 1. list_notifications — 200 all
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_notifications_200_all():
    from app.api.notifications import list_notifications

    user = _make_user()
    n1 = _make_notification(user_id=user.id, type_="like", is_read=False)
    n2 = _make_notification(user_id=user.id, type_="comment", is_read=True)
    db = _make_db(scalars_all=[n1, n2])

    resp = await list_notifications(
        unread_only=False, limit=30, types=None, user=user, db=db
    )

    assert "data" in resp
    assert len(resp["data"]) == 2


# ---------------------------------------------------------------------------
# 2. list_notifications — 200 unread_only
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_notifications_200_unread_only():
    from app.api.notifications import list_notifications

    user = _make_user()
    n1 = _make_notification(user_id=user.id, type_="like", is_read=False)
    db = _make_db(scalars_all=[n1])

    resp = await list_notifications(
        unread_only=True, limit=30, types=None, user=user, db=db
    )

    assert len(resp["data"]) == 1
    assert resp["data"][0]["is_read"] is False


# ---------------------------------------------------------------------------
# 3. list_notifications — 200 types=auction category slug
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_notifications_200_types_category():
    from app.api.notifications import list_notifications

    user = _make_user()
    n1 = _make_notification(user_id=user.id, type_="auction_ended", is_read=False)
    db = _make_db(scalars_all=[n1])

    resp = await list_notifications(
        unread_only=False, limit=30, types="auction", user=user, db=db
    )

    assert len(resp["data"]) == 1
    assert resp["data"][0]["type"] == "auction_ended"
    # Verify the DB query was constructed (execute was called)
    db.execute.assert_called_once()


# ---------------------------------------------------------------------------
# 4. list_notifications — 200 types=like,comment CSV
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_notifications_200_types_csv():
    from app.api.notifications import list_notifications

    user = _make_user()
    n1 = _make_notification(user_id=user.id, type_="like", is_read=False)
    db = _make_db(scalars_all=[n1])

    resp = await list_notifications(
        unread_only=False, limit=30, types="like,comment", user=user, db=db
    )

    assert len(resp["data"]) == 1


# ---------------------------------------------------------------------------
# 5. unread_count — 200
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_unread_count_200():
    from app.api.notifications import unread_count

    user = _make_user()
    db = _make_db(scalar=5)

    resp = await unread_count(user=user, db=db)

    assert resp == {"data": {"count": 5}}


# ---------------------------------------------------------------------------
# 6. mark_all_read — 200 updates unread
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mark_all_read_200():
    from app.api.notifications import mark_all_read

    user = _make_user()
    db = AsyncMock()
    result = MagicMock()
    result.rowcount = 3
    db.execute.return_value = result

    resp = await mark_all_read(user=user, db=db)

    assert resp["data"]["updated"] == 3
    db.commit.assert_called_once()


# ---------------------------------------------------------------------------
# 7. mark_all_read — idempotent (rowcount=0 on second call)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mark_all_read_idempotent():
    from app.api.notifications import mark_all_read

    user = _make_user()
    db = AsyncMock()
    result = MagicMock()
    result.rowcount = 0
    db.execute.return_value = result

    resp = await mark_all_read(user=user, db=db)

    assert resp["data"]["updated"] == 0


# ---------------------------------------------------------------------------
# 8. mark_read — 200 single notification
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mark_read_200():
    from app.api.notifications import mark_read

    user = _make_user()
    notif_id = uuid.uuid4()
    n = _make_notification(notif_id=notif_id, user_id=user.id, is_read=False)
    db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = n
    db.execute.return_value = result
    db.refresh = AsyncMock()

    resp = await mark_read(notification_id=notif_id, user=user, db=db)

    assert n.is_read is True
    assert resp["data"]["id"] == str(notif_id)


# ---------------------------------------------------------------------------
# 9. mark_read — 403 cross-user
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mark_read_403_cross_user():
    from app.api.notifications import mark_read

    user = _make_user()
    other_user_id = uuid.uuid4()
    notif_id = uuid.uuid4()
    n = _make_notification(notif_id=notif_id, user_id=other_user_id, is_read=False)
    db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = n
    db.execute.return_value = result

    with pytest.raises(ApiError) as exc_info:
        await mark_read(notification_id=notif_id, user=user, db=db)
    assert exc_info.value.status_code == 403


# ---------------------------------------------------------------------------
# 10. mark_read_by_type — 200 category slug
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mark_read_by_type_200_category():
    from app.api.notifications import mark_read_by_type

    user = _make_user()
    db = AsyncMock()
    result = MagicMock()
    result.rowcount = 4
    db.execute.return_value = result

    resp = await mark_read_by_type(types="auction", user=user, db=db)

    assert resp["data"]["updated"] == 4
    # returned types list should be the expanded auction types
    assert "auction_ended" in resp["data"]["types"]
    db.commit.assert_called_once()


# ---------------------------------------------------------------------------
# 11. mark_read_by_type — 200 explicit CSV
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mark_read_by_type_200_csv():
    from app.api.notifications import mark_read_by_type

    user = _make_user()
    db = AsyncMock()
    result = MagicMock()
    result.rowcount = 2
    db.execute.return_value = result

    resp = await mark_read_by_type(types="like,comment", user=user, db=db)

    assert resp["data"]["updated"] == 2
    assert set(resp["data"]["types"]) == {"like", "comment"}


# ---------------------------------------------------------------------------
# 12. mark_read_by_type — 422 empty types
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mark_read_by_type_422_empty():
    from app.api.notifications import mark_read_by_type

    user = _make_user()
    db = AsyncMock()

    with pytest.raises(ApiError) as exc_info:
        await mark_read_by_type(types="  ,  ", user=user, db=db)
    assert exc_info.value.status_code == 422
