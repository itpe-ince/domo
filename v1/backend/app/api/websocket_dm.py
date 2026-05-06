"""WebSocket DM endpoint — Phase 9 L-C (L-6 dm-expansion).

WS /ws/dm?token={access_token}

인증: JWT access token을 쿼리 파라미터로 수신
  (WebSocket은 커스텀 헤더를 지원하지 않으므로 query param 방식 사용)

연결 흐름:
  1. 클라이언트: new WebSocket("wss://.../ws/dm?token=<access_token>")
  2. 서버: JWT 검증 → 유효하지 않으면 1008 Policy Violation close
  3. 서버: ConnectionManager.connect(user_id, ws)
  4. 서버: 30초마다 ping frame 전송 (heartbeat)
  5. 클라이언트: pong 미응답 시 서버 측 disconnect
  6. 메시지 발송 이벤트 발생 시 → 수신자 user_id로 broadcast

브로드캐스트 페이로드:
  {
    "event": "new_message",
    "conversation_id": "<uuid>",
    "conversation_kind": "direct|group",
    "message": {
      "id": "<uuid>",
      "sender_id": "<uuid>",
      "body": "...",
      "attachment_url": null,
      "attachment_type": null,
      "created_at": "2026-05-05T12:00:00Z"
    }
  }
"""
from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.core.security import decode_token
from app.services.websocket_manager import get_ws_manager

log = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])

_HEARTBEAT_INTERVAL = 30  # 초


@router.websocket("/ws/dm")
async def ws_dm_endpoint(
    websocket: WebSocket,
    token: str = Query(..., description="JWT access token (WS 헤더 미지원으로 query param 사용)"),
):
    """DM 실시간 채널 WebSocket 엔드포인트.

    연결 성공 시 user_id 채널을 구독한다.
    메시지 전송 API(POST /conversations/{id}/messages, POST /me/messages/group/{id}/messages)에서
    이 채널로 new_message 이벤트를 broadcast한다.
    """
    # ── JWT 검증 ────────────────────────────────────────────────────────────
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            await websocket.close(code=1008, reason="Not an access token")
            return
        user_id: str = payload.get("sub", "")
        if not user_id:
            await websocket.close(code=1008, reason="Missing user id in token")
            return
    except (ValueError, Exception) as exc:
        log.warning("WS DM auth failed: %s", exc)
        await websocket.close(code=1008, reason="Invalid or expired token")
        return

    manager = get_ws_manager()
    await manager.connect(user_id, websocket)
    log.info("WS DM connected: user=%s", user_id)

    try:
        # ── Heartbeat + 메시지 수신 루프 ─────────────────────────────────
        while True:
            try:
                # 30초 타임아웃으로 클라이언트 메시지 대기
                # 클라이언트는 ping/pong 또는 keepalive 메시지를 보낼 수 있음
                data = await asyncio.wait_for(websocket.receive_text(), timeout=_HEARTBEAT_INTERVAL)
                # 클라이언트 메시지(ping/pong) 처리 — 현재는 무시
                _ = data
            except asyncio.TimeoutError:
                # 타임아웃 → ping 전송
                try:
                    await websocket.send_text('{"event":"ping"}')
                except Exception:
                    # ping 전송 실패 → 연결 종료
                    break
    except WebSocketDisconnect:
        log.info("WS DM disconnected: user=%s", user_id)
    except Exception as exc:
        log.warning("WS DM error: user=%s error=%s", user_id, exc)
    finally:
        await manager.disconnect(user_id, websocket)
        log.info("WS DM cleaned up: user=%s", user_id)
