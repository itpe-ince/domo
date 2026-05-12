---
template: design
version: 1.0
feature: dm-expansion
phase: 9-L-C
date: 2026-05-05
author: itpe-ince (Claude Sonnet 4.6)
project: domo
project_version: v1
status: Draft
depends_on:
  - Phase 8 B'-2 (0063_dm_messaging — dm_conversations, dm_messages)
  - Phase 8 B'-3 (0064_push_tokens — FCM/APNs)
  - Phase 8 G''-2 (Redis CacheClient)
  - Phase 4 M4 (StorageProvider — S3/local)
alembic:
  - "0068: group_conversations + group_participants (L-5 Group DM)"
  - "0069: dm_messages 첨부파일 컬럼 (L-7 File Attachment)"
---

# Phase 9 L-C Design — DM 확장 3종

> **Summary**: Phase 8 B'-2 1:1 DM 위에서 Group DM (3인 이상), WebSocket 실시간 브로드캐스트,
> 파일/이미지 첨부를 순차 완성한다. alembic 0068(L-5) + 0069(L-7) 두 마이그레이션으로 분리,
> WebSocket 서비스 레이어(L-6)는 스키마 변경 없음.

---

## 1. 목표 및 Acceptance Criteria

### 목표

| # | 목표 | Phase 8 현황 | L-C 목표 |
|---|------|:----------:|:-------:|
| L-5 | Group DM (3인 이상 대화방) | B'-2: 1:1만 지원 | 최대 50인 그룹, 관리자 역할 |
| L-6 | WebSocket 실시간 Push | B'-2: 1초 polling | WS 브로드캐스트, 100ms p95 |
| L-7 | 파일/이미지 첨부 DM | B'-2: 텍스트 only | 이미지+PDF ≤10MB presign 업로드 |

### Acceptance Criteria

- [ ] **L-5** `POST /me/messages/conversations/group` — 3인 이상 그룹 생성 정상 동작
- [ ] **L-5** `POST /me/messages/conversations/{id}/participants` — 참여자 추가 (관리자 전용)
- [ ] **L-5** `DELETE /me/messages/conversations/{id}/participants/{user_id}` — 참여자 제거 (관리자 전용)
- [ ] **L-5** alembic 0068 upgrade + downgrade 테스트 green
- [ ] **L-5** Group DM 발송 시 B'-3 Push notification 발화 확인
- [ ] **L-6** `WS /ws/dm` 핸드셰이크 + 인증 토큰 검증 정상 동작
- [ ] **L-6** 메시지 POST 시 수신자 WebSocket 채널로 실시간 브로드캐스트
- [ ] **L-6** Redis 미설정 시 in-memory fallback 자동 전환 (단일 인스턴스)
- [ ] **L-7** `POST /me/messages/{conv_id}/attachment/presign` — S3 presigned URL 발급
- [ ] **L-7** 첨부 포함 메시지 전송 + 수신 정상 동작 (attachment_url, attachment_type)
- [ ] **L-7** 크기 제한 10MB / MIME 검증 (image/jpeg, image/png, image/gif, image/webp, application/pdf)
- [ ] **L-7** alembic 0069 upgrade + downgrade 테스트 green
- [ ] 전체 신규/변경 테스트 ≥ 20개

---

## 2. Database Schema

### 2-1. alembic 0068 — Group DM (L-5)

**설계 원칙**: 기존 `dm_conversations` (1:1)에는 손대지 않는다. 그룹 전용 테이블 `group_conversations` + `group_participants`를 신규 생성하여 독립 운영한다. 클라이언트는 대화방 종류를 `kind` 필드로 구별한다.

