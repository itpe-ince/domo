"""WebSocket Connection Manager — Phase 9 L-C (L-6 dm-expansion).

단일 인스턴스: in-memory dict (user_id → list[WebSocket])
다중 인스턴스: Redis pub/sub (REDIS_URL 설정 시 자동 전환)

사용 패턴:
    manager = get_ws_manager()
    await manager.connect(user_id, websocket)
    await manager.broadcast_to_user(user_id, payload)
    await manager.disconnect(user_id, websocket)

주의:
  - REDIS_URL 미설정 시 in-memory fallback (단일 pod에서만 broadcast 동작)
  - 다중 pod 환경에서는 반드시 REDIS_URL 설정 필요
"""
from __future__ import annotations

import json
import logging

log = logging.getLogger(__name__)


class ConnectionManager:
    """in-memory WebSocket 연결 관리자 (단일 인스턴스 전용).

    multi-pod 환경에서는 Redis pub/sub 래퍼(RedisConnectionManager)로 대체.
    user_id(str) → list[WebSocket] 구조로 한 사용자의 다중 탭/기기를 지원.
    """

    def __init__(self) -> None:
        # user_id(str) → list[WebSocket]
        self._connections: dict[str, list] = {}

    async def connect(self, user_id: str, websocket) -> None:
        """WebSocket 연결 수락 후 user_id별 목록에 추가."""
        await websocket.accept()
        self._connections.setdefault(user_id, []).append(websocket)
        log.debug("WS connect: user=%s total_conns=%d", user_id, self.connection_count())

    async def disconnect(self, user_id: str, websocket) -> None:
        """WebSocket 연결 제거. 해당 user에 연결이 없으면 dict 키도 제거."""
        conns = self._connections.get(user_id, [])
        if websocket in conns:
            conns.remove(websocket)
        if not conns:
            self._connections.pop(user_id, None)
        log.debug("WS disconnect: user=%s total_conns=%d", user_id, self.connection_count())

    async def broadcast_to_user(self, user_id: str, payload: dict) -> None:
        """해당 user_id로 연결된 모든 WebSocket에 JSON 브로드캐스트.

        전송 실패(연결 끊김 등)한 WebSocket은 자동으로 목록에서 제거된다.
        """
        dead: list = []
        data = json.dumps(payload, ensure_ascii=False, default=str)
        for ws in list(self._connections.get(user_id, [])):
            try:
                await ws.send_text(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            await self.disconnect(user_id, ws)

    def is_connected(self, user_id: str) -> bool:
        """특정 user_id의 연결 여부 확인."""
        return bool(self._connections.get(user_id))

    def connection_count(self) -> int:
        """전체 활성 WebSocket 연결 수 (헬스체크용)."""
        return sum(len(v) for v in self._connections.values())

    def user_count(self) -> int:
        """연결된 고유 사용자 수."""
        return len(self._connections)


class RedisConnectionManager(ConnectionManager):
    """Redis pub/sub 기반 ConnectionManager (multi-pod 지원).

    REDIS_URL 환경 변수 설정 시 get_ws_manager()가 이 클래스를 반환한다.
    구독 채널: dm:user:{user_id}

    동작 방식:
      1. 메시지 전송 → 로컬 WebSocket에 직접 broadcast
      2. Redis publish → 다른 pod가 같은 채널을 구독 중이면 해당 pod의 로컬 연결에 전달
    """

    def __init__(self, redis_url: str) -> None:
        super().__init__()
        self._redis_url = redis_url

    async def broadcast_to_user(self, user_id: str, payload: dict) -> None:
        """로컬 연결에 직접 전송 + Redis 채널 publish (다른 pod 전달용)."""
        # 1. 로컬 in-memory 연결에 직접 전송
        await super().broadcast_to_user(user_id, payload)

        # 2. Redis publish — 다른 pod가 구독 중이면 수신
        channel = f"dm:user:{user_id}"
        try:
            # 지연 import로 순환 의존 방지. 테스트에서는 patch("app.services.cache.cache")로 mock.
            import app.services.cache as _cache_module
            _cache = _cache_module.cache
            if getattr(_cache, "_client", None) is not None:
                await _cache._client.publish(channel, json.dumps(payload, ensure_ascii=False, default=str))
        except Exception as exc:
            # Redis 장애 시 로컬 전송만으로 graceful degradation
            log.warning("Redis publish failed (user=%s): %s", user_id, exc)


# ── 싱글턴 팩토리 ──────────────────────────────────────────────────────────────

_memory_manager: ConnectionManager | None = None
_redis_manager: RedisConnectionManager | None = None


def _get_memory_manager() -> ConnectionManager:
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = ConnectionManager()
    return _memory_manager


def _get_redis_manager(redis_url: str) -> RedisConnectionManager:
    global _redis_manager
    if _redis_manager is None:
        _redis_manager = RedisConnectionManager(redis_url)
    return _redis_manager


def get_ws_manager() -> ConnectionManager:
    """설정에 따라 적합한 ConnectionManager 싱글턴을 반환.

    REDIS_URL 설정 시 → RedisConnectionManager (multi-pod 지원)
    REDIS_URL 미설정 시 → ConnectionManager (in-memory, 단일 pod)
    """
    from app.core.config import get_settings

    settings = get_settings()
    redis_url = getattr(settings, "redis_url", None)

    if redis_url:
        return _get_redis_manager(redis_url)

    # in-memory fallback — 시작 시 경고 로그 (최초 1회만)
    if _memory_manager is None:
        log.warning(
            "REDIS_URL not set — WebSocket using in-memory fallback. "
            "Multi-pod broadcast will NOT work. Set REDIS_URL for production."
        )
    return _get_memory_manager()
