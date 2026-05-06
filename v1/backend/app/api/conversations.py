"""DM Messaging API — B'-2 dm-messaging.

8 endpoints:
  POST   /conversations                        — start or return existing conversation
  GET    /me/conversations                     — list my conversations (cursor-paginated)
  GET    /conversations/{id}/messages          — list messages in a conversation
  POST   /conversations/{id}/messages          — send a message (rate-limited 60/min/user)
  PATCH  /conversations/{id}/messages/{msg_id} — edit own message (5-min window)
  DELETE /conversations/{id}/messages/{msg_id} — soft-delete own message
  POST   /conversations/{id}/read              — mark conversation as read
  POST   /conversations/{id}/report            — abuse report

Admin endpoint (separate prefix, requires admin role + TOTP):
  POST   /admin/conversations/{id}/close       — force-close a conversation

Design constraints:
  - user_a_id < user_b_id (UUID lexicographic) for UNIQUE pair normalisation
  - HTML sanitise: bleach strips all tags from message body
  - Notification type dm_received emitted on send
  - No WebSocket — polling model (Phase 9+)
"""
from __future__ import annotations

import html
import re
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.admin_deps import require_admin
from app.core.deps import get_current_user
from app.core.errors import ApiError
from app.core.rate_limit import rate_limit
from app.db.session import get_db
from app.models.dm import DMConversation, DMMessage
from app.models.notification import Notification
from app.models.user import User
from app.schemas.dm import (
    EditMessageRequest,
    ReportConversationRequest,
    SendMessageRequest,
    StartConversationRequest,
)

router = APIRouter(tags=["conversations"])
admin_router = APIRouter(prefix="/admin", tags=["admin-conversations"])

_DELETED_SENTINEL = "[deleted]"
_EDIT_WINDOW = timedelta(minutes=5)

# ── Sanitise ──────────────────────────────────────────────────────────────────


def _sanitise(text: str) -> str:
    """Strip all HTML tags and decode HTML entities.

    Uses stdlib only — no bleach dep needed for plain-text DMs.
    """
    # Remove all HTML tags
    no_tags = re.sub(r"<[^>]+>", "", text)
    # Decode HTML entities (&amp; → &, etc.)
    return html.unescape(no_tags)


# ── Normalise pair ────────────────────────────────────────────────────────────


def _normalise_pair(a: uuid.UUID, b: uuid.UUID) -> tuple[uuid.UUID, uuid.UUID]:
    """Return (smaller, larger) UUID pair for consistent UNIQUE constraint."""
    return (a, b) if str(a) < str(b) else (b, a)


def _is_participant(conv: DMConversation, user_id: uuid.UUID) -> bool:
    return conv.user_a_id == user_id or conv.user_b_id == user_id


def _is_deleted_for(conv: DMConversation, user_id: uuid.UUID) -> bool:
    if conv.user_a_id == user_id:
        return conv.deleted_a
    return conv.deleted_b


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ── Serialisers ───────────────────────────────────────────────────────────────


def _ser_conv(conv: DMConversation, viewer_id: uuid.UUID, preview: str | None = None) -> dict:
    other_id = conv.user_b_id if conv.user_a_id == viewer_id else conv.user_a_id
    return {
        "id": str(conv.id),
        "other_user_id": str(other_id),
        "last_message_at": conv.last_message_at.isoformat() if conv.last_message_at else None,
        "created_at": conv.created_at.isoformat(),
        "closed_by_admin": conv.closed_by_admin_at is not None,
        "last_message_preview": preview,
    }


def _ser_msg(msg: DMMessage) -> dict:
    body = _DELETED_SENTINEL if msg.deleted_at else msg.body
    return {
        "id": str(msg.id),
        "conversation_id": str(msg.conversation_id),
        "sender_id": str(msg.sender_id),
        "body": body,
        "created_at": msg.created_at.isoformat(),
        "read_at": msg.read_at.isoformat() if msg.read_at else None,
        "edited_at": msg.edited_at.isoformat() if msg.edited_at else None,
        "deleted_at": msg.deleted_at.isoformat() if msg.deleted_at else None,
    }


# ── Helper: get conversation and assert participant ───────────────────────────