```sql
-- group_conversations
CREATE TABLE group_conversations (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(100) NOT NULL,          -- 그룹명 (관리자 수정 가능)
    creator_id      UUID NOT NULL REFERENCES users(id) ON DELETE SET NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_message_at TIMESTAMPTZ,                    -- 최신 메시지 시각 (정렬용)
    max_participants INT NOT NULL DEFAULT 50,
    closed_at       TIMESTAMPTZ,                    -- 관리자 종료
    closed_by_id    UUID REFERENCES users(id) ON DELETE SET NULL
);

CREATE INDEX ix_group_conv_creator ON group_conversations(creator_id);
CREATE INDEX ix_group_conv_last_msg ON group_conversations(last_message_at DESC NULLS LAST);

-- group_participants
CREATE TABLE group_participants (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES group_conversations(id) ON DELETE CASCADE,
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role            VARCHAR(20) NOT NULL DEFAULT 'member',  -- 'member' | 'admin'
    joined_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    left_at         TIMESTAMPTZ,                            -- NULL = 현재 참여 중
    UNIQUE (conversation_id, user_id)
);

CREATE INDEX ix_group_part_user ON group_participants(user_id, left_at NULLS FIRST);
CREATE INDEX ix_group_part_conv ON group_participants(conversation_id, left_at NULLS FIRST);

-- group_messages (그룹 전용 메시지 테이블)
-- dm_messages는 1:1 전용이므로 그룹은 별도 테이블
CREATE TABLE group_messages (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES group_conversations(id) ON DELETE CASCADE,
    sender_id       UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    body            TEXT NOT NULL,                  -- max 2000 chars, app layer 검증
    attachment_url  TEXT,
    attachment_type VARCHAR(20),                    -- 'image' | 'file' | NULL
    attachment_size_bytes BIGINT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    edited_at       TIMESTAMPTZ,
    deleted_at      TIMESTAMPTZ
);

CREATE INDEX ix_group_msg_conv_created ON group_messages(conversation_id, created_at);
CREATE INDEX ix_group_msg_sender ON group_messages(sender_id, created_at);
```

**다운그레이드 순서**: group_messages → group_participants → group_conversations (CASCADE로 자동 처리되지 않으므로 명시적 drop 순서 유지)

**기존 dm_conversations 변경 없음**: 1:1 DM은 user_a_id/user_b_id 정규화 방식 그대로 유지. 클라이언트는 응답의 `kind` 필드("direct" | "group")로 구별.

---

### 2-2. alembic 0069 — DM 첨부파일 (L-7)

1:1 `dm_messages` 테이블에 첨부파일 컬럼 3개를 추가한다.

```sql
ALTER TABLE dm_messages
    ADD COLUMN attachment_url       TEXT,
    ADD COLUMN attachment_type      VARCHAR(20),        -- 'image' | 'file' | NULL
    ADD COLUMN attachment_size_bytes BIGINT;

-- 첨부파일 있는 메시지 조회용 (관리자 모더레이션 큐)
CREATE INDEX ix_dm_msg_attachment ON dm_messages(attachment_type)
    WHERE attachment_type IS NOT NULL;
```

**다운그레이드**:
```sql
DROP INDEX IF EXISTS ix_dm_msg_attachment;
ALTER TABLE dm_messages
    DROP COLUMN IF EXISTS attachment_size_bytes,
    DROP COLUMN IF EXISTS attachment_type,
    DROP COLUMN IF EXISTS attachment_url;
```

**revision 체인**:
- 0068: `down_revision = "0067_rss_source"` (L-B에서 생성)
- 0069: `down_revision = "0068_group_dm"`

---

## 3. Service Layer

### 3-1. `app/services/websocket_manager.py` (신규)

