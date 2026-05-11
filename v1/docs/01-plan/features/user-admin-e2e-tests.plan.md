---
template: plan
version: 1.0
feature: user-admin-e2e-tests
date: 2026-05-10
author: itpe-ince (GPT-5.5)
project: domo
version: v1
status: Draft
---

# 사용자·관리자 페이지 E2E 테스트 Plan

> **Summary**: Domo 사용자 웹앱(`frontend`)과 관리자 콘솔(`admin`)의 핵심 시연/운영 플로우를 Playwright 기반 E2E 테스트로 검증할 수 있도록 테스트 인프라, 시드 데이터, 인증 세션, 핵심 시나리오를 단계적으로 구축한다.
>
> **Project**: domo (v1)
> **Version**: v1
> **Author**: itpe-ince
> **Date**: 2026-05-10
> **Status**: Draft

---

## 1. Overview

### 1.1 Purpose

현재 `v1/frontend`에는 Jest 기반 단위/컴포넌트 테스트와 axe 감사 스크립트가 있으나, 실제 브라우저에서 사용자 여정 전체를 검증하는 Playwright E2E 설정은 없다. `v1/admin` 역시 빌드/린트 스크립트는 있으나 관리자 로그인, 2FA 게이트, 운영 화면 전환을 자동 검증하는 E2E 테스트가 없다.

이번 PDCA의 목적은 다음을 달성하는 것이다:

- 사용자 페이지 핵심 여정이 실제 브라우저에서 깨지지 않는지 검증
- 관리자 페이지 핵심 운영 여정이 실제 브라우저에서 깨지지 않는지 검증
- 사용자 앱과 관리자 앱이 같은 백엔드 상태를 공유하는 교차 플로우를 검증
- CI 또는 로컬 QA에서 반복 실행 가능한 E2E 테스트 명령을 제공
- 실패 시 스크린샷, trace, video 등 재현 가능한 증거를 남김

### 1.2 Background

- Domo v1은 사용자 웹앱(`frontend`, 기본 port 3000), 관리자 콘솔(`admin`, 기본 port 3800), FastAPI 백엔드로 구성되어 있다.
- 기존 문서의 핵심 시연 시나리오는 "사용자 신청/업로드 → 관리자 승인 → 사용자 화면 반영"처럼 사용자 앱과 관리자 앱을 오가는 흐름이 많다.
- 관리자 콘솔은 `/login`, `/dashboard`, `/users`, `/applications`, `/posts`, `/transactions`, `/moderation`, `/settings/*` 등 운영 페이지를 갖고 있다.
- 관리자 엔드포인트는 `require_admin_with_2fa` 정책이 적용되어 TOTP 또는 Passkey 등록 상태를 고려해야 한다.
- 현재 Playwright 설정 파일, `*.spec.ts`, `*.e2e.ts` 파일은 확인되지 않는다.

### 1.3 Related Documents

- 기본 Plan: [docs/01-plan/plan.md](../plan.md)
- 기본 Design: [docs/02-design/design.md](../../02-design/design.md)
- 실제 인증 Plan: [real-auth.plan.md](./real-auth.plan.md)
- 관리자 시스템 가이드: [docs/guides/admin-system-guide.ko.md](../../guides/admin-system-guide.ko.md)
- 접근성 감사 스크립트: `v1/frontend/scripts/axe-aaa-audit.ts`
- 사용자 앱 package: `v1/frontend/package.json`
- 관리자 앱 package: `v1/admin/package.json`

---

## 2. Scope

### 2.1 In Scope

#### Phase A — E2E 테스트 기반 구축

- [ ] `frontend`와 `admin` 중 어디에 공통 E2E 워크스페이스를 둘지 결정
- [ ] Playwright 설치 및 브라우저 설정
- [ ] 사용자 앱, 관리자 앱, 백엔드 서버 기동 방식 정의
- [ ] 테스트 전용 환경변수 문서화
- [ ] 테스트 결과물 저장 경로 정의 (`test-results`, `playwright-report` 등)
- [ ] 로컬 실행 명령과 CI 실행 명령 분리

#### Phase B — 테스트 데이터와 인증 세션 준비

- [ ] 테스트 전용 사용자 계정 시드 전략 정의
- [ ] 테스트 전용 관리자 계정 시드 전략 정의
- [ ] admin 2FA 우회/고정 TOTP/사전 등록 세션 중 하나를 선택
- [ ] 테스트 실행 전 DB 상태 초기화 또는 고유 데이터 생성 전략 정의
- [ ] 로그인 반복 비용을 줄이기 위한 `storageState` 전략 정의
- [ ] 테스트 데이터가 운영/개발 실제 데이터와 섞이지 않도록 환경 가드 적용

