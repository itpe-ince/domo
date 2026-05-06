---
template: plan
version: 1.0
feature: domo-phase8-roadmap
date: 2026-05-04
author: itpe-ince (Claude Sonnet 4.6)
project: domo
project_version: v1
parent_roadmap: Phase 8 (G'': Performance & Observability → H': Carry-over Consolidation → B': Patronage Maturity)
status: Draft (Roadmap)
---

# Domo Phase 8 — 로드맵 (Master Plan)

> **Summary**: Phase 7 종결(15/15 sub-PDCA, 100%, 2026-05-05) 후 세 단계를 순차 진행한다. G'': Performance & Observability(4주, G''-1~G''-5 필수) — G'-12 OpenTelemetry + G'-13 Redis deferred를 본격 흡수 + N+1 audit + DB pool 튜닝 + 프론트엔드 번들 최적화. H': Carry-over Consolidation(3주, H'-1~H'-6 필수) — Phase 7 carry-over 16건 중 13건 청산. B': Patronage Maturity(6주, B'-1~B'-5 필수) — README 비전 multi-currency + DM messaging + Push/Email 본격 + Stripe 자동 갱신 + 후원 분석 대시보드. 총 16 sub-PDCAs, 13주 계획.
>
> **Project**: domo (v1)
> **Author**: itpe-ince
> **Date**: 2026-05-04
> **Status**: Roadmap (Sub-PDCA 인덱스. 각 항목은 별도 plan 문서로 본격 진입)

---

## 0. Phase 8 배경 & 전략적 의미

### Phase 7 종결 성과

Phase 7은 G'(10/10) + C(5/5) = 15/15 sub-PDCA 100% 완료(2026-05-05). 주요 성과:

- **마케팅 허브 완성**: AI 인터뷰 자동 생성(tuzigroup LLM Gateway) + Press Kit PDF 자동 배포 + Multi-language 5 locale SEO + Media Coverage CMS + Newsletter AWS SES
- **Stripe 성숙화**: webhook 9개 핸들러 + signing secret + idempotency + winback coupon 실제 발행
- **인프라 확장**: alembic 0049 → 0058 (+9) + 8 cron workers (R-5 격리 일관) + 30+ 신규 endpoints + 6 신규 모델 + ~1100+ i18n × 5 locales
- **누적 지표**: 207 → 311 passed (+104 tests) + tsc 0 + Prometheus 22+ metrics + PostHog backend SDK

### Phase 8가 중요한 이유

Phase 5(후원 인프라) → Phase 6(그로스해킹 깔때기) → Phase 7(마케팅 허브 자동화) 위에서 Phase 8은 세 가지 목표를 순차 달성한다:

**1. G'' — Performance & Observability**: Phase 7 G'에서 "선택" 판정으로 defer된 G'-12(OpenTelemetry)와 G'-13(Redis)을 본격 흡수한다. 311 tests와 30+ endpoints, 8 cron workers를 운영하는 시점에서 distributed tracing과 캐시 레이어는 production-ready의 필수 요건이 됐다.

**2. H' — Carry-over Consolidation**: Phase 7 carry-over 16건(G'-11/G'-12/G'-13 deferred 3건 + Phase 7 보고서 기재 13건 중 G'+C 완료 제외 잔여분) 중 13건을 6개 sub-PDCAs로 체계적으로 청산한다.

**3. B' — Patronage Maturity**: README 핵심 비전 "글로벌 신진작가 후원" 의 마지막 미완 항목들 — multi-currency(KRW/EUR/JPY), DM messaging, Push/Email 본격 — 을 본격 구현한다. Phase 5 B-1 SetupIntent + Phase 7 G'-1 Webhook 성숙화 위에 multi-currency Stripe를 얹는다.

README 비전 직접 인용:

> "동유럽이든 남미든 동아시아든 이런 데들에게는 엄청난 꿈과 희망이 될 수 있음" — multi-currency 없이는 글로벌 후원이 불완전하다.

> "**AI 세상으로 가면 갈수록 예술가들이 제일 먼저 굶어 죽음**" — Push/Email 알림 없이 retention이 불가능하다.

> "유저들이 늘어나야 소비자들도 늘어남" — 그로스해킹 깔때기의 다음 단계는 후원자-작가 DM으로 관계를 깊게 하는 것이다.

---

## 1. 비즈니스 컨텍스트

### Phase 5~7 성과 + Phase 8 전략 구조

```
[Phase 5] 후원 인프라 완성 (Stripe SetupIntent + Blue Bird 후원 모달)
    ↓
[Phase 6] 그로스해킹 깔때기 + 신진작가 인덱스 + 스토리텔링 허브
    ↓
[Phase 7] Tech Debt 청산(G') + 마케팅 허브 자동화(C)
    ↓
[Phase 8 G''] Performance & Observability — 인프라 기반 강화
    ↓
[Phase 8 H'] Carry-over Consolidation — Tech Debt 최종 청산
    ↓
[Phase 8 B'] Patronage Maturity — Multi-currency + DM + Push = 글로벌 후원 완성
```

### 후원 인프라 Maturity — Phase 5→7→8 진화

```
Phase 5 B-1: SetupIntent + Blue Bird 후원 Modal + 취소 사유 추적
    ↓ (booster)
Phase 7 G'-1: Stripe webhook 9 핸들러 + idempotency + audit log
Phase 7 G'-2: Winback coupon 실제 발행 (too_expensive→50% 1mo)
    ↓ (booster)
Phase 8 B'-1: Multi-currency (KRW/EUR/JPY) — Stripe FX + 환율 cron
Phase 8 B'-4: Stripe billing 자동 갱신 deep integration
Phase 8 B'-2: DM messaging — 후원자 ↔ 작가 직접 소통
Phase 8 B'-3: Push/Email 본격 — FCM/APNs + AWS SES cron dispatch
```

### README "글로벌" 비전의 마지막 퍼즐

