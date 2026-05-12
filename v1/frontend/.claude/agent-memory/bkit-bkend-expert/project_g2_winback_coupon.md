---
name: G'-2 winback-coupon-endpoint
description: Phase 7 G'-2 implementation: POST /subscriptions/{id}/winback-coupon endpoint + CancelSubscriptionModal real endpoint integration
type: project
---

G'-2 winback-coupon-endpoint is implemented (2026-05-04). Builds on D'-3 CouponProvider abstraction.

**Why:** Phase 5 B-5 shipped with "준비 중" badge placeholder for winback offers. G'-2 implements the real endpoint.

**Reason → Coupon mapping:**
- too_expensive → percent_off=50, repeating, 1 month
- changed_mind → percent_off=30, repeating, 1 month
- not_satisfied → percent_off=20, repeating, 1 month + DM link placeholder (Phase 8+ carry-over)
- other → percent_off=10, once

**Backend files changed:**
- `/v1/backend/app/api/sponsorships.py` — `apply_winback_coupon` endpoint added after `my_subscriptions`
- `/v1/backend/app/schemas/coupon.py` — WinbackCouponRequest + WinbackCouponResponse schemas
- `/v1/backend/app/services/payments/coupon.py` — `create_winback_coupon()` helper + `_WINBACK_SPEC` + `winback_dm_link()`
- `/v1/backend/app/core/rate_limit.py` — `winback_coupon` 1/day/user (86400s window)
- `/v1/backend/app/services/payments/webhook_handlers.py` — Phase 8+ auto-winback placeholder comment
- `/v1/backend/tests/integration/test_winback_coupon.py` — 8 new integration tests

**Frontend files changed:**
- `/v1/frontend/src/lib/api.ts` — `applyWinbackCoupon()`, `WinbackReason`, `WinbackCouponResponse` types
- `/v1/frontend/src/lib/analytics/events.ts` — 3 new events: `winback_coupon_offered`, `winback_coupon_accepted`, `winback_coupon_declined`
- `/v1/frontend/src/components/sponsorships/CancelSubscriptionModal.tsx` — real endpoint integration replaces "준비 중" badge
- `/v1/frontend/src/components/sponsorships/WinbackSuccessModal.tsx` — NEW, z-[70] success modal
- `/v1/frontend/src/i18n/{ko,en,ja,zh,es}.json` — `retention.winback.success.*` + `retention.winback.offer.*` (~10 keys × 5 locales)

**Idempotency:** DB-level check `AppliedCoupon WHERE subscription_id=X AND applied_at > 24h ago` → 409 on duplicate.
Rate limit is a second layer (Redis-based, 1/day/user).

**Carry-over confirmed to Phase 8+:**
- DM messaging infra (not_satisfied 작가 직접 메시지): `dm_link` returns null, placeholder UI shown
- Stripe webhook → winback 자동화 (subscription.deleted 후 auto-issue): TODO comment in webhook_handlers.py
- Coupon stacking prevention: not implemented, Phase 8+ rule engine

**How to apply:** When working on Phase 8+ DM messaging or auto-winback, look at `winback_dm_link()` in coupon.py and the TODO in `handle_subscription_deleted` in webhook_handlers.py.
