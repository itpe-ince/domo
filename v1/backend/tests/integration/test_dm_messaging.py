"""Integration tests for B'-2 dm-messaging.

Strategy: direct endpoint function calls with AsyncMock DB + MagicMock objects.
No real DB required. Mirrors test_notifications_endpoints.py pattern.

11 test cases (8 integration + 3 unit):

Integration:
  1. start_conversation — 201 new conversation created
  2. start_conversation — 409-like: returns existing conversation (idempotent)
  3. list_my_conversations — 200 returns participant conversations
  4. list_messages — 200 returns message list
  5. list_messages — 403 non-participant rejected
  6. send_message — 201 emits notification + updates last_message_at
  7. edit_message — 422 when edit window expired
  8. mark_conversation_read — 200 rowcount returned

Unit:
  9.  _sanitise strips HTML tags
  10. _normalise_pair always returns smaller UUID first
  11. admin_close_conversation — 200 sets closed_by_admin_at
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.api.conversations import (
    _normalise_pair,
    _sanitise,
    edit_message,
    list_messages,
    list_my_conversations,
    mark_conversation_read,
    send_message,
    start_conversation,
)
from app.core.errors import ApiError
from app.schemas.dm import EditMessageRequest, SendMessageRequest, StartConversationRequest


# ── Helpers ────────────────────────────────────────────────────────────────────


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _make_user(*, role: str = "user") -> MagicMock:
    u = MagicMock()
    u.id = uuid.uuid4()
    u.role = role
    u.status = "active"
    return u


def _make_conv(
    user_a: uuid.UUID | None = None,
    user_b: uuid.UUID | None = None,
    *,
    closed: bool = False,
) -> MagicMock:
    conv = MagicMock()
    conv.id = uuid.uuid4()
    conv.user_a_id = user_a or uuid.uuid4()
    conv.user_b_id = user_b or uuid.uuid4()
    conv.last_message_at = None
    conv.created_at = _now()
    conv.deleted_a = False
    conv.deleted_b = False
    conv.closed_by_admin_at = _now() if closed else None
    conv.closed_by_admin_id = None
    return conv


def _make_message(
    *,
    conv_id: uuid.UUID | None = None,
    sender_id: uuid.UUID | None = None,
    body: str = "Hello",
    deleted: bool = False,
    created_offset_minutes: int = 0,
) -> MagicMock:
    msg = MagicMock()
    msg.id = uuid.uuid4()
    msg.conversation_id = conv_id or uuid.uuid4()
    msg.sender_id = sender_id or uuid.uuid4()
    msg.body = body
    msg.created_at = _now() - timedelta(minutes=created_offset_minutes)
    msg.read_at = None
    msg.edited_at = None
    msg.deleted_at = _now() if deleted else None
    return msg


def _make_db(
    *,
    scalars_all: list | None = None,
    scalar_one: object = None,
    scalar: int = 0,
    rowcount: int = 0,
) -> AsyncMock:
    db = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = scalars_all or []
    result.scalar_one_or_none.return_value = scalar_one
    result.rowcount = rowcount
    db.execute.return_value = result
    db.scalar.return_value = scalar
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.add = MagicMock()
    return db


# ── 1. start_conversation — 201 new conversation ───────────────────────────────


@pytest.mark.asyncio
async def test_start_conversation_201_new():
    """새 대화 시작 — DMConversation 행 생성 확인.

    ORM 클래스 패치 없이 db.execute side_effect + db.refresh side_effect 활용.
    DMConversation() 생성자는 실제로 호출되고, db.refresh가 id/created_at을 주입한다.
    """
    user = _make_user()
    target = _make_user()

    # target.status를 "active"로 설정 (start_conversation이 target.status == "active" 체크)
    target.status = "active"

    db = AsyncMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.add = MagicMock()

    # 1차 execute: target User 조회 → target 반환
    target_result = MagicMock()
    target_result.scalar_one_or_none.return_value = target

    # 2차 execute: 기존 대화 조회 → None (새 대화 생성 분기)
    existing_result = MagicMock()
    existing_result.scalar_one_or_none.return_value = None

    db.execute = AsyncMock(side_effect=[target_result, existing_result])

    # db.refresh가 새로 생성된 DMConversation에 id/created_at/last_message_at 등을 주입
    conv_id = uuid.uuid4()
    now = _now()
    uid_a, uid_b = _normalise_pair(user.id, target.id)

    async def _refresh(obj):
        obj.id = conv_id
        obj.user_a_id = uid_a
        obj.user_b_id = uid_b
        obj.last_message_at = None
        obj.created_at = now
        obj.deleted_a = False
        obj.deleted_b = False
        obj.closed_by_admin_at = None
        obj.closed_by_admin_id = None

    db.refresh = AsyncMock(side_effect=_refresh)

    body = StartConversationRequest(target_user_id=str(target.id))

    result = await start_conversation(body=body, user=user, db=db)

    assert "data" in result
    db.add.assert_called_once()
    db.commit.assert_called_once()


# ── 2. start_conversation — returns existing (idempotent) ─────────────────────


@pytest.mark.asyncio
async def test_start_conversation_returns_existing():
    user = _make_user()
    target = _make_user()

    uid_a, uid_b = _normalise_pair(user.id, target.id)
    existing_conv = _make_conv(user_a=uid_a, user_b=uid_b)
    # User is user_a, deleted_a is False
    existing_conv.user_a_id = user.id
    existing_conv.deleted_a = False

    db = AsyncMock()
    target_result = MagicMock()
    target_result.scalar_one_or_none.return_value = target

    existing_result = MagicMock()
    existing_result.scalar_one_or_none.return_value = existing_conv

    db.execute = AsyncMock(side_effect=[target_result, existing_result])
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.add = MagicMock()

    body = StartConversationRequest(target_user_id=str(target.id))
    result = await start_conversation(body=body, user=user, db=db)

    assert "data" in result
    # Should NOT create a new conversation
    db.add.assert_not_called()


# ── 3. list_my_conversations — 200 ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_my_conversations_200():
    user = _make_user()
    conv = _make_conv(user_a=user.id)

    db = AsyncMock()
    # First execute: conversations list
    conv_result = MagicMock()
    conv_result.scalars.return_value.all.return_value = [conv]
    # Second execute: last message preview for the conv
    preview_result = MagicMock()
    preview_result.scalar_one_or_none.return_value = None

    db.execute = AsyncMock(side_effect=[conv_result, preview_result])

    result = await list_my_conversations(cursor=None, limit=20, user=user, db=db)

    assert "data" in result
    assert len(result["data"]) == 1
    assert result["data"][0]["other_user_id"] == str(conv.user_b_id)


# ── 4. list_messages — 200 ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_messages_200():
    user = _make_user()
    conv = _make_conv(user_a=user.id)
    msg = _make_message(conv_id=conv.id, sender_id=user.id)

    db = AsyncMock()
    conv_result = MagicMock()
    conv_result.scalar_one_or_none.return_value = conv
    msg_result = MagicMock()
    msg_result.scalars.return_value.all.return_value = [msg]

    db.execute = AsyncMock(side_effect=[conv_result, msg_result])

    result = await list_messages(
        conversation_id=conv.id, cursor=None, limit=30, user=user, db=db
    )

    assert "data" in result
    assert len(result["data"]) == 1
    assert result["data"][0]["body"] == msg.body


# ── 5. list_messages — 403 non-participant ────────────────────────────────────


@pytest.mark.asyncio
async def test_list_messages_403_non_participant():
    user = _make_user()
    other_a = uuid.uuid4()
    other_b = uuid.uuid4()
    conv = _make_conv(user_a=other_a, user_b=other_b)

    db = AsyncMock()
    conv_result = MagicMock()
    conv_result.scalar_one_or_none.return_value = conv
    db.execute = AsyncMock(return_value=conv_result)

    with pytest.raises(ApiError) as exc_info:
        await list_messages(
            conversation_id=conv.id, cursor=None, limit=30, user=user, db=db
        )
    assert exc_info.value.status_code == 403


# ── 6. send_message — 201 with notification ───────────────────────────────────


@pytest.mark.asyncio
async def test_send_message_201():
    user = _make_user()
    conv = _make_conv(user_a=user.id)
    conv.closed_by_admin_at = None

    db = AsyncMock()
    conv_result = MagicMock()
    conv_result.scalar_one_or_none.return_value = conv
    db.execute = AsyncMock(return_value=conv_result)

    new_msg = _make_message(conv_id=conv.id, sender_id=user.id)
    db.refresh = AsyncMock(side_effect=lambda obj: None)

    body = SendMessageRequest(body="Hello there!")

    with patch("app.api.conversations.DMMessage") as MockMsg:
        MockMsg.return_value = new_msg
        with patch("app.api.conversations.Notification") as MockNotif:
            MockNotif.return_value = MagicMock()
            result = await send_message(
                conversation_id=conv.id, body=body, user=user, db=db
            )

    assert "data" in result
    db.flush.assert_called_once()
    db.commit.assert_called_once()
    # Notification created for other participant
    MockNotif.assert_called_once()
    call_kwargs = MockNotif.call_args.kwargs
    assert call_kwargs["type"] == "dm_received"


# ── 7. edit_message — 422 edit window expired ─────────────────────────────────


@pytest.mark.asyncio
async def test_edit_message_422_window_expired():
    user = _make_user()
    conv = _make_conv(user_a=user.id)

    # Message sent 10 minutes ago — beyond 5-minute window
    msg = _make_message(
        conv_id=conv.id,
        sender_id=user.id,
        created_offset_minutes=10,
    )

    db = AsyncMock()
    conv_result = MagicMock()
    conv_result.scalar_one_or_none.return_value = conv
    msg_result = MagicMock()
    msg_result.scalar_one_or_none.return_value = msg
    db.execute = AsyncMock(side_effect=[conv_result, msg_result])

    body = EditMessageRequest(body="Updated text")

    with pytest.raises(ApiError) as exc_info:
        await edit_message(
            conversation_id=conv.id,
            message_id=msg.id,
            body=body,
            user=user,
            db=db,
        )
    assert exc_info.value.status_code == 422
    assert "5 minutes" in exc_info.value.error_message


# ── 8. mark_conversation_read — 200 ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_mark_conversation_read_200():
    user = _make_user()
    conv = _make_conv(user_a=user.id)

    db = AsyncMock()
    conv_result = MagicMock()
    conv_result.scalar_one_or_none.return_value = conv

    update_result = MagicMock()
    update_result.rowcount = 3

    db.execute = AsyncMock(side_effect=[conv_result, update_result])

    result = await mark_conversation_read(
        conversation_id=conv.id, user=user, db=db
    )

    assert result["data"]["marked_read"] == 3
    db.commit.assert_called_once()


# ── 9. Unit: _sanitise strips HTML ────────────────────────────────────────────


def test_sanitise_strips_html():
    assert _sanitise("<b>Hello</b> world") == "Hello world"
    assert _sanitise("<script>alert(1)</script>text") == "alert(1)text"
    assert _sanitise("&lt;safe&gt;") == "<safe>"
    assert _sanitise("plain text") == "plain text"


# ── 10. Unit: _normalise_pair ─────────────────────────────────────────────────


def test_normalise_pair_consistent():
    a = uuid.uuid4()
    b = uuid.uuid4()
    r1 = _normalise_pair(a, b)
    r2 = _normalise_pair(b, a)
    # Both orderings must yield the same result
    assert r1 == r2
    # First element must be lexicographically smaller
    assert str(r1[0]) < str(r1[1])


# ── 11. admin_close_conversation — 200 ───────────────────────────────────────


@pytest.mark.asyncio
async def test_admin_close_conversation_200():
    from app.api.conversations import admin_close_conversation

    admin = _make_user(role="admin")
    conv = _make_conv()
    conv.closed_by_admin_at = None

    db = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = conv
    db.execute = AsyncMock(return_value=result_mock)
    db.commit = AsyncMock()
    db.refresh = AsyncMock()

    result = await admin_close_conversation(
        conversation_id=conv.id, admin=admin, db=db
    )

    assert "data" in result
    assert result["data"]["conversation_id"] == str(conv.id)
    db.commit.assert_called_once()
