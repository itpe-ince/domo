---
template: plan
version: 1.0
feature: domo-phase5-roadmap
date: 2026-05-04
author: itpe-ince (Claude Sonnet 4.6)
project: domo
project_version: v1
parent_roadmap: Phase 5 (D: Tech Debt Stabilization → B: Blue Bird Patronage UI)
status: Draft (Roadmap)
---

# Domo Phase 5 — 로드맵 (Master Plan)

> **Summary**: Phase 4 종결(11/11 sub-PDCA, 평균 Match Rate ~98%) 후 다음 두 단계를 순차 진행한다. D: Tech Debt Stabilization(1~2주, D-1~D-6) — Phase 4에서 축적된 8개 carry-over 청산 + observability baseline. B: Blue Bird Patronage UI(8~10주, B-1~B-6) — README 핵심 차별화인 블루버드 후원 micro-flow, 작가/후원자 dual dashboard, tier benefits 완비. 총 12 sub-PDCA, 10~12주 계획.
>
> **Project**: domo (v1)
> **Author**: itpe-ince
> **Date**: 2026-05-04
> **Status**: Roadmap (Sub-PDCA 인덱스. 각 항목은 별도 plan 문서로 본격 진입)

---

## 0. Phase 5 배경 & 전략적 의미

### Phase 4 종결 성과

editor-revamp-roadmap은 11/12 sub-PDCA 완료, Phase 4 종결. 주요 성과:

- **Critical Path 완주**: role-gating → draft-autosave → responsive-redesign → media-ux → media-studio → publish-controls → artist-tier-release → auction-promotion-suite
- **OQ 권장 기본값 패턴 확립**: 15 OQ 일괄 수락 → plan→design→do 전환 지연 0. Phase 5에도 동일 패턴 적용
- **아키텍처 패턴 적립**: cron 격리(R-5), computed effective state, idempotent dispatch(SELECT FOR UPDATE SKIP LOCKED + UPDATE WHERE IS NULL), 적응형 interval, Pillow 합성 + run_in_executor — 모두 Phase 5 B 단계에서 재사용 가능

### Phase 5가 중요한 이유

README 비전 직접 인용:

> "블루버드 후원 — 후원을 블루버드라고 예를 들어서 하나 만들어서 누른다면 생각보다 돈의 흐름이나 이런 것들이 원활해질 수 있고 공공의 이익을 왠지 표면적으로 많이 깔 수 있을 거라는 생각이 듦"

> "그로스해킹인가 이런 분석법 보면은 결국에는 깔대기 모양으로 사용자 층이 이만큼 있어야 맨 마지막에 소비자 층이 생기는 거임"

> "AI 세상으로 가면 갈수록 예술가들이 제일 먼저 굶어 죽음"

Phase 4까지는 에디터/발행 인프라 구축 — 그로스해킹 깔때기의 **상단** 구조(유저 유입·콘텐츠 생성)를 완성했다. Phase 5 B는 **하단** 구조(작가 수익화 + 후원자 전환)를 완성해 "유저층 → 소비자층" 전환 경로를 닫는다.