```python
"""WebSocket Connection Manager — L-6 dm-expansion.

단일 인스턴스: in-memory dict (user_id → WebSocket list)
다중 인스턴스: Redis pub/sub fallback (REDIS_URL 설정 시 자동 전환)

사용 패턴:
    manager = get_ws_manager()
    await manager.connect(user_id, websocket)
    await manager.broadcast_to_user(user_id, payload)
    await manager.disconnect(user_id, websocket)
"""

class ConnectionManager:
    """in-memory WebSocket 연결 관리자 (단일 인스턴스 전용).

    multi-pod 환경에서는 Redis pub/sub 래퍼(RedisConnectionManager)로 대체.
    """

    def __init__(self) -> None:
        # user_id(str) → list[WebSocket]
        self._connections: dict[str, list] = {}

    async def connect(self, user_id: str, websocket) -> None:
        await websocket.accept()
        self._connections.setdefault(user_id, []).append(websocket)

    async def disconnect(self, user_id: str, websocket) -> None:
        conns = self._connections.get(user_id, [])
        if websocket in conns:
            conns.remove(websocket)
        if not conns:
            self._connections.pop(user_id, None)

    async def broadcast_to_user(self, user_id: str, payload: dict) -> None:
        """해당 user_id로 연결된 모든 WebSocket에 JSON 브로드캐스트."""
        import json
        dead: list = []
        for ws in list(self._connections.get(user_id, [])):
            try:
                await ws.send_text(json.dumps(payload))
            except Exception:
                dead.append(ws)
        for ws in dead:
            await self.disconnect(user_id, ws)


class RedisConnectionManager(ConnectionManager):
    """Redis pub/sub 기반 ConnectionManager (multi-pod 지원).

    REDIS_URL 환경 변수 설정 시 get_ws_manager()가 이 클래스를 반환.
    구독 채널: dm:user:{user_id}
    """

    def __init__(self, redis_url: str) -> None:
        super().__init__()
        self._redis_url = redis_url
        self._pubsub_task = None  # asyncio.Task

    async def broadcast_to_user(self, user_id: str, payload: dict) -> None:
        """로컬 연결에 직접 전송 + Redis 채널 publish (다른 pod 전달용)."""
        import json
        channel = f"dm:user:{user_id}"
        # 로컬 전송
        await super().broadcast_to_user(user_id, payload)
        # Redis publish (다른 pod가 구독 중이면 수신)
        try:
            from app.services.cache import get_cache_client
            cache = get_cache_client()
            if hasattr(cache, "_redis"):  # 실제 Redis 클라이언트인 경우만
                await cache._redis.publish(channel, json.dumps(payload))
        except Exception:
            pass  # Redis 장애 시 로컬 전송만으로 graceful degradation


def get_ws_manager() -> ConnectionManager:
    """설정에 따라 적합한 ConnectionManager 싱글턴을 반환."""
    from app.core.config import get_settings
    settings = get_settings()
    redis_url = getattr(settings, "redis_url", None)
    if redis_url:
        return _redis_manager_singleton(redis_url)
    return _memory_manager_singleton()
```

**헬스체크**: `/health` 응답에 `ws_connections: int` 추가 (ConnectionManager.connection_count() 집계).

---

### 3-2. `app/api/websocket.py` (신규)

```python
"""WebSocket DM endpoint — L-6 dm-expansion.

WS /ws/dm?token={access_token}

인증: JWT access token을 쿼리 파라미터로 수신 (WS는 Authorization 헤더 지원 불가).
토큰 검증 후 user_id별 채널 구독.
Heartbeat: 30초 간격 ping, 클라이언트 pong 없으면 연결 종료.
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from app.core.security import decode_access_token
from app.services.websocket_manager import get_ws_manager

router = APIRouter(tags=["websocket"])

@router.websocket("/ws/dm")
async def ws_dm_endpoint(
    websocket: WebSocket,
    token: str = Query(..., description="JWT access token"),
):
    """
    연결 흐름:
    1. JWT 검증 → user_id 추출
    2. ConnectionManager.connect(user_id, ws)
    3. 30초 heartbeat loop (ping/pong)
    4. WebSocketDisconnect → disconnect 정리
    """
```

**브로드캐스트 트리거**: `POST /conversations/{id}/messages` (기존) 및 `POST /me/messages/group/{id}/messages` (신규) 내부에서 메시지 저장 후 수신자들에게 `broadcast_to_user()` 호출.

브로드캐스트 페이로드 형식:
```json
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
```

---

### 3-3. 그룹 DM 서비스 함수 (`app/api/group_conversations.py` 신규)

Group DM API를 conversations.py와 분리하여 독립 라우터로 구성한다.