#### Phase C — 사용자 페이지 E2E

- [ ] 비로그인 사용자의 랜딩/피드 접근 및 로그인 유도 확인
- [ ] 로그인 후 `/feed` 접근 및 기본 피드 렌더링 확인
- [ ] `/posts/new`에서 일반 포스트 작성 플로우 확인
- [ ] 작가 계정으로 상품 포스트 또는 경매 포스트 작성 플로우 확인
- [ ] `/me/account` 계정 화면 주요 상태 표시 확인
- [ ] 검색/탐색/작가 프로필 진입 등 핵심 발견 흐름 확인
- [ ] 결제/후원/경매처럼 외부 의존성이 있는 흐름은 mock provider 환경에서 검증

#### Phase D — 관리자 페이지 E2E

- [ ] `/login` 관리자 로그인 성공/실패 확인
- [ ] 2FA 미등록 또는 미완료 상태에서 `/settings/totp-setup` 강제 이동 확인
- [ ] 2FA 완료 관리자 기준 `/dashboard` 접근 확인
- [ ] `/users` 사용자 목록 조회 및 상세 진입 확인
- [ ] `/applications` 작가 심사 목록 조회 및 승인/거부 플로우 확인
- [ ] `/posts` 콘텐츠 검수 목록 조회 및 승인/거부 플로우 확인
- [ ] `/moderation` 신고 처리 플로우 확인
- [ ] `/transactions` 거래 목록 조회 및 상태 필터 확인

#### Phase E — 사용자·관리자 교차 E2E

- [ ] 사용자 작가 신청 → 관리자 승인 → 사용자 role/artist 상태 반영
- [ ] 작가 포스트 업로드 → 관리자 콘텐츠 승인 → 사용자 피드 노출
- [ ] 사용자 신고 생성 → 관리자 신고 처리 → 사용자 경고/알림 상태 반영
- [ ] 경매/주문 상태 변경이 관리자와 사용자 화면에 일관되게 반영되는지 확인

### 2.2 Out of Scope

- 실제 Google OAuth, 실제 결제, 실제 이메일 발송에 대한 외부 서비스 E2E
- 모든 브라우저/모바일 디바이스 조합의 완전 커버리지
- 성능 부하 테스트
- 시각 회귀 테스트 전용 인프라
- 백엔드 API 단위/통합 테스트 대체
- Playwright 외 Cypress 등 대체 도구 비교 구현

---

## 3. Requirements

### 3.1 Functional Requirements

| ID | Requirement | Priority | Phase | Status |
|----|-------------|----------|-------|--------|
| FR-01 | Playwright 기반 E2E 테스트를 로컬에서 실행할 수 있다 | High | A | Pending |
| FR-02 | 사용자 앱과 관리자 앱을 별도 baseURL로 테스트할 수 있다 | High | A | Pending |
| FR-03 | 테스트 전용 user/admin/artist 계정을 안정적으로 준비할 수 있다 | High | B | Pending |
| FR-04 | 관리자 2FA 정책을 테스트 환경에서 재현 가능하게 처리한다 | High | B | Pending |
| FR-05 | 사용자 로그인 세션을 `storageState` 등으로 재사용할 수 있다 | Medium | B | Pending |
| FR-06 | 관리자 로그인 세션을 `storageState` 등으로 재사용할 수 있다 | Medium | B | Pending |
| FR-07 | 사용자 핵심 페이지의 smoke E2E가 통과한다 | High | C | Pending |
| FR-08 | 사용자 포스트 작성 흐름의 E2E가 통과한다 | High | C | Pending |
| FR-09 | 관리자 핵심 페이지의 smoke E2E가 통과한다 | High | D | Pending |
| FR-10 | 관리자 승인/거부 운영 흐름의 E2E가 통과한다 | High | D | Pending |
| FR-11 | 사용자 액션이 관리자 화면에 반영되고, 관리자 액션이 사용자 화면에 반영되는 교차 E2E가 통과한다 | High | E | Pending |
| FR-12 | 실패 시 스크린샷/trace/report가 남는다 | High | A | Pending |
| FR-13 | CI에서 headless 모드로 E2E를 실행할 수 있다 | Medium | A | Pending |
| FR-14 | 테스트 데이터는 재실행해도 충돌하지 않는다 | High | B | Pending |

### 3.2 Non-Functional Requirements

