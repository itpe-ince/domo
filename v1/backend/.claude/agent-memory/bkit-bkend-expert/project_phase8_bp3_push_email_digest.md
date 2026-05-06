---
name: Phase 8 B'-3 Push Email Digest Foundation
description: B'-3 완료: alembic 0064, FCM+APNs Mock, push_notifier, email_digest 10th cron, 4 endpoints, 15 tests, 75 i18n
type: project
---

B'-3 push-email-digest-foundation 완료 (2026-05-04).

**Why:** Phase 8 B' 트랙 — 사용자 인게이지먼트 강화. FCM/APNs 푸시 + 이메일 다이제스트 기반 구축.

**How to apply:** 다음 push/email 관련 작업 시 이 기반 위에 구축. Phase 9+ Mobile PDCA에서 실제 FCM service worker 연결.

## 핵심 파일

### 신규
- `alembic/versions/0064_push_tokens.py` — device_tokens + notification_preferences 테이블, down_revision=0063_dm_messaging
- `app/models/device_token.py` — DeviceToken (soft-delete, platform Enum fcm|apns)
- `app/models/notification_preferences.py` — GDPR default=False, push/email_per_type JSONB
- `app/services/push/__init__.py` — 패키지 init
- `app/services/push/firebase.py` — FCMService lazy init + Mock fallback, singleton fcm_service
- `app/services/push/apns.py` — APNsService JWT ES256 + aiohttp + Mock fallback, singleton apns_service
- `app/services/push_notifier.py` — PushNotifier (preferences check → GDPR gate → device dispatch), singleton push_notifier
- `app/services/email_digest_jobs.py` — 10th R-5 cron worker, 1h interval, digest frequency weekly/biweekly/monthly/never
- `app/api/me_devices.py` — 5 endpoints (POST /me/devices, DELETE /me/devices/{id}, GET/PATCH /me/notifications/preferences, POST /me/test-push)
- `tests/integration/test_push_device_endpoints.py` — 10 integration tests
- `tests/unit/test_push_services.py` — 5 unit tests
- `frontend/src/app/me/notifications/preferences/page.tsx` — Toggle + SectionCard UI, GDPR compliant
- `frontend/src/lib/hooks/useDeviceRegistration.ts` — 안정적 device_id, placeholder token (Phase 9+에서 실제 FCM SDK로 교체)

### 수정
- `app/main.py` — me_devices 라우터 등록, email_digest_task 10th cron 등록 (all_tasks 포함)
- `app/core/config.py` — firebase_credentials_json, apns_* 설정 추가
- `app/models/__init__.py` — DeviceToken, NotificationPreferences 등록
- `app/services/subscription_expiry_jobs.py` — push_notifier 호출 (R-5: 별도 AsyncSessionLocal)
- `app/services/newsletter_jobs.py` — push_notifier 호출 (R-5: 별도 AsyncSessionLocal)
- `app/services/auction_promotion_jobs.py` — push_notifier 호출 (post-commit, same session OK)
- `frontend/src/lib/api.ts` — NotificationPreferencesView, DeviceTokenView, 4 API 함수 추가
- 5개 i18n 파일 (ko/en/ja/zh/es) — notifications.preferences.* 15키 × 5 = 75 entries

## 주요 설계 결정

- **GDPR default off**: push_enabled=False, email_enabled=False server_default. GET prefs에서 row 없으면 in-memory default 반환 (DB 저장 안 함, 첫 PATCH 시 upsert)
- **R-5 push isolation**: 기존 cron worker에서 push 호출 시 별도 AsyncSessionLocal 사용 → cron 자체 commit flow와 분리
- **Digest frequency tracking**: email_per_type["_last_digest_sent"] ISO timestamp 내부 키로 추적
- **Token deduplication**: (user_id, device_id) 우선 upsert → token string 중복 체크 → 신규 생성
- **10th cron worker confirm**: email_digest_cron_loop이 10번째, 11번째는 auto_renewal (B'-4)
- **Phase 8 web token**: localStorage device_id + placeholder "web-{id}" token. Phase 9+에서 실제 FCM service worker 연결

## 알림 타입 → 카테고리 매핑 (_TYPE_TO_CATEGORY)
auction_ending_* | auction_ended | auction_outbid | auction_won | auction_lost → auction
sponsor_received | sponsor_milestone | subscription_* → sponsorship
like | comment | reply | follow | mention → engagement
system | announcement | artist_approved | artist_rejected | warning_issued | tier_release → system
email_digest → digest