**주요 비즈니스 규칙**:
- 그룹 생성 시 creator는 자동으로 `role='admin'`
- 참여자 추가/제거는 현재 `role='admin'`인 사용자만 가능
- 참여자 제거 시 `left_at = NOW()` 소프트 삭제 (메시지 히스토리 보존)
- 메시지 전송 속도 제한: 5 messages/min/user/group (기존 1:1 60/min/user와 별도)
- 그룹 삭제(creator 전용): group_conversations.closed_at 설정 (하드 삭제 아님)
- 최대 참여자: 50인 초과 시 422

---

### 3-4. 첨부파일 presign 서비스 변경

기존 StorageProvider(`app/services/storage/`) 패턴을 그대로 활용한다.

```python
# app/api/group_conversations.py 또는 conversations.py 확장부

ALLOWED_ATTACHMENT_MIME = {
    "image/jpeg", "image/png", "image/gif", "image/webp",
    "application/pdf",
}
ATTACHMENT_MAX_BYTES = 10 * 1024 * 1024  # 10 MB

async def generate_attachment_presign(
    conv_id: uuid.UUID,
    filename: str,
    content_type: str,
    size_bytes: int,
    current_user: User,
    storage=Depends(get_storage_provider),
) -> dict:
    if content_type not in ALLOWED_ATTACHMENT_MIME:
        raise ApiError(422, "허용되지 않는 파일 형식입니다.")
    if size_bytes > ATTACHMENT_MAX_BYTES:
        raise ApiError(422, "파일 크기는 10MB를 초과할 수 없습니다.")
    key = f"dm-attachments/{conv_id}/{uuid.uuid4()}/{filename}"
    presigned = await storage.presign_put(key, content_type, expires=900)  # 15분
    return {"upload_url": presigned.url, "key": key}
```

**Mock fallback**: `STORAGE_PROVIDER=local` 시 `LocalStorageProvider.presign_put()`이 `/media/upload` 방식으로 대체 URL 반환 (기존 local.py 패턴 그대로).

---

## 4. API Endpoints

### 4-1. Group DM (L-5)

| Method | Path | 설명 | 인증 | Rate Limit |
|--------|------|------|------|-----------|
| `POST` | `/me/messages/conversations/group` | 그룹 대화방 생성 | user | 10/hr/user |
| `GET` | `/me/messages/conversations/group` | 내 그룹 대화방 목록 | user | — |
| `GET` | `/me/messages/group/{conv_id}/messages` | 그룹 메시지 목록 | user (참여자) | — |
| `POST` | `/me/messages/group/{conv_id}/messages` | 그룹 메시지 전송 | user (참여자) | 5/min/user/group |
| `POST` | `/me/messages/conversations/{conv_id}/participants` | 참여자 추가 | user (admin role) | — |
| `DELETE` | `/me/messages/conversations/{conv_id}/participants/{user_id}` | 참여자 제거 | user (admin role) | — |
| `PATCH` | `/me/messages/conversations/{conv_id}` | 그룹명 수정 | user (admin role) | — |

**POST /me/messages/conversations/group Request**:
```json
{
  "name": "그룹 이름 (max 100자)",
  "participant_user_ids": ["uuid1", "uuid2", "uuid3"]
}
```
- `participant_user_ids`: 2명 이상 필수 (creator 포함 최소 3인)
- 최대 49명 (creator 포함 50인)

**POST /me/messages/group/{conv_id}/messages Request**:
```json
{
  "body": "메시지 내용 (max 2000자)",
  "attachment_url": "https://...",
  "attachment_type": "image"
}
```

---

### 4-2. WebSocket (L-6)

| Endpoint | 설명 |
|----------|------|
| `WS /ws/dm?token={jwt}` | DM 실시간 채널 구독 |

**연결 흐름**:
1. 클라이언트: `new WebSocket("wss://api.domo.io/ws/dm?token=<access_token>")`
2. 서버: JWT 검증 → 유효하지 않으면 `1008 Policy Violation` close
3. 서버: ConnectionManager.connect(user_id, ws)
4. 서버: 30초마다 ping frame 전송
5. 클라이언트: pong 미응답 시 서버 측 disconnect
6. 메시지 발송 이벤트 발생 시: 수신자 user_id로 broadcast