| Category | Criteria | Measurement Method |
|----------|----------|-------------------|
| Reliability | 동일 환경에서 3회 연속 실행 시 flaky failure 없음 | 로컬 반복 실행 |
| Isolation | 테스트 데이터가 실제 개발 데이터와 충돌하지 않음 | 고유 prefix/seed reset 확인 |
| Speed | smoke suite는 5분 이내 완료 | CI 실행 시간 |
| Debuggability | 실패 시 trace/screenshot으로 원인 추적 가능 | Playwright report 확인 |
| Security | 테스트 전용 credential이 코드에 하드코딩되지 않음 | env 사용 + 코드 리뷰 |
| Maintainability | page object 또는 helper가 과도하지 않고 핵심 중복만 제거 | 코드 리뷰 |
| Accessibility | 핵심 페이지에 대해 기존 axe 감사와 병행 가능 | `a11y:audit` 또는 Playwright axe 후속 |

---

## 4. Success Criteria

### 4.1 Definition of Done

- [ ] `frontend` 또는 루트 E2E 위치에 Playwright 설정이 존재한다.
- [ ] `npm run e2e` 또는 이에 준하는 명령으로 사용자 앱 smoke 테스트를 실행할 수 있다.
- [ ] `npm run e2e:admin` 또는 이에 준하는 명령으로 관리자 앱 smoke 테스트를 실행할 수 있다.
- [ ] 사용자 로그인, 피드 접근, 포스트 작성 smoke가 통과한다.
- [ ] 관리자 로그인, 대시보드 접근, 주요 메뉴 접근 smoke가 통과한다.
- [ ] 최소 1개 이상의 사용자→관리자→사용자 교차 플로우가 통과한다.
- [ ] 실패 리포트가 `playwright-report` 또는 지정된 경로에 생성된다.
- [ ] 테스트 계정/환경변수 설정 방법이 문서화된다.
- [ ] 프런트엔드 기존 Jest 테스트와 충돌하지 않는다.
- [ ] 관리자 앱 기존 build/lint 흐름과 충돌하지 않는다.

### 4.2 Quality Criteria

- [ ] smoke suite flaky failure 0건
- [ ] 테스트 파일명/구조가 사용자 앱과 관리자 앱을 명확히 구분
- [ ] 테스트 credential은 `.env` 또는 CI secret으로만 주입
- [ ] 테스트가 외부 결제/OAuth/메일 서비스에 직접 의존하지 않음
- [ ] gap-detector Match Rate ≥ 90% (Do 완료 후)

---

## 5. Risks and Mitigation

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| 관리자 2FA 때문에 E2E 로그인이 불안정해짐 | 높음 | 중 | 테스트 전용 admin에 고정 TOTP secret을 시드하거나, 테스트 환경 전용 pre-auth helper를 설계 |
| DB 상태가 테스트마다 달라 flaky 발생 | 높음 | 높음 | 테스트 전용 prefix, seed reset, 고유 이메일 생성 중 하나를 Design 단계에서 확정 |
| 사용자 앱과 관리자 앱을 동시에 띄우는 설정이 복잡해짐 | 중 | 중 | Playwright `webServer` 다중 설정 또는 외부 docker compose 기동 방식 중 하나로 표준화 |
| 실제 외부 OAuth/결제/메일 의존으로 CI 실패 | 높음 | 중 | mock provider 환경에서만 E2E 실행, real provider는 수동 QA로 분리 |
| selector가 UI 텍스트 변경에 취약 | 중 | 높음 | 핵심 인터랙션에 `data-testid` 도입 기준 정의 |
| 테스트 시간이 길어져 개발자가 실행하지 않음 | 중 | 중 | smoke / full suite 분리 |
| E2E가 구현 세부사항을 과도하게 고정 | 중 | 중 | 사용자 행동 중심 assertion 유지, 내부 API 응답 구조 직접 검증 최소화 |

---

## 6. Architecture Considerations

### 6.1 Project Level Selection

| Level | Characteristics | Recommended For | Selected |
|-------|-----------------|-----------------|:--------:|
| Starter | 단일 정적 사이트 | 단순 랜딩 페이지 | ☐ |
| **Dynamic** | 사용자 앱 + 관리자 앱 + 백엔드 | 현재 Domo v1 구조 | **☑** |
| Enterprise | 다중 서비스/전용 QA 인프라 | 고트래픽 운영 단계 | ☐ |

현재 Domo v1은 FastAPI 백엔드와 Next.js 사용자/관리자 앱을 갖는 Dynamic 레벨이므로, E2E도 Dynamic 기준으로 구축한다.