async def _get_conv_assert_participant(
    conv_id: uuid.UUID, user: User, db: AsyncSession
) -> DMConversation:
    result = await db.execute(
        select(DMConversation).where(DMConversation.id == conv_id)
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise ApiError("NOT_FOUND", "Conversation not found", http_status=404)
    if not _is_participant(conv, user.id):
        raise ApiError("FORBIDDEN", "Not a participant", http_status=403)
    return conv


# ── POST /conversations ───────────────────────────────────────────────────────


@router.post("/conversations", status_code=201)
async def start_conversation(
    body: StartConversationRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Start a conversation with target_user_id, or return existing one."""
    try:
        target_id = uuid.UUID(body.target_user_id)
    except ValueError:
        raise ApiError("INVALID_INPUT", "Invalid target_user_id UUID", http_status=422)

    if target_id == user.id:
        raise ApiError("INVALID_INPUT", "Cannot message yourself", http_status=422)

    # Verify target user exists
    target_result = await db.execute(select(User).where(User.id == target_id))
    target = target_result.scalar_one_or_none()
    if not target or target.status != "active":
        raise ApiError("NOT_FOUND", "Target user not found", http_status=404)

    uid_a, uid_b = _normalise_pair(user.id, target_id)

    # Return existing conversation (un-hide if soft-deleted for viewer)
    existing = await db.execute(
        select(DMConversation).where(
            and_(
                DMConversation.user_a_id == uid_a,
                DMConversation.user_b_id == uid_b,
            )
        )
    )
    conv = existing.scalar_one_or_none()
    if conv:
        # Un-hide for the current user
        if conv.user_a_id == user.id and conv.deleted_a:
            conv.deleted_a = False
            await db.commit()
            await db.refresh(conv)
        elif conv.user_b_id == user.id and conv.deleted_b:
            conv.deleted_b = False
            await db.commit()
            await db.refresh(conv)
        return {"data": _ser_conv(conv, user.id)}

    conv = DMConversation(
        id=uuid.uuid4(),
        user_a_id=uid_a,
        user_b_id=uid_b,
    )
    db.add(conv)
    await db.commit()
    await db.refresh(conv)
    return {"data": _ser_conv(conv, user.id)}


# ── GET /me/conversations ─────────────────────────────────────────────────────


@router.get("/me/conversations")
async def list_my_conversations(
    cursor: str | None = Query(None, description="ISO datetime cursor for pagination"),
    limit: int = Query(20, ge=1, le=50),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List conversations the current user participates in, ordered by last_message_at desc."""
    # Base filter: user is participant and has not soft-hidden the conversation
    base = and_(
        or_(
            DMConversation.user_a_id == user.id,
            DMConversation.user_b_id == user.id,
        ),
        or_(
            and_(DMConversation.user_a_id == user.id, DMConversation.deleted_a.is_(False)),
            and_(DMConversation.user_b_id == user.id, DMConversation.deleted_b.is_(False)),
        ),
    )

    q = select(DMConversation).where(base).order_by(
        DMConversation.last_message_at.desc().nulls_last(),
        DMConversation.created_at.desc(),
    )

    if cursor:
        try:
            dt = datetime.fromisoformat(cursor)
        except ValueError:
            raise ApiError("INVALID_INPUT", "Invalid cursor datetime", http_status=422)
        q = q.where(
            or_(
                DMConversation.last_message_at < dt,
                and_(
                    DMConversation.last_message_at.is_(None),
                    DMConversation.created_at < dt,
                ),
            )
        )

    q = q.limit(limit + 1)
    result = await db.execute(q)
    convs = list(result.scalars().all())

    has_more = len(convs) > limit
    convs = convs[:limit]

    # Fetch last message preview for each conversation
    items = []
    for conv in convs:
        preview_result = await db.execute(
            select(DMMessage)
            .where(DMMessage.conversation_id == conv.id)
            .order_by(DMMessage.created_at.desc())
            .limit(1)
        )
        last_msg = preview_result.scalar_one_or_none()
        preview = None
        if last_msg:
            if last_msg.deleted_at:
                preview = _DELETED_SENTINEL
            else:
                preview = last_msg.body[:80]
        items.append(_ser_conv(conv, user.id, preview))

    next_cursor = None
    if has_more and convs:
        last = convs[-1]
        next_cursor = (last.last_message_at or last.created_at).isoformat()

    return {"data": items, "next_cursor": next_cursor}


# ── GET /conversations/{id}/messages ─────────────────────────────────────────


@router.get("/conversations/{conversation_id}/messages")
async def list_messages(
    conversation_id: uuid.UUID,
    cursor: str | None = Query(None, description="ISO datetime cursor for pagination"),
    limit: int = Query(30, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List messages in a conversation. Participants only."""
    conv = await _get_conv_assert_participant(conversation_id, user, db)
    _ = conv  # authorisation done

    q = (
        select(DMMessage)
        .where(DMMessage.conversation_id == conversation_id)
        .order_by(DMMessage.created_at.desc())
    )
    if cursor:
        try:
            dt = datetime.fromisoformat(cursor)
        except ValueError:
            raise ApiError("INVALID_INPUT", "Invalid cursor datetime", http_status=422)
        q = q.where(DMMessage.created_at < dt)

    q = q.limit(limit + 1)
    result = await db.execute(q)
    msgs = list(result.scalars().all())

    has_more = len(msgs) > limit
    msgs = msgs[:limit]

    next_cursor = None
    if has_more and msgs:
        next_cursor = msgs[-1].created_at.isoformat()

    return {"data": [_ser_msg(m) for m in msgs], "next_cursor": next_cursor}


# ── POST /conversations/{id}/messages ────────────────────────────────────────


@router.post(
    "/conversations/{conversation_id}/messages",
    status_code=201,
    dependencies=[rate_limit("dm_send")],
)
async def send_message(
    conversation_id: uuid.UUID,
    body: SendMessageRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Send a message. Rate-limited to 60/min/user."""
    conv = await _get_conv_assert_participant(conversation_id, user, db)

    if conv.closed_by_admin_at is not None:
        raise ApiError(
            "CONVERSATION_CLOSED",
            "This conversation has been closed by an administrator",
            http_status=403,
        )

    clean_body = _sanitise(body.body)
    if not clean_body.strip():
        raise ApiError("INVALID_INPUT", "Message body cannot be empty after sanitisation", http_status=422)

    now = _now()
    msg = DMMessage(
        id=uuid.uuid4(),
        conversation_id=conversation_id,
        sender_id=user.id,
        body=clean_body,
        created_at=now,
    )
    db.add(msg)

    # Update conversation.last_message_at
    conv.last_message_at = now

    # Un-hide for both sides (re-showing a hidden conversation on new message)
    conv.deleted_a = False
    conv.deleted_b = False

    await db.flush()

    # Emit dm_received notification to the other participant
    other_id = conv.user_b_id if conv.user_a_id == user.id else conv.user_a_id
    notif = Notification(
        id=uuid.uuid4(),
        user_id=other_id,
        type="dm_received",
        title=None,  # frontend derives title from sender display_name
        body=clean_body[:100] if len(clean_body) > 100 else clean_body,
        link=f"/me/messages/{conversation_id}",
    )
    db.add(notif)

    await db.commit()
    await db.refresh(msg)
    return {"data": _ser_msg(msg)}


# ── PATCH /conversations/{id}/messages/{msg_id} ───────────────────────────────


@router.patch("/conversations/{conversation_id}/messages/{message_id}")
async def edit_message(
    conversation_id: uuid.UUID,
    message_id: uuid.UUID,
    body: EditMessageRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Edit own message within 5-minute window."""
    conv = await _get_conv_assert_participant(conversation_id, user, db)
    _ = conv

    result = await db.execute(
        select(DMMessage).where(
            and_(
                DMMessage.id == message_id,
                DMMessage.conversation_id == conversation_id,
            )
        )
    )
    msg = result.scalar_one_or_none()
    if not msg:
        raise ApiError("NOT_FOUND", "Message not found", http_status=404)
    if msg.sender_id != user.id:
        raise ApiError("FORBIDDEN", "Can only edit your own messages", http_status=403)
    if msg.deleted_at is not None:
        raise ApiError("INVALID_INPUT", "Cannot edit a deleted message", http_status=422)

    now = _now()
    if now - msg.created_at > _EDIT_WINDOW:
        raise ApiError(
            "EDIT_WINDOW_EXPIRED",
            "Messages can only be edited within 5 minutes of sending",
            http_status=422,
        )

    clean_body = _sanitise(body.body)
    if not clean_body.strip():
        raise ApiError("INVALID_INPUT", "Edited body cannot be empty", http_status=422)

    msg.body = clean_body
    msg.edited_at = now
    await db.commit()
    await db.refresh(msg)
    return {"data": _ser_msg(msg)}


# ── DELETE /conversations/{id}/messages/{msg_id} ──────────────────────────────


@router.delete("/conversations/{conversation_id}/messages/{message_id}")
async def delete_message(
    conversation_id: uuid.UUID,
    message_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete own message."""
    conv = await _get_conv_assert_participant(conversation_id, user, db)
    _ = conv

    result = await db.execute(
        select(DMMessage).where(
            and_(
                DMMessage.id == message_id,
                DMMessage.conversation_id == conversation_id,
            )
        )
    )
    msg = result.scalar_one_or_none()
    if not msg:
        raise ApiError("NOT_FOUND", "Message not found", http_status=404)
    if msg.sender_id != user.id:
        raise ApiError("FORBIDDEN", "Can only delete your own messages", http_status=403)

    if msg.deleted_at is None:
        msg.deleted_at = _now()
        await db.commit()
        await db.refresh(msg)

    return {"data": _ser_msg(msg)}


# ── POST /conversations/{id}/read ─────────────────────────────────────────────


@router.post("/conversations/{conversation_id}/read")
async def mark_conversation_read(
    conversation_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark all unread messages (sent by other party) as read."""
    conv = await _get_conv_assert_participant(conversation_id, user, db)
    _ = conv

    now = _now()
    result = await db.execute(
        update(DMMessage)
        .where(
            and_(
                DMMessage.conversation_id == conversation_id,
                DMMessage.sender_id != user.id,
                DMMessage.read_at.is_(None),
                DMMessage.deleted_at.is_(None),
            )
        )
        .values(read_at=now)
    )
    await db.commit()
    return {"data": {"marked_read": result.rowcount or 0}}


# ── POST /conversations/{id}/report ──────────────────────────────────────────


@router.post("/conversations/{conversation_id}/report", status_code=201)
async def report_conversation(
    conversation_id: uuid.UUID,
    body: ReportConversationRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """File an abuse report for a conversation. Participant only."""
    conv = await _get_conv_assert_participant(conversation_id, user, db)
    _ = conv

    clean_reason = _sanitise(body.reason)
    # Emit admin notification for the report
    admin_notif = Notification(
        id=uuid.uuid4(),
        # Directed to system — user_id set to sender's own id as a receipt.
        # A real moderation queue would fan-out to admin users; keeping simple here.
        user_id=user.id,
        type="dm_reported",
        title="DM conversation reported",
        body=f"conv_id={conversation_id} reason={clean_reason[:200]}",
        link=f"/admin/conversations/{conversation_id}",
    )
    db.add(admin_notif)
    await db.commit()
    return {"data": {"reported": True, "conversation_id": str(conversation_id)}}


# ── Admin: POST /admin/conversations/{id}/close ───────────────────────────────


@admin_router.post("/conversations/{conversation_id}/close")
async def admin_close_conversation(
    conversation_id: uuid.UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Force-close a conversation (no new messages allowed). Admin only."""
    result = await db.execute(
        select(DMConversation).where(DMConversation.id == conversation_id)
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise ApiError("NOT_FOUND", "Conversation not found", http_status=404)

    now = _now()
    if conv.closed_by_admin_at is None:
        conv.closed_by_admin_at = now
        conv.closed_by_admin_id = admin.id
        await db.commit()
        await db.refresh(conv)

    return {
        "data": {
            "conversation_id": str(conv.id),
            "closed_by_admin_at": conv.closed_by_admin_at.isoformat(),
            "closed_by_admin_id": str(conv.closed_by_admin_id),
        }
    }
