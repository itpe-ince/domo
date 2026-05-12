---
template: plan
version: 1.0
feature: domo-phase6-roadmap
date: 2026-05-04
author: itpe-ince (Claude Sonnet 4.6)
project: domo
project_version: v1
parent_roadmap: Phase 6 (D': Carry-over Consolidation → A: Discovery & Growth Funnel)
status: Draft (Roadmap)
---

# Domo Phase 6 — 로드맵 (Master Plan)

> **Summary**: Phase 5 종결(12/12 sub-PDCA, 2026-05-04) 후 두 단계를 순차 진행한다. D': Carry-over Consolidation(1~2주, D'-1~D'-5 필수 + D'-6 선택) — Phase 5 종결 시 남은 carry-over 8개 청산 + Prometheus 배포 완성. A: Discovery & Growth Funnel(6~10주, A-1~A-8) — README 핵심 비전 "그로스해킹 깔때기"를 플랫폼으로 구현. analytics 기반 + onboarding 최적화 + 피드 알고리즘 + explore 큐레이션 + 검색 강화 + 글로벌 신진작가 인덱스 + 스토리텔링 허브 + retention loop. 총 12~13 sub-PDCA, 8~12주 계획.
>
> **Project**: domo (v1)
> **Author**: itpe-ince
> **Date**: 2026-05-04
> **Status**: Roadmap (Sub-PDCA 인덱스. 각 항목은 별도 plan 문서로 본격 진입)

---

## 0. Phase 6 배경 & 전략적 의미

### Phase 5 종결 성과

Phase 5는 12/12 sub-PDCA 100% 완료(2026-05-04). 주요 성과:

- **Blue Bird 후원 결제 인프라 완성**: Stripe SetupIntent + 5-step BluebirdModal + Mock 모드 fallback
- **작가/후원자 Dual Dashboard**: 수익 통계(SVG) + 후원자 목록 + Payout 요청 + 구독 history + tier benefits 시각화
- **Tier Benefits 커스터마이제이션**: alembic 0043 + ArtistTierBenefits JSONB + 플랫폼 default + 작가 override 하이브리드
- **Retention UX 5종**: thank-you + WinbackBanner(7d) + PostCard hover mini-button + ChurnList + 취소 사유 수집
- **Observability Baseline**: Prometheus 9 metrics + EXPLAIN ANALYZE 게이트 + observability.md 215L
- **누적 지표**: 77→147 passed (+70 tests) + tsc 0 + ~750+ 신규 i18n entries × 5 locales + 3 dashboard pages + ~20 components

### Phase 6가 중요한 이유

Phase 5까지는 "후원 인프라 완성" — 수익화 파이프라인의 하단 구조(작가 수익 + 후원자 전환)를 닫았다. 그러나 README 비전의 핵심인 **그로스해킹 깔때기**는 아직 구현되지 않았다.

README 비전 직접 인용:

> "유저들이 늘어나야 소비자들도 늘어남. 그로스해킹인가 이런 분석법 보면은 결국에는 깔대기 모양으로 사용자 층이 이만큼 있어야 맨 마지막에 소비자 층이 생기는 거임."

> "초기 작가들이 거래가 이루어지고 판매가 이루어지면 전 세계 아티스트들의 인덱스를 만들고 싶음"

> "히스토리를 두세 개 만든다고 치면 남미 페루에 사는 어떤 대학생 여자애가 그림을 하나 올려서 30만 원에 팔아보려고 했는데 … 히스토리를 유튜브도 만들겠지만 일간지라든지 라디오 같은 데서 풀 수 있음"

Phase 5 완료로 "사용자가 결제할 수 있는 플랫폼"은 완성됐다. Phase 6 목표는 "유저가 충분히 유입되고, 작가를 발견하고, 후원으로 전환되는 깔때기"를 완성하는 것이다. 이것이 진정한 그로스해킹 깔때기의 구현이다.

---

## 1. 비즈니스 컨텍스트

### 그로스해킹 깔때기 — Phase 6 구현 전략

```
[유입] 가입 → [발견] 작가 탐색 → [활성화] 첫 팔로우/후원 → [유지] retention loop → [수익화] 정기 구독
  A-2 Onboarding       A-3 Feed           A-2 Onboarding         A-8 Retention         Phase 5 ✅
  A-4 Explore          A-4 Explore         A-1 Analytics           A-5 Search
  A-5 Search           A-6 Artist Index    A-6 Index Badge
  A-6 Artist Index     A-7 Storytelling
```

이 깔때기의 각 단계는 A-1 Analytics Foundation 없이 측정 불가능하다. 따라서 A-1은 전체 A 단계의 선결 조건이며 Critical Path의 시작점이다.

### 신진작가 인덱스 — README 직접 비전