### 6.2 Key Architectural Decisions

| Decision | Options | Recommended | Rationale |
|----------|---------|-------------|-----------|
| E2E 위치 | `frontend/e2e` / `admin/e2e` / `v1/e2e` | `v1/e2e` | 사용자·관리자 교차 플로우를 한 suite에서 다루기 쉬움 |
| 테스트 도구 | Playwright / Cypress | Playwright | 다중 context, storageState, trace, multi-project 설정에 강점 |
| 실행 범위 | smoke only / full journey | smoke + selected journey | 초기에는 안정성 우선, 이후 점진 확장 |
| 인증 준비 | UI 로그인 반복 / API login setup / seed storageState | API login setup + storageState | 속도와 안정성 균형 |
| 관리자 2FA | 실제 TOTP 입력 / 테스트 우회 / fixed TOTP secret | fixed TOTP secret | 보안 정책을 유지하면서 재현 가능 |
| 테스트 데이터 | 매번 DB reset / 고유 데이터 생성 / 사전 seed | 사전 seed + 고유 데이터 | 속도와 충돌 방지 균형 |
| CI 실행 | 모든 PR / nightly / 수동 | smoke는 PR, full은 nightly | 비용과 신뢰성 균형 |

---

## 7. Proposed Test Matrix

### 7.1 사용자 앱 Smoke

| ID | Scenario | Role | Priority |
|----|----------|------|----------|
| U-01 | 랜딩 또는 피드 접근 → 로그인 유도 | guest | High |
| U-02 | 로그인 → `/feed` 렌더링 | user | High |
| U-03 | `/posts/new` 일반 포스트 작성 | user | High |
| U-04 | 작가 계정으로 상품 포스트 작성 | artist | High |
| U-05 | `/me/account` 계정 상태 확인 | user | Medium |
| U-06 | 작가 프로필 진입 → 팔로우/후원 CTA 확인 | user | Medium |

### 7.2 관리자 앱 Smoke

| ID | Scenario | Role | Priority |
|----|----------|------|----------|
| A-01 | 관리자 로그인 실패 메시지 확인 | admin | High |
| A-02 | 관리자 로그인 성공 → `/dashboard` 접근 | admin | High |
| A-03 | 2FA 미완료 관리자 → `/settings/totp-setup` 이동 | admin_without_2fa | High |
| A-04 | `/users` 목록 조회 | admin | High |
| A-05 | `/applications` 작가 심사 목록 조회 | admin | High |
| A-06 | `/posts` 콘텐츠 관리 목록 조회 | admin | High |
| A-07 | `/moderation` 신고 처리 목록 조회 | admin | Medium |
| A-08 | `/transactions` 거래 관리 목록 조회 | admin | Medium |

### 7.3 교차 플로우

| ID | Scenario | Apps | Priority |
|----|----------|------|----------|
| X-01 | 사용자 작가 신청 → 관리자 승인 → 사용자 artist 상태 확인 | frontend + admin | High |
| X-02 | 작가 포스트 작성 → 관리자 콘텐츠 승인 → 피드 노출 확인 | frontend + admin | High |
| X-03 | 사용자 신고 → 관리자 경고 처리 → 사용자 상태 반영 | frontend + admin | Medium |
| X-04 | 경매 생성/입찰/관리자 거래 확인 | frontend + admin | Medium |

---

## 8. Implementation Order

| Step | Task | Dependency |
|------|------|------------|
| 1 | E2E 위치와 package 관리 방식 확정 | 없음 |
| 2 | Playwright 설치 및 기본 config 작성 | Step 1 |
| 3 | 사용자/admin/baseURL/env 설계 | Step 2 |
| 4 | 테스트 seed 또는 setup helper 설계 | Step 3 |
| 5 | 사용자 login setup + smoke 작성 | Step 4 |
| 6 | 관리자 login setup + smoke 작성 | Step 4 |
| 7 | 관리자 2FA 테스트 전략 구현 | Step 6 |
| 8 | 사용자→관리자 교차 플로우 1개 구현 | Step 5, 6 |
| 9 | CI/headless 명령 추가 | Step 5~8 |
| 10 | 실패 리포트와 실행 가이드 문서화 | Step 9 |

---

## 9. Open Questions

