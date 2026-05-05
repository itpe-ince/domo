---
name: Phase 7 G'-1 Stripe Webhook Extension
description: G'-1 구현 완료 현황 — webhook handler 아키텍처, 신규/수정 파일 목록, alembic 결정
type: project
---

G'-1 stripe-webhook-extension 구현 완료 (2026-05-04).

**Why:** D'-6 deferred — Stripe webhook handler가 Phase 6까지 미구현 상태. G'-2 winback-coupon의 critical path dependency.

**How to apply:** G'-2 구현 시 `app/services/payments/webhook_handlers.py`의 HANDLERS dict에 `customer.subscription.updated` 또는 winback 관련 이벤트 핸들러 추가만 하면 됨.

신규 파일:
- `v1/backend/app/services/payments/webhook_handlers.py` — 9개 순수 핸들러 함수 + HANDLERS dispatch table
- `v1/backend/tests/integration/test_stripe_webhook.py` — 13 tests (207 baseline + 13 = 220+)

수정 파일:
- `v1/backend/app/api/webhooks.py` — 전면 재작성: `/stripe` (신규 primary) + `/payments` (legacy alias), _verify_stripe_signature, _process_event
- `v1/backend/app/core/metrics.py` — webhook_received_total, webhook_duration_seconds, webhook_idempotent_skip_total 추가
- `v1/frontend/src/components/sponsorships/SubscriptionCard.tsx` — past_due amber banner 추가
- `v1/frontend/src/i18n/{ko,en,ja,zh,es}.json` — webhook.notification.* 7 keys × 5 locales = 35 entries

alembic: 불필요 — WebhookEvent 모델 (id PK, type, payload, processed_at server_default) 기존으로 충분.

WebhookEvent 모델 위치: `v1/backend/app/models/webhook_event.py`
webhook_cleanup_jobs.py: 90d 보관 정책 cron — 무수정 유지.