> "미국 아저씨가 하는 걸 하고 있는데 초기 작가들이 거래가 이루어지고 판매가 이루어지면 전 세계 아티스트들의 인덱스를 만들고 싶음"

Phase 6 A-6는 이 비전의 v1 구현이다. 거래량 + 활동도 + 후원자 수 기반 ranking 알고리즘 + 지역/장르 필터링 + 작가 프로필 ranking badge.

### 스토리텔링 허브 — 히스토리 만들기

> "히스토리를 유튜브도 만들겠지만 일간지라든지 라디오 같은 데서 풀 수 있음"

A-7 Storytelling Hub는 작가의 성장 히스토리(가입→첫 포스트→첫 후원→마일스톤)를 자동 타임라인으로 생성하고, 외부 공유 OG 이미지로 미디어/SNS 배포 가능하게 한다. 이것이 마케팅 훅의 기술적 토대다.

### Blue Bird 후원 — Phase 5 완료 + Phase 6 retention 강화

Phase 5에서 후원 결제 인프라(Stripe + Mock)와 retention UX(WinbackBanner + ChurnList)를 완성했다. Phase 6 A-2(onboarding에서 첫 후원 인센티브)와 A-8(retention loop 강화)이 Phase 5 기반 위에서 전환율과 유지율을 높인다.

---

## 2. Phase 6 Sub-PDCA 목록

### D' 단계 — Carry-over Consolidation (1~2주)

Phase 5 종결 시 carry-over로 명시된 항목 8개를 청산한다.

| # | Feature | 우선순위 | 추정 기간 | 병렬 가능 | 의존성 | 핵심 산출물 |
|---|---------|:-------:|:--------:|:--------:|--------|------------|
| D'-1 | `phase4-tech-debt-cleanup` | Must | ~3일 | D'-2, D'-4, D'-5와 병렬 | 없음 (독립) | POST_TIER_RESTRICTED 후원/구독 deeplink CTA UI + sponsor N일 옵션화(작가 setting 1d/7d/30d/lifetime) + home_feed.following SQL-only tier filter(perf 측정 후 2단계→SQL-only) + is_tier_locked viewer hint UI |
| D'-2 | `subscription-cancellation-tracking` | Must | ~1.5일 | D'-1, D'-4, D'-5와 병렬 | 없음 (독립) | alembic 0044 (Subscription +cancellation_reason +cancellation_feedback +cancelled_at) + cancel endpoint body 활용 + audit log SUBSCRIPTION_CANCELLED_WITH_REASON + 작가 dashboard ChurnList 실제 사유 표시 |
| D'-3 | `stripe-coupon-foundation` | Should | ~3일 | D'-1 완료 후 시작 권장 | 없음 (독립) | `app/services/payments/coupon.py` + `POST /v1/admin/coupons` + apply during create_subscription + 사용자 dashboard "할인 적용 중" 표시. B-5 win-back discount 실제 구현 기반 |
| D'-4 | `phase5-i18n-cleanup` | Must | ~1.5일 | D'-1, D'-2, D'-5와 병렬 | 없음 (독립) | es.json artist.* 26 keys 완성 + WCAG 2.1 AA color contrast manual audit + h1→h2→h3 hierarchy 검증 + AuctionShareCard aria-label '닫기' 추가(B-6 carry-over) + EditorWorkspace 'ko-KR' locale formatter(D-1 carry-over) |
| D'-5 | `prometheus-deployment` | Should | ~1일 | D'-1, D'-2, D'-4와 병렬 | 없음 (독립) | `prometheus-client` pip install 공식 문서화 + Grafana dashboard JSON sample + Alerting rules import 가이드 + production-ready /metrics token rotation policy + observability.md v0.2 |

**선택 D' sub-PDCA (사용자 추후 결정)**:

| # | Feature | 우선순위 | 추정 기간 | 비고 |
|---|---------|:-------:|:--------:|------|
| D'-6 | `stripe-webhook-extension` | Could | ~2일 | payment_intent.succeeded/failed/requires_action + invoice.payment_failed handler 확장. Phase 5 carry-over 명시. 별도 spec 정의 후 진행 권장 |

**D' 단계 병렬화 계획** (OQ-1 B 권장 기준):
```
병렬 그룹 A (Day 1~3): D'-1 + D'-2 + D'-4 + D'-5 동시 진행
순차 (Day 3~6):        D'-3 (D'-1 완료 후 — phase4 deeplink CTA 기반 필요)
선택 (Day 5~7):        D'-6 (병렬 가능, 사용자 결정 시)
```

**D' 완료 기준**: Phase 5 8개 carry-over 청산 + Phase 6 본체(A 단계) 진입 전 기술 부채 0

---

### A 단계 — Discovery & Growth Funnel (6~10주)

README 핵심 비전 "그로스해킹 깔때기" 직접 구현. A-1 Analytics Foundation은 모든 후속 A sub-PDCA의 측정 인프라이므로 Critical Path 시작점이다.

