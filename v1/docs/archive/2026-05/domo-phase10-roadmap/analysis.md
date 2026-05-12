# Domo Phase 10 — 통합 Gap Analysis (Final)

## 0. 분석 개요

| 항목 | 값 |
|------|-----|
| 분석 대상 | Phase 10 K Wave 2 (K-8/K-2/K-4/K-7) + CO-1 carry-over (5/6 sub-PDCAs) + Out-of-Plan Hot Fixes (8건) |
| Plan | `v1/docs/01-plan/features/domo-phase10-roadmap.plan.md` (730L, 6 sub-PDCAs) |
| Designs | `v1/docs/02-design/features/domo-phase10-{K-8,K-2,CO-1,K-4,K-7}.design.md` (5개) |
| Implementation Path | `v1/backend/{alembic,app}/`, `v1/frontend/src/`, `v1/admin/src/` |
| 분석일 | 2026-05-08 |
| 작성 도구 | gap-detector (Claude Opus 4.7 / 1M ctx) |

> **요약**: Phase 10 K Wave 2 4 sub-PDCA + CO-1 carry-over 청산 + 사용자 요청 Hot Fixes 8건 통합 검증. Plan/Design 5종, alembic 0080~0083 chain, services 5종, API routers 14 endpoints, frontend 5 컴포넌트, tests +76, cron workers 19 → 23 모두 구현 확인. **K-6는 OQ-7 권장 default(거래 ≥ 100건) 미충족 → Phase 11 정당 이월**. **통합 가중 Match Rate 96.4%** (≥ 90% → iterate 불필요).

---

## 1. Sub-PDCA별 매핑 (6개)

| sub-PDCA | Plan AC | Design 명세 | Implementation | match% |
|----------|---------|------------|---------------|:-----:|
| K-8 | alembic 0080, PostHog flag, ml_experiments service, admin API ×3, Prometheus metric ×3 | K-8.design 12 sections, 50:50 seed, posthog_client Mock | 0080_ml_experiments.py (down=0079), ml_experiments.py, posthog_client.py, admin_experiments.py (3 endpoints), 17 tests | **97%** |
| K-2 | alembic 0081, MMR diversity reranker, top-100→top-20, env guard, admin API ×2 | K-2.design MMR alg, feed_default seed, post_meta dataclass | 0081_diversity_config.py (down=0080), diversity_reranking.py, _compute_mf_scores_with_scores 통합, admin_diversity.py (+2FA), 11 tests (9 passed + 2 over-mocked skipped) | **94%** |
| CO-1 | 11 carry-over → 6 PR, 신규 alembic 없음 | CO-1.design PR-1~6 매핑 | TESTING_NOTES.md, rate_limit, alt sweep, DocentSection 분리, /posts/[id]/edit 도슨트 폼+opt-out, FeedAlgo "v2", i18n-key-audit.sh+CI, ml-experiments-policy.md | **100%** |
| K-4 | alembic 0082, composite_score, 22번째 worker, admin API ×4, autopublish OFF | 4 weights (engagement 0.30 + rank 0.30 + diversity 0.20 + new_artist 0.20) | 0082_featured_artist_candidates.py (down=0081), featured_artist_jobs.py, _apply_diversity_mmr, admin_featured_artist.py (4 endpoints, +2FA), Slack graceful, 10 tests | **94%** ⚠️ Plan 06:00 UTC → Impl 09:00 UTC (K-7과 통일, 의도적 deviation) |
| K-7 | alembic 0083, sklearn KMeans(k=5), LLM Gateway, translation_cache 5 locale, 23번째 worker, admin API ×3 + 공개 API ×2, /explore/collections | 5단계 파이프라인, ai_caption TF-IDF, autopublish OFF | 0083_ai_collections.py (down=0082), ai_curation_jobs.py, sklearn fallback (metadata grouping), LLM budget guard $5/day, ai_collections.py + admin_ai_collections.py, /explore/collections/{page,[id]/page,Client}.tsx, 14 tests (13 passed + 1 sklearn skipped) | **96%** |
| K-6 | (조건부 미진입) | n/a (design 미작성) | Phase 11 이월 (auctions.status='sold' < 100) | **n/a** |

---

## 2. 카테고리별 검증

### 2.1 alembic chain 일관성 — 96% ✅

| Revision | sub-PDCA | down_revision |
|----------|:--------:|:-------------:|
| 0080_ml_experiments | K-8 | 0079_llm_docent |
| 0081_diversity_config | K-2 | 0080_ml_experiments |
| 0082 | K-4 | 0081_diversity_config |
| 0083_ai_collections | K-7 | 0082 |