| ID | Question | Options | Recommendation |
|----|----------|---------|----------------|
| OQ-01 | E2E 파일 위치 | A. `v1/e2e` / B. `frontend/e2e` + `admin/e2e` | A |
| OQ-02 | Playwright package 소유 | A. 루트 `v1/package.json` 신규 / B. `frontend/package.json`에 통합 / C. 별도 `e2e/package.json` | C |
| OQ-03 | 관리자 2FA 처리 | A. fixed TOTP secret / B. test env 우회 / C. UI에서 매번 등록 | A |
| OQ-04 | DB 초기화 전략 | A. 테스트 DB reset / B. 고유 prefix 데이터 / C. 사전 seed만 사용 | B |
| OQ-05 | CI 실행 범위 | A. smoke만 PR / B. full suite PR / C. nightly only | A |
| OQ-06 | 모바일 E2E 포함 여부 | A. desktop only first / B. mobile smoke 포함 / C. full responsive matrix | A |

권장값 일괄 채택 시: **OQ-01=A, OQ-02=C, OQ-03=A, OQ-04=B, OQ-05=A, OQ-06=A**.

---

## 10. Next Step

사용자 확인 후 `/pdca design user-admin-e2e-tests` 단계에서 다음을 상세 설계한다:

- Playwright 디렉터리 구조
- `package.json` 스크립트
- `playwright.config.ts` multi-project 구성
- 사용자/admin 인증 setup 방식
- 테스트 seed helper와 환경변수 목록
- 첫 smoke suite 상세 테스트 케이스
---
template: plan
version: 1.2
feature: user-admin-e2e-tests
date: 2026-05-10
author: itpe-ince (GPT-5.5)
project: domo
version: v1
status: Draft
---

# 사용자·관리자 페이지 E2E 테스트 Planning Document

> **Summary**: Domo 사용자 웹앱과 관리자 콘솔의 핵심 플로우를 Playwright 기반 E2E 테스트로 검증할 수 있도록 테스트 인프라, 시드 데이터, 시나리오, CI 실행 기준을 정의한다.
>
> **Project**: domo (v1)
> **Feature**: user-admin-e2e-tests
> **Date**: 2026-05-10
> **Status**: Draft

---

## 1. Overview

### 1.1 Purpose

현재 `v1/frontend`에는 Jest 단위 테스트와 axe 접근성 감사 스크립트가 있고, `v1/admin`에는 별도 E2E 실행 구성이 없다. 사용자 앱과 관리자 앱은 각각 독립된 Next.js 앱으로 동작하며, 실제 서비스 시연과 릴리즈 전 회귀 검증에는 브라우저 레벨의 통합 검증이 필요하다.

본 PDCA의 목적은 다음을 달성하는 것이다:

- 사용자 앱 핵심 플로우를 실제 브라우저에서 검증
- 관리자 콘솔의 인증, 2FA 게이트, 주요 운영 페이지 접근을 검증
- 사용자 플로우와 관리자 플로우가 연결되는 운영 시나리오를 검증
- 개발자 로컬과 CI에서 반복 실행 가능한 E2E 테스트 기준 수립

### 1.2 Background

- 사용자 앱: `v1/frontend`는 Next.js 15 기반이며 기본 포트는 `3000`이다.
- 관리자 앱: `v1/admin`은 Next.js 15 기반이며 개발 포트는 `3800`이다.
- 백엔드: `v1/backend`는 FastAPI 기반이며 사용자·관리자 API를 제공한다.
- 기존 문서의 핵심 시연 시나리오에는 작가 신청, 관리자 승인, 포스트 검수, 후원, 경매, 신고 처리 흐름이 포함되어 있다.
- `real-auth` 계획 문서에는 브라우저 E2E가 성공 기준으로 언급되어 있으나, 프로젝트 공통 E2E 테스트 인프라는 아직 확정되어 있지 않다.

### 1.3 Related Documents

- 기본 MVP 시연 시나리오: `v1/docs/02-design/design.md`
- 사용자·관리자 시연 흐름: `v1/docs/04-report/domo.report.md`
- 실제 인증 계획: `v1/docs/01-plan/features/real-auth.plan.md`
- 관리자 시스템 가이드: `v1/docs/guides/admin-system-guide.ko.md`
- 기존 접근성 감사 스크립트: `v1/frontend/scripts/axe-aaa-audit.ts`

---

## 2. Scope

### 2.1 In Scope

#### Phase A — E2E 테스트 인프라 구성

- [ ] Playwright 도입 여부 및 설치 위치 확정
- [ ] 사용자 앱(`frontend`)과 관리자 앱(`admin`)을 동시에 띄우는 실행 전략 정의
- [ ] 백엔드 API와 테스트 DB 연결 방식 정의
- [ ] 테스트 전용 환경변수와 포트 규칙 정리
- [ ] E2E 테스트 파일 위치와 네이밍 컨벤션 정의

