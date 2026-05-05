# PostHog Analytics — Setup Guide & Funnel Definitions

> **A-1 Analytics Foundation** — 2026-05-04

## 1. PostHog 프로젝트 설정

### 1.1 계정 생성 & 프로젝트 API Key 발급

1. [app.posthog.com](https://app.posthog.com) 가입 (US Cloud — GDPR EU 데이터 우려 시 EU Cloud: `eu.i.posthog.com`)
2. New Project 생성 — "Domo Production" / "Domo Staging"
3. **Project Settings > Project API Key** 복사 (`phc_...`)
4. Frontend `.env.production` 에 추가:
   ```
   NEXT_PUBLIC_POSTHOG_KEY=phc_your_key
   NEXT_PUBLIC_POSTHOG_HOST=https://us.i.posthog.com
   ```

### 1.2 Self-hosted 옵션 (동남아/남미 GDPR 친화)

PostHog 오픈소스를 자체 서버에 배포:
- Docker Compose: [posthog.com/docs/self-host](https://posthog.com/docs/self-host)
- 배포 완료 후 `NEXT_PUBLIC_POSTHOG_HOST=https://analytics.domo.example.com` 으로 변경
- 자체 호스팅 시 EU 데이터 규정 완전 준수 + GDPR 관련 법적 리스크 최소화

### 1.3 SDK 설정 (A-1 코드 기준)

- `opt_out_capturing_by_default: true` — 사용자 동의 전 capture 0
- `autocapture: false` — 명시적 이벤트만 (DOM 자동 캡처 비활성)
- `capture_pageview: false` — 수동 pageview (A-2에서 추가 예정)
- `persistence: "localStorage"` — 쿠키 동의 전 PostHog 쿠키 미생성

---

## 2. 핵심 이벤트 스키마

A-1에서 구현된 이벤트 (모두 `lib/analytics/events.ts`에 TypeScript 타입 정의됨):

| 이벤트 | 트리거 | 핵심 Properties |
|--------|--------|----------------|
| `signup` | 신규 가입 완료 | `method: "google"\|"email"\|"kakao"` |
| `login` | 로그인 성공 (LoginModal) | `method: "google"` |
| `logout` | 로그아웃 (Sidebar) | — |
| `first_action` | 첫 팔로우/후원/포스트/좋아요/댓글 | `action: "post"\|"follow"\|"like"\|"comment"\|"sponsor"` |
| `sponsor_start` | BluebirdModal Step 1 → Next 클릭 | `mode`, `amount_cents`, `artist_id` |
| `sponsor_success` | BluebirdModal Step 5 성공 | `mode`, `amount_cents`, `artist_id` |
| `sponsor_cancel` | CancelSubscriptionModal 확인 | `reason`, `tier` |
| `explore_view` | explore 페이지 진입 | `tab` |
| `search` | 검색 실행 완료 | `query`, `results_count` |
| `post_click` | PostCard 클릭 | `post_id`, `source: "feed"\|"explore"\|"search"\|"profile"` |
| `like` | 좋아요 | `post_id` |
| `comment` | 댓글 | `post_id` |
| `follow` | 팔로우 | `artist_id` |
| `feed_scroll_depth` | 스크롤 깊이 측정 | `depth_pct` |

---

## 3. Funnel 정의 (PostHog UI에서 직접 생성)

### 3.1 Onboarding Funnel — "가입 → 첫 액션"

**목적**: 가입 후 7일 내 첫 액션 전환율 측정 (A-2 KPI 핵심)

**PostHog Funnel 설정**:
1. Insights > + New Insight > Funnel
2. 이름: `Onboarding Funnel (7-day)`
3. Steps:
   - Step 1: `signup`
   - Step 2: `first_action` (any action type)
   - Step 3: `follow` (artist_id 있음)
   - Step 4: `sponsor_success` (첫 후원)
4. Conversion window: **7 days**
5. Save to Dashboard: "Growth Funnel"

**KPI 목표**: signup → first_action ≥ 50%, signup → sponsor_success ≥ 3% (90일 목표)

---

### 3.2 Sponsorship Funnel — "포스트 발견 → 후원 성공"

**목적**: 작가 발견 → 후원 전환 경로 분석

**PostHog Funnel 설정**:
1. Insights > + New Insight > Funnel
2. 이름: `Sponsorship Funnel`
3. Steps:
   - Step 1: `post_click`
   - Step 2: `sponsor_start`
   - Step 3: `sponsor_success`
4. Conversion window: **3 days**

**KPI 목표**: post_click → sponsor_success ≥ 2%

---

### 3.3 Retention Cohort — "D1/D7/D14/D30"

**목적**: 가입 후 일별 리텐션 측정 (A-8 Retention Loop 기준선)

**PostHog Retention 설정**:
1. Insights > + New Insight > Retention
2. 이름: `Signup Retention Cohort`
3. Starting event: `signup`
4. Return event: Any event (activity = DAU 대리지표)
5. Retention period: Weekly (D7/D14/D21/D28)

**KPI 목표**: D7 retention ≥ 25% (90일 목표)

---

### 3.4 Search Conversion Funnel — "검색 → 팔로우"

**목적**: 검색 → 작가 발견 → 팔로우 전환 (A-5 Search Enhancement 기준선)

**PostHog Funnel 설정**:
1. Insights > + New Insight > Funnel
2. 이름: `Search → Follow Conversion`
3. Steps:
   - Step 1: `search` (results_count > 0 필터 권장)
   - Step 2: `post_click` (source = "search")
   - Step 3: `follow`
4. Conversion window: **1 day**

**KPI 목표**: search → follow ≥ 10%

---

## 4. Dashboard 구성 권장

PostHog > Dashboards > + New Dashboard > "Domo Growth KPIs"

| 위젯 | 타입 | 기준 |
|------|------|------|
| DAU/WAU/MAU | Trend | 전체 이벤트 unique users |
| 가입 수 | Trend | `signup` |
| Onboarding Funnel | Funnel | §3.1 |
| Sponsorship Funnel | Funnel | §3.2 |
| D7 Retention | Retention | §3.3 |
| 후원 취소 사유 | Table | `sponsor_cancel.reason` breakdown |
| 탐색 탭 분포 | Bar | `explore_view.tab` breakdown |

---

## 5. GDPR 준수 체크리스트

- [x] `opt_out_capturing_by_default: true` — 동의 전 capture 0
- [x] CookieConsentBanner — Accept all 클릭 시 `opt_in_capturing()`
- [x] `/me/settings/privacy` — 언제든 opt-out 가능 (GDPR Art. 7)
- [x] `autocapture: false` — 명시적 이벤트만 (DOM 스크래핑 없음)
- [x] `persistence: "localStorage"` — 동의 전 쿠키 미생성
- [x] IP 익명화 — PostHog Cloud 기본값 (self-hosted 시 별도 설정 필요)
- [ ] EU Cloud / self-hosted — 동남아/남미 운영 시 데이터 주권 검토
- [ ] Data retention policy — PostHog > Settings > Data retention (30일 권장 초기)
- [ ] GDPR Data Deletion — PostHog > Settings > Users API 활용 (탈퇴 시 자동 삭제 연동 필요)

---

## 6. KPI Baseline 측정 시작 시점

A-1 배포 직후 PostHog에 첫 이벤트 유입 시 자동으로 baseline 측정 시작.

| KPI | 측정 시작 | 30일 목표 | 90일 목표 |
|-----|----------|:--------:|:--------:|
| DAU/WAU/MAU | A-1 배포 직후 | 측정 시작 | DAU/MAU ≥ 20% |
| first-week retention | A-1 배포 직후 | 측정 시작 | ≥ 25% (D7) |
| sponsor_start → sponsor_success | A-1 배포 직후 | 측정 시작 | ≥ 60% (단계 전환) |
| signup → sponsor_success | A-1 배포 직후 | 측정 시작 | ≥ 3% (전체 전환) |
| search → follow | A-1 배포 직후 | 측정 시작 | ≥ 10% |

---

## 7. Feature Flag 설정 (A-3 Feed Algorithm A/B)

A-3 진행 시 PostHog에서 feature flag 생성:

1. PostHog > Feature Flags > + New Feature Flag
2. 이름: `feed-algorithm-v2`
3. Type: Boolean (A/B) 또는 Multivariate (제어군/실험군)
4. Rollout: 50% (user_id hash 기반 — 동일 사용자 일관 버킷)
5. Frontend: `isFeatureEnabled("feed-algorithm-v2")` — `lib/analytics/featureFlags.ts`

**Frontend 사용 예시**:
```typescript
import { isFeatureEnabled } from "@/lib/analytics/featureFlags";

const useNewFeed = isFeatureEnabled("feed-algorithm-v2");
// useNewFeed가 true면 personalized feed API 호출
```