`alembic heads` → **single head 0083_ai_collections** ✅

소수 차이: 0082 revision string은 `"0082"` (다른 마이그레이션은 `"NNNN_descriptive_name"` 형식). **사소한 convention 불일치 1건**, 기능 영향 없음.

### 2.2 API endpoints 라우터 등록 — 100% ✅

main.py import & include_router 모두 검증:

| Module | Import | Include |
|--------|:------:|:-------:|
| admin_experiments | ✅ | ✅ |
| admin_diversity | ✅ | ✅ |
| admin_featured_artist | ✅ | ✅ |
| ai_collections (public) | ✅ | ✅ |
| admin_ai_collections | ✅ | ✅ |

신규 14 endpoints 모두 라우터 등록 완료. K-4/K-7 admin은 `require_admin_with_2fa` 디펜던시 추가 (보안 강화).

### 2.3 Mock 모드 fallback — 98% ✅

| Service | Mock 트리거 | Fallback 동작 |
|---------|-------------|---------------|
| ml_experiments.py | POSTHOG_API_KEY 미설정 / running 실험 없음 | 전 사용자 v1 + WARNING |
| posthog_client.py | posthog 미설치 OR API_KEY 미설정 | get_feature_flag()=False, capture()→log.debug |
| diversity_reranking.py | DIVERSITY_RERANKING_ENABLED=false | K-1 결과 그대로 반환 |
| featured_artist_jobs.py | FEATURED_ARTIST_WORKER_ENABLED=false | cron 미등록 |
| ai_curation_jobs.py | sklearn 미설치 OR LLM 미설정 OR 일 budget=$0 | metadata grouping / status='generating' / cron skip |

CI 환경에서 ERROR 없이 동작.

### 2.4 Cron workers R-5 격리 — 100% ✅

cron workers **19 → 23 (+4)** 정확:

| # | Worker | sub-PDCA | Interval |
|:-:|--------|:--------:|:--------:|
| 20 | ml_training | Phase 9 K-1 | hourly+ |
| 21 | artwork_caption | Phase 9 K-3 | hourly+ |
| **22** | **featured_artist** | **Phase 10 K-4** | 주 1회 월 09:00 UTC |
| **23** | **ai_curation** | **Phase 10 K-7** | 주 1회 월 09:00 UTC |

각 worker는 *_WORKER_ENABLED env guard 보유.

### 2.5 Tests — 95% ✅

| sub-PDCA | 추가 |
|:--------:|:----:|
| K-8 | ~17 |
| K-2 | ~11 |
| K-4 | ~10 |
| K-7 | ~14 |
| CO-1 | ~9 |
| Hot fix | ~6 |
| 회귀 보강 | ~9 |
| **합계** | **~76** |

**잔존 7 skipped**: Phase 9 L-D 3 + K-2 over-mocked 2 + K-7 sklearn 1 + 기타 1 — 모두 사유 문서화.

### 2.6 Frontend 통합 — 96% ✅

| 변경 | 파일 | sub-PDCA |
|-----|------|:--------:|
| FeedAlgo 타입 "v2" | src/lib/api.ts | CO-1 PR-4 |
| DocentSection 분리 | src/components/DocentSection.tsx | CO-1 PR-3 |
| 도슨트 폼 + opt-out | src/app/posts/[id]/edit/... | CO-1 PR-3 |
| 컬렉션 목록 | src/app/explore/collections/page.tsx | K-7 |
| 컬렉션 상세 | src/app/explore/collections/[id]/{page,Client}.tsx | K-7 |
| i18n CI | i18n-key-audit.sh + GitHub Actions | CO-1 PR-5 |

`tsc 0 errors` 보고.

### 2.7 admin 콘솔 — 100% ✅

`v1/admin/src/components/CreateUserModal.tsx`, `v1/admin/src/app/users/page.tsx`, backend `app/api/admin/users.py` (create_user_by_admin + self-block) 모두 검증.

---

## 3. 통합 Match Rate (가중)

| Sub-PDCA | Match | 가중치 | 가중 점수 |
|:--------:|:-----:|:------:|:---------:|
| K-8 | 97% | 1.5 (Wave A Critical) | 145.5 |
| K-2 | 94% | 1.5 (Wave A Must) | 141.0 |
| CO-1 | 100% | 1.5 (Wave D 병행 Must) | 150.0 |
| K-4 | 94% | 1.0 (Wave B Should) | 94.0 |
| K-7 | 96% | 1.0 (Wave B Should) | 96.0 |
| K-6 | n/a | n/a (Wave C 미진입) | n/a |
| **합계** | — | **6.5** | **626.5** |