#### Phase B — 테스트 데이터와 인증 세션 준비

- [ ] 일반 사용자, 작가, 관리자 테스트 계정 생성 방식 정의
- [ ] 관리자 2FA/TOTP 또는 passkey 테스트 우회·시드 전략 정의
- [ ] 작가 신청, 포스트, 신고, 경매 등 시나리오별 최소 fixture 정의
- [ ] 테스트 실행 전 DB 초기화 또는 격리 전략 정의
- [ ] 테스트 실패 시 디버깅 가능한 trace, screenshot, video 저장 정책 정의

#### Phase C — 사용자 페이지 E2E 시나리오

- [ ] 비로그인 사용자가 랜딩/피드/검색/작가 프로필을 탐색한다
- [ ] 사용자가 로그인 후 `/me/account` 또는 온보딩 페이지에 접근한다
- [ ] 작가 신청 플로우를 제출하고 신청 상태를 확인한다
- [ ] 작가가 포스트 또는 상품 포스트 작성 화면에 접근한다
- [ ] 컬렉터가 후원 또는 경매 상세에서 주요 CTA를 확인한다
- [ ] 신고 또는 댓글 같은 사용자 상호작용이 성공/실패 상태를 올바르게 표시한다

#### Phase D — 관리자 페이지 E2E 시나리오

- [ ] 관리자가 `/login`에서 로그인한다
- [ ] 2FA 미등록 또는 미완료 상태에서 보호 페이지 접근 시 `/settings/totp-setup`으로 이동한다
- [ ] 2FA 완료 관리자가 `/dashboard`에 접근한다
- [ ] 관리자 메뉴에서 `/users`, `/applications`, `/posts`, `/transactions`, `/moderation`, `/settings` 접근이 가능하다
- [ ] 작가 신청 목록에서 신청 상세를 확인하고 승인/거부 액션을 수행한다
- [ ] 콘텐츠 검수 또는 신고 처리 페이지에서 상태 변경 액션을 수행한다

#### Phase E — 사용자·관리자 연결 시나리오

- [ ] 사용자가 작가 신청 제출 → 관리자가 승인 → 사용자 계정이 artist 상태로 전환된다
- [ ] 작가가 포스트 제출 → 관리자가 콘텐츠 승인 → 사용자 피드에 노출된다
- [ ] 사용자가 신고 제출 → 관리자가 처리 → 신고/경고 상태가 사용자 화면에 반영된다
- [ ] 경매 또는 거래 상태를 관리자가 확인하고 사용자 화면의 상태와 일치하는지 검증한다

### 2.2 Out of Scope

- Playwright 외 브라우저 자동화 도구 도입 비교를 장기간 수행하는 것
- 모든 페이지의 픽셀 단위 스냅샷 테스트
- 외부 결제, 외부 이메일, 실제 OAuth Provider를 사용하는 완전한 production E2E
- 부하 테스트, 성능 테스트, 보안 침투 테스트
- 모바일 네이티브 앱 테스트
- 모든 관리자 기능의 CRUD exhaustive 테스트

---

## 3. Requirements

### 3.1 Functional Requirements

| ID | Requirement | Priority | Phase | Status |
|----|-------------|----------|-------|--------|
| FR-01 | 사용자 앱과 관리자 앱 E2E 테스트를 동일 명령 또는 명확한 명령 세트로 실행할 수 있다 | High | A | Pending |
| FR-02 | E2E 테스트는 backend, frontend, admin의 base URL을 환경변수로 주입받는다 | High | A | Pending |
| FR-03 | 테스트 계정과 fixture 데이터는 반복 실행해도 충돌하지 않는다 | High | B | Pending |
| FR-04 | 일반 사용자 로그인 세션을 생성하거나 재사용할 수 있다 | High | B | Pending |
| FR-05 | 관리자 로그인 및 2FA 완료 상태를 테스트에서 재현할 수 있다 | High | B | Pending |
| FR-06 | 사용자 핵심 탐색 플로우가 green 상태로 검증된다 | High | C | Pending |
| FR-07 | 작가 신청 제출 플로우가 green 상태로 검증된다 | High | C | Pending |
| FR-08 | 관리자 대시보드와 주요 운영 메뉴 접근이 green 상태로 검증된다 | High | D | Pending |
| FR-09 | 관리자 작가 승인 플로우가 green 상태로 검증된다 | High | D | Pending |
| FR-10 | 사용자 제출 → 관리자 처리 → 사용자 화면 반영 연결 시나리오가 최소 1개 이상 green 상태로 검증된다 | High | E | Pending |
| FR-11 | 실패 시 trace, screenshot, video 중 최소 trace와 screenshot을 확인할 수 있다 | Medium | A | Pending |
| FR-12 | CI에서는 headless 실행, 로컬에서는 headed/debug 실행이 가능하다 | Medium | A | Pending |

