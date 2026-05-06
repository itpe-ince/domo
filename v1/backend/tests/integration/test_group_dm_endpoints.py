"""Group DM 통합 테스트 — Phase 9 L-C.

AsyncMock DB + MagicMock objects 패턴 사용 (DB 불필요).
기존 test_dm_messaging.py 패턴을 따름.

테스트 케이스:
  1.  그룹 생성 정상 (creator + 2명) → 201
  2.  그룹 생성 실패 — participant 2명 미만 → 422
  3.  그룹 생성 실패 — participant 50명 초과 → 422
  4.  참여자 추가 (admin role) → 201
  5.  참여자 추가 실패 — non-admin → 403
  6.  참여자 제거 (admin role, left_at 설정 확인) → 200
  7.  그룹 메시지 전송 + 목록 조회
  8.  비참여자가 그룹 메시지 조회 시 403
  9.  그룹명 변경 (admin만 가능) → 200
  10. 그룹명 변경 non-admin → 403
  11. 종료된 그룹에 메시지 전송 → 403
  12. presign — 허용 MIME 정상 → 200
  13. presign — 금지 MIME → 422
  14. presign — 10MB 초과 → 422
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.api.group_conversations import (
    AddParticipantRequest,
    AttachmentPresignRequest,
    CreateGroupRequest,
    RenameGroupRequest,
    SendGroupMessageRequest,
    add_participant,
    create_group_conversation,
    list_group_messages,
    presign_group_dm_attachment,
    remove_participant,
    rename_group,
    send_group_message,
)
from app.core.errors import ApiError


# ── Helpers ────────────────────────────────────────────────────────────────────


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _make_user(*, role: str = "user") -> MagicMock:
    u = MagicMock()
    u.id = uuid.uuid4()
    u.role = role
    u.status = "active"
    return u


def _make_group_conv(*, creator_id: uuid.UUID | None = None, closed: bool = False) -> MagicMock:
    c = MagicMock()
    c.id = uuid.uuid4()
    c.name = "Test Group"
    c.creator_id = creator_id or uuid.uuid4()
    c.created_at = _now()
    c.last_message_at = None
    c.max_participants = 50
    c.closed_at = _now() if closed else None
    c.closed_by_id = None
    return c


def _make_participant(*, user_id: uuid.UUID, role: str = "member", left: bool = False) -> MagicMock:
    p = MagicMock()
    p.id = uuid.uuid4()
    p.conversation_id = uuid.uuid4()
    p.user_id = user_id
    p.role = role
    p.joined_at = _now()
    p.left_at = _now() if left else None
    return p


def _make_group_msg(*, conv_id: uuid.UUID, sender_id: uuid.UUID) -> MagicMock:
    m = MagicMock()
    m.id = uuid.uuid4()
    m.conversation_id = conv_id
    m.sender_id = sender_id
    m.body = "Hello group!"
    m.attachment_url = None
    m.attachment_type = None
    m.attachment_size_bytes = None
    m.created_at = _now()
    m.edited_at = None
    m.deleted_at = None
    return m


def _make_db(
    *,
    conv: MagicMock | None = None,
    participant: MagicMock | None = None,
    msg: MagicMock | None = None,
    users: list | None = None,
    participants_list: list | None = None,
) -> AsyncMock:
    """AsyncMock DB 세션 구성."""
    db = AsyncMock()

    def _make_result(obj):
        r = MagicMock()
        if isinstance(obj, list):
            r.scalars.return_value.all.return_value = obj
            r.scalar_one_or_none.return_value = obj[0] if obj else None
        else:
            r.scalar_one_or_none.return_value = obj
            r.scalars.return_value.all.return_value = [obj] if obj else []
        return r

    results = []
    # 순서: 첫 번째 execute → participant check, 두 번째 → conv, ...
    if participant is not None:
        results.append(_make_result(participant))
    if conv is not None:
        results.append(_make_result(conv))
    if users is not None:
        r = MagicMock()
        r.scalars.return_value.all.return_value = users
        results.append(r)
    if participants_list is not None:
        r = MagicMock()
        r.scalars.return_value.all.return_value = participants_list
        results.append(r)
    if msg is not None:
        results.append(_make_result(msg))

    # fallback — 모든 execute 호출에 대해 빈 결과 반환
    db.execute.side_effect = results if results else [MagicMock(scalar_one_or_none=lambda: None)]
    return db


# ── 테스트 1: 그룹 생성 정상 ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_group_success():
    """그룹 생성 정상 (creator + 2명) → 201."""
    creator = _make_user()
    target1, target2 = _make_user(), _make_user()
    conv = _make_group_conv(creator_id=creator.id)

    db = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()

    # 참여자 조회 결과
    user_result = MagicMock()
    user_result.scalars.return_value.all.return_value = [target1, target2]
    db.execute.return_value = user_result

    body = CreateGroupRequest(
        name="My Group",
        participant_user_ids=[str(target1.id), str(target2.id)],
    )

    with patch("app.api.group_conversations.GroupConversation", return_value=conv), \
         patch("app.api.group_conversations.GroupParticipant", return_value=MagicMock()):
        result = await create_group_conversation(body, creator, db)

    assert result["data"]["kind"] == "group"
    db.commit.assert_called_once()


# ── 테스트 2: 그룹 생성 실패 — 참여자 2명 미만 ───────────────────────────────


@pytest.mark.asyncio
async def test_create_group_too_few_participants():
    """participant_user_ids 2명 미만 → Pydantic ValidationError (FastAPI에서 422로 변환)."""
    from pydantic import ValidationError

    other = _make_user()

    # Pydantic validator가 min_length=2를 보장 — body 생성 시점에 ValidationError
    with pytest.raises(ValidationError):
        CreateGroupRequest(
            name="Group",
            participant_user_ids=[str(other.id)],  # 1명만
        )


# ── 테스트 3: 그룹 생성 실패 — 50명 초과 ─────────────────────────────────────


@pytest.mark.asyncio
async def test_create_group_too_many_participants():
    """참여자 50명 초과 → 422."""
    creator = _make_user()
    db = AsyncMock()
    # 50명 입력 (creator 포함 51인)
    many_ids = [str(uuid.uuid4()) for _ in range(50)]

    body = CreateGroupRequest(name="Big Group", participant_user_ids=many_ids)

    with pytest.raises(ApiError) as exc:
        await create_group_conversation(body, creator, db)

    assert exc.value.status_code == 422


# ── 테스트 4: 참여자 추가 (admin role) ────────────────────────────────────────


@pytest.mark.asyncio
async def test_add_participant_as_admin():
    """admin role → 참여자 추가 성공."""
    admin_user = _make_user()
    target_user = _make_user()
    conv = _make_group_conv()

    admin_part = _make_participant(user_id=admin_user.id, role="admin")
    target_part = _make_participant(user_id=target_user.id, role="member")

    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()

    # execute 순서: admin participant, conv, target user, 활성 참여자 수, 기존 이력
    call_results = [
        MagicMock(scalar_one_or_none=MagicMock(return_value=admin_part)),
        MagicMock(scalar_one_or_none=MagicMock(return_value=conv)),
        MagicMock(scalar_one_or_none=MagicMock(return_value=target_user)),
        MagicMock(**{"scalars.return_value.all.return_value": [admin_part]}),
        MagicMock(scalar_one_or_none=MagicMock(return_value=None)),  # 기존 이력 없음
    ]
    db.execute.side_effect = call_results

    db.refresh.side_effect = lambda p: None

    body = AddParticipantRequest(user_id=str(target_user.id))

    # ORM 클래스 패치 제거 — 실제 GroupParticipant() 생성자 호출됨 (select() 충돌 회피)
    result = await add_participant(conv.id, body, admin_user, db)

    db.commit.assert_called_once()
    db.add.assert_called_once()


# ── 테스트 5: 참여자 추가 실패 — non-admin ────────────────────────────────────


@pytest.mark.asyncio
async def test_add_participant_as_member_forbidden():
    """member role → 참여자 추가 시도 → 403."""
    member_user = _make_user()
    target_user = _make_user()

    member_part = _make_participant(user_id=member_user.id, role="member")

    db = AsyncMock()
    db.execute.side_effect = [
        MagicMock(scalar_one_or_none=MagicMock(return_value=member_part)),
    ]

    body = AddParticipantRequest(user_id=str(target_user.id))

    with pytest.raises(ApiError) as exc:
        await add_participant(uuid.uuid4(), body, member_user, db)

    assert exc.value.status_code == 403


# ── 테스트 6: 참여자 제거 (admin role, left_at 확인) ─────────────────────────


@pytest.mark.asyncio
async def test_remove_participant_sets_left_at():
    """admin role → 참여자 제거 → left_at 설정."""
    admin_user = _make_user()
    target_user = _make_user()

    admin_part = _make_participant(user_id=admin_user.id, role="admin")
    target_part = _make_participant(user_id=target_user.id, role="member")

    db = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.execute.side_effect = [
        MagicMock(scalar_one_or_none=MagicMock(return_value=admin_part)),
        MagicMock(scalar_one_or_none=MagicMock(return_value=target_part)),
    ]

    result = await remove_participant(
        uuid.uuid4(), target_user.id, admin_user, db
    )

    # left_at 설정 확인
    assert target_part.left_at is not None
    db.commit.assert_called_once()


# ── 테스트 7: 그룹 메시지 전송 + 목록 조회 ──────────────────────────────────


@pytest.mark.asyncio
async def test_send_group_message_success():
    """그룹 메시지 전송 성공 → 201."""
    sender = _make_user()
    conv = _make_group_conv(closed=False)
    sender_part = _make_participant(user_id=sender.id, role="member")
    msg = _make_group_msg(conv_id=conv.id, sender_id=sender.id)

    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.flush = AsyncMock()

    other_part_result = MagicMock()
    other_part_result.scalars.return_value.all.return_value = []

    db.execute.side_effect = [
        # _assert_active_participant
        MagicMock(scalar_one_or_none=MagicMock(return_value=sender_part)),
        # _get_conv
        MagicMock(scalar_one_or_none=MagicMock(return_value=conv)),
        # other participants
        other_part_result,
    ]

    body = SendGroupMessageRequest(body="Hello group!")

    with patch("app.api.group_conversations.GroupMessage", return_value=msg), \
         patch("app.api.group_conversations.Notification", return_value=MagicMock()), \
         patch("app.api.group_conversations.get_ws_manager") as mock_ws:
        mock_ws.return_value.broadcast_to_user = AsyncMock()
        result = await send_group_message(conv.id, body, sender, db)

    assert result["data"]["body"] == "Hello group!"
    db.commit.assert_called_once()


# ── 테스트 8: 비참여자 메시지 조회 → 403 ─────────────────────────────────────


@pytest.mark.asyncio
async def test_list_group_messages_non_participant_forbidden():
    """비참여자가 그룹 메시지 조회 → 403."""
    outsider = _make_user()
    db = AsyncMock()
    # _assert_active_participant → None (비참여자)
    db.execute.side_effect = [
        MagicMock(scalar_one_or_none=MagicMock(return_value=None)),
    ]

    with pytest.raises(ApiError) as exc:
        await list_group_messages(uuid.uuid4(), user=outsider, db=db)

    assert exc.value.status_code == 403


# ── 테스트 9: 그룹명 변경 (admin) ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_rename_group_as_admin():
    """admin role → 그룹명 변경 성공."""
    admin_user = _make_user()
    conv = _make_group_conv()
    admin_part = _make_participant(user_id=admin_user.id, role="admin")

    db = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.execute.side_effect = [
        MagicMock(scalar_one_or_none=MagicMock(return_value=admin_part)),
        MagicMock(scalar_one_or_none=MagicMock(return_value=conv)),
    ]

    body = RenameGroupRequest(name="New Name")
    result = await rename_group(conv.id, body, admin_user, db)

    assert conv.name == "New Name"
    db.commit.assert_called_once()


# ── 테스트 10: 그룹명 변경 non-admin → 403 ───────────────────────────────────


@pytest.mark.asyncio
async def test_rename_group_as_member_forbidden():
    """member role → 그룹명 변경 → 403."""
    member = _make_user()
    member_part = _make_participant(user_id=member.id, role="member")

    db = AsyncMock()
    db.execute.side_effect = [
        MagicMock(scalar_one_or_none=MagicMock(return_value=member_part)),
    ]

    body = RenameGroupRequest(name="Attempt")

    with pytest.raises(ApiError) as exc:
        await rename_group(uuid.uuid4(), body, member, db)

    assert exc.value.status_code == 403


# ── 테스트 11: 종료된 그룹에 메시지 전송 → 403 ───────────────────────────────


@pytest.mark.asyncio
async def test_send_message_to_closed_group():
    """closed_at 설정된 그룹에 메시지 → 403."""
    sender = _make_user()
    closed_conv = _make_group_conv(closed=True)
    sender_part = _make_participant(user_id=sender.id, role="member")

    db = AsyncMock()
    db.execute.side_effect = [
        MagicMock(scalar_one_or_none=MagicMock(return_value=sender_part)),
        MagicMock(scalar_one_or_none=MagicMock(return_value=closed_conv)),
    ]

    body = SendGroupMessageRequest(body="Hello?")

    with pytest.raises(ApiError) as exc:
        await send_group_message(closed_conv.id, body, sender, db)

    assert exc.value.status_code == 403


# ── 테스트 12: presign — 허용 MIME 정상 ──────────────────────────────────────


@pytest.mark.asyncio
async def test_presign_group_allowed_mime():
    """허용 MIME (image/jpeg) → presign URL 발급 성공."""
    user = _make_user()
    part = _make_participant(user_id=user.id, role="member")
    conv_id = uuid.uuid4()

    db = AsyncMock()
    db.execute.side_effect = [
        MagicMock(scalar_one_or_none=MagicMock(return_value=part)),
    ]

    mock_presigned = MagicMock()
    mock_presigned.url = "https://s3.example.com/presigned"
    mock_presigned.key = f"group-dm-attachments/{conv_id}/test.jpg"

    body = AttachmentPresignRequest(
        filename="photo.jpg",
        content_type="image/jpeg",
        size_bytes=1024 * 1024,  # 1MB
    )

    with patch("app.api.group_conversations.get_storage_provider") as mock_storage:
        mock_provider = MagicMock()
        mock_provider.presign_post = AsyncMock(return_value=mock_presigned)
        mock_storage.return_value = mock_provider

        result = await presign_group_dm_attachment(conv_id, body, user, db)

    assert "upload_url" in result["data"]
    assert result["data"]["expires_in"] == 900


# ── 테스트 13: presign — 금지 MIME → 422 ─────────────────────────────────────


@pytest.mark.asyncio
async def test_presign_forbidden_mime():
    """금지 MIME (video/mp4) → 422."""
    user = _make_user()
    part = _make_participant(user_id=user.id, role="member")
    conv_id = uuid.uuid4()

    db = AsyncMock()
    db.execute.side_effect = [
        MagicMock(scalar_one_or_none=MagicMock(return_value=part)),
    ]

    body = AttachmentPresignRequest(
        filename="video.mp4",
        content_type="video/mp4",
        size_bytes=1024 * 1024,
    )

    with pytest.raises(ApiError) as exc:
        await presign_group_dm_attachment(conv_id, body, user, db)

    assert exc.value.status_code == 422


# ── 테스트 14: presign — 10MB 초과 → 422 ─────────────────────────────────────


@pytest.mark.asyncio
async def test_presign_file_too_large():
    """10MB 초과 파일 → 422."""
    user = _make_user()
    part = _make_participant(user_id=user.id, role="member")
    conv_id = uuid.uuid4()

    db = AsyncMock()
    db.execute.side_effect = [
        MagicMock(scalar_one_or_none=MagicMock(return_value=part)),
    ]

    body = AttachmentPresignRequest(
        filename="large.pdf",
        content_type="application/pdf",
        size_bytes=11 * 1024 * 1024,  # 11MB (초과)
    )

    with pytest.raises(ApiError) as exc:
        await presign_group_dm_attachment(conv_id, body, user, db)

    assert exc.value.status_code == 422
