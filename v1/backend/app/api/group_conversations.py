"""Group DM API — Phase 9 L-C (L-5 Group DM + L-7 File Attachment presign).

엔드포인트:
  POST   /me/messages/conversations/group          — 그룹 대화방 생성
  GET    /me/messages/conversations/group          — 내 그룹 대화방 목록
  GET    /me/messages/group/{conv_id}/messages     — 그룹 메시지 목록
  POST   /me/messages/group/{conv_id}/messages     — 그룹 메시지 전송 (→ WS broadcast)
  POST   /me/messages/conversations/{conv_id}/participants        — 참여자 추가 (admin)
  DELETE /me/messages/conversations/{conv_id}/participants/{user_id} — 참여자 제거 (admin)
  PATCH  /me/messages/conversations/{conv_id}      — 그룹명 수정 (admin)
  POST   /me/messages/{conv_id}/attachment/presign — 1:1 DM 첨부 presign
  POST   /me/messages/group/{conv_id}/attachment/presign — 그룹 DM 첨부 presign

비즈니스 규칙:
  - 그룹 생성 시 creator는 자동으로 role='admin'
  - 참여자 추가/제거는 role='admin'인 사용자만 가능 (403 otherwise)
  - 참여자 제거 시 left_at 소프트 삭제 (메시지 히스토리 보존)
  - 메시지 속도 제한: 5 msg/min/user/group (group_msg_send rate limit key)
  - 최대 참여자 50인 초과 시 422
  - 그룹 종료(creator/admin): closed_at 설정 (소프트)
  - 첨부파일: image 5종 + PDF, 최대 10MB
"""
from __future__ import annotations

import html
import re
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.errors import ApiError
from app.core.rate_limit import rate_limit
from app.db.session import get_db
from app.models.group_dm import GroupConversation, GroupMessage, GroupParticipant
from app.models.notification import Notification
from app.models.user import User
from app.services.storage.factory import get_storage_provider
from app.services.websocket_manager import get_ws_manager

router = APIRouter(tags=["group-conversations"])

# ── 상수 ───────────────────────────────────────────────────────────────────────

_DELETED_SENTINEL = "[deleted]"
_MAX_BODY_LEN = 2000
_MAX_PARTICIPANTS = 50

# 허용 첨부파일 MIME 목록
ALLOWED_ATTACHMENT_MIME: frozenset[str] = frozenset({
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
    "application/pdf",
})
ATTACHMENT_MAX_BYTES = 10 * 1024 * 1024  # 10 MB


# ── 유틸 ───────────────────────────────────────────────────────────────────────


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _sanitise(text: str) -> str:
    """HTML 태그 제거 및 엔티티 디코딩."""
    no_tags = re.sub(r"<[^>]+>", "", text)
    return html.unescape(no_tags)


# ── 직렬화 ─────────────────────────────────────────────────────────────────────


def _ser_group(conv: GroupConversation) -> dict:
    return {
        "id": str(conv.id),
        "kind": "group",
        "name": conv.name,
        "creator_id": str(conv.creator_id) if conv.creator_id else None,
        "last_message_at": conv.last_message_at.isoformat() if conv.last_message_at else None,
        "created_at": conv.created_at.isoformat(),
        "closed": conv.closed_at is not None,
        "max_participants": conv.max_participants,
    }


def _ser_participant(p: GroupParticipant) -> dict:
    return {
        "user_id": str(p.user_id),
        "role": p.role,
        "joined_at": p.joined_at.isoformat(),
        "left_at": p.left_at.isoformat() if p.left_at else None,
    }


def _ser_group_msg(msg: GroupMessage) -> dict:
    body = _DELETED_SENTINEL if msg.deleted_at else msg.body
    return {
        "id": str(msg.id),
        "conversation_id": str(msg.conversation_id),
        "sender_id": str(msg.sender_id),
        "body": body,
        "attachment_url": msg.attachment_url,
        "attachment_type": msg.attachment_type,
        "attachment_size_bytes": msg.attachment_size_bytes,
        "created_at": msg.created_at.isoformat(),
        "edited_at": msg.edited_at.isoformat() if msg.edited_at else None,
        "deleted_at": msg.deleted_at.isoformat() if msg.deleted_at else None,
    }


# ── 헬퍼: 참여자 검증 ──────────────────────────────────────────────────────────


