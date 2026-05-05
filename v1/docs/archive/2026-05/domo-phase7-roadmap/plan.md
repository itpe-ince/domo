---
template: plan
version: 1.0
feature: domo-phase7-roadmap
date: 2026-05-04
author: itpe-ince (Claude Sonnet 4.6)
project: domo
project_version: v1
parent_roadmap: Phase 7 (G': Carry-over Consolidation → C: Press Kit & PR Automation)
status: Draft (Roadmap)
---

# Domo Phase 7 — 로드맵 (Master Plan)

> **Summary**: Phase 6 종결(12/13 sub-PDCA, 92%, 2026-05-04) 후 두 단계를 순차 진행한다. G': Carry-over Consolidation(2~3주, G'-1~G'-10 필수 + G'-11~G'-13 선택) — Phase 6 종결 시 남은 carry-over 18건 청산 + Stripe webhook maturity 달성. C: Press Kit & PR Automation(6주, C-1~C-5 필수 + C-6~C-7 선택) — README 핵심 비전 "히스토리/유튜브/일간지/라디오" 마케팅 채널을 플랫폼으로 자동화. AI 인터뷰 생성 + press kit PDF 자동 배포 + multi-language story + media coverage CMS + newsletter digest. 총 15~20 sub-PDCA, 8~9주 계획.
>
> **Project**: domo (v1)
> **Author**: itpe-ince
> **Date**: 2026-05-04
> **Status**: Roadmap (Sub-PDCA 인덱스. 각 항목은 별도 plan 문서로 본격 진입)

---

## 0. Phase 7 배경 & 전략적 의미

### Phase 6 종결 성과

Phase 6는 12/13 sub-PDCA 92% 완료(2026-05-04). D' 5/6 (D'-6 deferred) + A 8/8. 주요 성과:

- **그로스해킹 깔때기 완성**: PostHog 14 events + 4 funnels + Onboarding 3-step wizard + Feed algorithm v1 SQL-only
- **신진작가 인덱스 v1**: weighted score ranking cron (recent 0.5 + sales 0.25 + supporters 0.15 + tenure 0.10) + `/artists/index` 공개 페이지 + tier badge
- **스토리텔링 허브**: 작가 auto timeline (6 milestones) + `/stories` hub + Featured Artist 섹션
- **Stripe Coupon SDK**: CouponProvider 추상화 (Mock + Real) + admin/me coupon UI + idempotency
- **인프라 확장**: alembic 0049 + 16 신규 endpoints + 6 backend services + 30+ frontend components + ~1100 i18n entries × 5 locales
- **누적 지표**: 147→207 passed (+60 tests) + tsc 0 + Prometheus 14 metrics + PostHog 14 events

### Phase 7가 중요한 이유

Phase 6까지는 "사용자가 플랫폼에서 작가를 발견하고 후원하는 그로스해킹 깔때기" 내부 구조를 완성했다. Phase 7의 핵심은 두 가지다:

**1. G' — Tech Debt 청산**: Phase 6 종결 시 명시된 carry-over 18건 중 D'-6 Stripe webhook을 포함한 핵심 부채를 청산해 인프라 안정성을 높인다. Stripe webhook idempotency + winback coupon + a11y + posthog backend SDK + Jest 테스트 환경 등이 대상.

**2. C — 마케팅 허브 본격 진입**: README 비전의 "외부 마케팅" 레이어를 본격 구현한다. A-7 스토리텔링 허브가 내부 작가 타임라인을 만들었다면, Phase 7 C 단계는 그 콘텐츠를 **외부 미디어(유튜브/일간지/라디오)**로 자동화 배포하는 채널을 연다.

README 비전 직접 인용:

> "히스토리를 두세 개 만든다고 치면 남미 페루에 사는 어떤 대학생 여자애가 그림을 하나 올려서 30만 원에 팔아보려고 했는데 … **히스토리를 유튜브도 만들겠지만 일간지라든지 라디오 같은 데서 풀 수 있음**."

> "**AI 세상으로 가면 갈수록 예술가들이 제일 먼저 굶어 죽음**" — AI 시대 예술가 생존을 위한 LLM 자동화 인터뷰/번역/press kit 생성이 Phase 7 C의 핵심.

> "컬렉터들한테는 **회비 1년 회비로 10분씩 받겠다고 함**" — C-5 newsletter를 구독자 차별화 채널로 활용.

---

## 1. 비즈니스 컨텍스트

### Tech Debt 청산 후 마케팅 허브 진입 — Phase 7 전략 구조

```
[Phase 5] 후원 인프라 완성          →  [Phase 6] 그로스해킹 깔때기 완성
[Phase 7 G'] Tech Debt 청산         →  [Phase 7 C] 마케팅 허브 진입
  Stripe webhook maturity               AI 인터뷰 자동 생성
  winback coupon 실제 발행              Press Kit PDF 자동 배포
  a11y WCAG AA 완성                     Multi-language story (LLM)
  PostHog backend SDK                   Media Coverage CMS
  Jest 테스트 환경                       Newsletter Digest (구독자 차별화)
```

### 마케팅 허브 — README "히스토리/유튜브/일간지/라디오" 구현 전략

Phase 6 A-7이 작가 성장 히스토리 타임라인(내부)을 완성했다면, Phase 7 C는 그 히스토리를 **외부 채널**로 확산시키는 자동화 파이프라인을 구축한다:

```
작가 프로필 + 포트폴리오 + milestones
           ↓ (LLM auto-generate, C-1)
     AI 인터뷰 기사 (5 locale)
           ↓
   Press Kit PDF (C-2) ──→ 외부 미디어 배포 (일간지/유튜브/라디오)
           ↓
Multi-language Story (C-3) ──→ 글로벌 SEO + 공유
           ↓
Media Coverage CMS (C-4) ──→ 외부 노출 자료 누적
           ↓
Newsletter Digest (C-5) ──→ 컬렉터/후원자 구독 차별화
```

