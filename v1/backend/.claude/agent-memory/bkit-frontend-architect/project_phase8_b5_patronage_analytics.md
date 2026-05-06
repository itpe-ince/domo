---
name: Phase 8 B'-5 Patronage Analytics Dashboard
description: B'-5 완료: 5 chart components + 1 hook + 75 i18n keys + 5 tests + B-2 dashboard booster; tsc 0 (pre-existing errors excluded)
type: project
---

B'-5 patronage-analytics-dashboard 완료.

**Why:** Phase 8 B'-5 task — artist patronage dashboard에 PostHog/self-aggregated analytics metrics 통합, mock fallback 포함.

**How to apply:** 추가 analytics metric이나 PostHog event를 연동할 때 usePatronageAnalytics hook 확장하고 MOCK_ANALYTICS에도 반영.

## 신규 파일

- `src/components/patronage/CohortRetentionChart.tsx` — D1/D7/D30 SVG 3-line chart
- `src/components/patronage/CouponRedemptionStats.tsx` — winback coupon donut chart
- `src/components/patronage/NewsletterStats.tsx` — newsletter open/click bar chart
- `src/components/patronage/ConversionFunnel.tsx` — 4-step sponsorship funnel SVG
- `src/components/patronage/DmEngagementCard.tsx` — B'-2 booster 3-metric card
- `src/lib/hooks/usePatronageAnalytics.ts` — GET /v1/me/patronage/analytics + mock fallback

## 수정 파일

- `src/app/me/patronage/page.tsx` — analytics section 추가 (6 components + usePatronageAnalytics)
- `src/lib/api.ts` — PatronageAnalyticsResponse type + fetchPatronageAnalytics() 추가
- 5 locale i18n files — `patronage.analytics.*` 15 keys × 5 = 75 entries

## 테스트

- `src/__tests__/patronage/CohortRetentionChart.test.tsx`
- `src/__tests__/patronage/CouponRedemptionStats.test.tsx`
- `src/__tests__/patronage/ConversionFunnel.test.tsx`
- `src/__tests__/patronage/NewsletterStats.test.tsx`
- `src/__tests__/patronage/DmEngagementCard.test.tsx`

## Mock 모드

- `NEXT_PUBLIC_POSTHOG_KEY` 미설정 시 → 즉시 MOCK_ANALYTICS 반환
- API 404 시 → dev 환경 mock fallback, prod 환경 error 표시
- 모든 chart component에 `isMock=true` prop + "sample data" badge 표시

## 기존 오류 (pre-existing, B'-5 무관)

- `icons.tsx`: MessageCircleIcon 중복 선언
- `ExpiryBanner.tsx`: expiry_banner_renew_success type mismatch