| # | Feature | 우선순위 | 추정 기간 | 의존성 | 핵심 산출물 |
|---|---------|:-------:|:--------:|--------|------------|
| A-1 | `analytics-foundation` | Must | ~3일 | D' 완료 | PostHog(권장) 또는 Amplitude SDK 도입 + event tracking baseline (signup / first-action / sponsor / cancel / churn / explore_view / search) + funnel dashboard 정의. **모든 후속 A sub-PDCAs의 선결 조건** |
| A-2 | `onboarding-funnel` | Must | ~5일 | A-1 ✅ | 가입 직후 추천 작가 5명 follow CTA + 첫 Bluebird 후원 인센티브(작가 thank-you 강조) + 첫 포스트 발견 hook + 가입 7일 후 retention metric 측정 endpoint |
| A-3 | `feed-algorithm-v1` | Must | ~7일 | A-1 ✅ | 현재 시간순 feed → personalized(팔로잉 우선 + 추천 + 트렌딩). SQL-only 단순 알고리즘(Phase 6). PostHog feature flag A/B 테스트 인프라 |
| A-4 | `explore-revamp` | Should | ~5일 | A-1 ✅ | 카테고리 탭(Trending / New Artists / By Region / By Genre / Pricing) + "오늘의 작가" hero card + A-6 ranking preview 섹션 |
| A-5 | `search-enhancement` | Should | ~5일 | A-1 ✅ | 작가명 + 작품명 + tag + genre fuzzy match + filter(price range / region / tier_only / 활성도) + search history(logged-in) + popular searches |
| A-6 | `artist-index-v1` | Must | ~7일 | A-1 ✅, A-4 권장 | 거래량 + 활동도 + 후원자 수 기반 weighted score cron worker + `/artists/index?region=&genre=` public ranking page + 작가 프로필 ranking badge(top 10/100/1000). **README "신진작가 인덱스" 직접 구현** |
| A-7 | `storytelling-hub` | Should | ~5일 | A-1 ✅, A-6 권장 | "Featured Artist" 월간/주간 큐레이션 + 작가 히스토리 timeline(가입→첫 포스트→첫 후원→마일스톤) + 외부 공유 OG 이미지(AuctionShareCard Pillow 패턴 재사용) + 마케팅 hook. **README "히스토리/유튜브/일간지/라디오" 출처** |
| A-8 | `retention-loop-enhancement` | Should | ~4일 | A-1 ✅, A-2 권장 | 후원 만료 7일 전 알림(재구독 prompt) + 작가 매주 활동 digest(이메일 옵트인) + "예전에 응원하던 작가" 활동 알림(WinbackBanner 강화) + retention metric A/B 테스트 |

**A 단계 실행 순서**:
```
A-1 (Analytics Foundation — Critical Path 시작, 선결 필수)
  ↓
A-2 + A-3 (병렬 — Onboarding Funnel + Feed Algorithm)
  ↓
A-4 + A-5 (병렬 — Explore Revamp + Search Enhancement)
  ↓
A-6 (Artist Index — A-4 Explore 통합 권장, A-1 필수)
  ↓
A-7 + A-8 (병렬 — Storytelling Hub + Retention Loop)
```

**A 완료 기준**: 7~8 sub-PDCAs 100% archived + funnel KPI baseline 측정 시작 + ranking 알고리즘 v1 production-ready

---

## 3. Open Questions

사용자 결정 필요 항목. **권장 기본값 표** — "권장대로" 한 번에 수락 시 즉시 D' 단계 진입 가능.