### 신진작가 인덱스 강화 — Phase 6 → Phase 7

Phase 6 A-6에서 전체 ranking(artist_index_score/rank)을 완성했다. Phase 7 G'-8은 `User.artist_index_rank_region` (alembic 0050)을 추가해 **지역별/장르별 별도 ranking** + frontend filter 강화 + region top 10 카드를 구현한다. 이는 "동유럽/남미/동아시아 신진작가에게 꿈과 희망"이라는 README 비전의 지역 친화 구현이다.

### Stripe 인프라 성숙도 — G'-1 + G'-2

Phase 5에서 SetupIntent + Mock 모드를 완성하고, Phase 6 D'-3에서 Coupon SDK를 구축했다. Phase 7 G'에서 마지막 미완성 항목인 **webhook 이벤트 핸들러 확장**(G'-1)과 **winback coupon 실제 발행**(G'-2)을 완성해 Stripe 통합을 production-ready 수준으로 끌어올린다.

---

## 2. Phase 7 Sub-PDCA 목록

### G' 단계 — Carry-over Consolidation (2~3주)

Phase 6 종결 시 명시된 carry-over 18건 중 핵심 항목을 흡수한다. G'-1 Stripe webhook이 Critical Path이며 G'-1 완료 후 나머지를 병렬 진행한다.

#### 필수 G' sub-PDCAs (10개)

| # | Feature | 우선순위 | 추정 기간 | 의존성 | 핵심 산출물 | Phase 6 carry-over 출처 |
|---|---------|:-------:|:--------:|--------|------------|------------------------|
| **G'-1** | `stripe-webhook-extension` | **Must** | ~3일 | 없음 (Critical Path) | payment_intent.succeeded/failed/requires_action + invoice.payment_failed + customer.subscription.deleted + charge.dispute.created handler. webhook signing secret + idempotency key + audit log + Notification 자동 생성 | D'-6 deferred (OQ-2=B) |
| **G'-2** | `winback-coupon-endpoint` | **Must** | ~2일 | G'-1 ✅ 권장 | POST `/v1/subscriptions/{id}/winback-coupon`. CancelSubscriptionModal "월 50% 할인 1개월" 클릭 → 즉석 Stripe Coupon.create + Subscription.modify + cancel 자동 무효화. 취소 사유 라디오 → coupon 매핑 (too_expensive→50% 1mo, changed_mind→30% 1mo, not_satisfied→DM link). 1/day/subscription rate limit | D'-3 AC carry-over (B-5 winback-coupon) |
| **G'-3** | `a11y-tailwind-cleanup` | **Must** | ~3일 | 없음 (독립) | `text.muted` (#7A6F60→3.8:1) + `border` (#3D2F24→1.4:1) tailwind.config 색상 조정 (시각 회귀 spot check). OEmbedInput/SchedulePicker `<h4>` heading 정정 + 한국어 hardcode 외재화 + axe-core CI 통합 | D'-4 color contrast carry-over + B-6 heading hierarchy carry-over |
| **G'-4** | `backend-posthog-integration` | **Must** | ~2일 | 없음 (독립) | posthog Python SDK 추가 + server-side events (signup confirmation 후 + Notification 발송 + cron worker 결과). PII redact + GDPR opt-out 적용 + frontend events와 user_id 통합 | A-1 backend Python SDK carry-over |
| **G'-5** | `jest-test-runner-setup` | **Must** | ~1일 | 없음 (독립) | Jest + ts-jest + jest-environment-jsdom 설치 + analytics events 테스트 실행 환경 + i18n provider mock + tsconfig test exclude 정리 | A-1 Jest runner carry-over |
| **G'-6** | `dynamic-og-card` | **Must** | ~2일 | 없음 (독립) | `/users/[id]/timeline/opengraph-image.tsx` (Next.js next/og) + 작가 프로필 OG + 작품 OG + sponsor success OG. C 단계 외부 마케팅 hook의 선결 의존성 | A-7 dynamic OG card carry-over (next/og 별도) |
| **G'-7** | `admin-featured-artists` | **Should** | ~1.5일 | G'-6 ✅ 권장 | `app/admin/featured-artists/page.tsx` 월간 Featured 작가 큐레이션 UI + system_settings.featured_artist_id_current + admin POST/GET endpoints + /stories hub fetch 통합 | A-7 admin Featured Artist UI + monthly curation carry-over |
| **G'-8** | `region-genre-ranking` | **Should** | ~3일 | 없음 (독립) | alembic 0050 (User.artist_index_rank_region 컬럼 추가) + 지역별/장르별 별도 ranking 계산 로직 보강 + frontend region/genre filter 강화 + /artists/index region top 10 카드 | A-6 Region별/Genre별 ranking carry-over |
| **G'-9** | `post-engagement-cache` | **Should** | ~2일 | 없음 (독립) | alembic 0051 + post_engagement_cache 테이블 + cron (1h, R-5 격리 패턴 적용) + feed_v1 cache 활용으로 inline subquery 제거 + perf benchmark + Prometheus metrics 추가 | A-3 post_engagement_cache carry-over |
| **G'-10** | `price-unit-consistency` | **Must** | ~1일 | 없음 (독립) | Post.price `Numeric(12,2)` vs A-5 search filter cents 단위 불일치 해소. cents 채택 권장 + 모든 API 응답/요청 단위 통일 + DB 마이그레이션 (alembic 0052) | A-5 price filter 단위 통일 carry-over |

**G' 필수 단계 병렬화 계획** (OQ-1 B 권장 기준):
```
Day 1~3 [Critical Path]: G'-1 (stripe-webhook-extension) — 선결
Day 1~3 [병렬 그룹 A]:  G'-3 + G'-4 + G'-5 + G'-6 + G'-8 + G'-9 + G'-10 동시
Day 3~5 [순차]:          G'-2 (G'-1 완료 후 — winback coupon은 webhook 안정화 후 권장)
Day 3~6 [순차]:          G'-7 (G'-6 완료 후 — Featured Artist는 OG card 통합 권장)
```