**클라이언트 재연결**: exponential backoff (1s → 2s → 4s → 최대 30s)

---

### 4-3. 파일/이미지 첨부 (L-7)

| Method | Path | 설명 | 인증 |
|--------|------|------|------|
| `POST` | `/me/messages/{conv_id}/attachment/presign` | presigned URL 발급 (1:1) | user (참여자) |
| `POST` | `/me/messages/group/{conv_id}/attachment/presign` | presigned URL 발급 (그룹) | user (참여자) |

**POST /me/messages/{conv_id}/attachment/presign Request**:
```json
{
  "filename": "photo.jpg",
  "content_type": "image/jpeg",
  "size_bytes": 2048000
}
```

**Response**:
```json
{
  "upload_url": "https://s3.amazonaws.com/...",
  "key": "dm-attachments/<conv_id>/<uuid>/photo.jpg",
  "expires_in": 900
}
```

**업로드 완료 후 메시지 전송**:
```
클라이언트 → PUT {upload_url} (binary, Content-Type: image/jpeg)
클라이언트 → POST /conversations/{conv_id}/messages
             body: { "body": "", "attachment_url": "<CDN URL>", "attachment_type": "image", "attachment_size_bytes": 2048000 }
```

**MIME 허용 목록**: `image/jpeg`, `image/png`, `image/gif`, `image/webp`, `application/pdf`
**크기 제한**: 10MB (presign 요청 시 서버 측 `size_bytes` 검증)

---

## 5. Frontend Changes

### 5-1. Group DM UI

**신규 컴포넌트**:

| 컴포넌트 | 경로 | 설명 |
|---------|------|------|
| `GroupConversationCreate` | `src/components/dm/GroupConversationCreate.tsx` | 그룹 생성 모달 (참여자 검색 + 선택) |
| `GroupParticipantList` | `src/components/dm/GroupParticipantList.tsx` | 참여자 목록 + 추가/제거 (관리자용) |
| `GroupConversationHeader` | `src/components/dm/GroupConversationHeader.tsx` | 그룹명 + 참여자 수 표시, 관리자 메뉴 |

**기존 컴포넌트 변경**:
- `src/app/messages/page.tsx`: 1:1 대화 목록에 그룹 대화 탭 추가
- `src/app/messages/[id]/page.tsx`: `conversation.kind`에 따라 1:1/그룹 UI 분기

**API 호출**:
```typescript
// src/lib/api.ts 추가
export const groupConversationsApi = {
  create: (body: CreateGroupRequest) =>
    apiFetch("POST", "/me/messages/conversations/group", body),
  list: () => apiFetch("GET", "/me/messages/conversations/group"),
  getMessages: (convId: string, cursor?: string) =>
    apiFetch("GET", `/me/messages/group/${convId}/messages`, undefined, { cursor }),
  sendMessage: (convId: string, body: SendGroupMessageRequest) =>
    apiFetch("POST", `/me/messages/group/${convId}/messages`, body),
  addParticipant: (convId: string, userId: string) =>
    apiFetch("POST", `/me/messages/conversations/${convId}/participants`, { user_id: userId }),
  removeParticipant: (convId: string, userId: string) =>
    apiFetch("DELETE", `/me/messages/conversations/${convId}/participants/${userId}`),
};
```

---

### 5-2. WebSocket 클라이언트

**신규 훅**: `src/lib/hooks/useWebSocketDM.ts`

```typescript
/**
 * DM WebSocket 연결 훅 — L-6
 *
 * 연결: WS /ws/dm?token={accessToken}
 * 수신 이벤트: new_message → QueryClient invalidateQueries
 * 재연결: exponential backoff (최대 30초)
 */
export function useWebSocketDM() {
  const { accessToken } = useAuth();
  const queryClient = useQueryClient();

  useEffect(() => {
    if (!accessToken) return;

    const wsUrl = `${WS_BASE_URL}/ws/dm?token=${accessToken}`;
    let ws: WebSocket;
    let retryDelay = 1000;

    function connect() {
      ws = new WebSocket(wsUrl);

      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.event === "new_message") {
          // 해당 대화방 메시지 캐시 무효화
          queryClient.invalidateQueries({
            queryKey: ["messages", data.conversation_id],
          });
          // 대화방 목록 last_message_at 갱신
          queryClient.invalidateQueries({ queryKey: ["conversations"] });
        }
      };

      ws.onclose = () => {
        setTimeout(() => {
          retryDelay = Math.min(retryDelay * 2, 30000);
          connect();
        }, retryDelay);
      };

      ws.onopen = () => {
        retryDelay = 1000; // 성공 시 초기화
      };
    }

    connect();
    return () => ws?.close();
  }, [accessToken, queryClient]);
}
```