| ID | 질문 | 옵션 | 권장 default | 근거 |
|----|------|------|:------------:|------|
| OQ-1 | D' 진행 방식 | A: 5 sub-PDCAs 순차 / **B: 독립 병렬(D'-1+D'-2+D'-4+D'-5 동시, D'-3 이후)** / C: 우선순위 분리(D'-2+D'-3 first) | **B** | 병렬 가능 PDCA는 시간 절약 — Phase 5와 동일 패턴. D'-1~D'-5 대부분 독립적 |
| OQ-2 | D'-6 Stripe webhook 포함 여부 | A: D'에 포함 / **B: Phase 6.5 또는 carry-over 유지** / C: A 단계 진입 전 필수 | **B** | D' 1~2주 목표 — webhook은 별도 spec 필요. D'-1~D'-5 완료 후 판단 |
| OQ-3 | PostHog vs Amplitude 선택(A-1 핵심) | **A: PostHog(오픈소스 + self-hosted + feature flag 통합)** / B: Amplitude(SaaS 표준 + product analytics) / C: Mixpanel / D: GA4 + 자체 funnel | **A** | PostHog: feature flag(A/B 테스트) + 오픈소스(동남아/남미 self-host 옵션) + GDPR 자체 처리 가능. Phase 6 목표인 A/B 테스트(A-3 feed) 통합 우선 |
| OQ-4 | feed 알고리즘 v1 단순도 | **A: SQL-only(팔로잉 + 트렌딩 weighted score)** / B: ML 도입(collaborative filtering) / C: 하이브리드(SQL + 사용자 행동 score) | **A** | Phase 6 SQL-only — 데이터 축적 우선. ML은 Phase 7+ (데이터 50k+ 이벤트 후) |
| OQ-5 | ranking 알고리즘 score 방식 | A: 단순(lifetime sales + active sponsorships count) / **B: 가중치(recent_activity×0.5 + sales×0.3 + supporters×0.2 + tenure×0.1)** / C: 시장별 분리(region/genre 별도 score) | **B** | 신진작가 친화적 — recent activity 강조로 신규 작가가 초기 ranking에서 가시성 확보 가능. 단순 lifetime sales는 기존 작가 편향 |
| OQ-6 | storytelling 콘텐츠 생산 방식 | A: 작가 자율(timeline 자동 생성) / B: 플랫폼 큐레이션(월간 featured) / **C: 둘 다(작가 자율 timeline + 플랫폼 featured 월간 큐레이션)** | **C** | 작가 자율 timeline은 자동 생성으로 비용 0. 플랫폼 featured는 마케팅 훅. 두 레이어 병존이 리치 스토리텔링 |
| OQ-7 | multi-currency 처리(A 단계) | **A: USD lock 유지(Phase 6)** / B: KRW/USD 듀얼 / C: 4 currency(USD/KRW/EUR/JPY) | **A** | Phase 5 결정 유지. multi-currency는 Phase 6.5 또는 7 별도 PDCA (Stripe currency 분기 + FX risk 관리 필요) |
| OQ-8 | D' 시작 트리거 | **A: Phase 5 alembic 0043 적용 확인 후 즉시** / B: 사용자 결정 대기 / C: D'-1만 즉시 시작 후 나머지 sequential | **A** | Phase 5 마이그레이션(alembic upgrade head) 사용자 측 적용 확인 즉시 D' 시작. Phase 5와 동일 패턴(OQ-6=A) |
| OQ-9 | A 단계 KPI 목표 설정 방식 | A: 정량 정의("DAU +30%", "first-week retention 25%", "conversion 3%") / B: 정성 정의(NPS) / **C: 둘 다(정량 baseline + 정성 NPS 분기별)** | **C** | §8 KPI 표 기준. 정량 baseline은 A-1 Analytics 도입 직후 측정 시작. NPS는 분기별 수집 |
| OQ-10 | Phase 6 종료 기준 | A: 12+ sub-PDCAs 100% archived / **B: Phase 5 패턴(모든 sub-PDCAs archived)** / C: 추가 — funnel KPI baseline + ranking v1 production-ready | **B** | Phase 5와 동일 기준. sub-PDCAs 100% archived가 종결 기준. KPI baseline 측정은 AC에 추가 조건으로 명시 |

---

## 4. Acceptance Criteria (Phase 6 종료 기준)

| ID | 기준 | 검증 방법 |
|----|------|----------|
| AC-1 | D' 단계 5 sub-PDCAs 모두 archived | `.pdca-status.json` D'-1~D'-5 phase="archived" |
| AC-2 | Phase 5 carry-over 8개 청산 | §7 carry-over 매핑표 모두 ✅ |
| AC-3 | A 단계 7~8 sub-PDCAs 모두 archived | `.pdca-status.json` A-1~A-8 phase="archived" |
| AC-4 | 각 sub-PDCA Match Rate ≥ 90% (목표 ≥ 95%) | 개별 analysis.md matchRate 필드 |
| AC-5 | Analytics Foundation production-ready — PostHog(권장) SDK 통합 + 8개 baseline events 추적 | A-1 AC 목록 내 event tracking sandbox 검증 |
| AC-6 | Artist Index v1 production-ready — ranking cron worker 실행 + `/artists/index` 페이지 공개 | A-6 AC — 작가 ranking 데이터 1회 이상 생성 확인 |
| AC-7 | funnel KPI baseline 측정 시작 — signup → first-follow → first-sponsor 전환 funnel 데이터 수집 | A-1 PostHog funnel dashboard 정의 완료 |
| AC-8 | 5 locale(ko/en/ja/zh/es) i18n 100% — es.json artist.* 26 keys 포함 | D'-4 AC + B-6 패턴 — grep "[가-힣]" + locale parity |
| AC-9 | WCAG 2.1 AA — color contrast manual audit + h1→h2→h3 hierarchy 검증 완료 | D'-4 AC |
| AC-10 | tsc 0 에러, 147 → N tests passed (회귀 0) | CI pipeline 자동 |
| AC-11 | Prometheus /metrics production-ready — token rotation policy + Grafana dashboard JSON | D'-5 AC |

