---
name: Phase 6 A-8 Retention Loop Enhancement
description: A-8 완료: subscription expiry cron, alembic 0048, ExpiryBanner, WinbackBanner B-5 booster, 5 PostHog events, 5 locale i18n, 7 new backend tests
type: project
---

Phase 6 A-8 retention-loop-enhancement 완료 (2026-05-04). Phase 6 A 단계 마지막 sub-PDCA.

**Why:** B-5 carry-over (후원 만료 알림) + WinbackBanner cancellation_reason 강화 → 구독 재활성화 retention loop 완성.

**How to apply:** Phase 7 시작 시 이 PDCA가 baseline. 이후 email digest, Stripe 자동 갱신, AI 개인화 메시지는 carry-over.

## Backend 구현

- `alembic/versions/0048_subscription_expiry_notif.py` — Subscription.expiry_notified_at 컬럼 + partial index WHERE expiry_notified_at IS NULL AND status='active'. down_revision=0047_artist_index.
- `app/models/sponsorship.py` — Subscription에 expiry_notified_at: Mapped[datetime | None] 추가
- `app/services/subscription_expiry_jobs.py` — R-5 격리 cron. 1h interval. notify_expiring_subscriptions_once() + subscription_expiry_cron_loop(). idempotent: expiry_notified_at stamp으로 중복 방지.
- `app/core/metrics.py` — domo_subscription_expiry_notif_total{result} + domo_subscription_expiring_count{window_days} Counter 추가
- `app/main.py` — subscription_expiry_cron_loop lifespan 등록 (interval=3600s)
- `tests/unit/test_subscription_expiry_jobs.py` — 7 tests (no-op, eligible, already-notified, cancelled, days_left body, multiple subs, metrics import)

## Frontend 구현

- `lib/hooks/useExpiryBanner.ts` (신규) — 7d cooldown localStorage. SSR-safe. useWinbackBanner 패턴 미러.
- `components/sponsorships/ExpiryBanner.tsx` (신규) — amber 색상 배너. PostHog 3 events. "잊기" dismiss 7d cooldown.
- `components/sponsorships/WinbackBanner.tsx` (수정) — cancellationReason prop 추가 (optional). getSubtitle() conditional message (too_expensive→coupon hint, not_satisfied→new series prompt). PostHog 2 events (view + resubscribe_click).
- `lib/analytics/events.ts` (수정) — 5 신규 events: ExpiryBannerView, ExpiryBannerRenewClick, ExpiryBannerDismiss, WinbackBannerView, WinbackBannerResubscribeClick
- `lib/api.ts` (수정) — SubscriptionView에 cancellation_reason 필드 추가
- `app/me/sponsorships/page.tsx` (수정) — useExpiryBanner 통합, ExpiryBanner 렌더링 (active subs only)
- `i18n/{ko,en,ja,zh,es}.json` — retention.expiry.banner.* (4 keys) + retention.winback.conditional.* (2 keys) × 5 locale = 30 entries

## i18n 키 목록 (A-8 신규, per locale)

- retention.expiry.banner.title ("D-{{days}}일 후 만료됩니다" pattern)
- retention.expiry.banner.subtitle
- retention.expiry.banner.renewCta
- retention.expiry.banner.dismiss
- retention.winback.conditional.tooExpensive
- retention.winback.conditional.notSatisfied

## PostHog Funnel 구성

subscription_expiring(notification) → expiry_banner_view → expiry_banner_renew_click → renew complete
(또는) winback_banner_view → winback_banner_resubscribe_click → sponsor_success

## Carry-over → Phase 7+

- Email digest 실제 발송: D-4 push/email PDCA
- Push notification: D-4 carry-over
- Stripe 자동 갱신 deep integration: Phase 7+ (현재 ExpiryBanner renewCta는 /users/{artistId} 링크만)
- AI 개인화 메시지: Phase 7+ LLM PDCA
- A/B 테스트 (retention metric): Phase 7+

## 테스트 기대값

- Baseline 191 + 신규 7 = 198+ expected
- tsc 0 errors (optional props만 추가, 기존 시그니처 유지)
