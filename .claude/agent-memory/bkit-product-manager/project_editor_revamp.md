---
name: domo Phase 4~13 로드맵 상태
description: Phase 4~12 종결 현황 + Phase 13 로드맵 계획 (2026-05-09 기준)
type: project
---

**Phase 4 완료 (2026-05-04 종결)**

editor-revamp-roadmap 11/11 sub-PDCA 모두 archived. Match Rate 평균 ~98%.

---

**Phase 5~7 누적 완료 (2026-05-05 기준)**

- Phase 5: D(6)+B(6) = 12 sub-PDCAs. Blue Bird Patronage 후원 인프라 완성.
- Phase 6: D'(5/6)+A(8/8) = 13/13 sub-PDCAs 100%. 그로스해킹 깔때기 + 신진작가 인덱스 + 스토리텔링 허브.
- Phase 7: G'(10/10)+C(5/5) = 15/15 sub-PDCAs 100%. Tech Debt 청산 + 마케팅 허브 자동화(AI 인터뷰 + Press Kit + Newsletter).
- 누적 지표: 77 → 311 passed / alembic 0043 → 0058 / ~2850+ i18n × 5 locales / 8 cron workers (R-5 격리)

**Phase 8 완료 (2026-05-05 기준)**

- Phase 8: G''(5/5)+H'(6/6)+B'(5/5) = 15/15(+G''-6 Phase 9 defer) sub-PDCAs 100%.
- G'': OpenTelemetry X-Ray + Redis ElastiCache + N+1 audit + DB pool. p95 187ms, Redis hit 73%.
- H': VoiceOver/NVDA WCAG AA + CJK PDF + Multi-language SEO + Click tracking + SES bounce + ML 데이터(50K events).
- B': Multi-currency(USD/KRW/EUR/JPY) + DM 1:1 + FCM/APNs Push + Stripe 자동갱신 96.3% + 후원 analytics.
- 누적 지표: 311 → 412 passed (+101) / alembic 0050~0065 (16건) / Cron 11개 R-5 격리 / i18n +1500 × 5 locales.

**Why:** Phase 8까지 후원 인프라 Maturity 완성. Phase 9 = Carry-over 청산 + ML/AI 고도화.

**How to apply:**
- Phase 8 plan: `/Users/sangincha/dev/domo/v1/docs/archive/2026-05/domo-phase8-roadmap/plan.md`
- Phase 9 plan: `/Users/sangincha/dev/domo/v1/docs/01-plan/features/domo-phase9-roadmap.plan.md`

---

**Phase 9 종결 (2026-05-06 기준)**

총 9 sub-PDCAs (L 6 + K Wave 1 3) 100% 완료. 가중 Match Rate 93.0%.

- L-A~L-F: Phase 8 carry-over 청산 + pgvector 임베딩 인프라 완성
- K-1: ML 피드 v2 (Collaborative Filtering, alembic 0073) — Critical Path 완성
- K-3: AI 작품 캡션 (alembic 0078, vision LLM + translation_cache)
- K-5: LLM 도슨트 (alembic 0079, 3~5문단 큐레이터 해설)
- 누적: 테스트 510→581(+71), alembic 0066~0079 (14건), cron 16→21

**Phase 9 Carry-over 11항목 → Phase 10 CO-1으로 이월**

---

**Phase 10 계획 (2026-05-06 초안, 사용자 옵션 A 수락)**

총 6 sub-PDCAs (K Wave 2 5 + CO-1 1), 6~8주 예정.

- Wave A (즉시, 병렬): K-8 `ml-ab-test-infra` (alembic 0080) + K-2 `feed-diversity-reranking` (alembic 0081)
- Wave B (Wave A +2주, 병렬): K-4 `ai-featured-artist` (alembic 0082) + K-7 `ai-curation-collection` (alembic 0083)
- Wave C (조건부, 거래≥100건): K-6 `ai-price-recommendation` (alembic 0084 예약)
- Wave D (Wave A 병행): CO-1 `phase9-carryover-cleanup` (6 sub-task PR, alembic 없음)

**alembic 사전 배정**: 0080(ml_experiments+assignments) 0081(diversity_constraints) 0082(featured_artist_candidates) 0083(ai_collections+posts) 0084(예약, K-6)

**Phase 10 OQ-1~OQ-15**: 권장 default 표 `/v1/docs/01-plan/features/domo-phase10-roadmap.plan.md §5` 참조.

