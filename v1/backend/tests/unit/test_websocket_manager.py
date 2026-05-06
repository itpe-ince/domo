"""WebSocket Manager 단위 테스트 — Phase 9 L-C.

ConnectionManager(in-memory) connect/disconnect/broadcast 검증.
RedisConnectionManager는 Redis mock으로 동작 검증.

테스트 케이스:
  1. connect — user WebSocket 목록에 추가
  2. disconnect — WebSocket 제거, 마지막 연결 제거 시 dict 키도 제거
  3. broadcast_to_user — 연결된 user에게 JSON 전달
  4. broadcast_to_user — 연결 없는 user (정상 종료, 예외 없음)
  5. broadcast_to_user — 전송 실패 WebSocket 자동 제거 (dead ws cleanup)
  6. is_connected — 연결 상태 확인
  7. connection_count — 전체 연결 수
  8. user_count — 고유 사용자 수
  9. get_ws_manager — REDIS_URL 없으면 ConnectionManager 반환
  10. get_ws_manager — 동일 인스턴스 반환 (싱글턴)
"""
from __future__ import annotations

import json
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.websocket_manager import ConnectionManager, RedisConnectionManager


# ── Helpers ────────────────────────────────────────────────────────────────────


def _make_ws(*, fail_send: bool = False) -> MagicMock:
    """Mock WebSocket 객체 생성."""
    ws = MagicMock()
    ws.accept = AsyncMock()
    if fail_send:
        ws.send_text = AsyncMock(side_effect=RuntimeError("connection closed"))
    else:
        ws.send_text = AsyncMock()
    return ws


# ── ConnectionManager 테스트 ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_connect_adds_websocket():
    """connect: user_id 목록에 WebSocket 추가 + accept 호출."""
    manager = ConnectionManager()
    ws = _make_ws()
    await manager.connect("user-1", ws)

    ws.accept.assert_called_once()
    assert manager.is_connected("user-1")
    assert manager.connection_count() == 1


@pytest.mark.asyncio
async def test_connect_multiple_tabs():
    """같은 user의 다중 탭 연결을 모두 유지."""
    manager = ConnectionManager()
    ws1, ws2 = _make_ws(), _make_ws()
    await manager.connect("user-1", ws1)
    await manager.connect("user-1", ws2)

    assert manager.connection_count() == 2
    assert manager.user_count() == 1


@pytest.mark.asyncio
async def test_disconnect_removes_websocket():
    """disconnect: WebSocket 목록에서 제거."""
    manager = ConnectionManager()
    ws = _make_ws()
    await manager.connect("user-1", ws)
    await manager.disconnect("user-1", ws)

    assert not manager.is_connected("user-1")
    assert manager.connection_count() == 0
    # dict 키도 제거되어야 함
    assert "user-1" not in manager._connections


@pytest.mark.asyncio
async def test_disconnect_last_connection_removes_user_key():
    """마지막 연결 제거 시 user_id 키도 dict에서 삭제."""
    manager = ConnectionManager()
    ws1, ws2 = _make_ws(), _make_ws()
    await manager.connect("user-1", ws1)
    await manager.connect("user-1", ws2)
    await manager.disconnect("user-1", ws1)

    assert manager.is_connected("user-1")  # ws2 아직 연결
    await manager.disconnect("user-1", ws2)
    assert not manager.is_connected("user-1")
    assert "user-1" not in manager._connections


@pytest.mark.asyncio
async def test_broadcast_to_user_sends_json():
    """broadcast_to_user: 연결된 WebSocket에 JSON 전달."""
    manager = ConnectionManager()
    ws = _make_ws()
    await manager.connect("user-1", ws)

    payload = {"event": "new_message", "body": "hello"}
    await manager.broadcast_to_user("user-1", payload)

    ws.send_text.assert_called_once_with(json.dumps(payload, ensure_ascii=False, default=str))


@pytest.mark.asyncio
async def test_broadcast_to_disconnected_user_no_error():
    """연결 없는 user에게 broadcast — 예외 없이 정상 종료."""
    manager = ConnectionManager()

    # 연결 없는 user_id에 broadcast — 에러 없어야 함
    await manager.broadcast_to_user("nonexistent-user", {"event": "test"})
    # 정상 종료 = 예외 미발생