Phase 7까지 완성한 글로벌 인프라(5 locale i18n + Multi-language story + region/genre ranking)는 화면 표시 단계다. Phase 8 B'-1 multi-currency가 완성되면 "동유럽 신진작가가 페루 팬에게 KRW/EUR/JPY로 후원을 받는" 실제 자금 흐름이 글로벌하게 연결된다. 이는 README 핵심 비전의 가장 구체적인 구현이다.

---

## 2. Phase 8 Sub-PDCA 목록

### G'' 단계 — Performance & Observability (4주, 5개 sub-PDCAs)

Phase 7 G'-12(OpenTelemetry)/G'-13(Redis) 선택 항목을 본격 흡수 + 추가 최적화.

#### 필수 G'' sub-PDCAs (5개)

| # | Feature | 우선순위 | 추정 기간 | 의존성 | 핵심 산출물 | Phase 7 carry-over 출처 |
|---|---------|:-------:|:--------:|--------|------------|------------------------|
| **G''-1** | `opentelemetry-tracing` | **Must** | ~5일 | 없음 (Critical Path) | OpenTelemetry SDK (FastAPI + asyncio) + Trace context propagation (HTTP headers + cron worker) + Jaeger/Tempo/AWS X-Ray 통합 + 핵심 endpoint 자동 instrumentation + G'-4 backend PostHog trace_id 통합. Mock 모드(OTEL_EXPORTER_OTLP_ENDPOINT 미설정 시 noop) | G'-12 deferred (OQ-2=C Phase 8) |
| **G''-2** | `redis-cache-layer` | **Must** | ~5일 | 없음 (병렬 가능) | Redis docker-compose/production 인프라 + app/services/cache.py (async redis client + Mock 모드) + 핵심 캐싱: popular searches 5min TTL + artist_index ranking 1h TTL + feed scoring 5min TTL per user + rate limit Redis (in-memory → production-ready). Prometheus cache hit rate metrics | G'-13 deferred (OQ-2=C Phase 8) |
| **G''-3** | `n-plus-one-audit` | **Must** | ~3일 | 없음 (병렬 가능) | 핵심 endpoint EXPLAIN ANALYZE 자동화 스크립트 + N+1 query 발견 및 수정 (selectinload + joinedload + batch fetch) + 필요 시 alembic 0059 인덱스 추가 + 응답 시간 baseline/개선 후 metric. D-6 Phase 5 perf docs 본 PDCA에서 CI 통합 | D-6 Phase 5 carry-over (partial) |
| **G''-4** | `db-connection-pool-tuning` | **Should** | ~2일 | 없음 (병렬 가능) | SQLAlchemy async pool size 튜닝 (pool_size + max_overflow + pool_pre_ping) + production load test 시뮬레이션 (locust 또는 perf script) + Prometheus connection pool metrics | Phase 8 신규 |
| **G''-5** | `frontend-bundle-optimization` | **Should** | ~4일 | 없음 (병렬 가능) | next/bundle-analyzer 도입 + 핵심 큰 chunk 분리 (Konva A-image-studio + Stripe + Pillow PDF preview) + Dynamic import 강화 (BluebirdModal + AdminPressKit + Newsletter editor) + Initial bundle < 200KB 목표 + Lighthouse score baseline/개선 | Phase 8 신규 |

**G'' 병렬화 계획** (OQ-1 B 권장 기준):
```
Day 1~5 [병렬 그룹 전체]: G''-1 + G''-2 + G''-3 + G''-4 + G''-5 동시 (5개 독립)
Milestone: G'' 4주 — 5 sub-PDCAs archived + perf KPI baseline 측정 + Redis production-ready
```

**G'' 완료 기준**: 5 sub-PDCAs archived + HTTP p95 latency baseline 측정 + Redis cache hit rate 기록 시작 + OTEL trace coverage 핵심 endpoint 달성

---

### H' 단계 — Carry-over Consolidation (3주, 6개 sub-PDCAs)

Phase 7 종결 carry-over 16건 체계적 청산. 우선순위: a11y (H'-1) + CJK PDF (H'-2) + multi-language SEO (H'-3) + Media Coverage 보강 (H'-4) + Newsletter bounce (H'-5) + ML 데이터 준비 (H'-6).

#### 필수 H' sub-PDCAs (6개)

| # | Feature | 우선순위 | 추정 기간 | 의존성 | 핵심 산출물 | Phase 7 carry-over 출처 |
|---|---------|:-------:|:--------:|--------|------------|------------------------|
| **H'-1** | `voiceover-nvda-test-fix` | **Must** | ~3일 | 없음 | VoiceOver (macOS) + NVDA (Windows) 시뮬레이션 + 핵심 11페이지 audit (home/feed/explore/search/posts/[id]/users/[id]/me/*) + 발견 이슈 fix + audit_report v0.4. G'-3 axe-core CI 기반 확장 | G'-11 deferred (선택→H' 필수 승격) |
| **H'-2** | `cjk-font-pdf-embedding` | **Must** | ~3일 | 없음 (독립) | reportlab CID font 임베딩 (Noto Sans CJK) + C-2 PressKit PDF + C-5 newsletter PDF 적용 + 5 locale × 1~2 page samples 검증. 한국어/일본어/중국어 PDF 렌더링 완성 | C-2 carry-over (CJK font) |
| **H'-3** | `multi-language-seo-meta` | **Should** | ~2일 | 없음 (독립) | G'-6 dynamic OG 4 routes → locale param 추가 + twitter:card + og:image locale별 자동 노출 + C-3 multi-language story SEO 보강. Phase 8 B'-1 multi-currency 후속 연동 준비 | G'-6 + C-3 carry-over (OG locale) |
| **H'-4** | `click-tracking-rss-thumbnail` | **Should** | ~3일 | 없음 (독립) | click tracking (외부 link 클릭 PostHog event C-4 media coverage 통합) + auto-thumbnail OG image scraping (httpx + BeautifulSoup). RSS auto-fetch cron은 시간 부족 시 Phase 9 carry-over 허용 | C-4 carry-over (click tracking + thumbnail) |
| **H'-5** | `newsletter-bounce-handling` | **Must** | ~3일 | 없음 (독립) | AWS SES SNS topic + webhook endpoint + Hard bounce → NewsletterPreferences.is_subscribed=False 자동 + Soft bounce + complaint 처리 + R-5 격리 패턴 적용 + delivery tracking. open rate 수집은 선택 (Phase 9 carry-over 허용) | C-5 carry-over (SES bounce) |
| **H'-6** | `ml-feed-personalization-prep` | **Could** | ~3일 | 없음 (독립) | PostHog event → DB 저장 cron (사용자 행동 history 축적) + 향후 ML feed v2 (collaborative filtering) + newsletter personalization 위한 데이터 파이프라인 준비. PostHog → Redshift export 또는 자체 cohort table | A-3 + C-5 carry-over (ML 데이터) |