---

## 5. Risks & Mitigation

| Risk | 영향 | 가능성 | 완화 방안 |
|------|:----:|:------:|----------|
| **Analytics GDPR 준수** — PostHog/Amplitude EU 데이터 저장 규정 | High | High | PostHog self-hosted(EU server) 또는 EU cloud region 선택. IP anonymization default on. 사용자 동의 배너(GDPR consent) A-1 범위 내 구현 |
| **feed 알고리즘 cold-start** — 신규 사용자 팔로잉 0, 추천 대상 없음 | Medium | High | 신규 사용자 fallback: 트렌딩 + 지역별 top 작가 + 장르별 신규 작가. A-2 onboarding에서 5명 강제 follow CTA로 cold-start 단축 |
| **ranking 신진작가 친화 보장** — recent activity 가중치가 낮으면 기존 작가 편향 | High | Medium | OQ-5=B 가중치(recent_activity 0.5)로 신진작가 boosting. 작가 데뷔 6개월 이내 bonus score 검토. A-1 metrics으로 신진작가 가시성 모니터링 |
| **Stripe coupon abuse** — 쿠폰 코드 유출 + 반복 적용 | Medium | Medium | D'-3: coupon 1회 사용 제한(idempotent) + 작가별/사용자별 usage tracking + admin 만료 기능. Stripe built-in max_redemptions 활용 |
| **search 비용** — fuzzy search full-scan 시 DB 부하 | Medium | High | A-5: PostgreSQL tsvector + GIN index 우선(Phase 6). Elasticsearch는 Phase 7+. EXPLAIN ANALYZE 게이트(D'-5 observability)로 쿼리 비용 사전 검증 |
| **multi-region scale** — 동남아/남미 사용자 latency | Medium | Low | OQ-7=A Phase 6 USD 유지. CDN(Cloudflare/S3 presigned) 이미지/OG 카드 전송. DB replica는 Phase 7+ |
| **A/B 테스트 오염** — feed 알고리즘 A/B feature flag 누출 | Low | Medium | A-3: PostHog feature flag user-level hash(동일 사용자 일관 버킷). 테스트 기간 명시(2주 이상 통계 유의성) |
| **D' scope creep** — carry-over 청산 중 신규 작업 발견 | Medium | Medium | D' 각 sub-PDCA plan "Out of Scope" 섹션 필수. 신규 발견 항목은 A 단계 backlog 또는 Phase 6.5로 이관 |

---

## 6. Timeline & Milestones

```
Week 1~2 — D': Carry-over Consolidation
┌────────────────────────────────────────────────────────────────┐
│ Day 1~3 [병렬 A] D'-1 + D'-2 + D'-4 + D'-5                   │
│ Day 3~6 [순차]   D'-3 (D'-1 완료 후)                           │
│ Day 5~7 [선택]   D'-6 (사용자 결정 시)                         │
│ Milestone: D' 완료 — Phase 5 carry-over 청산 + 기술 부채 0 ✅  │
└────────────────────────────────────────────────────────────────┘

Week 3 — A-1: Analytics Foundation (Critical Path)
┌────────────────────────────────────────────────────────────────┐
│ Day 1~3  PostHog SDK 도입 + 8 baseline events + funnel 정의   │
│ Milestone: Analytics infra 완료 — A 단계 모든 KPI 측정 시작 ✅ │
└────────────────────────────────────────────────────────────────┘

Week 4~5 — A-2 + A-3: Onboarding + Feed Algorithm (병렬)
┌────────────────────────────────────────────────────────────────┐
│ A-2 Onboarding Funnel (5일) — 추천 작가 follow CTA + 첫 후원  │
│ A-3 Feed Algorithm v1 (7일) — SQL personalized + A/B 인프라   │
│ Milestone: 가입 → 발견 → 첫 액션 깔때기 기반 완성 ✅          │
└────────────────────────────────────────────────────────────────┘

Week 6~7 — A-4 + A-5: Explore + Search (병렬)
┌────────────────────────────────────────────────────────────────┐
│ A-4 Explore Revamp (5일) — 큐레이션 탭 + "오늘의 작가"        │
│ A-5 Search Enhancement (5일) — fuzzy + filter + history       │
│ Milestone: 발견 경로 다양화 ✅                                 │
└────────────────────────────────────────────────────────────────┘

Week 8~9 — A-6: Artist Index v1 (Critical Path)
┌────────────────────────────────────────────────────────────────┐
│ Day 1~7  ranking cron worker + /artists/index + badge          │
│ Milestone: 글로벌 신진작가 인덱스 v1 production-ready ✅       │
└────────────────────────────────────────────────────────────────┘

Week 10~11 — A-7 + A-8: Storytelling + Retention (병렬)
┌────────────────────────────────────────────────────────────────┐
│ A-7 Storytelling Hub (5일) — 작가 히스토리 + OG 이미지 공유  │
│ A-8 Retention Loop (4일) — 만료 알림 + digest + A/B 테스트   │
│ Milestone: 스토리텔링 마케팅 훅 + retention loop 완성 ✅      │
└────────────────────────────────────────────────────────────────┘

Week 12 — Phase 6 종결
┌────────────────────────────────────────────────────────────────┐
│ 전체 archive + KPI baseline 측정 확인 + Phase 7 backlog 정리  │
│ Milestone: Phase 6 종결 — 12~13/12~13 archived ✅             │
└────────────────────────────────────────────────────────────────┘
```

---

## 7. Dependencies & Carry-over Mapping

Phase 5 carry-over → D' sub-PDCAs 흡수 매핑:

| Carry-over 원본 | 출처 | D' sub-PDCA | 처리 내용 |
|----------------|------|:-----------:|----------|
| POST_TIER_RESTRICTED CTA UI (out-of-scope §F-12) | artist-tier-release #10 | **D'-1** | 후원/구독 deeplink CTA UI 구현 |
| sponsor N일 옵션화 (#10.1) | artist-tier-release #10 carry-over | **D'-1** | 작가 setting 1d/7d/30d/lifetime 선택 |
| home_feed.following SQL-only tier filter (#10.1) | artist-tier-release #10 carry-over | **D'-1** | 성능 측정 후 Python post-filter → SQL-only 전환 |
| is_tier_locked viewer hint UI (out-of-scope §F-12) | artist-tier-release #10 | **D'-1** | API field 기존 노출 → UI hint 구현 |
| alembic 0045 cancellation_reason + cancellation_feedback | B-5 patronage-retention-ux carry-over | **D'-2** | alembic 0044로 번호 재지정(0043 기준) + backend 팀 실제 마이그레이션 |
| Stripe coupon Phase 6+ | B-5 patronage-retention-ux carry-over | **D'-3** | win-back discount 실제 구현 인프라 |
| es.json artist.* 26 keys | B-6 patronage-i18n-a11y-audit carry-over | **D'-4** | Phase 6 i18n sprint 내 완성 |
| WCAG 2.1 AA color contrast manual audit | B-6 patronage-i18n-a11y-audit carry-over | **D'-4** | 수동 audit 실행 + 위반 항목 fix |
| h1→h2→h3 heading hierarchy 검증 | B-6 patronage-i18n-a11y-audit carry-over | **D'-4** | 전체 페이지 heading 구조 audit |
| AuctionShareCard aria-label '닫기' | B-6 patronage-i18n-a11y-audit carry-over | **D'-4** | common.close 키 적용 |
| EditorWorkspace 'ko-KR' locale formatter | D-1 carry-over (Phase 5) | **D'-4** | 예약 배지 locale-aware formatter 적용 |
| prometheus-client pip install + Grafana JSON | D-6 observability-monitoring-baseline carry-over | **D'-5** | 설치 문서화 + 운영 가이드 완성 |
| Stripe webhook handler 확장 | B-1 bluebird-sponsor-flow carry-over | **D'-6 (선택)** | payment_intent + invoice event handler |

---

## 8. 비즈니스 메트릭 (KPI)

Phase 6 완료 후 30일, 90일 기준 측정. A-1 PostHog Analytics 도입 직후 baseline 수집 시작.

| KPI | 측정 도구 | 30일 목표 | 90일 목표 |
|-----|----------|:---------:|:---------:|
| **DAU / WAU / MAU** | PostHog + DB | baseline 측정 시작 | DAU/MAU ≥ 20% (healthy app 기준) |
| **가입 후 first-week retention rate** | PostHog funnel | baseline 측정 시작 | ≥ 25% (day 7 기준) |
| **Bluebird 후원 conversion rate** | PostHog funnel + Stripe | baseline 측정 시작 | ≥ 3% (방문자 → 첫 후원) |
| **작가 first-week active rate** | PostHog + DB | baseline 측정 시작 | ≥ 40% (가입 후 7일 내 1 post 이상) |
| **feed engagement rate** | PostHog | baseline 측정 시작 | clicks per impression ≥ 5% |
| **search → 작가 발견 → follow conversion** | PostHog funnel | baseline 측정 시작 | search to follow ≥ 10% |
| **ranking 신진작가 가시성** | DB ranking cron | A-6 배포 후 측정 | top 100 중 신진작가(6개월 이내) 비율 ≥ 30% |
| **storytelling hub 외부 공유 클릭률** | PostHog + OG 이미지 조회 수 | A-7 배포 후 측정 | 공유 카드 클릭 → 가입 전환 ≥ 2% |
| **정기 구독 retention rate(3개월)** | Stripe + B-5 churn dashboard | 이미 측정 중 | ≥ 60% (Phase 5 목표 유지) |

**정성 KPI**:
- 작가 NPS (분기별 설문) — "이 플랫폼을 동료 작가에게 추천하겠습니까?"
- 후원자 NPS (분기별 설문) — "이 플랫폼에서 다시 후원하겠습니까?"

---

## 9. Out of Scope (Phase 7+)

Phase 6에서 명시적으로 제외. 이후 로드맵에서 처리.

| 항목 | 이유 | 예상 Phase |
|------|------|:----------:|
| **ML feed 알고리즘** (collaborative filtering, content-based) | 데이터 축적 필요 (50k+ events). Phase 6 SQL-only 우선 | Phase 7+ |
| **실시간 WebSocket** (알림 push, 경매 실시간 bid) | 인프라 비용 + 복잡도. SSE/polling으로 Phase 6 대응 | Phase 7+ |
| **multi-currency** (KRW/EUR/JPY) | Stripe currency 분기 + FX risk. Phase 6 USD 유지 | Phase 6.5+ |
| **모바일 앱** (React Native) | 웹 안정화 후. 현재 PWA로 임시 커버 | Phase 7+ |
| **P3-1 커뮤니티/그룹** | 별도 P3 roadmap. 유저 100+ 조건부 | P3 별도 |
| **editor-video-studio (ffmpeg)** | ffmpeg 인프라 결정 차단. 서버 vs wasm vs 외부 transcode | Phase 7+ |
| **real-auth** (실제 인증 시스템 전환) | 현재 Mock + 어댑터. 트래픽 확보 후 전환 | Phase 7+ |
| **DM messaging** | 비용 + 모더레이션 복잡도. 커뮤니티 P3 이후 | Phase 7+ |
| **artist-pricing-assist** (#9 deferred) | 거래 데이터 축적 필요. 현재 샘플 부족 | Phase 7+ (거래 50건+ 후) |
| **B2B 리포트** (갤러리/학교 파트너십) | 파트너십 체결 후. 현재 B2B 파이프라인 없음 | Phase 7+ |
| **OpenTelemetry 도입** | D-6 carry-over. 단계적 — Prometheus 안정화 후 | Phase 6.5+ |
| **외부 SNS 자동 포스팅** | 작가 수동 다운로드/공유 우선. 자동화는 법적 검토 필요 | Phase 7+ |

---

## 10. README 비즈니스 비전 매핑

| README 비전 | Phase 6 sub-PDCA | 구현 방식 |
|------------|:----------------:|----------|
| "그로스해킹 깔대기 — 사용자 층이 이만큼 있어야 소비자 층이 생김" | **A-1/A-2/A-8** | Analytics funnel + 가입 후 onboarding CTA + retention loop |
| "전 세계 아티스트들의 인덱스를 만들고 싶음" | **A-6** | weighted score ranking cron + /artists/index + badge |
| "히스토리 — 유튜브도 만들겠지만 일간지/라디오 같은 데서 풀 수 있음" | **A-7** | 작가 성장 타임라인 + 외부 공유 OG 이미지 + Featured Artist 큐레이션 |
| "블루버드 후원 — 돈의 흐름이 원활해질 수 있고 공공의 이익" | Phase 5 완료 ✅ + **A-2/A-8** | Phase 5 후원 인프라 위에서 onboarding 첫 후원 CTA + retention 강화 |
| "동유럽이든 남미든 동아시아든 이런 데들에게 엄청난 꿈과 희망" | **A-2/A-4/A-6** | 지역별 explore 탭 + 신진작가 ranking 가시성 (OQ-5=B recent activity 강조) |
| "차별점 — 후원이라는 개념을 넣고 후원할 수 있는 구조를 만듦" | Phase 5 완료 ✅ + **D'-1** | tier release CTA UI + deeplink 보강으로 차별화 강화 |
| "포지셔닝이 굉장히 중요함 — 신진작가 타깃" | **A-4/A-5/A-6** | Explore "New Artists" 탭 + Search tier_only filter + Index 신진작가 badge |
| "남미 페루 대학생 그림 30만원 → 45만원 판매 히스토리" | **A-7** | 작가 milestone 타임라인 (가입→첫 판매→첫 후원→성장 기록) |

---

## 11. Phase 5 Lessons Applied (Phase 6 적용 방침)

| Phase 5 학습 사항 | Phase 6 적용 방식 |
|------------------|-----------------|
| OQ 권장 기본값 일괄 수락 패턴 (OQ-8 모두 권장대로) | Phase 6 OQ-1~OQ-10 + 각 sub-PDCA OQ — 동일 권장 default 표 형식 제공 |
| booster 패턴 (B-4가 B-3 TierBenefitsPanel 보강) | A 단계 sub-PDCAs 간 상호 보강 명시 (A-6 badge → A-4 Explore hero card 연결 등) |
| audit-driven scope (B-6에서 dead key 17개 × 5 발견 후 제거) | D'-4에서 carry-over a11y audit 먼저 수행 → A 단계 진입 전 tech debt 0 |
| mock 모드 fallback (B-1 Stripe mock 모드) | A-1 PostHog SDK: analytics disabled fallback (privacy mode) — 쿠키 차단 환경 대응 |
| Schema Sync Checklist (BE/FE schema pair) | 각 A sub-PDCA Design 단계 필수. 특히 A-3 feed 응답 + A-6 ranking score 페이로드 |
| i18n Exhaustive Check (grep -r "i18n key" 일관성) | D'-4에서 es.json 26 keys 완성 후, A 단계 신규 feature 추가 시 동시 5 locale 제공 |
| Prometheus + cron 격리 패턴 (R-5) | A-3 feed scoring cron + A-6 ranking cron — 각각 별도 파일 + AsyncSessionLocal + 별도 lifespan task |

---

## 12. 다음 액션

### Phase 6 시작 전 체크리스트

1. **alembic upgrade head 실행 확인** (OQ-8=A — D' 단계 시작 트리거). Phase 5 0043 포함
2. **OQ-1~OQ-10 결정** — "권장대로" 일괄 수락 시 즉시 D'-1 진입 가능
3. **D' 병렬 전략 확인** (OQ-1=B 권장: D'-1+D'-2+D'-4+D'-5 동시 + D'-3 이후)

### D' 단계 진입 명령 (OQ-1=B 병렬 채택 시)

```bash
# 병렬 그룹 A (동시 시작 권장)
/pdca plan phase4-tech-debt-cleanup           # D'-1
/pdca plan subscription-cancellation-tracking  # D'-2
/pdca plan phase5-i18n-cleanup                # D'-4
/pdca plan prometheus-deployment              # D'-5

# 순차 (D'-1 완료 후)
/pdca plan stripe-coupon-foundation           # D'-3

# 선택 (사용자 결정 시)
/pdca plan stripe-webhook-extension           # D'-6
```

### A 단계 진입 명령 (D' 완료 후)

```bash
# Critical Path 시작 (A-1 선결 필수)
/pdca plan analytics-foundation               # A-1

# A-1 완료 후 병렬 그룹
/pdca plan onboarding-funnel                  # A-2
/pdca plan feed-algorithm-v1                  # A-3

# A-2/A-3 완료 후 병렬 그룹
/pdca plan explore-revamp                     # A-4
/pdca plan search-enhancement                 # A-5

# A-4 권장 후 시작
/pdca plan artist-index-v1                   # A-6

# A-6 권장 후 병렬 그룹
/pdca plan storytelling-hub                   # A-7
/pdca plan retention-loop-enhancement         # A-8
```

---

## 13. 결정 기록 (Decisions Log)

### 2026-05-04 — Phase 6 로드맵 초안 (product-manager)

| 결정 | 내용 | 근거 |
|------|------|------|
| Phase 6 구조 | D'(1~2주) → A(6~10주) 순차 | 사용자 전략 결정: option D → A sequential |
| D' 단계 sub-PDCA | 5개 필수 + 1개 선택 (D'-1~D'-5 + D'-6) | Phase 5 8개 carry-over 청산 + Prometheus 배포 완성 |
| A 단계 sub-PDCA | 8개 (A-1~A-8) | README 그로스해킹 깔때기 + 신진작가 인덱스 + 스토리텔링 완전 구현 |
| A-1 Critical Path 지정 | Analytics Foundation 선결 | 모든 A 단계 KPI 측정의 기반 — 없으면 A/B 테스트 + funnel 측정 불가 |
| OQ-3 PostHog 권장 | PostHog A 권장 | feature flag(A/B) + 오픈소스(자체 호스팅) + GDPR 자체 처리 |
| OQ-5 ranking 가중치 | Option B 권장 (recent_activity 0.5) | 신진작가 친화적 — 최근 활동 강조로 신규 작가 가시성 확보 |
| Phase 5 lessons 적용 | 8개 항목 §11에 명시 | booster 패턴 / audit-driven / mock fallback / Schema Sync / cron 격리 |

---

## Version History

| 버전 | 날짜 | 변경사항 | 작성자 |
|------|------|---------|--------|
| 0.1 | 2026-05-04 | Phase 6 로드맵 초안. D'(5+1 sub-PDCA) + A(8 sub-PDCA) = 12~13 sub-PDCA. 10 OQ (권장 default 포함). Phase 5 lessons §11. Phase 5 carry-over 매핑 §7. README 비전 매핑 §10. | itpe-ince (Claude Sonnet 4.6 / product-manager) |