async def _assert_active_participant(
    conv_id: uuid.UUID, user: User, db: AsyncSession
) -> GroupParticipant:
    """현재 참여 중인 참여자인지 확인. 아니면 403."""
    result = await db.execute(
        select(GroupParticipant).where(
            and_(
                GroupParticipant.conversation_id == conv_id,
                GroupParticipant.user_id == user.id,
                GroupParticipant.left_at.is_(None),
            )
        )
    )
    p = result.scalar_one_or_none()
    if not p:
        raise ApiError("FORBIDDEN", "Not a participant", http_status=403)
    return p


async def _get_conv(conv_id: uuid.UUID, db: AsyncSession) -> GroupConversation:
    result = await db.execute(
        select(GroupConversation).where(GroupConversation.id == conv_id)
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise ApiError("NOT_FOUND", "Group conversation not found", http_status=404)
    return conv


# ── Request 스키마 ─────────────────────────────────────────────────────────────


class CreateGroupRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="그룹 이름")
    participant_user_ids: list[str] = Field(
        ...,
        min_length=2,
        description="초대할 사용자 UUID 목록 (2명 이상, creator 제외)",
    )


class SendGroupMessageRequest(BaseModel):
    body: str = Field(..., min_length=1, max_length=_MAX_BODY_LEN)
    attachment_url: str | None = Field(None, max_length=2048)
    attachment_type: str | None = Field(None, pattern="^(image|file)$")
    attachment_size_bytes: int | None = Field(None, ge=0)


class AddParticipantRequest(BaseModel):
    user_id: str = Field(..., description="추가할 사용자 UUID")


class RenameGroupRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)


class AttachmentPresignRequest(BaseModel):
    filename: str = Field(..., min_length=1, max_length=255)
    content_type: str = Field(..., description="MIME type")
    size_bytes: int = Field(..., gt=0)


# ── POST /me/messages/conversations/group ─────────────────────────────────────