@pytest.mark.asyncio
async def test_broadcast_dead_websocket_cleaned_up():
    """전송 실패 WebSocket은 dead 목록으로 분류 후 자동 제거."""
    manager = ConnectionManager()
    good_ws = _make_ws()
    bad_ws = _make_ws(fail_send=True)

    await manager.connect("user-1", good_ws)
    await manager.connect("user-1", bad_ws)

    payload = {"event": "ping"}
    await manager.broadcast_to_user("user-1", payload)

    # good_ws는 정상 전송, bad_ws는 제거 후 연결 수 감소
    good_ws.send_text.assert_called_once()
    assert manager.connection_count() == 1  # bad_ws 제거됨


@pytest.mark.asyncio
async def test_is_connected():
    """is_connected: 연결/미연결 상태 정확히 반환."""
    manager = ConnectionManager()
    ws = _make_ws()

    assert not manager.is_connected("user-1")
    await manager.connect("user-1", ws)
    assert manager.is_connected("user-1")
    await manager.disconnect("user-1", ws)
    assert not manager.is_connected("user-1")


@pytest.mark.asyncio
async def test_connection_count():
    """connection_count: 전체 연결 수 집계."""
    manager = ConnectionManager()
    ws1, ws2, ws3 = _make_ws(), _make_ws(), _make_ws()
    await manager.connect("user-1", ws1)
    await manager.connect("user-2", ws2)
    await manager.connect("user-1", ws3)  # user-1 의 두 번째 탭

    assert manager.connection_count() == 3
    assert manager.user_count() == 2


@pytest.mark.asyncio
async def test_get_ws_manager_returns_in_memory_when_no_redis():
    """REDIS_URL 미설정 시 ConnectionManager(in-memory) 반환."""
    from app.services import websocket_manager as wsm_module

    # 싱글턴 초기화 초기화
    original = wsm_module._memory_manager
    wsm_module._memory_manager = None

    with patch("app.core.config.get_settings") as mock_settings:
        mock_settings.return_value.redis_url = None
        manager = wsm_module.get_ws_manager()

    assert isinstance(manager, ConnectionManager)
    assert not isinstance(manager, RedisConnectionManager)

    # 복원
    wsm_module._memory_manager = original


@pytest.mark.asyncio
async def test_get_ws_manager_singleton():
    """get_ws_manager: 동일 인스턴스를 반환 (싱글턴)."""
    from app.services import websocket_manager as wsm_module

    # 싱글턴 초기화
    original = wsm_module._memory_manager
    wsm_module._memory_manager = None

    with patch("app.core.config.get_settings") as mock_settings:
        mock_settings.return_value.redis_url = None
        m1 = wsm_module.get_ws_manager()
        m2 = wsm_module.get_ws_manager()

    assert m1 is m2

    # 복원
    wsm_module._memory_manager = original


# ── RedisConnectionManager 테스트 ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_redis_manager_local_broadcast():
    """RedisConnectionManager: 로컬 연결에는 직접 전송."""
    manager = RedisConnectionManager("redis://localhost:6379")
    ws = _make_ws()
    await manager.connect("user-1", ws)

    payload = {"event": "new_message"}

    # cache._client = None → Redis publish skip, 로컬 전송만 수행
    mock_cache_module = MagicMock()
    mock_cache_module.cache._client = None

    with patch.dict("sys.modules", {"app.services.cache": mock_cache_module}):
        await manager.broadcast_to_user("user-1", payload)

    ws.send_text.assert_called_once()


@pytest.mark.asyncio
async def test_redis_manager_falls_back_on_redis_error():
    """Redis publish 실패해도 로컬 전송은 완료 (graceful degradation)."""
    manager = RedisConnectionManager("redis://localhost:6379")
    ws = _make_ws()
    await manager.connect("user-1", ws)

    mock_redis_client = MagicMock()
    mock_redis_client.publish = AsyncMock(side_effect=ConnectionError("Redis down"))
    mock_cache_obj = MagicMock(_client=mock_redis_client)
    mock_cache_module = MagicMock()
    mock_cache_module.cache = mock_cache_obj

    with patch.dict("sys.modules", {"app.services.cache": mock_cache_module}):
        await manager.broadcast_to_user("user-1", {"event": "test"})

    # 로컬 전송은 성공해야 함
    ws.send_text.assert_called_once()
