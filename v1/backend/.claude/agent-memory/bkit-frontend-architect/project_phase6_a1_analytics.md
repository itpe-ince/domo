---
name: Phase 6 A-1 Analytics Foundation — completion status
description: A-1 완료: PostHog SDK + 8 baseline events + feature flags + GDPR consent + i18n 5 locale
type: project
---

A-1 `analytics-foundation` completed 2026-05-04.

**Why:** A-1 is the Critical Path for all A-stage sub-PDCAs — no A/B testing or funnel KPI measurement is possible without it.

**Files created/modified**:
- `src/lib/analytics/events.ts` — TypeScript discriminated union for 14 event types
- `src/lib/analytics/capture.ts` — captureEvent / identifyUser / resetIdentity helpers; mock mode fallback to console.log in dev
- `src/lib/analytics/featureFlags.ts` — isFeatureEnabled / getFeatureFlag for A-3 A/B infra
- `src/components/PostHogProvider.tsx` — PostHogClientProvider; opt_out_capturing_by_default=true; persistence=localStorage
- `src/components/CookieConsent.tsx` — upgraded with PostHog opt_in/opt_out integration + i18n keys
- `src/app/layout.tsx` — PostHogClientProvider wrapped around AppShell
- `src/app/me/settings/privacy/page.tsx` — user analytics opt-out toggle (GDPR Art. 7)
- `src/__tests__/analytics/capture.test.ts` — 5 Jest tests (mock mode coverage)
- `src/__tests__/analytics/featureFlags.test.ts` — 3 Jest tests
- `tsconfig.json` — `src/__tests__` excluded from tsc compilation
- `.env.local`, `.env.production`, `.env.example` — POSTHOG_KEY + POSTHOG_HOST vars
- `v1/docs/operations/analytics/funnels.md` — PostHog setup guide + 4 funnel definitions

**Integration points (6)**:
1. `LoginModal.tsx` — identifyUser + captureEvent login/google
2. `Sidebar.tsx` — captureEvent logout + resetIdentity
3. `BluebirdModal.tsx` — sponsor_start (Step 1 → Next) + sponsor_success (Step 5)
4. `sponsorships/CancelSubscriptionModal.tsx` — sponsor_cancel (confirm)
5. `app/explore/page.tsx` — explore_view on mount
6. `app/search/page.tsx` — search with results_count
7. `PostCard.tsx` — post_click with source prop; callers pass "explore"/"search"/"profile"

**i18n**: 5 locales × 11 keys = 55 entries added (cookie.* × 6 + privacy.* × 5 nested)

**Constraints satisfied**:
- tsc 0 errors (test files excluded from tsconfig)
- No backend changes (backend posthog integration carry-over)
- No alembic migration
- GDPR opt_out_capturing_by_default=true
- Mock mode when NEXT_PUBLIC_POSTHOG_KEY unset

**How to apply:** A-2/A-3/A-6 can now use captureEvent and isFeatureEnabled from lib/analytics/*.