### 3.2 Non-Functional Requirements

| Category | Criteria | Measurement Method |
|----------|----------|-------------------|
| Reliability | 핵심 E2E 테스트는 동일 환경에서 3회 연속 통과한다 | 로컬 반복 실행 |
| Speed | 기본 smoke E2E는 5분 이내 완료한다 | Playwright report |
| Debuggability | 실패 시 trace와 screenshot으로 원인 위치를 파악할 수 있다 | 실패 리포트 확인 |
| Maintainability | 테스트 selector는 텍스트 의존을 최소화하고 안정적인 role/test id를 사용한다 | 코드 리뷰 |
| Isolation | 테스트 실행 후 DB 상태가 다음 실행에 영향을 주지 않는다 | fixture reset 검증 |
| Accessibility | 주요 클릭 대상은 role 기반 locator로 접근 가능하다 | Playwright locator 리뷰 |
| Security | production 인증·2FA 정책을 테스트 편의를 위해 약화하지 않는다 | 코드 리뷰 |

---

## 4. Success Criteria

### 4.1 Definition of Done

- [ ] Playwright 기반 E2E 실행 구조가 확정되어 문서화된다
- [ ] 사용자 앱 smoke 테스트 3개 이상 작성 및 통과
- [ ] 관리자 앱 smoke 테스트 3개 이상 작성 및 통과
- [ ] 사용자→관리자 연결 시나리오 1개 이상 작성 및 통과
- [ ] 테스트용 계정/fixture 생성 방식이 반복 실행 가능하다
- [ ] 실패 리포트(trace/screenshot)가 로컬에서 확인 가능하다
- [ ] `frontend`와 `admin`의 기존 build/lint 흐름을 깨지 않는다
- [ ] CI 도입 여부와 실행 조건이 결정된다

### 4.2 Initial E2E Candidate List

| Group | Scenario | Expected Result |
|-------|----------|-----------------|
| User smoke | 랜딩 또는 피드 진입 | 주요 내비게이션과 핵심 CTA가 렌더링된다 |
| User auth | 로그인 후 계정 페이지 진입 | 인증 사용자 정보가 표시된다 |
| User artist | 작가 신청 제출 | 신청 완료 또는 pending 상태가 표시된다 |
| Admin auth | 관리자 로그인 | `/dashboard` 접근 가능 |
| Admin 2FA | 2FA 미완료 보호 라우트 접근 | 설정 페이지로 리다이렉트 |
| Admin ops | 작가 신청 큐 접근 | 신청 목록 또는 empty state 표시 |
| Cross-app | 사용자 작가 신청 → 관리자 승인 | 사용자 role/status가 artist로 반영 |
| Cross-app | 포스트 제출 → 관리자 승인 | 사용자 피드 또는 상세에 published 상태 노출 |

---

## 5. Risks and Mitigation

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| 2FA/passkey를 E2E에서 안정적으로 재현하기 어려움 | 높음 | 중 | 테스트 전용 admin seed에서 TOTP secret을 고정하고 실제 TOTP 코드를 생성하는 방식 우선 검토 |
| DB fixture가 기존 개발 데이터와 충돌 | 높음 | 중 | E2E 전용 DB 또는 테스트 namespace/email prefix 사용 |
| 실제 OAuth/메일/결제 의존으로 테스트가 flaky해짐 | 높음 | 중 | smoke E2E는 mock/provider stub 기반, 실제 provider는 수동 QA 또는 별도 nightly로 분리 |
| 다중 앱 동시 실행 설정이 복잡해짐 | 중 | 중 | Playwright webServer 여러 개 또는 상위 orchestration script 중 하나로 표준화 |
| 텍스트 기반 selector가 i18n 변경에 취약 | 중 | 높음 | role locator 우선, 필요 시 `data-testid` 최소 도입 |
| CI 실행 시간이 길어짐 | 중 | 중 | smoke suite와 full suite를 분리 |
| 테스트가 구현 세부사항에 과도하게 결합 | 중 | 중 | 사용자 행동 중심의 페이지 객체 또는 fixture helper만 도입 |