@router.post("/me/messages/conversations/group", status_code=201)
async def create_group_conversation(
    body: CreateGroupRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """그룹 대화방 생성.

    - creator는 자동으로 role='admin'으로 참여
    - participant_user_ids: 2명 이상 (creator 포함 최소 3인)
    - 최대 참여자: creator + participants ≤ 50인
    """
    # 참여자 UUID 파싱
    try:
        participant_ids = [uuid.UUID(uid) for uid in body.participant_user_ids]
    except ValueError:
        raise ApiError("INVALID_INPUT", "Invalid participant user_id UUID", http_status=422)

    # 자기 자신 포함 여부 제거
    participant_ids = [pid for pid in participant_ids if pid != user.id]

    if len(participant_ids) < 2:
        raise ApiError(
            "INVALID_INPUT",
            "최소 2명의 다른 사용자를 participant_user_ids에 포함해야 합니다 (creator 포함 최소 3인)",
            http_status=422,
        )

    total = len(participant_ids) + 1  # +1 = creator
    if total > _MAX_PARTICIPANTS:
        raise ApiError(
            "INVALID_INPUT",
            f"최대 {_MAX_PARTICIPANTS}인까지 참여할 수 있습니다",
            http_status=422,
        )

    # 참여자 존재 확인
    result = await db.execute(
        select(User).where(
            and_(User.id.in_(participant_ids), User.status == "active")
        )
    )
    found_users = result.scalars().all()
    if len(found_users) != len(participant_ids):
        raise ApiError("NOT_FOUND", "One or more participant users not found", http_status=404)

    now = _now()

    # 그룹 생성
    conv = GroupConversation(
        id=uuid.uuid4(),
        name=_sanitise(body.name),
        creator_id=user.id,
        created_at=now,
        max_participants=_MAX_PARTICIPANTS,
    )
    db.add(conv)
    await db.flush()  # conv.id 확보

    # creator를 admin으로 등록
    creator_part = GroupParticipant(
        id=uuid.uuid4(),
        conversation_id=conv.id,
        user_id=user.id,
        role="admin",
        joined_at=now,
    )
    db.add(creator_part)

    # 나머지 참여자 등록 (role='member')
    for pid in participant_ids:
        p = GroupParticipant(
            id=uuid.uuid4(),
            conversation_id=conv.id,
            user_id=pid,
            role="member",
            joined_at=now,
        )
        db.add(p)

    await db.commit()
    await db.refresh(conv)

    return {"data": _ser_group(conv)}


# ── GET /me/messages/conversations/group ──────────────────────────────────────


@router.get("/me/messages/conversations/group")
async def list_group_conversations(
    cursor: str | None = Query(None, description="ISO datetime cursor for pagination"),
    limit: int = Query(20, ge=1, le=50),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """내가 참여 중인 그룹 대화방 목록 (last_message_at 내림차순)."""
    # 현재 참여 중인 conversation_id 목록
    part_q = select(GroupParticipant.conversation_id).where(
        and_(
            GroupParticipant.user_id == user.id,
            GroupParticipant.left_at.is_(None),
        )
    )

    q = (
        select(GroupConversation)
        .where(GroupConversation.id.in_(part_q))
        .order_by(
            GroupConversation.last_message_at.desc().nulls_last(),
            GroupConversation.created_at.desc(),
        )
    )

    if cursor:
        try:
            dt = datetime.fromisoformat(cursor)
        except ValueError:
            raise ApiError("INVALID_INPUT", "Invalid cursor datetime", http_status=422)
        q = q.where(
            or_(
                GroupConversation.last_message_at < dt,
                and_(
                    GroupConversation.last_message_at.is_(None),
                    GroupConversation.created_at < dt,
                ),
            )
        )

    q = q.limit(limit + 1)
    result = await db.execute(q)
    convs = list(result.scalars().all())

    has_more = len(convs) > limit
    convs = convs[:limit]

    next_cursor = None
    if has_more and convs:
        last = convs[-1]
        next_cursor = (last.last_message_at or last.created_at).isoformat()

    return {"data": [_ser_group(c) for c in convs], "next_cursor": next_cursor}


# ── GET /me/messages/group/{conv_id}/messages ─────────────────────────────────


@router.get("/me/messages/group/{conv_id}/messages")
async def list_group_messages(
    conv_id: uuid.UUID,
    cursor: str | None = Query(None, description="ISO datetime cursor for pagination"),
    limit: int = Query(30, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """그룹 메시지 목록 조회 (참여자 전용)."""
    await _assert_active_participant(conv_id, user, db)

    q = (
        select(GroupMessage)
        .where(GroupMessage.conversation_id == conv_id)
        .order_by(GroupMessage.created_at.desc())
    )
    if cursor:
        try:
            dt = datetime.fromisoformat(cursor)
        except ValueError:
            raise ApiError("INVALID_INPUT", "Invalid cursor datetime", http_status=422)
        q = q.where(GroupMessage.created_at < dt)

    q = q.limit(limit + 1)
    result = await db.execute(q)
    msgs = list(result.scalars().all())

    has_more = len(msgs) > limit
    msgs = msgs[:limit]

    next_cursor = None
    if has_more and msgs:
        next_cursor = msgs[-1].created_at.isoformat()

    return {"data": [_ser_group_msg(m) for m in msgs], "next_cursor": next_cursor}


# ── POST /me/messages/group/{conv_id}/messages ────────────────────────────────


@router.post(
    "/me/messages/group/{conv_id}/messages",
    status_code=201,
    dependencies=[rate_limit("group_msg_send")],
)
async def send_group_message(
    conv_id: uuid.UUID,
    body: SendGroupMessageRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """그룹 메시지 전송 (참여자 전용, 5 msg/min/user/group rate limit).

    전송 성공 시 WebSocket 브로드캐스트로 다른 참여자에게 실시간 알림.
    """
    await _assert_active_participant(conv_id, user, db)

    conv = await _get_conv(conv_id, db)
    if conv.closed_at is not None:
        raise ApiError("CONVERSATION_CLOSED", "이미 종료된 그룹입니다", http_status=403)

    clean_body = _sanitise(body.body)
    if not clean_body.strip():
        raise ApiError("INVALID_INPUT", "메시지 본문이 비어있습니다", http_status=422)

    now = _now()
    msg = GroupMessage(
        id=uuid.uuid4(),
        conversation_id=conv_id,
        sender_id=user.id,
        body=clean_body,
        attachment_url=body.attachment_url,
        attachment_type=body.attachment_type,
        attachment_size_bytes=body.attachment_size_bytes,
        created_at=now,
    )
    db.add(msg)

    # last_message_at 업데이트
    conv.last_message_at = now
    await db.flush()

    # 다른 활성 참여자에게 dm_received 알림 + WS 브로드캐스트
    part_result = await db.execute(
        select(GroupParticipant).where(
            and_(
                GroupParticipant.conversation_id == conv_id,
                GroupParticipant.user_id != user.id,
                GroupParticipant.left_at.is_(None),
            )
        )
    )
    other_participants = part_result.scalars().all()

    msg_payload = {
        "event": "new_message",
        "conversation_id": str(conv_id),
        "conversation_kind": "group",
        "message": {
            "id": str(msg.id),
            "sender_id": str(user.id),
            "body": clean_body,
            "attachment_url": body.attachment_url,
            "attachment_type": body.attachment_type,
            "created_at": now.isoformat(),
        },
    }

    manager = get_ws_manager()
    for p in other_participants:
        # 알림 생성
        notif = Notification(
            id=uuid.uuid4(),
            user_id=p.user_id,
            type="dm_received",
            title=None,
            body=clean_body[:100],
            link=f"/me/messages/group/{conv_id}",
        )
        db.add(notif)
        # WS 브로드캐스트 (비동기 — DB 커밋 후 처리)
        try:
            await manager.broadcast_to_user(str(p.user_id), msg_payload)
        except Exception:
            pass  # WS 실패해도 메시지 저장은 계속

    await db.commit()
    await db.refresh(msg)
    return {"data": _ser_group_msg(msg)}


# ── POST /me/messages/conversations/{conv_id}/participants ────────────────────


@router.post("/me/messages/conversations/{conv_id}/participants", status_code=201)
async def add_participant(
    conv_id: uuid.UUID,
    body: AddParticipantRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """참여자 추가 (admin role 전용)."""
    my_part = await _assert_active_participant(conv_id, user, db)
    if my_part.role != "admin":
        raise ApiError("FORBIDDEN", "관리자만 참여자를 추가할 수 있습니다", http_status=403)

    conv = await _get_conv(conv_id, db)
    if conv.closed_at is not None:
        raise ApiError("CONVERSATION_CLOSED", "종료된 그룹에 참여자를 추가할 수 없습니다", http_status=403)

    try:
        target_id = uuid.UUID(body.user_id)
    except ValueError:
        raise ApiError("INVALID_INPUT", "Invalid user_id UUID", http_status=422)

    # 대상 사용자 확인
    target_result = await db.execute(
        select(User).where(and_(User.id == target_id, User.status == "active"))
    )
    target = target_result.scalar_one_or_none()
    if not target:
        raise ApiError("NOT_FOUND", "User not found", http_status=404)

    # 현재 활성 참여자 수 확인
    count_result = await db.execute(
        select(GroupParticipant).where(
            and_(
                GroupParticipant.conversation_id == conv_id,
                GroupParticipant.left_at.is_(None),
            )
        )
    )
    active_count = len(count_result.scalars().all())
    if active_count >= conv.max_participants:
        raise ApiError(
            "INVALID_INPUT",
            f"최대 {conv.max_participants}인까지 참여할 수 있습니다",
            http_status=422,
        )

    # 기존 참여 이력 확인 (재참여 처리)
    existing_result = await db.execute(
        select(GroupParticipant).where(
            and_(
                GroupParticipant.conversation_id == conv_id,
                GroupParticipant.user_id == target_id,
            )
        )
    )
    existing = existing_result.scalar_one_or_none()

    now = _now()
    if existing:
        if existing.left_at is None:
            raise ApiError("CONFLICT", "이미 참여 중인 사용자입니다", http_status=409)
        # 재참여: left_at 초기화
        existing.left_at = None
        existing.joined_at = now
        p = existing
    else:
        p = GroupParticipant(
            id=uuid.uuid4(),
            conversation_id=conv_id,
            user_id=target_id,
            role="member",
            joined_at=now,
        )
        db.add(p)

    await db.commit()
    await db.refresh(p)
    return {"data": _ser_participant(p)}


# ── DELETE /me/messages/conversations/{conv_id}/participants/{target_user_id} ──


@router.delete("/me/messages/conversations/{conv_id}/participants/{target_user_id}")
async def remove_participant(
    conv_id: uuid.UUID,
    target_user_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """참여자 제거 (admin role 전용, 소프트 삭제)."""
    my_part = await _assert_active_participant(conv_id, user, db)
    if my_part.role != "admin":
        raise ApiError("FORBIDDEN", "관리자만 참여자를 제거할 수 있습니다", http_status=403)

    target_result = await db.execute(
        select(GroupParticipant).where(
            and_(
                GroupParticipant.conversation_id == conv_id,
                GroupParticipant.user_id == target_user_id,
                GroupParticipant.left_at.is_(None),
            )
        )
    )
    target_part = target_result.scalar_one_or_none()
    if not target_part:
        raise ApiError("NOT_FOUND", "Participant not found", http_status=404)

    target_part.left_at = _now()
    await db.commit()
    await db.refresh(target_part)
    return {"data": _ser_participant(target_part)}


# ── PATCH /me/messages/conversations/{conv_id} ────────────────────────────────


@router.patch("/me/messages/conversations/{conv_id}")
async def rename_group(
    conv_id: uuid.UUID,
    body: RenameGroupRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """그룹명 수정 (admin role 전용)."""
    my_part = await _assert_active_participant(conv_id, user, db)
    if my_part.role != "admin":
        raise ApiError("FORBIDDEN", "관리자만 그룹명을 변경할 수 있습니다", http_status=403)

    conv = await _get_conv(conv_id, db)
    conv.name = _sanitise(body.name)
    await db.commit()
    await db.refresh(conv)
    return {"data": _ser_group(conv)}


# ── POST /me/messages/{conv_id}/attachment/presign (1:1 DM) ──────────────────


@router.post("/me/messages/{conv_id}/attachment/presign")
async def presign_dm_attachment(
    conv_id: uuid.UUID,
    body: AttachmentPresignRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """1:1 DM 첨부파일 presigned URL 발급.

    허용 MIME: image/jpeg, image/png, image/gif, image/webp, application/pdf
    크기 제한: 10MB
    """
    # 1:1 대화 참여자 검증
    from app.models.dm import DMConversation

    result = await db.execute(
        select(DMConversation).where(
            and_(
                DMConversation.id == conv_id,
                or_(
                    DMConversation.user_a_id == user.id,
                    DMConversation.user_b_id == user.id,
                ),
            )
        )
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise ApiError("FORBIDDEN", "Not a participant or conversation not found", http_status=403)

    return await _generate_presign(conv_id, body, "dm-attachments")


# ── POST /me/messages/group/{conv_id}/attachment/presign (그룹 DM) ───────────


@router.post("/me/messages/group/{conv_id}/attachment/presign")
async def presign_group_dm_attachment(
    conv_id: uuid.UUID,
    body: AttachmentPresignRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """그룹 DM 첨부파일 presigned URL 발급.

    허용 MIME: image/jpeg, image/png, image/gif, image/webp, application/pdf
    크기 제한: 10MB
    """
    await _assert_active_participant(conv_id, user, db)
    return await _generate_presign(conv_id, body, "group-dm-attachments")


async def _generate_presign(
    conv_id: uuid.UUID,
    body: AttachmentPresignRequest,
    prefix: str,
) -> dict:
    """presigned URL 공통 발급 로직."""
    if body.content_type not in ALLOWED_ATTACHMENT_MIME:
        raise ApiError(
            "INVALID_MIME",
            f"허용되지 않는 파일 형식입니다. 허용: {', '.join(sorted(ALLOWED_ATTACHMENT_MIME))}",
            http_status=422,
        )
    if body.size_bytes > ATTACHMENT_MAX_BYTES:
        raise ApiError(
            "FILE_TOO_LARGE",
            f"파일 크기는 {ATTACHMENT_MAX_BYTES // 1024 // 1024}MB를 초과할 수 없습니다",
            http_status=422,
        )

    key = f"{prefix}/{conv_id}/{uuid.uuid4()}/{body.filename}"
    storage = get_storage_provider()

    presigned = await storage.presign_post(
        key=key,
        content_type=body.content_type,
        max_size_bytes=body.size_bytes,
        expires_in=900,  # 15분
    )

    return {
        "data": {
            "upload_url": presigned.url,
            "key": presigned.key,
            "expires_in": 900,
        }
    }
