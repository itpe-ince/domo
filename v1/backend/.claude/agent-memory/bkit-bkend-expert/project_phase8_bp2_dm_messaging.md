---
name: Phase 8 B'-2 DM Messaging
description: B'-2 완료: alembic 0063, 9 endpoints(8+1 admin), 11 tests, 75 i18n, Notification.type=dm_received, polling model
type: project
---

B'-2 dm-messaging 완료 (Phase 8). 기준선 382 tests + alembic 0062 기반.

**Why:** OQ-7=A (1:1 DM only, Group은 Phase 9+ P3-1). WebSocket은 Phase 9+ — 현재 polling (5s message, 10s conv list).

**How to apply:** DM 관련 기능 수정 시 이 패턴 참고.

## 신규 파일

### Backend
- `alembic/versions/0063_dm_messaging.py` — dm_conversations + dm_messages 테이블, 인덱스 5개
- `app/models/dm.py` — DMConversation, DMMessage SQLAlchemy models
- `app/schemas/dm.py` — StartConversationRequest, SendMessageRequest, EditMessageRequest, ReportConversationRequest
- `app/api/conversations.py` — 8 user endpoints + 1 admin endpoint (admin_router 분리)
- `tests/integration/test_dm_messaging.py` — 11 tests (8 integration + 3 unit)

### Frontend
- `src/app/me/messages/page.tsx` — conversation list page
- `src/app/me/messages/[id]/page.tsx` — single conversation page (polling 5s)
- `src/components/messaging/ConversationList.tsx`
- `src/components/messaging/MessageBubble.tsx` — edit/delete within 5min window
- `src/components/messaging/MessageComposer.tsx` — Enter to send, Shift+Enter newline, auto-resize
- `src/lib/hooks/useConversations.ts` — polling 10s + visibility API

## 수정 파일

### Backend
- `app/models/__init__.py` — DMConversation, DMMessage 추가
- `app/core/rate_limit.py` — dm_send: 60/min/user 추가
- `app/main.py` — conversations_router + admin_router 등록

### Frontend
- `src/lib/api.ts` — ConversationView, MessageView types + 8 API functions
- `src/components/icons.tsx` — SendIcon, MessageCircleIcon 추가
- `src/components/Sidebar.tsx` — nav.messages → /me/messages 추가
- `src/app/notifications/page.tsx` — dm_received → SendIcon 처리
- `src/i18n/{ko,en,ja,zh,es}.json` — messaging.* 15키 × 5 locale = 75 entries

## 핵심 설계

- Conversation pair normalise: user_a_id < user_b_id (UUID lexicographic) → UNIQUE constraint
- HTML sanitise: stdlib re + html.unescape (bleach 불필요 — plain text only)
- Edit window: 5분 이내만 PATCH 허용
- Soft delete: deleted_at nullable → body를 [deleted] sentinel로 교체
- Notification: dm_received type → Notification 모델 재사용 (D-4 통합)
- Admin close: closed_by_admin_at 설정 → 이후 send 403
- Rate limit scope: dm_send (60/min/user)