---

## 6. Architecture Considerations

### 6.1 Project Level Selection

| Level | Characteristics | Recommended For | Selected |
|-------|-----------------|-----------------|:--------:|
| Starter | Simple static site | 정적 페이지 중심 | ☐ |
| **Dynamic** | Fullstack app with backend and BaaS/custom API | 현재 Domo v1 구조 | **☑** |
| Enterprise | Multi-service infra and complex CI grid | 대규모 병렬 테스트 | ☐ |

현재 프로젝트는 `frontend`, `admin`, `backend`가 분리되어 있지만 단일 v1 애플리케이션 단위로 운영되므로 Dynamic 레벨의 E2E 체계를 우선 적용한다.

### 6.2 Key Architectural Decisions

| Decision | Options | Recommended | Rationale |
|----------|---------|-------------|-----------|
| E2E runner | Playwright / Cypress | **Playwright** | 다중 브라우저, trace, multi webServer, role locator 지원이 강함 |
| 테스트 위치 | 루트 `e2e/` / 각 앱 내부 | **Design 단계에서 확정** | 사용자·관리자 연결 시나리오는 루트가 자연스럽고, 앱별 smoke는 각 앱 내부도 가능 |
| 인증 준비 | UI 로그인 / API 로그인 / storageState | **storageState + 핵심 UI 로그인 1개** | 속도와 실제성 균형 |
| 관리자 2FA | 우회 / 고정 TOTP secret / passkey mock | **고정 TOTP secret** | production 정책을 약화하지 않고 자동화 가능 |
| 데이터 준비 | SQL seed / API factory / UI 생성 | **API/seed hybrid** | 연결 시나리오는 빠른 seed 후 UI 액션으로 검증 |
| Suite 분리 | smoke/full 단일 / 분리 | **smoke와 full 분리** | CI 시간을 제어하고 로컬 디버깅을 단순화 |

---

## 7. Implementation Order

| Step | Work | Dependency |
|------|------|------------|
| 1 | 현재 `frontend`, `admin`, `backend` 실행 방식과 테스트 환경변수 정리 | 없음 |
| 2 | Playwright 설치 위치와 `playwright.config.ts` 위치 결정 | Step 1 |
| 3 | webServer 또는 실행 스크립트로 backend/frontend/admin 기동 방식 구성 | Step 2 |
| 4 | 테스트 계정/fixture 생성 helper 설계 | Step 1 |
| 5 | 사용자 앱 smoke 테스트 작성 | Step 2~4 |
| 6 | 관리자 앱 smoke 테스트 작성 | Step 2~4 |
| 7 | 사용자→관리자 연결 시나리오 1개 작성 | Step 5~6 |
| 8 | trace/screenshot/report 설정 및 README 또는 docs 보강 | Step 5~7 |
| 9 | CI 실행 조건 결정 및 필요 시 workflow 반영 | Step 8 |

---

## 8. Open Questions

| ID | Question | Options | Recommendation |
|----|----------|---------|----------------|
| OQ-1 | Playwright 설정 위치 | A. `v1/e2e` 루트 통합 / B. `frontend`와 `admin` 각각 / C. `frontend`에 두 앱 통합 | **A**: 사용자·관리자 연결 시나리오를 한 suite에서 다루기 좋음 |
| OQ-2 | E2E 테스트 DB | A. 로컬 dev DB 재사용 / B. 별도 e2e DB / C. transaction rollback fixture | **B**: 반복 실행 안정성이 높음 |
| OQ-3 | 관리자 2FA 자동화 방식 | A. 고정 TOTP secret / B. 테스트 우회 env / C. passkey mock | **A**: 실제 정책과 가장 가까움 |
| OQ-4 | CI 도입 시점 | A. smoke만 즉시 / B. 로컬 안정화 후 / C. nightly만 | **A**: 작은 smoke부터 회귀 방지 효과가 큼 |
| OQ-5 | selector 정책 | A. role/text 우선 + 최소 `data-testid` / B. 전부 `data-testid` / C. CSS selector | **A**: 접근성과 유지보수 균형 |

---

## 9. Next Step

사용자 확인 후 `/pdca design user-admin-e2e-tests` 단계에서 다음을 상세화한다:

- Playwright config 위치와 실행 명령
- 테스트 DB/fixture 전략
- 인증 storageState 생성 방식
- 사용자·관리자 smoke suite 상세 케이스
- CI와 로컬 디버깅 운영 방식