**적용 위치**: `src/app/messages/layout.tsx`에서 `useWebSocketDM()` 마운트 — 메시지 페이지 전체에서 실시간 수신.

**폴링 제거**: 기존 `useInterval(fetchMessages, 1000)` 패턴을 WebSocket 연결 성공 시 비활성화. WS 연결 실패 시 3초 폴링 fallback 유지 (`isWsConnected` 상태로 조건부 처리).

---

### 5-3. 첨부파일 UI

**신규 컴포넌트**: `src/components/dm/MessageAttachmentPicker.tsx`

```typescript
/**
 * 첨부파일 선택 + presign 업로드 컴포넌트
 *
 * 허용: image/jpeg, image/png, image/gif, image/webp, application/pdf
 * 제한: 10MB
 * 흐름: 파일 선택 → presign 요청 → S3 PUT → attachment_url 반환
 */
```

**메시지 입력 영역 변경** (`src/components/dm/MessageInput.tsx`):
- 클립 아이콘 버튼 추가 → `MessageAttachmentPicker` 열기
- 업로드 중 로딩 인디케이터
- 첨부 완료 시 미리보기 썸네일 (이미지) 또는 파일명 표시 (PDF)
- 전송 시 `attachment_url`, `attachment_type`, `attachment_size_bytes` 포함

**메시지 버블 변경** (`src/components/dm/MessageBubble.tsx`):
- `attachment_type === "image"`: `<img>` 태그 렌더링 (lazy load, max-width 240px)
- `attachment_type === "file"`: 파일 아이콘 + 다운로드 링크
- `attachment_url` 없으면 기존 텍스트 버블 그대로

---

## 6. Mock 모드 Fallback

### Redis 미설정 시 (L-6)

`REDIS_URL` 환경 변수 없으면 `get_ws_manager()`가 `ConnectionManager`(in-memory) 반환.

| 항목 | Redis 설정 시 | Redis 미설정 시 |
|------|:------------:|:--------------:|
| 단일 인스턴스 | pub/sub | in-memory dict |
| 다중 인스턴스 | 정상 동작 | pod간 broadcast 누락 (경고 로그) |
| 개발 환경 | 불필요 | in-memory로 충분 |

```python
# 시작 시 로그
if not redis_url:
    logger.warning(
        "REDIS_URL not set — WebSocket using in-memory fallback. "
        "Multi-pod broadcast will NOT work. Set REDIS_URL for production."
    )
```

### S3 미설정 시 (L-7)

`STORAGE_PROVIDER=local` 시 LocalStorageProvider가 presign URL 대신 내부 경로(`/media/upload`) 반환.

```python
# local.py 확장 — presign_put mock
async def presign_put(self, key: str, content_type: str, expires: int) -> PresignedPost:
    # 로컬 개발: 즉시 업로드 URL 대신 mock URL 반환
    mock_url = f"{settings.api_base_url}/media/mock-presign?key={key}"
    return PresignedPost(url=mock_url, fields={})
```

실제 S3 없이 개발 시: 파일을 `UPLOAD_ROOT/dm-attachments/` 로컬 디렉토리에 직접 저장 후 static URL 반환 (`GET /media/local/{key}`).

---

## 7. i18n Keys (5 locale)

추가 대상 파일: `v1/frontend/src/i18n/{ko,en,ja,zh,es}.json`

