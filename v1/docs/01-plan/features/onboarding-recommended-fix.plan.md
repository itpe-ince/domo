---
template: plan
version: 1.0
feature: onboarding-recommended-fix
date: 2026-05-17
author: itpe-ince (Claude Opus 4.7)
project: domo
project_version: v1
parent_pdca: domo-phase6-roadmap A-2 (onboarding-funnel, archived 2026-05-04)
status: retroactive (post-implementation documentation)
---

# onboarding-recommended-fix Planning Document

> **Summary**: Phase 6 A-2(onboarding-funnel)에서 carry-over로 deferred되었던 백엔드 `GET /v1/onboarding/recommended-artists` 엔드포인트 구현 + 프론트 `OnboardingStep2Sponsor`의 null-artist 무반응 버튼 핫픽스.
>
> **Project**: domo / v1
> **Date**: 2026-05-17
> **Status**: Retroactive (구현 완료 후 PDCA 문서화)
> **Parent**: [Phase 6 roadmap](../../archive/2026-05/domo-phase6-roadmap/report.md) — A-2 carry-over

---

## 1. Overview

### 1.1 Purpose

사용자 보고 버그: 온보딩 Step 2("Blue Bird로 작가를 응원해보세요")의 **"지금 응원하기"** 버튼 클릭이 무반응이며, 콘솔에 404 발생. 다음을 해결한다.

1. 404 발생 — 백엔드 `/v1/onboarding/recommended-artists` 미구현(Phase 6 carry-over)
2. 무반응 버튼 — 프론트 모달 렌더 조건이 `showModal && artist`이라 `artist`가 null이면 클릭이 조용히 폐기됨

### 1.2 Background