#### 선택 G' sub-PDCAs (3개, 사용자 추후 결정)

| # | Feature | 우선순위 | 추정 기간 | 비고 |
|---|---------|:-------:|:--------:|------|
| G'-11 | `voiceover-nvda-test` | Could | ~1일 | 실제 VoiceOver/NVDA 테스트 결과 docs 작성. 사용자 측 manual test 필요 — 자동화 불가 영역 | D'-4 VoiceOver/NVDA carry-over |
| G'-12 | `opentelemetry-tracing` | Could | ~2일 | distributed tracing 통합. Prometheus 안정화 후 단계적 도입 권장 | D-6 Phase 5 carry-over |
| G'-13 | `redis-cache-layer` | Could | ~2일 | Redis 도입 + popular search 5min TTL + feed scoring cache. 트래픽 증가 대비 | A-5 Redis 인기 검색어 carry-over |

**G' 완료 기준**: 10 필수 sub-PDCAs archived + Phase 6 carry-over 18건 중 13건 청산 + G' 부채 0 상태로 C 단계 진입

---

### C 단계 — Press Kit & PR Automation (6주)

README 비전 "히스토리/유튜브/일간지/라디오" 마케팅 채널 직접 구현. A-7 스토리텔링 허브 위에 **외부 마케팅 자동화** 파이프라인 추가. tuzigroup LLM Gateway (gemma4-e4b) 활용.

#### 필수 C sub-PDCAs (5개)