**Phase 10 plan**: `/Users/sangincha/dev/domo/v1/docs/01-plan/features/domo-phase10-roadmap.plan.md`

**Why:** K-1 출시 후 운영 데이터 기반 A/B 검증 + Diversity Reranking으로 ML 피드 가치 측정. CO-1로 기술 부채 완전 청산.

**How to apply:**
- Phase 9 archived: `/Users/sangincha/dev/domo/v1/docs/archive/2026-05/domo-phase9-roadmap/`
- Phase 10 plan: `/Users/sangincha/dev/domo/v1/docs/archive/2026-05/domo-phase10-roadmap/plan.md`

---

**Phase 10 종결 (2026-05-06 기준)**

총 5 sub-PDCAs (K-8/K-2/K-4/K-7/CO-1) 100% 완료. K-6 거래 100건 미달로 정당 이월. 가중 Match Rate 96.4%.

- K-8: PostHog A/B 테스트 인프라 (alembic 0080, ml_experiments+assignments)
- K-2: Diversity Reranking + 신진작가 부스팅 (alembic 0081, diversity_configs)
- K-4: Featured Artist 자동 추천 (alembic 0082, featured_artist_candidates)
- K-7: AI 큐레이션 컬렉션 (alembic 0083, ai_collections+posts)
- CO-1: Phase 9 carry-over 11항목 6 PR 청산 (alembic 없음)
- 누적: 테스트 581→646(+65), alembic 0080~0083 (4건, single head), cron 21→23

**가이드 v2 정본화 (2026-05-08) 에서 Phase 11 carry-over 식별**
- 키보드 단축키 12개 미구현 (가이드 주장과 다름)
- audit_logs 테이블 미존재 (Python 구조화 로그만)
- 회원가입 Google OAuth 1종뿐 (이메일+비밀번호 미구현)
- Admin 콘솔 누락 메뉴 7개 (백엔드 API는 완성, 프론트 미구현)

---

**Phase 11 계획 (2026-05-08 초안)**

총 8 sub-PDCAs, 6~8주 예정.

- Wave A (즉시, 병렬): A-1 `/admin/featured-artist/queue` UI + A-2 `/admin/ai-collections/queue` UI
- Wave B (Wave A 후, 병렬): B-1 `/admin/experiments` UI + B-2 `/admin/diversity-config` UI
- Wave C (조건부, 거래≥100건): C-1 K-6 AI 가격 추천 (alembic 0086)
- Wave D (Wave A 후 Wave B 병행): D-1 키보드 단축키 + D-2 audit_logs (alembic 0084) + D-3 이메일+비밀번호 가입 (alembic 0085)

**alembic 사전 배정**: 0084(audit_logs) 0085(email_auth 컬럼) 0086(K-6 조건부)

**Phase 11 OQ-1~OQ-13**: 권장 default 표 포함.

**Phase 11 plan**: `/Users/sangincha/dev/domo/v1/docs/01-plan/features/domo-phase11-roadmap.plan.md`

**Why:** Phase 10 백엔드 완성 → Admin 콘솔 UI 격차 해소. 가입 다양화로 글로벌 접근성 확대. audit_logs로 규정 준수 실현.

**How to apply:**
- Phase 10 archived: `/Users/sangincha/dev/domo/v1/docs/archive/2026-05/domo-phase10-roadmap/`
- Phase 11 plan: `/Users/sangincha/dev/domo/v1/docs/archive/2026-05/domo-phase11-roadmap/plan.md`

---

**Phase 11 종결 (2026-05-08 기준)**

총 7/8 sub-PDCAs 완료. C-1(K-6) 거래 < 100건으로 정당 이월. 가중 Match Rate 96.9%.

- A-1: `/admin/featured-artist/queue` UI (K-4 검수 큐) 97%
- A-2: `/admin/ai-collections/queue` UI (K-7 검수 큐) 96%
- B-1: `/admin/experiments` UI (A/B 결과, PATCH 미구현 88%)
- B-2: `/admin/diversity-config` UI 96%
- D-1: 전역 단축키 (j/k/⌘S/?) 97%
- D-2: audit_logs (alembic 0084) 94%
- D-3: 이메일+비밀번호 가입 (alembic 0085, password reset 미구현 93%)
- 누적: 테스트 657→694(+37), alembic 0083→0085, cron 23→24, AdminShell 신규 그룹 2개
- Phase 12 carry-over 12개 식별

---