```json
// dm.* 확장 (기존 B'-2 키 유지)
{
  "dm.group.create": "그룹 대화 만들기",
  "dm.group.name_placeholder": "그룹 이름을 입력하세요",
  "dm.group.add_participants": "참여자 추가",
  "dm.group.remove_participant": "참여자 제거",
  "dm.group.leave": "그룹 나가기",
  "dm.group.you_left": "대화에서 나갔습니다",
  "dm.group.participant_joined": "{{name}}님이 참여했습니다",
  "dm.group.participant_left": "{{name}}님이 나갔습니다",
  "dm.group.max_participants": "최대 {{max}}명까지 참여할 수 있습니다",
  "dm.group.admin_only": "관리자만 수행할 수 있습니다",
  "dm.group.rename": "그룹 이름 변경",
  "dm.group.manage_participants": "참여자 관리",

  "dm.attachment.pick": "파일 첨부",
  "dm.attachment.uploading": "업로드 중...",
  "dm.attachment.too_large": "파일은 10MB를 초과할 수 없습니다",
  "dm.attachment.invalid_type": "지원하지 않는 파일 형식입니다",
  "dm.attachment.download": "다운로드",

  "dm.ws.reconnecting": "연결 중...",
  "dm.ws.connected": "실시간 연결됨",
  "dm.ws.disconnected": "오프라인 — 새 메시지는 새로고침 후 표시됩니다",

  "dm.error.group_not_found": "그룹 대화를 찾을 수 없습니다",
  "dm.error.not_participant": "대화 참여자가 아닙니다",
  "dm.error.rate_limited": "잠시 후 다시 시도하세요 (분당 5개 제한)"
}
```

총 추가 i18n 키: **22개 × 5 locale = 110 entries**

---

## 8. Test Plan

### 8-1. 백엔드 테스트

**신규 테스트 파일**: `v1/backend/tests/test_group_dm.py`, `v1/backend/tests/test_dm_attachment.py`, `v1/backend/tests/test_websocket_manager.py`

| # | 테스트 케이스 | 종류 |
|---|------------|------|
| 1 | 그룹 생성 정상 (creator + 2명) | 통합 |
| 2 | 그룹 생성 실패 — 참여자 2명 미만 (422) | 단위 |
| 3 | 그룹 생성 실패 — 참여자 50명 초과 (422) | 단위 |
| 4 | 참여자 추가 (admin role) | 통합 |
| 5 | 참여자 추가 실패 — non-admin (403) | 통합 |
| 6 | 참여자 제거 (admin role, left_at 설정 확인) | 통합 |
| 7 | 그룹 메시지 전송 + 메시지 목록 조회 | 통합 |
| 8 | 그룹 메시지 속도 제한 (5/min 초과 시 429) | 단위 |
| 9 | WebSocket manager connect/disconnect (in-memory) | 단위 |
| 10 | broadcast_to_user — 연결된 user에게 전달 | 단위 |
| 11 | broadcast_to_user — 연결 없는 user (정상 종료) | 단위 |
| 12 | presign 요청 — 허용 MIME 정상 (200) | 통합 |
| 13 | presign 요청 — 금지 MIME (422) | 단위 |
| 14 | presign 요청 — 10MB 초과 (422) | 단위 |
| 15 | 첨부 포함 메시지 전송 — dm_messages 컬럼 저장 확인 | 통합 |
| 16 | alembic 0068 upgrade/downgrade | 마이그레이션 |
| 17 | alembic 0069 upgrade/downgrade | 마이그레이션 |
| 18 | 그룹 DM 전송 시 Push notification 발화 확인 | 통합 |
| 19 | 비참여자가 그룹 메시지 조회 시 403 | 통합 |
| 20 | 그룹명 변경 (admin만 가능) | 통합 |

**WebSocket E2E 테스트 한계**: FastAPI TestClient는 WebSocket을 `client.websocket_connect()` 방식으로 테스트 가능하나, 실시간 broadcast 검증은 두 개의 WebSocket 클라이언트를 동시에 연결해야 한다. 이는 pytest-asyncio 환경에서 가능하나 flaky 위험이 있어 ConnectionManager 단위 테스트에 집중하고, E2E는 별도 smoke test 스크립트로 분리한다.