| # | Feature | 우선순위 | 추정 기간 | 의존성 | 핵심 산출물 | 비고 |
|---|---------|:-------:|:--------:|--------|------------|------|
| **C-1** | `ai-artist-interview-generation` | **Must** | ~7일 | G' 완료 (**Critical Path**) | 작가 프로필 + portfolio + milestones → LLM 자동 인터뷰 기사 생성. tuzigroup LLM Gateway (LLM_GATEWAY_URL + LLM_GATEWAY_APIKEY + LLM_MODEL_NAME=gemma4-e4b) 활용. admin 검수 workflow + 작가 opt-in + i18n 5 locale 자동 번역. interview_articles 모델 + admin UI + 작가 프로필 통합 | C 단계 전체의 콘텐츠 소스 |
| **C-2** | `press-kit-auto-export` | **Must** | ~5일 | C-1 ✅ | 작가별 press kit PDF 자동 생성. 작가 소개 + 대표작 5점 + AI 인터뷰 (C-1) + ranking badge + sponsor 통계 + 연락처. Pillow + reportlab backend 생성 + idempotency_key. 다운로드 endpoint (`GET /artists/{id}/press-kit/pdf`) + admin trigger UI | 외부 미디어 자료원 (일간지/라디오/유튜브) |
| **C-3** | `multi-language-story` | **Must** | ~5일 | C-1 ✅ | A-7 storytelling-hub 5 locale 확장. milestone text LLM Gateway 자동 번역 + 작가 bio multi-language input + Next.js i18n routing SEO meta + OG card multi-language (G'-6 기반). 외부 글로벌 공유 강화 | 글로벌 신진작가 접근성 |
| **C-4** | `media-coverage-cms` | **Should** | ~3일 | G'-7 ✅ 권장 | system_settings.media_coverage 또는 별도 MediaCoverage 모델로 외부 미디어 노출 관리. admin UI: 기사/유튜브/라디오 link + 썸네일 + 발행일 + 작가 tag. 공개 표시 (/stories MediaCoverageGrid) + 작가 프로필 통합. A-7 MediaCoverage placeholder 구현 완성 | A-7 carry-over 완성 |
| **C-5** | `newsletter-digest` | **Should** | ~5일 | C-1 ✅, 이메일 인프라 | 주간/월간 newsletter 자동 발송. Featured Artist + 신진작가 ranking changes + 후원자 alert + new posts highlight. AWS SES (OQ-6 B 권장) + opt-in/out + GDPR. "컬렉터 회비 1년 회비로 10분씩" — 구독자 차별화 채널 | A-8 push/email digest carry-over |

**C 단계 실행 순서**:
```
C-1 (AI Interview Generation — Critical Path 시작, 콘텐츠 소스 선결 필수)
  ↓
C-2 + C-3 (병렬 — Press Kit PDF + Multi-language Story)
  ↓
C-4 (Media Coverage CMS — C-1/G'-7 기반)
  ↓
C-5 (Newsletter Digest — C-1 콘텐츠 소스 활용)
```

#### 선택 C sub-PDCAs (2개)

| # | Feature | 우선순위 | 추정 기간 | 비고 |
|---|---------|:-------:|:--------:|------|
| C-6 | `youtube-integration` | Could | ~3일 | 작가 YouTube 채널 link + 자동 video embed + C-4 media coverage 연동 |
| C-7 | `press-kit-template-customization` | Could | ~2일 | 작가별 PDF template 선택 + 배경색/accent color 커스터마이징 |

**C 완료 기준**: 5 필수 sub-PDCAs archived + 외부 마케팅 hook (AI 인터뷰 + PDF press kit + multi-language + media coverage + newsletter) production-ready

---

## 3. Open Questions

사용자 결정 필요 항목. **"권장대로" 한 번에 수락 시 즉시 G' 진입 가능**.

| ID | 질문 | 옵션 | 권장 default | 근거 |
|----|------|------|:------------:|------|
| OQ-1 | G' 진행 방식 | A: 10 순차 / **B: 독립 병렬 (G'-1 Critical Path → G'-3+G'-4+G'-5+G'-6+G'-8+G'-9+G'-10 동시 + G'-2 단독 + G'-7 순차)** / C: 우선순위 분리 (G'-1 first → 나머지 병렬) | **B** | Phase 6 패턴 — 독립 항목 병렬화로 시간 절약. G'-1이 Critical Path이지만 나머지는 대부분 독립적 |
| OQ-2 | G' 선택 sub-PDCAs (G'-11~G'-13) 포함 여부 | A: 모두 포함 (G' 13개) / B: G'-12 OpenTelemetry만 / **C: 모두 carry-over Phase 8+** / D: G'-13 Redis만 (트래픽 대비) | **C** | G' 2~3주 목표 달성 우선 — 선택 항목은 별도 인프라 PDCA로 격리. Redis는 트래픽 증가 시 도입 |
| OQ-3 | LLM Provider for C-1 (AI 인터뷰 생성) | **A: tuzigroup LLM Gateway (기존 자격증명, 즉시 사용 가능)** / B: Anthropic Claude 직접 (전용 API key) / C: OpenAI GPT-4 / D: self-hosted (Llama/Mistral) | **A** | memory에 기존 자격증명 확인 (LLM_GATEWAY_URL + LLM_GATEWAY_APIKEY + LLM_MODEL_NAME=gemma4-e4b) — 즉시 사용. 추가 계약 불필요 |
| OQ-4 | PDF 생성 방식 (C-2) | **A: Backend Pillow + reportlab (Pillow 기존 활용)** / B: Frontend html2pdf (서버 부담 ↓) / C: Cloud service (Puppeteer/Browserless) / D: Admin manual (template 다운로드) | **A** | Pillow 기존 활용 + 백엔드 통합 + idempotency_key 적용 용이. Phase 6 A-7 OG image Pillow 패턴 재사용 |
| OQ-5 | multi-language LLM 자동 번역 (C-3) | **A: tuzigroup LLM Gateway (일관성 + 기존 자격증명)** / B: DeepL API / C: Google Translate / D: Manual (작가 직접 + admin 검수) | **A** | OQ-3과 동일 Gateway 활용 — 아키텍처 일관성. 비용 추가 없음 |
| OQ-6 | 이메일 인프라 (C-5) | A: SendGrid (SaaS 표준) / **B: AWS SES (cost-efficient + 인프라 통합 + scalability)** / C: Mailgun / D: self-hosted SMTP | **B** | cost-efficient (SES vs SendGrid ~10:1 절감) + AWS 인프라 통합 + 글로벌 전송률. 동남아/남미 타깃 확장에 적합 |
| OQ-7 | Newsletter 빈도 (C-5) | A: 매주 / B: 격주 / C: 매월 / **D: 사용자 선택 (기본값 매월)** | **D** | 사용자 선호 존중 + 스팸 신고 위험 최소화. opt-in 시 빈도 선택 UI 제공. 초기 운영 부담 적정 |
| OQ-8 | Featured Artist 큐레이션 주기 (G'-7 + C-5) | A: 매주 / B: 격주 / **C: 매월** / D: 분기별 | **C** | 매월 — 비즈니스 운영 부담 적정 + newsletter 발행 주기와 정렬 가능. Phase 6 A-7 계획과 일관성 |
| OQ-9 | Phase 7 종료 기준 | A: 15 sub-PDCAs (G' 10 + C 5) archived / **B: Phase 5/6 패턴 (모든 sub-PDCAs 100% archived)** / C: C 단계 KPI 측정 시작 (PR 자료원 N건 발행 + newsletter open rate ≥ 30%) | **B** | Phase 5/6와 동일 기준. 100% archived가 종결 기준. C 단계 KPI는 §4 AC에 추가 조건으로 명시 |
| OQ-10 | Phase 7 시작 트리거 | **A: Phase 6 alembic 0049 적용 확인 후 즉시** / B: 사용자 결정 대기 / C: G'-1 먼저 → 나머지 병렬 | **A** | Phase 6 마이그레이션 적용 완료 확인 즉시 진입. Phase 5/6와 동일 패턴 (OQ-8=A, OQ-10=A 일관성) |

---

## 4. Acceptance Criteria (Phase 7 종료 기준)

| ID | 기준 | 검증 방법 |
|----|------|----------|
| AC-1 | G' 10 필수 sub-PDCAs 모두 archived | `.pdca-status.json` G'-1~G'-10 phase="archived" |
| AC-2 | Phase 6 carry-over 18건 중 13건 청산 | §7 carry-over 매핑표 13건 ✅ |
| AC-3 | C 5 필수 sub-PDCAs 모두 archived | `.pdca-status.json` C-1~C-5 phase="archived" |
| AC-4 | 각 sub-PDCA Match Rate ≥ 90% (목표 평균 ≥ 95%) | 개별 analysis.md matchRate 필드 |
| AC-5 | Stripe webhook production-ready — 4개 이벤트 핸들러 + signing secret + idempotency + audit log | G'-1 AC — webhook signing secret 검증 + test mode 4 events 처리 확인 |
| AC-6 | AI 인터뷰 생성 production-ready — tuzigroup LLM Gateway + 5 locale 자동 번역 + admin 검수 workflow | C-1 AC — 샘플 작가 1명 인터뷰 생성 + 5 locale 번역 완료 확인 |
| AC-7 | Press Kit PDF production-ready — Pillow + reportlab 생성 + 다운로드 endpoint | C-2 AC — 샘플 press kit PDF 생성 + 파일 무결성 확인 |
| AC-8 | Newsletter opt-in/out + GDPR 준수 + AWS SES 발송 확인 | C-5 AC — test 발송 1건 + opt-out 동작 확인 |
| AC-9 | tsc 0 에러, 207 → N tests passed (회귀 0) | CI pipeline 자동 |
| AC-10 | 5 locale(ko/en/ja/zh/es) i18n — Phase 7 신규 feature 동시 5 locale 제공 | grep "[가-힣]" + locale parity 검증 |
| AC-11 | C 단계 KPI baseline 측정 시작 — Press kit 다운로드 1건 이상 + Newsletter open rate 수집 시작 | §8 KPI 측정 도구 연동 확인 |
| AC-12 | WCAG 2.1 AA — G'-3 color contrast fix + axe-core CI 통합 | axe-core CI 통과 + tailwind.config 색상 검증 |

---

## 5. Risks & Mitigation

| Risk | 영향 | 가능성 | 완화 방안 |
|------|:----:|:------:|----------|
| **Stripe webhook signature 위조** — webhook 수신 시 서명 검증 누락 시 replay attack 가능 | High | Medium | G'-1: `stripe.WebhookSignature.verify()` 필수 적용. STRIPE_WEBHOOK_SECRET env var + 시간 tolerance 5분. 서명 검증 실패 시 HTTP 400 즉시 반환. 테스트 시 Stripe CLI `stripe listen --forward-to` 활용 |
| **Stripe webhook idempotency** — 동일 event 중복 수신 시 중복 처리 위험 | High | High | G'-1: idempotency_key = stripe_event_id + DB UNIQUE constraint. 처리 전 `WHERE stripe_event_id = ? AND processed = true` 확인. SELECT FOR UPDATE SKIP LOCKED 패턴 (R-5 cron 격리 패턴 동일 적용) |
| **LLM 비용 + rate limit** — C-1 인터뷰 생성 대량 요청 시 Gateway 부하 | Medium | Medium | tuzigroup Gateway 기존 자격증명 활용 — 비용 추가 없음. rate limit: admin trigger 방식으로 bulk 방지 + 작가 opt-in 1회/월 제한 + 비동기 큐 처리 (async background task). retry backoff 구현 |
| **PDF 생성 timeout** — 대형 포트폴리오 (이미지 다수) press kit PDF 생성 시간 초과 | Medium | Medium | C-2: 이미지 최대 5장 고정 + Pillow 리사이징 사전 처리 + 비동기 생성 (status endpoint 폴링). PDF 생성 완료 전 S3 presigned URL 발급 대기. 생성 시간 목표 ≤ 10초 |
| **multi-language 일관성** — LLM 번역 품질 편차 (특히 ja/zh 전문 용어) | Medium | High | C-3: 인터뷰 기사 핵심 용어 glossary 사전 정의 + LLM prompt에 포함. admin 검수 workflow (작가 opt-in 후 admin confirm 전 공개 차단). 자동 번역 후 "기계 번역" 라벨 표시 (투명성) |
| **Newsletter 스팸 신고** — 대량 발송 시 AWS SES 평판 훼손 | High | Low | C-5: 이중 opt-in (confirm 이메일 필수) + 구독 취소 one-click (CAN-SPAM/GDPR). 초기 소규모(100명 이하) 발송 테스트 후 단계적 확대. bounce/complaint rate 모니터링 (SES dashboard). |
| **GDPR 준수** — AI 인터뷰 생성 시 작가 개인정보(프로필/작품) LLM 전송 | High | High | C-1: 작가 명시적 opt-in 필수 (콘텐츠 생성 동의). LLM Gateway 전송 전 PII 최소화 (이름/이메일 제외, 작품명/장르/milestone만 전송). data processing agreement 확인. GDPR Article 22 (자동화 결정) 공지 |
| **alembic 충돌** — G'-8/G'-9/G'-10 병렬 진행 시 revision ID 충돌 | Medium | High | Phase 6 A-5/A-8 패턴 적용: linter auto-rename 메커니즘 유지. G' 병렬 시작 전 revision ID 배정표 사전 정의 (0050 = G'-8, 0051 = G'-9, 0052 = G'-10). `alembic heads` 명령으로 충돌 감지 후 auto-rename |
| **winback coupon 남용** — G'-2 rate limit 우회 시 반복 할인 발급 | Medium | Low | G'-2: DB-level UNIQUE (subscription_id + date 조합) + Stripe max_redemptions=1 설정 + 발급 이력 audit log. coupon 이미 적용 중인 구독에 재발행 차단 |

---

## 6. Timeline & Milestones

```
Week 1~2 — G': Carry-over Consolidation (Tech Debt 청산)
┌─────────────────────────────────────────────────────────────────────┐
│ Day 1~3 [Critical Path]  G'-1 stripe-webhook-extension             │
│ Day 1~3 [병렬 그룹 A]    G'-3 + G'-4 + G'-5 + G'-6 동시 진행     │
│ Day 1~5 [병렬 그룹 B]    G'-8 + G'-9 + G'-10 동시 진행           │
│ Day 3~5 [순차]           G'-2 (G'-1 완료 후)                      │
│ Day 4~6 [순차]           G'-7 (G'-6 완료 후)                      │
│ Milestone: G' 완료 — Phase 6 carry-over 13건 청산 + Stripe maturity ✅ │
└─────────────────────────────────────────────────────────────────────┘

Week 3~4 — C-1: AI Artist Interview Generation (Critical Path)
┌─────────────────────────────────────────────────────────────────────┐
│ Day 1~7   LLM Gateway 통합 + 인터뷰 생성 + admin 검수 workflow    │
│ Milestone: AI 인터뷰 콘텐츠 소스 완성 — C 단계 모든 후속 의존성 ✅ │
└─────────────────────────────────────────────────────────────────────┘

Week 5~6 — C-2 + C-3: Press Kit PDF + Multi-language Story (병렬)
┌─────────────────────────────────────────────────────────────────────┐
│ C-2 Press Kit PDF (5일) — Pillow + reportlab + 다운로드 endpoint  │
│ C-3 Multi-language Story (5일) — LLM 번역 + Next.js i18n SEO     │
│ Milestone: 외부 미디어 배포 자료 (PDF) + 글로벌 공유 페이지 ✅     │
└─────────────────────────────────────────────────────────────────────┘

Week 7 — C-4: Media Coverage CMS
┌─────────────────────────────────────────────────────────────────────┐
│ Day 1~3  admin UI + MediaCoverage 모델 + /stories 통합            │
│ Milestone: 외부 미디어 노출 자료 누적 관리 시스템 ✅               │
└─────────────────────────────────────────────────────────────────────┘

Week 8~9 — C-5: Newsletter Digest
┌─────────────────────────────────────────────────────────────────────┐
│ Day 1~5  AWS SES 설정 + opt-in/out + GDPR + digest 자동 생성     │
│ Milestone: 구독자 차별화 newsletter 채널 production-ready ✅       │
└─────────────────────────────────────────────────────────────────────┘

Phase 7 종결
┌─────────────────────────────────────────────────────────────────────┐
│ 전체 archive + KPI baseline 측정 확인 + Phase 8 backlog 정리       │
│ Milestone: Phase 7 종결 — 15/15 sub-PDCAs archived ✅             │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 7. Dependencies & Phase 6 Carry-over Mapping

Phase 6 종결 보고서에 명시된 carry-over 18건 → G' + C sub-PDCAs 흡수 매핑:

| # | Carry-over 원본 | 출처 | Phase 7 흡수 | 처리 내용 |
|---|----------------|------|:------------:|----------|
| 1 | D'-6 Stripe webhook 확장 | OQ-2=B deferred | **G'-1** | payment_intent 4종 + invoice.payment_failed + subscription.deleted + dispute.created handler |
| 2 | B-5 winback-coupon endpoint | D'-3 AC carry-over | **G'-2** | POST /subscriptions/{id}/winback-coupon + 취소 사유 → coupon 매핑 + rate limit |
| 3 | post_engagement_cache alembic + cron | A-3 carry-over | **G'-9** | alembic 0051 + 1h cron (R-5 격리) + feed_v1 inline subquery 제거 |
| 4 | SQL-only tier filter | A-6 carry-over | **G'-10 범위 포함** | price 단위 통일과 함께 A-5/A-6 DB 일관성 청산 |
| 5 | Region별/Genre별 별도 ranking | A-6 carry-over | **G'-8** | alembic 0050 + rank_region 컬럼 + 별도 ranking 계산 + frontend filter |
| 6 | Featured Artist admin UI + monthly curation | A-7 carry-over | **G'-7** | admin/featured-artists 페이지 + system_settings + /stories 통합 |
| 7 | dynamic OG card (next/og) | A-7 carry-over | **G'-6** | /users/[id]/timeline/opengraph-image.tsx + 작가/작품/sponsor OG |
| 8 | POST /me/subscriptions/{id}/renew | A-8 carry-over | **G'-1 통합** | G'-1 webhook succeeded 이후 renewal 플로우 연동 (별도 sub-PDCA 불필요) |
| 9 | pg_trgm fuzzy match | A-5 carry-over | Phase 8+ | DB extension 별도 검토 필요 |
| 10 | price filter 단위 통일 (cents vs Numeric(12,2)) | A-5 carry-over | **G'-10** | alembic 0052 + cents 채택 + 모든 API 단위 통일 |
| 11 | backend posthog Python SDK | A-1 carry-over | **G'-4** | posthog Python SDK + server-side events + user_id 통합 |
| 12 | Jest test runner | A-1 carry-over | **G'-5** | Jest + ts-jest + jest-environment-jsdom + i18n mock |
| 13 | color contrast + h1→h3 hierarchy | D'-4 carry-over | **G'-3** | tailwind.config 색상 조정 + heading hierarchy + axe-core CI |
| 14 | VoiceOver/NVDA real test | D'-4 carry-over | **G'-11 (선택)** | 사용자 측 manual test 필요 |
| 15 | /metrics 포트 분리 + Bearer token rotation | D'-5 carry-over | Phase 8+ | 인프라 PDCA 별도 (트래픽 증가 시) |
| 16 | OpenTelemetry distributed tracing | D-6 Phase 5 carry-over | **G'-12 (선택)** | Prometheus 안정화 후 단계적 도입 |
| 17 | push/email digest | A-8 carry-over | **C-5** | C-5 newsletter-digest로 흡수. AWS SES 기반 구현 |
| 18 | DM messaging | B-5 carry-over | Phase 8+ | 별도 P3 또는 Phase 8+ PDCA |

**G' 필수(G'-1~G'-10)**: carry-over 12건 청산
**C 필수(C-5)**: carry-over 1건 (push/email digest) 흡수
**선택(G'-11/G'-12)**: carry-over 2건
**Phase 8+ deferred**: carry-over 3건 (pg_trgm, /metrics 포트 분리, DM messaging)

---

## 8. 비즈니스 메트릭 (KPI)

Phase 7 완료 후 측정. Phase 6 PostHog + Prometheus baseline 위에서 신규 지표 추가.

| KPI | 측정 도구 | 목표 | 비고 |
|-----|----------|:----:|------|
| **Newsletter open rate** | AWS SES + PostHog | ≥ 30% | 업계 평균 21% 대비 높음 목표 — 신진작가 팬층 niche 타깃 |
| **Newsletter click-through rate** | AWS SES + PostHog | ≥ 5% | Featured Artist CTA 클릭 |
| **Press kit 다운로드 횟수/월** | PostHog custom event | ≥ 10건/월 | 외부 미디어 관심 지표 |
| **AI 인터뷰 기사 발행 건수** | DB interview_articles | ≥ 20건 (Phase 7 기간) | 콘텐츠 파이프라인 활성도 |
| **Multi-language story page views** | PostHog + Next.js Analytics | baseline 측정 시작 | 5 locale 별 분석 |
| **외부 미디어 게재 건수** | C-4 media coverage CMS | ≥ 3건 (Phase 7 기간) | 일간지/유튜브/라디오 실제 게재 |
| **Stripe webhook 이벤트 처리 성공률** | Prometheus + audit log | ≥ 99.9% (drop rate ≤ 0.1%) | G'-1 idempotency + signing secret 효과 |
| **Winback coupon 전환율** | Stripe + PostHog | ≥ 20% (쿠폰 발행 → 구독 유지) | G'-2 too_expensive→50% 할인 효과 |
| **Backend PostHog event coverage** | posthog Python SDK | ≥ 5 server-side events | G'-4 backend SDK 효과 |
| **Artist Index region ranking 정확도** | DB + cron audit | 1h 이내 갱신 | G'-8 region_rank 정확성 |
| **Press kit → 작가 문의 전환** | 외부 채널 (정성) | 측정 시작 | 미디어 PR 효과 측정 |

**정성 KPI**:
- 외부 미디어(유튜브/일간지/라디오) 게재 후 작가 SNS 팔로워 증가 (측정 어렵지만 작가 대상 설문)
- 작가 NPS: "이 플랫폼의 press kit 기능이 실제 홍보에 도움이 됩니까?" (C 단계 후 설문)

---

## 9. Out of Scope (Phase 8+)

Phase 7에서 명시적으로 제외. 이후 로드맵에서 처리.

| 항목 | 이유 | 예상 Phase |
|------|------|:----------:|
| **DM messaging** | 비용 + 모더레이션 복잡도. 커뮤니티 P3 이후 | P3 또는 Phase 8+ |
| **multi-currency** (KRW/EUR/JPY) | Stripe currency 분기 + FX risk. 별도 PDCA 필요 | Phase 8+ |
| **모바일 native 앱** (React Native/Flutter) | 웹 안정화 우선. 트래픽 확보 후 | Phase 8+ |
| **P3-1 커뮤니티/그룹** | 별도 P3 roadmap. 유저 100+ 조건부 | P3 별도 |
| **ML feed 알고리즘 v2** | Phase 6 SQL-only 데이터 축적 후. 50k+ events 필요 | Phase 8+ |
| **VoiceOver/NVDA real test** | 사용자 측 manual test 필요 (G'-11 선택) | G'-11 선택 또는 Phase 8+ |
| **OpenTelemetry distributed tracing** | Prometheus 안정화 후 단계적 (G'-12 선택) | G'-12 선택 또는 Phase 8+ |
| **Redis cache layer** | 트래픽 증가 대비 (G'-13 선택) | G'-13 선택 또는 Phase 8+ |
| **pg_trgm fuzzy match** | DB extension 별도 검토 + DBA 승인 필요 | Phase 8+ |
| **/metrics 포트 분리 + Bearer rotation** | 인프라 PDCA 별도. Prometheus 이미 production-ready | Phase 8+ |
| **외부 SNS 자동 포스팅** | 법적 검토 필요 (각 플랫폼 ToS). 수동 공유 우선 | Phase 8+ |
| **B2B 리포트** (갤러리/학교 파트너십) | 파트너십 체결 후 구현 | Phase 8+ |
| **실시간 WebSocket** (경매 실시간 bid) | 인프라 비용 + 복잡도. SSE/polling 현행 유지 | Phase 8+ |

---

## 10. README 비즈니스 비전 매핑

| README 비전 | Phase 7 sub-PDCA | 구현 방식 |
|------------|:----------------:|----------|
| "히스토리를 유튜브도 만들겠지만 **일간지라든지 라디오 같은 데서 풀 수 있음**" | **C-1 + C-2 + C-4** | AI 자동 인터뷰 기사 (C-1) + Press Kit PDF 외부 배포 (C-2) + Media Coverage CMS 노출 관리 (C-4) |
| "**AI 세상으로 가면 갈수록 예술가들이 제일 먼저 굶어 죽음**" — AI 시대 예술가 생존 | **C-1 + C-3** | LLM 자동 인터뷰 생성 (tuzigroup Gateway) + 5 locale 자동 번역 (C-3) — AI가 작가 홍보를 자동화 |
| "컬렉터들한테는 **회비 1년 회비로 10분씩 받겠다고 함**" | **C-5** | Newsletter digest — 후원자/컬렉터 구독 차별화 채널. Featured Artist + ranking changes |
| "**후원 인프라 안정화**" — Stripe 성숙도 | **G'-1 + G'-2** | webhook 이벤트 핸들러 완성 (G'-1) + winback coupon 실제 발행 (G'-2) = Stripe production maturity |
| "전 세계 아티스트들의 **인덱스를 만들고 싶음**" | **G'-8** | 지역별/장르별 별도 ranking (alembic 0050 + rank_region) + region top 10 카드 |
| "동유럽이든 남미든 동아시아든 이런 데들에게 **엄청난 꿈과 희망**" | **C-3 + G'-8** | Multi-language story 5 locale SEO (C-3) + 지역별 ranking 가시성 강화 (G'-8) |
| "남미 페루 대학생 그림 **30만원 → 45만원 판매 히스토리**" | **C-1 + C-2** | AI 인터뷰로 이런 히스토리 자동 기사화 + press kit PDF로 외부 배포 가능 |

---

## 11. Phase 6 Lessons Applied (Phase 7 적용 방침)

| Phase 6 학습 사항 | Phase 7 적용 방식 |
|------------------|-----------------|
| **권장 default 일괄 수락 패턴** (OQ 10개 모두 권장대로, 협상 라운드 0) | Phase 7 OQ-1~OQ-10 동일 표 형식 + 권장 default 명시. "권장대로" 응답 시 즉시 G'-1 진입 |
| **alembic revision ID 충돌 감지 + linter auto-rename** (A-5/A-8 0048 충돌 → auto-rename) | G' 병렬 시작 전 0050/0051/0052 배정표 사전 정의. `alembic heads` 충돌 감지 자동화 |
| **Critical Path 선결 강화** (A-1 Analytics Foundation 선결 → 모든 후속 측정 가능) | G'-1 Stripe webhook (Critical Path) + C-1 AI 인터뷰 (C 단계 Critical Path) 각 단계 선결 필수 |
| **R-5 cron 격리 표준** (별도 파일 + AsyncSessionLocal + 별도 lifespan task) | G'-9 post_engagement_cache cron + G'-8 region ranking cron — 동일 R-5 패턴 적용 |
| **Mock 모드 fallback** (PostHog/Stripe 미설정 시 자동 mock) | C-1 LLM Gateway: LLM_GATEWAY_APIKEY 미설정 시 mock 인터뷰 반환. C-5 AWS SES: EMAIL_BACKEND=console fallback |
| **booster 패턴** (D'-3 CouponProvider → B-1 Stripe 재사용, ChurnList → D'-2 사유 활용) | G'-2 winback coupon은 D'-3 CouponProvider 직접 재사용 (booster). C-2 PDF는 A-7 Pillow 패턴 재사용 |
| **i18n namespace 분리 strict** (13 sub-PDCAs 다른 namespace, race condition 0) | G' + C 각 sub-PDCA 별 namespace 사전 배정: `webhook.*` `winback.*` `a11y.*` `interview.*` `presskit.*` `story.multilang.*` `media.*` `newsletter.*` |
| **Schema Sync Checklist** (BE/FE schema pair 필수) | G'-1 webhook payload schema + C-1 interview_article 모델 + C-2 PDF 요청/응답 — 각 Design 단계에서 필수 |

---

## 12. 다음 액션

### Phase 7 시작 전 체크리스트

1. **alembic upgrade head 실행 확인** (OQ-10=A — G' 시작 트리거). Phase 6 0049 포함
2. **OQ-1~OQ-10 결정** — "권장대로" 일괄 수락 시 즉시 G'-1 진입 가능
3. **G' 병렬 전략 확인** (OQ-1=B 권장: G'-1 Critical Path + G'-3+G'-4+G'-5+G'-6+G'-8+G'-9+G'-10 동시 + G'-2 이후)
4. **alembic revision ID 사전 배정** (0050=G'-8, 0051=G'-9, 0052=G'-10)

### G' 단계 진입 명령 (OQ-1=B 병렬 채택 시)

```bash
# Critical Path (먼저 단독 시작)
/pdca plan stripe-webhook-extension        # G'-1

# 병렬 그룹 A (G'-1과 동시 시작 가능)
/pdca plan a11y-tailwind-cleanup           # G'-3
/pdca plan backend-posthog-integration     # G'-4
/pdca plan jest-test-runner-setup          # G'-5
/pdca plan dynamic-og-card                 # G'-6

# 병렬 그룹 B (G'-1과 동시 시작 가능)
/pdca plan region-genre-ranking            # G'-8
/pdca plan post-engagement-cache           # G'-9
/pdca plan price-unit-consistency          # G'-10

# 순차 (G'-1 완료 후)
/pdca plan winback-coupon-endpoint         # G'-2

# 순차 (G'-6 완료 후)
/pdca plan admin-featured-artists          # G'-7
```

### C 단계 진입 명령 (G' 완료 후)

```bash
# Critical Path (C 단계 시작 — 선결 필수)
/pdca plan ai-artist-interview-generation  # C-1

# C-1 완료 후 병렬 그룹
/pdca plan press-kit-auto-export           # C-2
/pdca plan multi-language-story            # C-3

# 이후 순차
/pdca plan media-coverage-cms              # C-4
/pdca plan newsletter-digest               # C-5
```

---

## 13. 결정 기록 (Decisions Log)

### 2026-05-04 — Phase 7 로드맵 초안 (product-manager)

| 결정 | 내용 | 근거 |
|------|------|------|
| Phase 7 구조 | G'(2~3주) → C(6주) 순차 | 사용자 전략 결정: option G → C sequential |
| G' 단계 sub-PDCA | 10개 필수 + 3개 선택 (G'-1~G'-10 + G'-11~G'-13) | Phase 6 18개 carry-over 청산 우선. D'-6 deferred G'-1로 통합 |
| C 단계 sub-PDCA | 5개 필수 + 2개 선택 (C-1~C-5 + C-6~C-7) | README "히스토리/유튜브/일간지/라디오" 마케팅 비전 구현 |
| C-1 Critical Path 지정 | AI 인터뷰 생성 선결 | C-2/C-3/C-5 모두 C-1 콘텐츠 소스 의존 — C-1 없으면 press kit, multi-language, newsletter 콘텐츠 부재 |
| OQ-3 LLM Provider | tuzigroup LLM Gateway (A 권장) | memory에 기존 자격증명 (gemma4-e4b) — 즉시 사용 가능. 추가 계약 불필요 |
| OQ-4 PDF 생성 | Pillow + reportlab (A 권장) | Phase 6 A-7 OG image Pillow 패턴 재사용 (booster). 백엔드 통합 + idempotency_key 적용 용이 |
| OQ-6 이메일 인프라 | AWS SES (B 권장) | cost-efficient (SendGrid 대비 ~10배 절감) + AWS 인프라 통합 + 글로벌 전송률 |
| G'-1 Critical Path 지정 | Stripe webhook 선결 | G'-2 winback coupon이 webhook 안정화 이후 안전. webhook idempotency 먼저 확보 필요 |
| alembic revision 배정 | 0050=G'-8, 0051=G'-9, 0052=G'-10 | Phase 6 A-5/A-8 충돌 교훈 적용 — 병렬 전 사전 배정 |
| Phase 6 lessons 적용 | 8개 항목 §11에 명시 | booster 패턴 / Mock fallback / R-5 cron 격리 / i18n namespace / Schema Sync |

---

## Version History

| 버전 | 날짜 | 변경사항 | 작성자 |
|------|------|---------|--------|
| 0.1 | 2026-05-04 | Phase 7 로드맵 초안. G'(10+3 sub-PDCA) + C(5+2 sub-PDCA) = 15~20 sub-PDCA. 10 OQ (권장 default 포함). Phase 6 carry-over 18건 매핑 §7. README 비전 매핑 §10. Phase 6 lessons §11. | itpe-ince (Claude Sonnet 4.6 / product-manager) |