**H' 실행 순서**:
```
H'-1 + H'-2 + H'-3 + H'-4 + H'-5 병렬 (3주 목표 달성)
H'-6는 H'-1~H'-5 완료 후 남은 시간에 진행 (시간 부족 시 Phase 9+ carry-over 허용)
```

**H' 완료 기준**: H'-1~H'-5 (5개 필수) archived + Phase 7 carry-over 16건 중 13건 청산 완료 (3건 Phase 9+ defer: pg_trgm + /metrics 포트 분리 + RSS auto-fetch)

---

### B' 단계 — Patronage Maturity (6주, 5개 sub-PDCAs)

README 비전 "후원 = 그로스해킹의 본질" — Phase 5/7 후원 인프라 위에 multi-currency + DM + Push/Email 본격 구현. Phase 8의 핵심이자 비즈니스 가치의 정점.

#### 필수 B' sub-PDCAs (5개)

| # | Feature | 우선순위 | 추정 기간 | 의존성 | 핵심 산출물 | Phase 7 carry-over 출처 |
|---|---------|:-------:|:--------:|--------|------------|------------------------|
| **B'-1** | `multi-currency-foundation` | **Must** | ~7일 | 없음 (**Critical Path**) | alembic 0060 (Post.buy_now_currency + Auction.currency + Sponsorship.currency) + Currency 모델 (rate + last_updated) + 환율 fetch cron (Open Exchange Rates API, 1h, R-5 격리) + Stripe multi-currency (Coupon + SetupIntent + Subscription) + Frontend currency switcher + 사용자 preferred_currency + 5 locale × KRW/EUR/JPY/USD 표시 (lib/format.ts G'-10 booster) | Phase 7 Phase 8+ defer (Phase 7 §9 Out of Scope) |
| **B'-2** | `dm-messaging` | **Must** | ~7일 | B'-1 완료 권장 | Conversation + Message 모델 + alembic 0061 + 1:1 conversation (Group은 P3-1 Phase 9+) + WebSocket 또는 polling + D-4 Notification 통합 + 모더레이션 (admin abuse report) | Phase 7 Phase 8+ defer (§9: P3 또는 Phase 8+) |
| **B'-3** | `push-email-digest-foundation` | **Must** | ~7일 | B'-1 ✅ 권장 | FCM/APNs SDK 통합 (Mock + Real) + User device token 관리 + 사용자 opt-in per-type + 4 cron worker 알림 → push/email 자동 dispatch + C-5 newsletter SES 활용. **Phase 7 8번째 cron → Phase 8 9번째 cron worker** (R-5 격리 패턴 일관) | D-4 carry-over (push/email) + A-8 carry-over |
| **B'-4** | `stripe-billing-auto-renewal` | **Must** | ~5일 | B'-1 ✅ 권장 | POST /me/subscriptions/{id}/renew 완성 (A-8 carry-over 본격) + Stripe billing 자동 갱신 deep integration (G'-1 webhook customer.subscription 활용 booster) + 갱신 실패 retry + 만료 7일 전 자동 갱신 시도 + 사용자 알림 B'-3 dispatch | A-8 carry-over (POST /renew) |
| **B'-5** | `patronage-analytics-dashboard` | **Should** | ~5일 | B'-3 ✅ 권장 | 작가 dashboard PostHog event 시각화 + 후원자 cohort retention (D1/D7/D30) + winback coupon redemption rate (G'-2 booster) + newsletter open rate + click rate (B'-3 + C-5 booster). A-1 PostHog foundation booster | Phase 8 신규 (A-1 + B-2 carry-over 통합) |

**B' 실행 순서** (OQ-9 B 권장 기준):
```
B'-1 (multi-currency — Critical Path 선결, 단독 7일)
    ↓
B'-2 + B'-3 병렬 (DM messaging + Push/Email 동시, 7일)
    ↓
B'-4 + B'-5 병렬 (Stripe 자동 갱신 + 분석 대시보드, 5일)
```

**B' 완료 기준**: 5 sub-PDCAs archived + multi-currency 결제 1건 실제 처리 + DM 1건 실제 송수신 + Push notification 1건 실제 발송 + Stripe 자동 갱신 성공 1회

---

## 3. Open Questions

사용자 결정 필요 항목. **"권장대로" 한 번에 수락 시 즉시 G'' 진입 가능**.

| ID | 질문 | 옵션 | 권장 default | 근거 |
|----|------|------|:------------:|------|
| **OQ-1** | G'' 진행 방식 | A: 5 순차 / **B: 독립 병렬 (G''-1+G''-2+G''-3+G''-4+G''-5 동시)** / C: 우선순위 분리 | **B** | Phase 6/7 패턴 — 5개 모두 독립, 병렬화 최적. 4주 목표 달성 |
| **OQ-2** | H' 우선순위 범위 | A: 16 carry-over 모두 H'-1~H'-6 흡수 / **B: 일부 Phase 9+ defer (ML 등 무거운 항목)** / C: H'-1+H'-2+H'-5 필수만 | **B** | 3주 목표 달성 — H'-6 ML feed prep은 Phase 9+ carry-over 허용. H'-1~H'-5 필수 5개 우선 |
| **OQ-3** | Redis Cache 운영 (G''-2) | **A: AWS ElastiCache (managed)** / B: Self-hosted Redis (docker) / C: Upstash (serverless) / D: Mock 모드만 | **A** | AWS 인프라 통합 (SES + EC2) + scalability + 관리 부담 최소. 초기 캐시 레이어에 최적 |
| **OQ-4** | OpenTelemetry Backend (G''-1) | A: Jaeger (open-source) / **B: AWS X-Ray (AWS 통합)** / C: Tempo (Grafana) / D: Honeycomb (SaaS) | **B** | AWS SES + ElastiCache 인프라 통합 일관성. X-Ray SDK FastAPI 공식 지원. 추가 계약 불필요 |
| **OQ-5** | Multi-currency 정책 (B'-1) | A: USD lock + display only / B: Full multi-currency / **C: 4 currency (USD/KRW/EUR/JPY) Full** | **C** | README 글로벌 비전 직접 구현. "동유럽/남미/동아시아" 타깃 = KRW/EUR/JPY 필수. Stripe multi-currency 공식 지원 |
| **OQ-6** | 환율 데이터 source (B'-1) | **A: Open Exchange Rates (1000 free/mo)** / B: ExchangeRate-API (1500 free/mo) / C: Stripe FX rates (자동) / D: Fixer.io | **A** | 무료 1000건/월 충분 (1h cron × 30일 = 720건) + 공식 REST API + 신뢰도. 추가 비용 0 |
| **OQ-7** | DM 모델 (B'-2) | **A: 1:1 only (단순)** / B: 1:1 + Group (작가 fan club) / C: 1:1 + Customer Service | **A** | P3-1 Community(Phase 9+)와 분리 — 단순 1:1. 모더레이션 복잡도 최소화. 후속 Group은 Phase 9 별도 |
| **OQ-8** | Push 인프라 (B'-3) | A: FCM only (Android+Web) / **B: FCM + APNs (iOS 포함)** / C: OneSignal (SaaS) / D: Web Push only (PWA) | **B** | FCM + APNs 표준 구현. iOS 사용자 포함 필요 (글로벌 신진작가 타깃). Mock 모드 fallback으로 개발 부담 0 |
| **OQ-9** | B' 진행 방식 | A: 5 순차 / **B: B'-1 단독 → B'-2+B'-3 병렬 → B'-4+B'-5 병렬** / C: B'-1+B'-2+B'-3 병렬 | **B** | B'-1 multi-currency Critical Path 선결 필수 (currency 없이 DM/Push currency-aware 구현 불가). 이후 병렬화로 효율화 |
| **OQ-10** | Phase 8 종료 기준 | A: 16 sub-PDCAs archived / **B: Phase 5/6/7 패턴 (100% archived)** / C: 추가 perf KPI (p95<200ms + cache hit>70% + multi-currency 결제 1건 + DM 1건) | **B** | Phase 5/6/7 동일 기준 — 100% archived가 종결 기준. perf KPI와 DM/Push 동작은 §4 AC에 추가 조건 명시 |
| **OQ-11** | Phase 8 시작 트리거 | **A: Phase 7 alembic 0058 적용 확인 후 즉시** / B: 사용자 결정 대기 / C: G''-1 먼저 후 나머지 병렬 | **A** | Phase 7 마이그레이션 완료 확인 즉시 진입. Phase 5/6/7 동일 패턴 |
| **OQ-12** | Mobile Native + P3-1 Community Phase 분리 | **A: Phase 9 separate** / B: Phase 8 후반 일부 (B'-2 DM 후 P3-1 진입) / C: 별도 P3 진행 | **A** | Phase 8 = G''(5)+H'(6)+B'(5) = 16 sub-PDCAs로 충분. Mobile + Community는 Phase 9 별도 — scope 경계 명확 |

---

## 4. Acceptance Criteria (Phase 8 종료 기준)

| ID | 기준 | 검증 방법 |
|----|------|----------|
| **AC-1** | G'' 5 sub-PDCAs (G''-1~G''-5) 모두 archived | `.pdca-status.json` G''-1~G''-5 phase="archived" |
| **AC-2** | H' 최소 5 sub-PDCAs (H'-1~H'-5) archived + carry-over 13건 청산 | `.pdca-status.json` + §7 carry-over 매핑표 13건 ✅ |
| **AC-3** | B' 5 sub-PDCAs (B'-1~B'-5) 모두 archived | `.pdca-status.json` B'-1~B'-5 phase="archived" |
| **AC-4** | 각 sub-PDCA Match Rate ≥ 90% (목표 평균 ≥ 95%) | 개별 analysis.md matchRate 필드 |
| **AC-5** | HTTP p95 latency baseline 측정 시작 (G''-1 OTEL trace coverage) | Prometheus + X-Ray dashboard |
| **AC-6** | Redis cache hit rate ≥ 70% (popular search + artist_index 캐시 기준) | Prometheus cache_hit_rate metric |
| **AC-7** | Multi-currency 결제 1건 실제 처리 (USD/KRW/EUR/JPY 중 1건) | Stripe dashboard + DB Sponsorship.currency 확인 |
| **AC-8** | DM 메시지 1건 실제 송수신 (작가 ↔ 후원자) | DB Message 테이블 확인 |
| **AC-9** | Push notification 1건 실제 발송 (FCM or APNs) | Firebase console 또는 APNs dashboard 확인 |
| **AC-10** | Stripe 자동 갱신 성공 1회 (subscription renewal) | Stripe billing dashboard + audit log 확인 |
| **AC-11** | tsc 0 에러, 311 → N tests passed (회귀 0) | CI pipeline 자동 |
| **AC-12** | 5 locale(ko/en/ja/zh/es) i18n — Phase 8 신규 feature 동시 5 locale | grep "[가-힣]" + locale parity 검증 |
| **AC-13** | R-5 cron 격리 일관 — B'-3 push/email이 9번째 worker로 격리 적용 | push_notification_jobs.py R-5 패턴 코드 검증 |
| **AC-14** | alembic 0060(B'-1) + 0061(B'-2) 마이그레이션 무결 | `alembic upgrade head` 성공 + downgrade 테스트 |

---

## 5. Risks & Mitigation

| Risk | 영향 | 가능성 | 완화 방안 |
|------|:----:|:------:|----------|
| **Redis 인프라 비용 급증** — AWS ElastiCache 운영 비용 예상 초과 | Medium | Low | G''-2: 초기 cache.small 인스턴스 선택 + 트래픽 기반 autoscale. Mock 모드(REDIS_URL 미설정 시) 개발 환경 fallback으로 비용 0. 월 ~$20 예상 |
| **OpenTelemetry overhead** — OTEL SDK 추가로 인한 latency 증가 | Medium | Medium | G''-1: sampling rate 10% 초기 설정 + async exporter (non-blocking). noop exporter Mock 모드. 핵심 10개 endpoint만 우선 instrumentation |
| **Multi-currency 환율 정확성** — 환율 갱신 지연 시 결제 금액 오차 | High | Low | B'-1: 1h cron 갱신 + 최대 허용 오차 ±2%. 갱신 실패 시 마지막 valid rate 사용 + admin 알림. Stripe 실시간 FX rate는 display용, DB rate는 audit용 이원 관리 |
| **Stripe FX 시각 차이** — Stripe currency charge 시점과 환율 표시 시점 불일치 | Medium | Medium | B'-1: charge 전 최신 rate 재확인 + 실제 청구액 표시 (Stripe calculate) + 사용자 "최종 청구액은 Stripe 결제 시점 환율 기준" 안내 |
| **DM abuse + 모더레이션** — 스팸/불법 콘텐츠 DM 전송 | High | Medium | B'-2: 1:1 only (Group 제외) + report/block UI + admin abuse queue + 메시지 soft delete + rate limit (10 DM/min/user). Phase 9 이후 NLP 자동 감지 |
| **Push 인프라 latency** — FCM/APNs 토큰 등록 실패 또는 지연 | Medium | Medium | B'-3: Mock 모드(FCM_SERVER_KEY 미설정 시) + token 유효성 주기적 검증 cron + 발송 실패 시 fallback email. delivery receipt 저장 |
| **FCM/APNs token 만료** — 앱 재설치 또는 장기 미사용 시 device token 무효화 | Medium | High | B'-3: 발송 실패 응답(InvalidRegistration) 수신 시 DB token 자동 삭제 + 다음 앱 실행 시 재등록 flow. token refresh cron (7일 주기) |
| **alembic 충돌** — B'-1(0060) + B'-2(0061) 병렬 작업 시 revision 충돌 | Medium | Medium | Phase 6/7 패턴: revision ID 사전 배정 (0059=G''-3 optional, 0060=B'-1, 0061=B'-2). `alembic heads` 충돌 감지 자동화 |
| **Newsletter bounce loop** — H'-5 SES bounce webhook 재귀 호출 | Low | Low | H'-5: idempotency key (bounce notification ID) + WebhookEvent DB 중복 처리 방지 (G'-1 패턴 재사용 booster) |

---

## 6. Timeline & Milestones

```
Phase 8 총 13주 (G'' 4주 + H' 3주 + B' 6주)

Week 1~4 — G'': Performance & Observability
┌─────────────────────────────────────────────────────────────────────┐
│ Day 1~5 [병렬 전체]  G''-1 (OpenTelemetry) + G''-2 (Redis)         │
│                      + G''-3 (N+1 Audit) + G''-4 (DB Pool)         │
│                      + G''-5 (Bundle Optimization) 동시             │
│ Week 1: G''-3/G''-4 완료 (S~M 항목 선결)                           │
│ Week 2~3: G''-1/G''-2 완료 (M 항목 본론)                           │
│ Week 4: G''-5 완료 + perf KPI baseline 측정                        │
│ Milestone: G'' 종결 — 5 sub-PDCAs archived + Redis production-ready │
└─────────────────────────────────────────────────────────────────────┘

Week 5~7 — H': Carry-over Consolidation
┌─────────────────────────────────────────────────────────────────────┐
│ Week 5~6 [병렬]:   H'-1 (VoiceOver/NVDA) + H'-2 (CJK Font PDF)    │
│                    + H'-3 (OG SEO meta) + H'-4 (Click tracking)    │
│                    + H'-5 (Newsletter bounce) 동시                  │
│ Week 7 [마무리]:   H'-6 (ML 데이터 준비, 시간 허용 시)              │
│ Milestone: H' 종결 — carry-over 16건 중 13건 청산 + 3건 Phase 9+   │
└─────────────────────────────────────────────────────────────────────┘

Week 8~13 — B': Patronage Maturity
┌─────────────────────────────────────────────────────────────────────┐
│ Week 8~9 [단독]:    B'-1 multi-currency-foundation (Critical Path) │
│                     USD/KRW/EUR/JPY Stripe + 환율 cron + UI        │
│ Week 10~11 [병렬]:  B'-2 dm-messaging + B'-3 push-email-digest     │
│                     DM 1:1 + FCM/APNs + 9번째 cron worker          │
│ Week 12~13 [병렬]:  B'-4 stripe-billing-auto-renewal               │
│                     + B'-5 patronage-analytics-dashboard           │
│ Milestone: B' 종결 — multi-currency 결제 실제 + DM + Push 동작 ✅   │
└─────────────────────────────────────────────────────────────────────┘

Phase 8 종결 (Week 13)
┌─────────────────────────────────────────────────────────────────────┐
│ 전체 archive + KPI baseline 확인 + Phase 9 backlog 정리             │
│ Milestone: Phase 8 종결 — 16/16 sub-PDCAs archived ✅              │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 7. Dependencies & Phase 7 Carry-over Mapping

Phase 7 종결 보고서(§8)에 기재된 carry-over 16건 → Phase 8 H' + G'' + B' 흡수 매핑:

| # | Carry-over 원본 | 출처 | Phase 8 흡수 | 처리 방식 |
|---|----------------|------|:------------:|----------|
| 1 | G'-11 voiceover-nvda-test | 선택 sub-PDCA defer | **H'-1** | VoiceOver/NVDA 시뮬레이션 + 발견 이슈 fix + audit_report v0.4 |
| 2 | G'-12 opentelemetry-tracing | 선택 sub-PDCA defer | **G''-1** | OpenTelemetry SDK + AWS X-Ray + trace context propagation |
| 3 | G'-13 redis-cache-layer | 선택 sub-PDCA defer | **G''-2** | Redis async client + popular search/feed/rate-limit 캐싱 |
| 4 | pg_trgm fuzzy search | Phase 7 §8 planned carry-over | **Phase 9+** | DB extension 별도 검토. DBA 승인 필요 |
| 5 | /metrics 포트 분리 + Bearer rotation | Phase 7 §8 planned carry-over | **Phase 9+** | 인프라 PDCA 별도. Prometheus production-ready 이미 달성 |
| 6 | DM messaging | Phase 7 §8 planned carry-over (P3/Phase 8+) | **B'-2** | Phase 8에서 본격 구현. 1:1 only (Group P3-1 Phase 9+) |
| 7 | CJK font PDF embedding | C-2 carry-over | **H'-2** | reportlab Noto Sans CJK + PressKit/newsletter PDF |
| 8 | OG locale param + twitter:card | G'-6 + C-3 carry-over | **H'-3** | 4 OG routes locale param + SEO meta 강화 |
| 9 | click tracking (외부 link) | C-4 carry-over | **H'-4** | PostHog event + C-4 media coverage 통합 |
| 10 | RSS auto-fetch cron | C-4 carry-over | **Phase 9+** | 시간 우선순위 낮음 — H'-4 필수 작업 우선 |
| 11 | auto-thumbnail OG scraping | C-4 carry-over | **H'-4** (통합) | httpx + BeautifulSoup auto-thumbnail (H'-4 통합) |
| 12 | SES bounce/complaint handling | C-5 carry-over | **H'-5** | SNS topic + webhook + Hard/Soft bounce 처리 |
| 13 | delivery tracking + open rate | C-5 carry-over | **H'-5** (선택) | SES receipt 저장 (open rate는 Phase 9 carry-over 허용) |
| 14 | ML feed v2 데이터 수집 | A-3 + C-5 carry-over | **H'-6** | PostHog → cohort table. H'-1~H'-5 완료 후 진행 |
| 15 | multi-currency (KRW/EUR/JPY) | Phase 7 §9 Out of Scope | **B'-1** | Stripe multi-currency + 환율 cron + currency switcher |
| 16 | POST /me/subscriptions/{id}/renew | A-8 carry-over (G'-1에 통합 → 미완) | **B'-4** | Stripe billing 자동 갱신 deep integration |

**Phase 8 흡수 (13건)**: G''-1(1건) + G''-2(1건) + H'-1~H'-5(7건) + H'-6(1건) + B'-1(1건) + B'-2(1건) + B'-4(1건)
**Phase 9+ defer (3건)**: pg_trgm + /metrics 포트 분리 + RSS auto-fetch

---

## 8. 비즈니스 메트릭 (KPI)

Phase 8 완료 후 측정. Phase 7 PostHog + Prometheus + AWS SES baseline 위에서 신규 지표 추가.

| KPI | 측정 도구 | 목표 | 담당 sub-PDCA |
|-----|----------|:----:|:-------------:|
| **HTTP p50 latency** | Prometheus + OTEL X-Ray | ≤ 100ms | G''-1 |
| **HTTP p95 latency** | Prometheus + OTEL X-Ray | ≤ 200ms | G''-1 |
| **HTTP p99 latency** | Prometheus + OTEL X-Ray | ≤ 500ms | G''-1 |
| **DB connection pool 사용률** | Prometheus pool metrics | ≤ 80% (평균) | G''-4 |
| **Redis cache hit rate** | Prometheus cache metrics | ≥ 70% | G''-2 |
| **OpenTelemetry trace coverage** | X-Ray sampled traces | ≥ 80% 핵심 endpoint | G''-1 |
| **Frontend bundle initial size** | next/bundle-analyzer + Lighthouse | ≤ 200KB | G''-5 |
| **Lighthouse performance score** | Lighthouse CI | ≥ 85 | G''-5 |
| **Multi-currency 결제 conversion rate** | Stripe dashboard + PostHog | baseline 측정 시작 | B'-1 |
| **DM 일일 active 사용자 (DAU)** | PostHog custom event | baseline 측정 시작 | B'-2 |
| **Push notification open rate** | FCM/APNs delivery receipt | ≥ 20% (업계 평균) | B'-3 |
| **Email digest open rate** | AWS SES + SES receipt | ≥ 30% (C-5 baseline 기준) | B'-3 + H'-5 |
| **Subscription 자동 갱신 성공률** | Stripe billing + audit log | ≥ 95% | B'-4 |
| **후원자 D1/D7/D30 cohort retention** | PostHog cohort + B'-5 dashboard | baseline 측정 시작 | B'-5 |
| **Winback coupon redemption rate** | Stripe + PostHog | ≥ 20% (G'-2 baseline 기준) | B'-5 |
| **Newsletter open rate (bounce 제거 후)** | AWS SES (H'-5 보강 후) | ≥ 30% | H'-5 + B'-5 |

**정성 KPI**:
- 글로벌 후원자(KRW/EUR/JPY) 첫 결제 사례 발생 — B'-1 multi-currency 실제 효과 측정
- 작가-후원자 DM 대화 1:1 관계 심화 — B'-2 DM messaging retention 기여 측정
- Push notification으로 휴면 사용자 재활성화율 — B'-3 winback push 효과

---

## 9. Out of Scope (Phase 9+)

Phase 8에서 명시적으로 제외. 이후 로드맵에서 처리.

| 항목 | 이유 | 예상 Phase |
|------|------|:----------:|
| **Mobile native 앱** (React Native/Flutter) | 웹 안정화 우선. B' 후원 maturity 달성 후 앱 진입 | Phase 9+ |
| **P3-1 커뮤니티/그룹** (학교/장르/국가 게시판) | B'-2 DM 1:1 완성 후 Group으로 확장. 별도 P3 roadmap | Phase 9 별도 |
| **ML feed v2** (collaborative filtering) | PostHog + H'-6 데이터 축적 후. 50k+ events 필요 | Phase 9+ |
| **AI 작품 캡션 자동 생성** | LLM Gateway 활용 가능하나 범위 확대 우선순위 낮음 | Phase 9+ |
| **Featured Artist AI 추천** | ML v2 이후. Phase 7 G'-7 admin 큐레이션 유지 | Phase 9+ |
| **Real-time collaborative editing** | 복잡도 + 인프라 비용. 필요성 검증 후 | Phase 10+ |
| **DM Group 메시징** | B'-2 1:1 완성 후 P3-1 Community와 통합 계획 | P3-1 Phase 9 |
| **pg_trgm fuzzy search** | DB extension 별도 DBA 검토. Phase 8 범위 밖 | Phase 9+ |
| **/metrics 포트 분리 + Bearer rotation** | 인프라 PDCA 별도. Prometheus 이미 production-ready | Phase 9+ |
| **RSS auto-fetch cron** | H'-4 필수 작업 완료 후 시간 허용 시. 미디어 파트너 협의 필요 | Phase 9+ |
| **B2B 리포트** (갤러리/학교 파트너십) | 파트너십 체결 후 | Phase 9+ |
| **WebSocket 실시간 경매 bid** | 인프라 비용 + 복잡도. SSE/polling 현행 유지 | Phase 9+ |

---

## 10. README 비즈니스 비전 매핑

| README 비전 | Phase 8 sub-PDCA | 구현 방식 |
|------------|:----------------:|----------|
| "동유럽이든 남미든 동아시아든 **엄청난 꿈과 희망**" — 글로벌 신진작가 후원 | **B'-1** | USD/KRW/EUR/JPY 4 currency Stripe 결제 + 환율 cron + 사용자 preferred_currency — 국경 없는 후원 실현 |
| "유저들이 늘어나야 소비자들도 늘어남" — 그로스해킹 retention | **B'-2 + B'-3** | DM messaging 후원자-작가 관계 deepening + Push/Email 알림 retention 강화 |
| "**AI 세상으로 가면 갈수록 예술가들이 제일 먼저 굶어 죽음**" — 작가 수익 안정화 | **B'-4 + B'-1** | Stripe 자동 갱신 deep integration + multi-currency 후원으로 글로벌 수익 안정화 |
| "후원 개념을 넣고 **후원할 수 있는 구조를 만듦**" — 후원 인프라 성숙 | **B'-4 + B'-5** | 자동 갱신 성공률 ≥95% + 후원자 retention 대시보드로 후원 구조 완성 |
| "전 세계 아티스트들의 **인덱스를 만들고 싶음**" — 글로벌 신진작가 가시성 | **G''-2 + B'-5** | artist_index ranking Redis 1h TTL 캐시 + 후원자 cohort retention 대시보드 통합 |
| "히스토리를 두세 개 만든다" — 성공 사례 확산 | **H'-3 + H'-4** | OG SEO locale meta + click tracking → 외부 미디어 트래픽 측정 + 글로벌 공유 강화 |
| "컬렉터들한테는 **회비 1년에 10분씩**" — 구독 수익 모델 | **B'-4 + H'-5** | Stripe 자동 갱신 + newsletter bounce 제거로 구독자 이탈 최소화 |

---

## 11. Phase 5~7 Lessons Applied (Phase 8 적용 방침)

| 학습 사항 | Phase 8 적용 방식 |
|----------|-----------------|
| **권장 default 일괄 수락 패턴** (Phase 5/6/7 OQs 모두 권장 채택, 협상 라운드 0) | Phase 8 OQ-1~OQ-12 동일 표 형식 + 권장 default 명시. "권장대로" 응답 시 즉시 G'' 진입 |
| **Wave 기반 병렬 위임** (최대 5 agents 동시, 시간 단축 ~40%) | G'' 5개 동시 병렬 + H' 5개 동시 병렬 + B' B'-2+B'-3 병렬, B'-4+B'-5 병렬 |
| **alembic revision ID 충돌 감지 + linter auto-rename** | B' 시작 전 0059(optional G''-3)/0060(B'-1)/0061(B'-2) 배정표 사전 정의. `alembic heads` 자동 감지 |
| **R-5 cron 격리 표준** (Phase 5→7 누적 8 workers 모두 R-5 격리 일관) | B'-3 push/email이 **9번째 cron worker** — 동일 R-5 패턴 (별도 파일 + AsyncSessionLocal + 별도 lifespan task) |
| **Mock 모드 fallback** (PostHog/Stripe/LLM/SES 모두 Mock 지원) | G''-1 OTEL: OTEL_EXPORTER_OTLP_ENDPOINT 미설정 → noop. G''-2 Redis: REDIS_URL 미설정 → in-memory. B'-3 Push: FCM_SERVER_KEY 미설정 → mock |
| **Booster 패턴** (기존 sub-PDCA 재사용, 신규 기술 도입 0) | G''-2 Redis → G'-9 post_engagement_cache hit rate. B'-4 → G'-1 webhook subscription 이벤트 재사용. B'-5 → G'-2 winback coupon redemption rate + C-5 newsletter open rate |
| **Critical Path 선결 강화** (G'-1/C-1이 각 단계 선결) | G'' = 5개 독립(병렬). H' = 5개 독립(병렬). B' = B'-1(Critical Path) 단독 선결 |
| **i18n namespace 분리 strict** (15 sub-PDCAs, race condition 0) | Phase 8 16 sub-PDCAs 다른 namespace 사전 배정: `otel.*` `redis.*` `dm.*` `push.*` `currency.*` `billingRenewal.*` `patronageAnalytics.*` `a11yAudit.*` `cjkFont.*` |
| **Schema Sync Checklist** (각 Design 단계 BE/FE schema pair) | B'-1 currency 모델 + frontend currency switcher type. B'-2 Conversation/Message 모델 + DM UI type. B'-3 device token 모델 + push payload type |

---

## 12. 다음 액션

### Phase 8 시작 전 체크리스트

1. **alembic upgrade head 실행 확인** (OQ-11=A 권장 — Phase 7 0058 포함)
2. **OQ-1~OQ-12 결정** — "권장대로" 일괄 수락 시 즉시 G''-1~G''-5 병렬 진입 가능
3. **G'' 병렬 전략 확인** (OQ-1=B 권장: G''-1~G''-5 동시)
4. **alembic revision ID 사전 배정** (0059=G''-3 optional, 0060=B'-1, 0061=B'-2)
5. **AWS ElastiCache 인프라 확인** (OQ-3=A 채택 시 ElastiCache cluster 생성)

### G'' 단계 진입 명령 (OQ-1=B 병렬 채택 시)

```bash
# 5개 동시 병렬 시작
/pdca plan opentelemetry-tracing            # G''-1
/pdca plan redis-cache-layer                # G''-2
/pdca plan n-plus-one-audit                 # G''-3
/pdca plan db-connection-pool-tuning        # G''-4
/pdca plan frontend-bundle-optimization     # G''-5
```

### H' 단계 진입 명령 (G'' 완료 후)

```bash
# 5개 동시 병렬 시작
/pdca plan voiceover-nvda-test-fix          # H'-1
/pdca plan cjk-font-pdf-embedding           # H'-2
/pdca plan multi-language-seo-meta          # H'-3
/pdca plan click-tracking-rss-thumbnail     # H'-4
/pdca plan newsletter-bounce-handling       # H'-5
# H'-6는 시간 허용 시
/pdca plan ml-feed-personalization-prep     # H'-6
```

### B' 단계 진입 명령 (H' 완료 후)

```bash
# Critical Path (먼저 단독 시작)
/pdca plan multi-currency-foundation        # B'-1

# B'-1 완료 후 병렬
/pdca plan dm-messaging                     # B'-2
/pdca plan push-email-digest-foundation     # B'-3

# B'-2/B'-3 완료 후 병렬
/pdca plan stripe-billing-auto-renewal      # B'-4
/pdca plan patronage-analytics-dashboard    # B'-5
```

---

## 13. 결정 기록 (Decisions Log)

### 2026-05-04 — Phase 8 로드맵 초안 (product-manager)

| 결정 | 내용 | 근거 |
|------|------|------|
| Phase 8 구조 | G''(4주) → H'(3주) → B'(6주) = 총 13주 순차 | 사용자 전략 결정: option G+H sequential → B sequential |
| G'' sub-PDCAs | 5개 필수 (G''-1~G''-5) | G'-12/G'-13 deferred 본격 흡수 + perf 최적화 추가 |
| H' sub-PDCAs | 6개 (H'-1~H'-6, H'-6 선택) | Phase 7 carry-over 16건 중 13건 청산 목표. ML 데이터(H'-6) 낮은 우선순위 |
| B' sub-PDCAs | 5개 필수 (B'-1~B'-5) | README 비전 multi-currency + DM + Push = Patronage Maturity |
| B'-1 Critical Path | multi-currency-foundation 단독 선결 | currency 없이 DM/Push currency-aware 구현 불가. Stripe FX dependency |
| OQ-3 Redis | AWS ElastiCache (A 권장) | AWS 인프라 통합 일관성 + managed |
| OQ-4 OTEL Backend | AWS X-Ray (B 권장) | AWS SES + ElastiCache 통합 일관성 |
| OQ-5 Multi-currency | 4 currency Full (C 권장) | README 글로벌 비전 직접 구현 — USD/KRW/EUR/JPY |
| OQ-7 DM 모델 | 1:1 only (A 권장) | P3-1 Community와 분리 — 단순. 모더레이션 복잡도 최소화 |
| OQ-8 Push 인프라 | FCM + APNs (B 권장) | iOS 글로벌 사용자 포함. Mock 모드 fallback으로 개발 부담 0 |
| R-5 cron 격리 | B'-3 push/email = 9번째 worker | Phase 5→7 8 workers R-5 격리 일관성 유지 |
| alembic 배정 | 0059(G''-3 선택) + 0060(B'-1) + 0061(B'-2) | Phase 6/7 충돌 방지 사전 배정 패턴 재현 |

---

## Version History

| 버전 | 날짜 | 변경사항 | 작성자 |
|------|------|---------|--------|
| 0.1 | 2026-05-04 | Phase 8 로드맵 초안. G''(5 sub-PDCA) + H'(6 sub-PDCA) + B'(5 sub-PDCA) = 16 sub-PDCAs. 12 OQs (권장 default 포함). Phase 7 carry-over 16건 매핑 §7. README 비전 매핑 §10. Phase 5~7 lessons §11. | itpe-ince (Claude Sonnet 4.6 / product-manager) |