기 구축된 재사용 인프라:
- KYC (P3-2 완료 — MockProvider + Toss/Stripe 어댑터)
- 정산 배치 (P3-3 완료 — 주간/월간 + 관리자 승인/지급)
- artist-tier-release (#10 완료 — sponsorships 모델 + early_access tier)
- auction-promotion-suite (#11 완료 — idempotent cron 패턴 + Pillow 합성)

---

## 1. 비즈니스 컨텍스트

### 글로벌 신진작가 인덱스 & 스토리텔링

> "초기 작가들이 거래가 이루어지고 판매가 이루어지면 전 세계 아티스트들의 인덱스를 만들고 싶음"

블루버드 후원 결제가 실제 흐르기 시작하는 시점이 바로 "거래 이루어짐"의 첫 사례. Phase 5 B 완료 = 글로벌 신진작가 인덱스 + 스토리텔링 캠페인(히스토리 만들기) 진입의 물질적 전제 조건.

### 신진작가 진입장벽 해소

> "미국 아저씨가 하는 걸 하고 있는데 초기 작가들이 거래가 이루어지고 판매가 이루어지면 전 세계 아티스트들의 인덱스를 만들고 싶음"
> "동유럽이든 남미든 동아시아든 이런 데들에게는 엄청난 꿈과 희망이 될 수 있음"

Blue Bird 후원은 갤러리 백이 없는 신진작가에게 첫 번째 수익화 경로. 저진입장벽 micro-patronage → 정기 구독 → 경매 전환 깔때기 완성.

---

## 2. Phase 5 Sub-PDCA 목록

### D 단계 — Tech Debt Stabilization (1~2주)

Phase 4 8개 carry-over + D-6 observability baseline = 6 sub-PDCAs.

| # | Feature | 우선순위 | 추정 기간 | 병렬 가능 | 의존성 | 핵심 산출물 |
|---|---------|:-------:|:--------:|:--------:|--------|------------|
| D-1 | `editor-i18n-cleanup-v3` | Must | ~3일 | D-3, D-5와 병렬 가능 | 없음 (독립) | `share.*`↔`auction.shareCard.*` namespace 통합 + 비-wizard 영역 한국어 hardcode 25곳 제거. 5 locale JSON valid |
| D-2 | `upload-retry-ui` | Should | ~3일 | D-4와 병렬 가능 | 없음 (독립) | `useMediaUploadQueue.retry/cancel` + SortableMediaCard error overlay + i18n ~6키 |
| D-3 | `series-reorder-persistence` | Must | ~2일 | D-1, D-5와 병렬 가능 | #8 publish-controls ✅ | `POST /v1/series/{id}/reorder` 신규 endpoint. 현재 local-only 순서 변경 → 서버 영속화 |
| D-4 | `notifications-ux-audit` | Must | ~3일 | D-2와 병렬 가능 | 없음 (독립) | 알림 센터 UX 점검 + 미확인 카운트 N뱃지 + 분류 탭 + push/email 옵션 UI |
| D-5 | `server-side-notification-i18n` | Should | ~1일 | D-1, D-3와 병렬 가능 | 없음 (독립) | `auction_promotion_jobs.py` _TITLE_MAP/_BODY_MAP → user.language 기반 i18n (5 locale) |
| D-6 | `observability-monitoring-baseline` | Should | ~3일 | D-1 완료 후 | D-1 완료 권장 | EXPLAIN ANALYZE 자동화 게이트 + Prometheus metrics (cron rows/min, share_card hit rate, tier_release cleared rows) |

**D 단계 선택 항목 (Phase 5.5로 defer 권장)**:
- D-7 (Phase 4.1 #10 carry-over): POST_TIER_RESTRICTED 후원/구독 deeplink CTA UI + sponsor N일 옵션화 + home_feed Python post-filter SQL-only 전환 — 별도 spec 정의 필요, D 단계 1~2주 목표와 병존 어려움

**D 단계 병렬화 계획** (OQ-1 B 권장 기준):
```
병렬 그룹 A (Day 1~3): D-1 + D-3 + D-5 동시 진행
병렬 그룹 B (Day 2~5): D-2 + D-4 동시 진행 (그룹 A와 독립)
순차 (Day 4~7):        D-6 (D-1 완료 후 EXPLAIN ANALYZE 기준점 활용)
```

### B 단계 — Blue Bird Patronage UI (8~10주)

README 핵심 차별화 구현. KYC/정산/tier 인프라 위에서 후원 micro-flow + 양측 dashboard + retention 완비.

| # | Feature | 우선순위 | 추정 기간 | 의존성 | 핵심 산출물 |
|---|---------|:-------:|:--------:|--------|------------|
| B-1 | `bluebird-sponsor-flow` | Must | ~10일 | D 완료, KYC ✅, 정산 ✅ | 후원 button + micro-flow + Stripe SetupIntent UX + 일회/정기 선택 + 금액 입력 + 결제 confirmation. UI 브랜딩: "Blue Bird 후원" |
| B-2 | `artist-patronage-dashboard` | Must | ~8일 | B-1 ✅ | 작가 dashboard: 후원자 list + 수익 통계(daily/monthly) + 송금 요청 + tier 자동 부여 logs |
| B-3 | `supporter-dashboard` | Must | ~5일 | B-1 ✅ | 후원자 dashboard: 구독/일회 후원 history + cancel/upgrade + tier benefits visualization |
| B-4 | `tier-benefits-customization` | Should | ~5일 | B-2 ✅, #10 tier-release ✅ | 작가별 tier benefits customization (subscriber/sponsor/follower 별 혜택 정의 + tier_release 통합). 하이브리드: 플랫폼 default + 작가 override |
| B-5 | `patronage-retention-ux` | Should | ~5일 | B-3 ✅ | 이탈 방지 alert + 재구독 prompt + churn dashboard + 후원자 thank-you flow |
| B-6 | `patronage-i18n-a11y-audit` | Must | ~3일 | B-1~B-5 완료 후 | 5 locale(ko/en/ja/zh/es) 완성 + WCAG 2.1 AA + screen reader audit. 블루버드 브랜딩 5 locale 적용 |

**B 단계 실행 순서**:
```
B-1 (기반 결제 플로우, Critical Path)
  ↓
B-2 + B-3 (병렬 — 작가 dashboard / 후원자 dashboard)
  ↓
B-4 + B-5 (병렬 — tier 커스텀 / retention UX)
  ↓
B-6 (i18n/a11y 마무리 audit)
```

---

## 3. Open Questions

사용자 결정 필요 항목. **권장 기본값 표** — "권장대로" 한 번에 수락 가능.

| ID | 질문 | 옵션 | 권장 default | 근거 |
|----|------|------|:------------:|------|
| OQ-1 | D 단계 진행 방식 | A: 6 sub-PDCAs 순차 / **B: 독립 병렬 (D-1+D-3+D-5 + D-2+D-4)** / C: 우선순위 분리(D-1/D-4 first) | **B** | 시간 절약. D-1~D-5 모두 독립적 — 병렬로 1~2주 목표 달성 가능 |
| OQ-2 | D-7 포함 여부 | A: D 단계 포함 / **B: Phase 5.5로 defer** / C: Phase 5 본 plan에서 deprioritize | **B** | D는 1~2주 목표. D-7은 별도 spec 정의 필요 — spec 없이 시작 불가 |
| OQ-3 | Blue Bird 브랜드명 코드 반영 | A: 코드/UI 모두 "BlueBird"/"BB" / B: UI는 "후원/Sponsor" 일반어 유지 / **C: 코드는 sponsorships 그대로, UI는 "Blue Bird 후원" 브랜딩** | **C** | 브랜드 마케팅 hook + 기존 코드 호환. Phase 4 sponsorships 모델 무수정 |
| OQ-4 | 결제 모델 | A: 일회 후원만 / B: 정기 구독만 / **C: 둘 다 — Stripe SetupIntent + Subscription** | **C** | artist-tier-release가 이미 정기 구독 가정. 일회 후원 동시 지원으로 진입장벽 최소화 |
| OQ-5 | 작가별 vs 플랫폼 통일 tier benefits | A: 플랫폼 통일 default만 / B: 작가별 완전 커스텀 / **C: 플랫폼 default + 작가 override (하이브리드)** | **C** | 구현 복잡도 균형. 플랫폼 default가 있어 신규 작가 빈 state 방지 |
| OQ-6 | D 단계 시작 트리거 | **A: alembic upgrade head 적용 후 즉시 시작** / B: 사용자 결정 대기 / C: D-1만 즉시 시작 후 순차 | **A** | alembic upgrade는 사용자 측 실행 필요 — 실행 확인 즉시 D 단계 진입 |
| OQ-7 | P3-1 커뮤니티(domo-p3-roadmap)와의 관계 | **A: Phase 5 외부 — 별도 P3 진행** / B: Phase 5 후반 B-7로 통합 / C: Phase 6로 defer | **A** | P3는 KYC/정산 라인 (별도 roadmap 문서 존재). Phase 5 B와 분리해 집중 |
| OQ-8 | Phase 5 종료 기준 metric | A: 평균 Match Rate ≥95% / **B: 12 sub-PDCAs 100% archived** / C: 수동 QA + Blue Bird 후원 1건 실제 결제 완료 | **B** | Phase 4와 동일 기준. Match Rate는 sub-PDCA 별 검증 — 전체 archived = 종결 |

---

## 4. Acceptance Criteria (Phase 5 종료 기준)

| ID | 기준 | 검증 방법 |
|----|------|----------|
| AC-1 | D 단계 6 sub-PDCAs 모두 archived | `.pdca-status.json` D-1~D-6 phase="archived" |
| AC-2 | Phase 4 8개 carry-over 전부 청산 | §7 carry-over 매핑표 모두 ✅ |
| AC-3 | B 단계 6 sub-PDCAs 모두 archived | `.pdca-status.json` B-1~B-6 phase="archived" |
| AC-4 | 각 sub-PDCA Match Rate ≥ 90% (목표 ≥ 95%) | 개별 analysis.md matchRate 필드 |
| AC-5 | Blue Bird 후원 micro-flow production-ready — Stripe SetupIntent 통합 완료, 결제 테스트 통과 | B-1 AC 목록 내 결제 sandbox 검증 |
| AC-6 | 작가/후원자 양측 dashboard 기능 완비 | B-2, B-3 ACs |
| AC-7 | 5 locale(ko/en/ja/zh/es) 블루버드 브랜딩 포함 i18n 100% 적용 | B-6 AC — grep "[가-힣]" + locale parity |
| AC-8 | WCAG 2.1 AA — 후원 flow, dashboard 핵심 경로 | B-6 AC — screen reader + keyboard nav |
| AC-9 | Prometheus metrics 3개 (cron rows/min, share_card hit rate, tier_release cleared rows) + EXPLAIN ANALYZE 게이트 활성화 | D-6 AC |
| AC-10 | tsc 0 에러, 77 → N tests passed (회귀 0) | CI pipeline 자동 |

---

## 5. Risks & Mitigation

| Risk | 영향 | 가능성 | 완화 방안 |
|------|:----:|:------:|----------|
| **PCI-DSS 준수** — Stripe 카드 정보 처리 범위 | High | Medium | Stripe Elements + Stripe.js — 카드 데이터 Domo 서버 미경유. PCI SAQ-A 수준 유지 |
| **환율 처리** — USD/KRW/기타 동시 표시 | Medium | High | B-1에서 USD 단일 기준 (Stripe USD), 표시는 user.currency 기준 실시간 환율 API (환율 변동은 작가/후원자 양측 표시). Phase 6에서 다통화 정산 |
| **송금 지연** — 정산 배치(P3-3)와 Stripe payout 타이밍 불일치 | Medium | Medium | 정산 배치는 이미 주간/월간 사이클 존재. Payout 상태를 작가 dashboard에 표시 (pending/processing/paid) — UX로 기대값 관리 |
| **후원자 이탈(churn)** — 정기 구독 취소율 | High | High | B-5 retention UX: 취소 전 재구독 prompt + thank-you flow + churn 원인 단순 설문 (1문항). 초기 3개월 churn metric 수집 |
| **글로벌 i18n 깊이 부족** — 결제 UI 법적 언어(이용약관, 환불 정책) | High | Medium | B-1에서 한국어 + 영어 이중 법적 텍스트 표준. 나머지 3 locale(ja/zh/es)는 B-6 audit에서 법적 텍스트 별도 검수 |
| **정기 구독 vs 일회 결제 UX 혼란** — 사용자가 구독인지 일회인지 모름 | Medium | High | B-1 micro-flow에서 선택 명확히 분리 (radio 선택 + 확인 모달). 구독은 취소 경로 최상단 노출 |
| **Stripe 의존성** — 글로벌 미지원 국가(일부 동남아/동유럽) | High | Medium | KYC P3-2에 Mock + Toss/Stripe 어댑터 존재. Phase 5에서는 Stripe 우선, Phase 6에서 지역별 PSP 어댑터 확장 |
| **D 단계 carry-over 예상 외 scope 확장** | Medium | Low | D-1~D-6 각각 XS~S 규모. scope creep 방지: 각 D sub-PDCA plan에 "Out of Scope" 명시 필수 |

---

## 6. Timeline & Milestones

```
Week 1~2 — D: Tech Debt Stabilization
┌──────────────────────────────────────────────────────────────┐
│ Day 1~3   [병렬 A] D-1 + D-3 + D-5                          │
│ Day 2~5   [병렬 B] D-2 + D-4                                │
│ Day 4~7   [순차]   D-6 (D-1 완료 후)                         │
│ Milestone: D 완료 — 8 carry-over 청산 + observability ✅     │
└──────────────────────────────────────────────────────────────┘

Week 3~4 — B-1: Blue Bird Sponsor Flow (Critical Path)
┌──────────────────────────────────────────────────────────────┐
│ Day 1~5   Backend: Stripe SetupIntent + 결제 model           │
│ Day 6~10  Frontend: micro-flow UI + 브랜딩 + 5 locale       │
│ Milestone: 블루버드 후원 결제 첫 sandbox 완료 ✅              │
└──────────────────────────────────────────────────────────────┘

Week 5~7 — B-2 + B-3: Dual Dashboard (병렬)
┌──────────────────────────────────────────────────────────────┐
│ B-2 작가 dashboard (8일)                                     │
│ B-3 후원자 dashboard (5일) — B-2와 병렬                      │
│ Milestone: 양측 dashboard 기본 기능 완비 ✅                   │
└──────────────────────────────────────────────────────────────┘

Week 8~9 — B-4 + B-5: Tier Benefits + Retention (병렬)
┌──────────────────────────────────────────────────────────────┐
│ B-4 tier-benefits-customization (5일)                       │
│ B-5 patronage-retention-ux (5일) — B-4와 병렬               │
│ Milestone: 작가별 tier 혜택 정의 + churn 방어 ✅             │
└──────────────────────────────────────────────────────────────┘

Week 10~12 — B-6: i18n / a11y Audit + Phase 5 종결
┌──────────────────────────────────────────────────────────────┐
│ B-6 전체 i18n / WCAG 2.1 AA audit (3일)                     │
│ Phase 5 archive + 메트릭 측정 + Phase 6 backlog 정리        │
│ Milestone: Phase 5 종결 — 12/12 archived ✅                  │
└──────────────────────────────────────────────────────────────┘
```

---

## 7. Dependencies & Carry-over Mapping

Phase 4 8개 carry-over → D 단계 흡수 매핑:

| Carry-over 원본 | 출처 | D sub-PDCA | 처리 내용 |
|----------------|------|:----------:|----------|
| #3 m-2: 비-wizard 한국어 hardcode (EditorWorkspace/ProductFields/PostPreviewCard) | editor-i18n-cleanup plan v0.1 | **D-1** | 기존 키 13개 활용 + 신규 키 9개 추가 |
| #4 m-2: dead key (`post.editor.media.uploading`) | editor-media-ux analysis | **D-1** | 제거 또는 upload-retry-ui에서 활용 |
| #4 m-3: EditorStepContent 모바일 "업로드 중..." 인라인 | editor-media-ux analysis | **D-1** | i18n 키 외재화 |
| #11 m-1: `share.*` ↔ `auction.shareCard.*` namespace 중복 | auction-promotion-suite analysis C-2 | **D-1** | namespace 통합 — 5 locale 일괄 정리 |
| #4 R-FE-7: upload-retry-ui carry-over | upload-retry-ui.plan.md | **D-2** | `useMediaUploadQueue.retry/cancel` + SortableMediaCard UI |
| #8 carry-over: series 순서 변경 서버 미영속 | publish-controls 설계 | **D-3** | `POST /v1/series/{id}/reorder` 신규 endpoint |
| #12 notifications-ux-audit (Phase 3 독립 PDCA) | editor-revamp-roadmap Phase 3 | **D-4** | 알림 UX 점검 — Phase 5 D로 편입 |
| #11 m-2: `auction_promotion_jobs.py` _TITLE_MAP/_BODY_MAP 한국어 hardcode | auction-promotion-suite analysis | **D-5** | user.language 기반 서버사이드 i18n |

**D-6 신규 (Phase 4 observability 미비)**:

| 항목 | 근거 | D sub-PDCA |
|------|------|:----------:|
| EXPLAIN ANALYZE 자동화 게이트 | Phase 4에서 cron job 추가. DB 성능 회귀 자동 탐지 부재 | **D-6** |
| Prometheus metrics 3종 | cron worker rows/min, share_card cache hit rate, tier_release cleared rows — 현재 측정 수단 없음 | **D-6** |

---

## 8. 비즈니스 메트릭 (Phase 5 완료 후 측정)

Phase 5 B 완료 후 30일, 90일 기준으로 아래 KPI 측정.

| KPI | 측정 방법 | 30일 목표 | 90일 목표 |
|-----|----------|:---------:|:---------:|
| **활성 후원자 수** (unique 결제 완료) | Stripe dashboard + DB sponsorships | 10명 | 50명 |
| **활성 후원 작가 수** (후원 수령 확인 작가) | artist-patronage-dashboard | 5명 | 20명 |
| **평균 후원 금액** (USD, 일회+정기 합산) | Stripe + 정산 배치 | $5 | $8 |
| **정기 구독 retention rate** (3개월 유지율) | B-5 churn dashboard | — | ≥ 60% |
| **tier conversion rate** (팔로워 → 후원자) | tier_release logs | — | ≥ 5% |
| **후원 결제 성공률** | Stripe webhook success/fail | ≥ 95% | ≥ 97% |

**PostHog/Amplitude 도입 권장 여부**: Phase 5 B-1 시작 전에 사용자 결정 필요. 현재 Prometheus 도입(D-6)으로 서버 메트릭은 커버. 클라이언트 이벤트(버튼 클릭, 페이지 전환, funnel 이탈)는 PostHog(오픈소스 셀프호스팅 가능) 권장. B-1 착수 전 D-6 완료 후 판단.

---

## 9. Phase 4 Lessons Applied (Phase 5 적용 방침)

| Phase 4 학습 사항 | Phase 5 적용 방식 |
|------------------|-----------------|
| OQ 권장 기본값 일괄 수락 패턴 (15 OQ) | Phase 5 OQ-1~OQ-8 + 각 sub-PDCA OQ — 동일 권장 default 표 형식 제공 |
| cron 격리 (R-5): 별도 파일 + AsyncSessionLocal + 다른 컬럼 | B-1 결제 후처리 cron, B-5 churn alert cron에 동일 패턴 적용 |
| Computed effective state pattern | B-3 tier benefits 표시: `effective_tier = max(sponsorship_tier, subscription_tier)` |
| idempotent dispatch (UPDATE WHERE col IS NULL) | B-5 thank-you email cron, retention alert cron |
| Schema Sync Checklist (AC-12 사후 gap 방지) | 각 B sub-PDCA Design 단계에서 BE/FE schema pair checklist 필수 |
| i18n Exhaustive Check (M-1 사후 gap 방지) | 각 sub-PDCA PR 마지막 단계에서 `grep -r "i18n key"` 일관성 검증 |
| Integration Point Regression Matrix | B 단계 진입 시 5개 기존 통합 지점 × 신규 변경 영역 사전 매핑 |

---

## 10. Out of Scope (Phase 6+)

Phase 5에서 명시적으로 제외. 이후 로드맵에서 처리.

| 항목 | 이유 | Phase |
|------|------|:-----:|
| **P3-1 커뮤니티/그룹** | 별도 P3 roadmap 존재. 유저 100+ 조건부 | Phase 6 or P3 별도 |
| **domo-mobile-app (React Native)** | P3-9 — 웹 안정화 후. 현재 PWA로 임시 커버 | Phase 6+ |
| **real-auth (실제 인증 시스템)** | 현재 Mock + 어댑터 구조. 트래픽 확보 후 전환 | Phase 6+ |
| **editor-video-studio (ffmpeg)** | #6 video editor — ffmpeg 인프라 결정 차단. 별도 brainstorming 필요 | Phase 6+ |
| **Artist Index / 글로벌 신진작가 인덱스** | README 최종 목표지만 거래 데이터 축적 필요 | Phase 6+ (거래 50건+ 후) |
| **AI 시대 예술가 스토리텔링 캠페인** | 히스토리 제작은 마케팅 단계 — Phase 5 B 완료 후 소재 확보 가능 | Phase 6 마케팅 |
| **팔로워 알림 옵트인** | #11 OQ-2=B 결정 — notifications-ux-audit(D-4) 완료 후 재검토 | D-4 완료 후 결정 |
| **외부 SNS 자동 포스팅** | 작가 수동 다운로드/공유 우선. 자동화는 B-6 이후 검토 | Phase 6+ |
| **D-7 POST_TIER_RESTRICTED deeplink CTA** | Phase 5.5로 defer (OQ-2=B 권장) | Phase 5.5 |
| **B2B 리포트 (P3-6)** | 갤러리/학교 파트너십 체결 후. 현재 B2B 파이프라인 없음 | Phase 7+ |

---

## 11. 다음 액션

### Phase 5 시작 전 체크리스트

1. **alembic upgrade head 실행 확인** (OQ-6=A — D 단계 시작 트리거)
2. **OQ-1~OQ-8 결정** — "권장대로" 일괄 수락 시 즉시 D-1 진입 가능
3. **D 단계 병렬 전략 확인** (OQ-1=B 권장: D-1+D-3+D-5 동시 + D-2+D-4 동시)

### D 단계 진입 명령 (OQ-1=B 병렬 채택 시)

```
# 병렬 그룹 A (동시 시작 권장)
/pdca plan editor-i18n-cleanup-v3         # D-1
/pdca plan series-reorder-persistence      # D-3
/pdca plan server-side-notification-i18n   # D-5

# 병렬 그룹 B (동시 시작 권장)
/pdca plan upload-retry-ui                 # D-2 (plan 이미 존재 — design/do 직접 진입)
/pdca plan notifications-ux-audit          # D-4
```

---

## 12. 결정 기록 (Decisions Log)

### 2026-05-04 — Phase 5 로드맵 초안 (product-manager)

| 결정 | 내용 | 근거 |
|------|------|------|
| Phase 5 구조 | D(1~2주) → B(8~10주) 순차 | 사용자 전략 결정: defensive option 1 |
| D 단계 sub-PDCA | 6개 (D-1~D-6) | 8개 carry-over 청산 + #12 편입 + observability |
| B 단계 sub-PDCA | 6개 (B-1~B-6) | KYC/정산/tier 재사용 전제 하 최소 완성 집합 |
| 총 12 sub-PDCA | D(6) + B(6) | Phase 4 pattern (11 sub-PDCA) 유사 규모 |
| D-7 defer | Phase 5.5 | spec 정의 필요, D 1~2주 목표 압박 |
| Phase 4 lessons | 8개 항목 §9에 명시 | cron 격리, OQ 패턴, schema sync, i18n exhaustive check |

---

## Version History

| 버전 | 날짜 | 변경사항 | 작성자 |
|------|------|---------|--------|
| 0.1 | 2026-05-04 | Phase 5 로드맵 초안. D(6 sub-PDCA) + B(6 sub-PDCA) = 12 sub-PDCA. 8 OQ (권장 default 포함). Phase 4 lessons §9. carry-over 매핑 §7. | itpe-ince (Claude Sonnet 4.6 / product-manager) |
