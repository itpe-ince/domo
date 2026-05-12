---
name: Phase 9 L-C DM Expansion
description: Phase 9 L-C 완료: alembic 0068+0069, Group DM 3테이블, WebSocket Manager, 9 endpoints, 23 tests
type: project
---

Phase 9 L-C — DM 확장 3종 (Group DM + WebSocket + File Attachment)

**Why:** Phase 8 B'-2 1:1 DM 위에서 그룹 대화(50인), 실시간 WS broadcast, 첨부파일 presign 완성

**How to apply:** 기존 dm_conversations/dm_messages 스키마 무변경, group_* 테이블 분리 원칙 유지

## alembic

- 0068_group_dm: group_conversations + group_participants + group_messages (3 테이블, 5 인덱스)
  - down_revision = "0067_external_content_tracking"
- 0069_dm_attachments: dm_messages에 attachment_url/type/size_bytes 컬럼 추가
  - down_revision = "0068_group_dm"

## 신규 파일

- `app/models/group_dm.py` — GroupConversation, GroupParticipant, GroupMessage 모델
- `app/services/websocket_manager.py` — ConnectionManager(in-memory) + RedisConnectionManager(pub/sub) + get_ws_manager() 팩토리
- `app/api/websocket_dm.py` — WS /ws/dm?token={jwt} 엔드포인트, 30초 heartbeat
- `app/api/group_conversations.py` — 9 endpoints (그룹 CRUD + presign)

## 변경 파일

- `app/core/rate_limit.py` — group_msg_send(5/min/user), group_create(10/hr/user) 추가
- `app/main.py` — group_conversations_router + websocket_dm_router 등록

## 엔드포인트 (9개)

- POST /me/messages/conversations/group — 그룹 생성 (creator=admin)
- GET /me/messages/conversations/group — 내 그룹 목록
- GET /me/messages/group/{id}/messages — 메시지 목록 (참여자만)
- POST /me/messages/group/{id}/messages — 전송 → WS broadcast (5/min rate limit)
- POST /me/messages/conversations/{id}/participants — 참여자 추가 (admin only)
- DELETE /me/messages/conversations/{id}/participants/{user_id} — 제거 (admin, left_at 소프트)
- PATCH /me/messages/conversations/{id} — 그룹명 변경 (admin only)
- POST /me/messages/{id}/attachment/presign — 1:1 DM 첨부 presign
- POST /me/messages/group/{id}/attachment/presign — 그룹 DM 첨부 presign
- WS /ws/dm?token= — JWT auth, user별 채널 구독

## 테스트

- `tests/unit/test_websocket_manager.py` — 13 tests (ConnectionManager + RedisConnectionManager)
- `tests/integration/test_group_dm_endpoints.py` — 14 tests
- `tests/unit/test_dm_attachment.py` — 9 tests (presign MIME/크기 검증)

## 주요 비즈니스 규칙

- 그룹 최대 50인, 참여자 추가/제거는 admin role 전용
- 참여자 제거: left_at 소프트 삭제 (메시지 히스토리 보존)
- REDIS_URL 없으면 in-memory fallback (단일 pod OK)
- 첨부파일: image/jpeg, png, gif, webp + application/pdf, 10MB 제한
- presign 만료: 900초(15분)