**Phase 12 계획 (2026-05-08 초안, 옵션 D 균형 진행)**

총 7~8 sub-PDCAs, ~10주 예정. Wave A/B/C 3단계.

- Wave A (즉시, 병렬): A-1 17 tests refactor (freezegun+testcontainers) + A-2 B-1 PATCH endpoint (pause/complete)
- Wave B (조건부 분기, 거래 카운트 기준):
  - ≥ 100건: B-1k K-6 AI 가격 추천 (alembic 0086)
  - < 100건 (예상): B-1a admin audit log 조회 UI + B-2 analytics 대시보드 + B-3 payouts 관리 UI
- Wave C: C-1 password reset (alembic 0086/0087) + C-2 GitHub OAuth+매직링크 + C-3 단축키 확장

**alembic 사전 배정**: 0086~0088 (시나리오에 따라 번호 조정)

**Phase 12 OQ-1~OQ-13**: 권장 default 표 포함.

**Phase 12 plan**: `/Users/sangincha/dev/domo/v1/docs/01-plan/features/domo-phase12-roadmap.plan.md`

**Why:** Phase 11 안정성 부채(17 skipped tests + password reset 미구현) 청산. Admin 콘솔 마지막 3개 메뉴 완성(거래 < 100건 시). 인증 플로우 4종 완성.

**How to apply:**
- Phase 11 archived: `/Users/sangincha/dev/domo/v1/docs/archive/2026-05/domo-phase11-roadmap/`
- Phase 12 plan: `/Users/sangincha/dev/domo/v1/docs/01-plan/features/domo-phase12-roadmap.plan.md`

---

**Phase 12 종결 (2026-05-09 기준)**

총 8/8 sub-PDCAs 완료. K-6 거래 < 100건으로 정당 이월. 통합 가중 Match Rate 92.1%.

- A-1: freezegun+testcontainers+factory_boy 도입 80% (12 GitHub/매직링크 skip → Phase 13 carry-over)
- A-2: PATCH /admin/experiments 엔드포인트 + ExperimentStatusModals 96%
- B-1: /admin/audit-logs UI + cursor pagination + 5 필터 96%
- B-2: /admin/analytics 통합 대시보드 + Redis 5분 캐시 95%
- B-3: /admin/payouts KYC + Stripe Connect mock 97%
- C-1: /auth/password-reset (alembic 0086) 92%
- C-2: GitHub OAuth + 매직링크 88% (12 tests skip)
- C-3: 단축키 9개(6 nav + 3 actions) + KeyboardShortcutsHelp 97%
- 누적: 테스트 694→750(+56), alembic 0086(single head 패치 후), cron 24개, API 17개 신규
- AdminShell 4개 메뉴 그룹: Curation + ML Operations + Security(신규) + Finance(신규)
- Phase 13 carry-over 7개 식별

---

**Phase 13 계획 (2026-05-09 초안, 옵션 D 균형 진행)**

총 5~6 sub-PDCAs, ~8주 예정. Wave A/B/C 3단계.

- Wave A (~2주): A-1 12 GitHub/매직링크 tests → respx+moto mock + A-2 otel/redis/SES → LocalStack
- Wave B (조건부, ~3주): Day 0 SQL sold_count 기준
  - ≥ 100건: B-1k K-6 AI 가격 추천 (alembic 0088)
  - < 100건 (가능성 높음): B-1p audit_logs 파티셔닝 (alembic 0088, 월별 DECLARATIVE)
- Wave C (~3주): C-1 /admin/system cron 모니터 + C-2 ML 회귀 K-6 v2 (거래 ≥ 500건 시)

**alembic 사전 배정**: 0088(B-1k 또는 B-1p), 0089(cron_status 선택), 0090(C-2 진입 시)

**Phase 13 OQ-1~OQ-13**: 권장 default 표 포함.

**Phase 13 plan**: `/Users/sangincha/dev/domo/v1/docs/01-plan/features/domo-phase13-roadmap.plan.md`

**Why:** Phase 12 carry-over 7개 청산. 테스트 skip 24 → <6 목표. Wave B 조건부로 K-6 진입 또는 audit_logs 장기 보존 준비.

**How to apply:**
- Phase 12 archived: `/Users/sangincha/dev/domo/v1/docs/archive/2026-05/domo-phase12-roadmap/`
- Phase 13 plan: `/Users/sangincha/dev/domo/v1/docs/01-plan/features/domo-phase13-roadmap.plan.md`