- Phase 6 A-2 `onboarding-funnel` 보고서 명시: **"Carry-over: backend /onboarding/recommended-artists endpoint (Phase 6.5)"** ([report.md L218](../../archive/2026-05/domo-phase6-roadmap/report.md))
- 프론트엔드는 엔드포인트가 구현될 것을 전제로 `fetchRecommendedArtists()`를 호출하도록 빌드되어 있음 ([api.ts:2614](../../../frontend/src/lib/api.ts#L2614))
- 결과적으로 온보딩 Funnel A-2의 "첫 후원 인센티브" CTA가 작동 불능 — Funnel 전환율 측정 불가

### 1.3 Related Documents

- Parent: `v1/docs/archive/2026-05/domo-phase6-roadmap/{plan,report}.md`
- Frontend caller: `v1/frontend/src/components/onboarding/OnboardingStep2Sponsor.tsx`
- API type: `v1/frontend/src/lib/api.ts` (`RecommendedArtist`, `fetchRecommendedArtists`)

---

## 2. Scope

### 2.1 In Scope

- [x] Backend `GET /v1/onboarding/recommended-artists?limit=N` 신규 엔드포인트 (anonymous-accessible)
- [x] Onboarding 라우터 모듈 `app/api/onboarding.py` 신규 + `main.py` 등록
- [x] Rate limit 키 `onboarding_recommended_read` (60/min/IP) 추가
- [x] Frontend `OnboardingStep2Sponsor.tsx` null-artist 분기 보강
  - [x] `loadingArtist` / `artistLoadFailed` state 분리
  - [x] artist 없을 때 CTA 버튼 비표시
  - [x] load 실패 시 안내 메시지 표시
  - [x] loading 중 disabled 상태 표시
- [x] 응답 shape이 frontend `RecommendedArtist` 타입과 정확히 일치

### 2.2 Out of Scope

- 통합 테스트 코드 작성 (스모크 테스트로 대체)
- E2E 자동화 (Playwright 시나리오 미작성)
- `OnboardingStep1Follow`의 동일 호출 경로 보강(이미 catch에서 빈 배열 fallback — 동작 문제 없음)
- artist_index_score 기반 추천 알고리즘 고도화(현재는 rank ASC + follower fallback + shuffle)
- 다국어 i18n 신규 키 — 기존 `onboarding.step1.noArtists` 재사용

---

## 3. Requirements

### 3.1 Functional Requirements

| ID | Requirement | Priority | Status |
|----|-------------|----------|--------|
| FR-01 | `GET /v1/onboarding/recommended-artists?limit=N` (1 ≤ N ≤ 20, default 5)는 200으로 `{data: RecommendedArtist[]}` 반환 | High | ✅ Done |
| FR-02 | 익명 사용자도 호출 가능(JWT 불필요) | High | ✅ Done |
| FR-03 | 응답 필드: `user_id, username, avatar_url, bio_short, tier_default, recent_works_count` | High | ✅ Done |
| FR-04 | 추천 우선순위: `artist_index_rank` ASC → follower count DESC 보충 → 같은 pool 안에서 shuffle | High | ✅ Done |
| FR-05 | 프론트 Step2에서 artist null일 때 버튼 무반응 제거 | High | ✅ Done |
| FR-06 | artist load 실패 시 사용자에게 시각적 피드백 제공 | Medium | ✅ Done |
| FR-07 | artist load 중에는 disabled 상태 노출 | Medium | ✅ Done |

### 3.2 Non-Functional Requirements

| Category | Criteria | Measurement Method |
|----------|----------|-------------------|
| Performance | p95 응답 < 200ms (소규모 dev DB) | TestClient smoke (200 OK, ~3 SQL) |
| Security | OWASP A01 — anonymous endpoint, no PII leakage (bio 100자 truncate) | Manual review + smoke output check |
| Rate limit | 60/min/IP | `onboarding_recommended_read` config |
| Type safety | Frontend `tsc --noEmit` 0 errors | `npx tsc --noEmit -p .` |

---

## 4. Success Criteria

### 4.1 Definition of Done

- [x] FR-01 ~ FR-07 모두 구현
- [x] Backend smoke test: status 200 + 정상 shape 반환
- [x] Frontend TypeScript 0 errors
- [x] 변경된 파일 모두 기존 코드 컨벤션 준수 (FastAPI router pattern, `{"data": [...]}` envelope)

### 4.2 Quality Criteria

- [x] Lint: 신규 파일에 추가 lint 오류 없음 (B008 경고는 기존 라우터와 동일한 FastAPI 관행)
- [x] No backward compatibility break (기존 `RecommendedArtist` consumer `OnboardingStep1Follow`도 동일 shape으로 동작)

---

## 5. Risks and Mitigation

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| 추천 artist가 0명인 환경(신규 DB) | Medium | Low | 응답이 빈 배열이어도 200 보장 + 프론트 `artistLoadFailed`로 graceful 처리 |
| 동시 트래픽으로 인한 follower count subquery 비용 | Low | Low | pool은 최대 30개로 제한, 인덱스는 `followee_id` PK로 충분 |
| 추후 작가 추천 알고리즘 변경 시 응답 호환성 | Low | Medium | 응답 shape이 `RecommendedArtist` 타입으로 lockdown — 알고리즘 변경 시에도 shape 유지 |

---

## 6. Architecture Considerations

### 6.1 Project Level Selection

| Level | Selected |
|-------|:--------:|
| Starter | ☐ |
| Dynamic | ☐ |
| Enterprise | ☑ (기존 v1 backend는 FastAPI + SQLAlchemy async + Alembic 구조) |

### 6.2 Key Architectural Decisions

| Decision | Selected | Rationale |
|----------|----------|-----------|
| Router prefix | `/onboarding` | 프론트 호출 경로 `/v1/onboarding/recommended-artists`와 일치 |
| Auth | Anonymous (no `Depends(get_current_user)`) | 온보딩 wizard는 로그인 직후 + 익명 미리보기 시나리오 모두 허용 |
| Response envelope | `{"data": [...]}` | 기존 `me_bio.py`, `communities.py` 등과 동일 패턴 (apiFetch 자동 unwrap) |
| Pool 전략 | rank ASC top 3×limit (max 30) → follower fallback → shuffle | 변동성(visual variety) + 품질 보장 |
| `recent_works_count` 의미 | published post 총 개수(시간 제약 없음) | 신규 작가는 작품 수가 적어 30일 제한 시 0이 많음 — UX 측면 단순 카운트가 더 유익 |

---

## 7. Convention Prerequisites

기존 v1 backend 컨벤션 준수:
- FastAPI `APIRouter(prefix="...", tags=["..."])` 패턴
- `rate_limit("scope_key")` 의존성 주입
- 응답 envelope: `{"data": ...}`
- SQLAlchemy async `select(...).join(...).where(...)` 패턴
- snake_case 응답 키

기존 frontend 컨벤션 준수:
- `useI18n()` 훅 + `t("key")` 호출
- camelCase state, snake_case API field
- 기존 i18n 키 재사용

---

## 8. Next Steps

1. [x] Plan 문서 작성 (이 문서 — retroactive)
2. [x] Design 문서 작성 (`onboarding-recommended-fix.design.md`)
3. [x] 구현 (master 직접 commit)
4. [ ] gap-detector로 Design vs Implementation 검증
5. [ ] Match Rate ≥ 90%이면 `/pdca report` → `/pdca archive`

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2026-05-17 | Retroactive plan (post-fix) | itpe-ince (Claude Opus 4.7) |