**스모크 테스트**: `v1/backend/scripts/smoke_test_group_dm.sh` (수동 실행)
- wscat 또는 websocat으로 WS 연결 → 메시지 전송 → broadcast 수신 확인

---

### 8-2. 프론트엔드 테스트

| # | 테스트 케이스 | 도구 |
|---|------------|------|
| 1 | GroupConversationCreate — 참여자 2명 미만 시 버튼 비활성화 | Jest + RTL |
| 2 | MessageAttachmentPicker — 10MB 초과 파일 에러 메시지 표시 | Jest + RTL |
| 3 | MessageAttachmentPicker — 금지 MIME 에러 메시지 표시 | Jest + RTL |
| 4 | MessageBubble — attachment_type="image" 시 img 렌더링 | Jest + RTL |
| 5 | useWebSocketDM — WS 연결 실패 시 폴링 fallback 전환 | Jest |

---

## 9. 위임 Agent

| 역할 | Agent | 담당 작업 |
|------|-------|---------|
| 주도 | **bkend-expert** | alembic 0068+0069, websocket_manager.py, group_conversations.py, presign endpoint, 백엔드 테스트 20개 |
| 보조 | **frontend-architect** | GroupConversationCreate/Header/ParticipantList 컴포넌트, useWebSocketDM 훅, MessageAttachmentPicker, i18n 110 entries |

**실행 순서**:
1. (bkend-expert) alembic 0068 — group_conversations + group_participants + group_messages
2. (bkend-expert) `app/services/websocket_manager.py` + `app/api/websocket.py`
3. (bkend-expert) `app/api/group_conversations.py` + conversations.py presign 확장
4. (bkend-expert) alembic 0069 — dm_messages 첨부파일 컬럼
5. (bkend-expert) 백엔드 테스트 (1~20번)
6. (frontend-architect) WS 훅 + 그룹 DM 컴포넌트 + 첨부파일 UI
7. (frontend-architect) i18n 5 locale 추가
8. (공동) smoke test + AC 체크리스트 검증

---

## 10. 의존성 및 위험 관리

### 신규 의존성

| 패키지 | 용도 | 기존 사용 여부 |
|--------|------|:------------:|
| `fastapi[websockets]` | WebSocket 지원 | FastAPI 기본 포함 (확인 필요) |
| `websockets` | FastAPI WS 내부 | 별도 설치 필요 가능성 |
| `redis` (aioredis) | WS pub/sub | G''-2에서 이미 사용 중 |

`websockets` 패키지가 requirements.txt에 없을 경우 추가 필요. fastapi의 WebSocket 지원은 `uvicorn[standard]`에 포함된 경우가 많아 확인 후 추가.

### 위험 항목

| 위험 | 확률 | 대응 |
|------|:----:|------|
| WS 다중 인스턴스 broadcast 누락 | 중 | Redis pub/sub (G''-2 booster 활용), 개발 단계는 in-memory |
| 이미지 첨부 모더레이션 지연 | 중 | 비동기 처리 — 즉시 표시 후 백그라운드 admin 큐 연동 |
| Group DM 스팸 | 중 | 5 msg/min/user/group rate limit + report 기능 |
| presign URL 만료 후 전송 시도 | 저 | 클라이언트 15분 내 업로드 유도 (UI 타이머 표시) |
| 0068 downgrade 시 데이터 손실 | 저 | 그룹 메시지 먼저 삭제 후 테이블 drop (순서 명시) |

---

## 11. 완료 기준 요약

| 항목 | 기준 |
|------|------|
| alembic | 0068 + 0069 upgrade/downgrade green |
| 백엔드 테스트 | 20개 신규, 기존 회귀 0건 |
| WebSocket | WS 연결 + broadcast 단위 테스트 통과 |
| 첨부파일 | presign + 메시지 전송 + MIME 검증 통합 테스트 통과 |
| 프론트엔드 | 5개 컴포넌트/훅 테스트 통과 |
| i18n | 5 locale × 22 키 = 110 entries 완성 |
| AC 체크리스트 | §1의 13개 항목 전체 충족 |
