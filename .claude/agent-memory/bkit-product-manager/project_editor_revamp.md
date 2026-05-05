---
name: domo Phase 4 종결 + Phase 5 로드맵 상태
description: editor-revamp-roadmap 11/11 완료 종결 + Phase 5 D/B 단계 로드맵 현황 (2026-05-04 기준)
type: project
---

**Phase 4 완료 (2026-05-04 종결)**

editor-revamp-roadmap 11/11 sub-PDCA 모두 archived. Match Rate 평균 ~98%.

완료 목록: #1 role-gating(98%), #2 draft-autosave, #3 responsive-redesign(96%), #4 media-ux(95%), #6-image media-studio(96%), #8 publish-controls(100%), #10 artist-tier-release, #11 auction-promotion-suite(97%)

Deferred: #9 artist-pricing-assist (데이터 축적 부족, Phase 4.5)

**Why:** Phase 4 Critical Path 완주. 에디터/발행 인프라 완성 → Phase 5로 전환.

**How to apply:** Phase 5 로드맵 문서: `/Users/sangincha/dev/domo/v1/docs/01-plan/features/domo-phase5-roadmap.plan.md`

---

**Phase 5 계획 (2026-05-04 초안)**

총 12 sub-PDCA (D 6 + B 6), 10~12주 예정.

**D 단계 — Tech Debt Stabilization (1~2주)**
- D-1 `editor-i18n-cleanup-v3` (Must, ~3일) — #3/#4/#11 carry-over 25곳 i18n + namespace 통합
- D-2 `upload-retry-ui` (Should, ~3일) — #4 R-FE-7 carry-over (retry/cancel 버튼). plan 이미 존재
- D-3 `series-reorder-persistence` (Must, ~2일) — #8 carry-over 서버 영속화
- D-4 `notifications-ux-audit` (Must, ~3일) — #12 Phase 3 독립 → D로 편입
- D-5 `server-side-notification-i18n` (Should, ~1일) — #11 m-2 서버사이드 i18n
- D-6 `observability-monitoring-baseline` (Should, ~3일) — Prometheus + EXPLAIN ANALYZE 게이트
- D-7 defer → Phase 5.5

병렬 전략(OQ-1=B 권장): 그룹A(D-1+D-3+D-5) 동시 + 그룹B(D-2+D-4) 동시 → D-6 순차

**B 단계 — Blue Bird Patronage UI (8~10주)**
- B-1 `bluebird-sponsor-flow` (Must, ~10일) — Critical Path. Stripe SetupIntent + 일회/정기
- B-2 `artist-patronage-dashboard` (Must, ~8일)
- B-3 `supporter-dashboard` (Must, ~5일) — B-2와 병렬
- B-4 `tier-benefits-customization` (Should, ~5일)
- B-5 `patronage-retention-ux` (Should, ~5일) — B-4와 병렬
- B-6 `patronage-i18n-a11y-audit` (Must, ~3일) — 마무리

재사용 인프라: KYC(P3-2 ✅), 정산 배치(P3-3 ✅), artist-tier-release(#10 ✅), sponsorships 모델

**Phase 5 OQ-1~OQ-8**: 권장 default 표 `/domo-phase5-roadmap.plan.md §3` 참조. "권장대로" 일괄 수락 시 즉시 D 단계 진입 가능.

**Phase 4 lessons → Phase 5 적용**: cron 격리(R-5), computed effective state, idempotent dispatch, OQ 일괄 수락 패턴, Schema Sync Checklist, i18n Exhaustive Check