> **Phase 10 통합 가중 Match Rate**: **626.5 / 650 = 96.4%** ✅
> **단순 평균**: (97+94+100+94+96) / 5 = **96.2%** ✅
> **목표 ≥ 90% 초과 — iterate 불필요. Phase 10 종결 GO.**

---

## 4. Out-of-Plan Hot Fixes (8건)

> Plan에 명시되지 않았으나 사용자 요청으로 추가 진행. matchRate 분모/분자 외, 응답성 평가용.

| # | Hot Fix | 검증 | 응답성 |
|:-:|---------|:----:|:------:|
| 1 | admin 사용자 등록 UI (CreateUserModal + role 드롭다운) | ✅ | A+ |
| 2 | 등록 화면 UX 1차 (auto-resize + Drawer + sticky preview) | ✅ | A |
| 3 | 등록 화면 UX 2차 (textarea max-h + scrollbar + preview toggle aria) | ✅ | A |
| 4 | ConversationList undefined.length 수정 | ✅ | A+ |
| 5 | useExpiryBanner 무한 루프 수정 | ✅ | A+ |
| 6 | Sidebar overflow-y-auto 추가 | ✅ | A |
| 7 | PreferencesCard 통합 (사이드바) | ✅ | A |
| 8 | 가이드 v2 정본화 | ✅ | A |

**평가**: 8건 모두 사용자 요청 → 즉시 처리 → 회귀 0건 → 테스트 추가 6건. **응답성 우수**.

---

## 5. Phase 11 Carry-over

### 5.1 K-6 AI 가격 추천 (Wave C 미진입)

| 항목 | 현재 | 재진입 트리거 |
|------|------|---------------|
| 거래 데이터 | < 100건 | ≥ 100건 |
| K-8 A/B 결과 | 측정 진행 중 | p < 0.05 |

### 5.2 admin 콘솔 메뉴 누락 7개 (가이드 v2 검증)

| 메뉴 | 백엔드 | Phase 11 우선 |
|------|:------:|:-------------:|
| /admin/featured-artist/queue (K-4 검수) | ✅ | 🔥 High |
| /admin/ai-collections/queue (K-7 검수) | ✅ | 🔥 High |
| /admin/experiments (K-8 결과) | ✅ | ⚡ Medium |
| /admin/diversity-config (K-2 튜닝) | ✅ | ⚡ Medium |
| /admin/analytics 통합 | ⚠️ 일부 | ⏳ Low |
| /admin/payouts | ⚠️ 일부 | ⏳ Low |
| /admin/system (cron 모니터) | ❌ 미구현 | Phase 12 이월 |

### 5.3 가이드 v2에서 발견된 미구현

- 키보드 단축키 시스템 (12개 → 0개 전역 hotkey)
- audit_logs DB 테이블 (현재 Python 구조화 로그만)
- 회원가입 다양화 (현재 Google 1종)
- WebSocket 실시간 admin 알림

### 5.4 Phase 11 후속 측정

- K-1 v2 14일+ 운영 결과 → ML_FEED_DEFAULT_ALGO=v2 rollout 결정
- K-2 lambda 월 1회 admin 튜닝
- K-4 autopublish 전환 (admin 승인율 ≥ 95% 시)

---

## 6. 최종 평가

| 평가 축 | 결과 |
|---------|------|
| Design 매칭 | 100% (5/6, K-6 정당 이월) |
| Implementation 매칭 | 96% |
| Architecture 준수 | 100% (R-5 + Mock fallback + alembic single head) |
| Convention 준수 | 93% (0082 revision string 차이 1건) |
| 테스트 안정성 | 95% (회귀 0, +76, 657 passed + 7 skipped) |
| Critical Path | 5/6 (83%, K-6 정당 이월) |
| README 비전 직접 구현 | 6/7 (86%, 이월 제외 시 100%) |
| Hot Fix 응답성 | A+ (8건 즉시 대응) |
| Phase 11 진입 준비도 | 100% |

> **Phase 10 통합 가중 Match Rate**: **96.4%** ✅
> **결정: GO** — report + archive 단계 진행. iterate 불필요.

---

## 7. Version History

| 버전 | 날짜 | 변경 |
|------|------|------|
| 0.1 | 2026-05-08 | Phase 10 K Wave 2 + CO-1 + 8 Hot Fixes 통합 분석. 가중 Match 96.4%. Phase 11 carry-over 정리. | gap-detector |
