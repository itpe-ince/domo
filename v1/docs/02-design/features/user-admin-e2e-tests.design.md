---
template: design
version: 1.0
feature: user-admin-e2e-tests
date: 2026-05-11
author: itpe-ince (GPT-5.5)
project: domo
version: v1
status: Draft
---

# 사용자·관리자 페이지 E2E 테스트 Design Document

> **Summary**: Domo 사용자 웹앱과 관리자 콘솔의 핵심 브라우저 플로우를 Playwright 기반 통합 E2E 워크스페이스로 검증한다.
>
> **Project**: domo (v1)
> **Version**: v1
> **Author**: itpe-ince
> **Date**: 2026-05-11
> **Status**: Draft
> **Planning Doc**: [user-admin-e2e-tests.plan.md](../../01-plan/features/user-admin-e2e-tests.plan.md)

---

## 1. Overview

### 1.1 Design Goals

이번 Design의 목표는 구현자가 바로 Do 단계에 들어갈 수 있도록 E2E 테스트의 실행 구조, 인증 세션 준비 방식, 테스트 데이터 전략, 첫 smoke suite 범위를 명확히 정하는 것이다.

- `frontend` 사용자 앱과 `admin` 관리자 앱을 하나의 Playwright 워크스페이스에서 검증
- 사용자 세션과 관리자 세션을 `storageState`로 준비해 테스트 속도와 안정성 확보
- 관리자 2FA 정책은 우회하지 않고 고정 TOTP secret 기반으로 자동화
- 사용자 앱 smoke, 관리자 앱 smoke, 교차 플로우를 suite 단위로 분리
- 실패 시 trace/screenshot/report를 남겨 재현 가능한 QA 증거 확보

### 1.2 Design Principles

- **사용자 행동 중심**: 내부 구현보다 실제 화면 이동, 버튼 클릭, 상태 변화에 집중한다.
- **운영 정책 보존**: 관리자 2FA, 권한 게이트, 인증 토큰 저장 정책을 테스트 편의 때문에 약화하지 않는다.
- **반복 실행 안정성**: 테스트 데이터는 고유 prefix와 seed helper로 충돌을 피한다.
- **작은 smoke 우선**: PR/로컬 기본 suite는 짧게 유지하고, 긴 교차 플로우는 full suite로 분리한다.
- **증거 기반 디버깅**: 실패 시 trace와 screenshot을 기본 산출물로 남긴다.

---

## 2. Architecture

### 2.1 Component Diagram

```
v1/e2e
  ├─ Playwright runner
  ├─ auth setup projects
  ├─ smoke tests
  ├─ cross-app tests
  └─ fixture helpers
       │
       ├── http://localhost:3000  → frontend Next.js
       ├── http://localhost:3800  → admin Next.js
       └── http://localhost:8000  → backend FastAPI
                                      │
                                      └── E2E DB / seeded test data
```

### 2.2 Runtime Topology

| Service | Default URL | Owner | Purpose |
|---------|-------------|-------|---------|
| Backend API | `http://localhost:8000/v1` | `v1/backend` | 사용자·관리자 API, seed helper 호출 대상 |
| User Web | `http://localhost:3000` | `v1/frontend` | 사용자 페이지 E2E 대상 |
| Admin Web | `http://localhost:3800` | `v1/admin` | 관리자 콘솔 E2E 대상 |
| E2E Runner | local process | `v1/e2e` | Playwright 테스트 실행 |

### 2.3 Data Flow

```
global setup
  ↓
seed or ensure E2E accounts
  ↓
API login user/admin
  ↓
write storageState files
  ↓
run smoke projects
  ↓
run selected cross-app projects
  ↓
collect trace/screenshot/report
```

### 2.4 Playwright Projects

| Project | Depends On | Browser Context | Scope |
|---------|------------|-----------------|-------|
| `setup:user` | none | API request only | 일반 사용자/작가 `storageState` 생성 |
| `setup:admin` | none | API request only | 관리자 2FA 완료 `storageState` 생성 |
| `user-smoke` | `setup:user` | user state or guest | 사용자 앱 핵심 smoke |
| `admin-smoke` | `setup:admin` | admin state | 관리자 앱 핵심 smoke |
| `cross-app` | `setup:user`, `setup:admin` | multi-context | 사용자→관리자→사용자 연결 플로우 |

### 2.5 Dependencies

| Component | Depends On | Purpose |
|-----------|------------|---------|
| `@playwright/test` | Node.js | 브라우저 E2E runner |
| `otplib` | Node.js | 고정 TOTP secret으로 6자리 코드 생성 |
| `dotenv` | Node.js | `.env.e2e` 로딩 |
| Backend seed endpoint or script | FastAPI/DB | 테스트 계정과 fixture 보장 |
| `storageState` files | Playwright | 로그인 비용 절감 |

---

## 3. File Structure

### 3.1 Proposed Workspace

Plan의 권장값 OQ-01=A, OQ-02=C를 채택해 `v1/e2e`를 별도 워크스페이스로 둔다. 사용자 앱과 관리자 앱을 함께 다루는 교차 플로우가 핵심이므로 한쪽 앱 내부에 종속시키지 않는다.

```
v1/
  e2e/
    package.json
    package-lock.json
    playwright.config.ts
    .env.e2e.example
    README.md
    tests/
      setup/
        user-auth.setup.ts
        admin-auth.setup.ts
      user/
        user-smoke.spec.ts
        post-authoring.spec.ts
      admin/
        admin-smoke.spec.ts
        admin-2fa.spec.ts
      cross-app/
        artist-application-review.spec.ts
        post-review-publish.spec.ts
    fixtures/
      accounts.ts
      seed.ts
      test-data.ts
    support/
      api.ts
      auth.ts
      env.ts
      routes.ts
      selectors.ts
    playwright/.auth/
      user.json
      artist.json
      admin.json
```

### 3.2 Generated Artifacts

| Path | Git Policy | Description |
|------|------------|-------------|
| `v1/e2e/playwright-report/` | ignored | HTML report |
| `v1/e2e/test-results/` | ignored | trace, screenshot, video |
| `v1/e2e/playwright/.auth/*.json` | ignored | 로그인 세션 상태 |
| `v1/e2e/.env.e2e` | ignored | 로컬 credential |
| `v1/e2e/.env.e2e.example` | tracked | 필요한 env 문서 |

---

## 4. Configuration Design

### 4.1 Package Scripts

`v1/e2e/package.json`에 독립 실행 명령을 둔다.

| Script | Command | Purpose |
|--------|---------|---------|
| `test` | `playwright test` | 전체 E2E 실행 |
| `test:smoke` | `playwright test --project=user-smoke --project=admin-smoke` | 로컬/PR 기본 smoke |
| `test:user` | `playwright test --project=user-smoke` | 사용자 앱만 실행 |
| `test:admin` | `playwright test --project=admin-smoke` | 관리자 앱만 실행 |
| `test:cross` | `playwright test --project=cross-app` | 교차 플로우 실행 |
| `test:headed` | `playwright test --headed` | 로컬 디버깅 |
| `test:debug` | `playwright test --debug` | Playwright Inspector |
| `report` | `playwright show-report` | 실패/성공 report 확인 |

### 4.2 Environment Variables

`.env.e2e.example` 기준 변수:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `E2E_FRONTEND_URL` | yes | `http://localhost:3000` | 사용자 앱 base URL |
| `E2E_ADMIN_URL` | yes | `http://localhost:3800` | 관리자 앱 base URL |
| `E2E_API_URL` | yes | `http://localhost:8000/v1` | Backend API base URL |
| `E2E_USER_EMAIL` | yes | none | 일반 사용자 계정 |
| `E2E_USER_PASSWORD` | yes | none | 일반 사용자 비밀번호 |
| `E2E_ARTIST_EMAIL` | yes | none | 작가 계정 |
| `E2E_ARTIST_PASSWORD` | yes | none | 작가 비밀번호 |
| `E2E_ADMIN_EMAIL` | yes | none | 관리자 계정 |
| `E2E_ADMIN_PASSWORD` | yes | none | 관리자 비밀번호 |
| `E2E_ADMIN_TOTP_SECRET` | yes | none | 테스트 관리자 고정 TOTP secret |
| `E2E_RUN_ID` | no | timestamp | 고유 데이터 prefix |
| `E2E_HEADLESS` | no | `true` | headless 실행 여부 |

### 4.3 Playwright Defaults

| Setting | Value | Rationale |
|---------|-------|-----------|
| `testDir` | `./tests` | 테스트 위치 명확화 |
| `timeout` | `60_000` | 다중 앱 E2E 여유 |
| `expect.timeout` | `10_000` | Next.js 렌더링 대기 |
| `retries` | CI 1, local 0 | flaky 탐지와 CI 일시 오류 균형 |
| `trace` | `retain-on-failure` | 실패 분석 |
| `screenshot` | `only-on-failure` | 실패 증거 |
| `video` | `retain-on-failure` | 긴 교차 플로우 분석 |
| `reporter` | `html`, `list` | 로컬/CI 양쪽 대응 |
| `use.baseURL` | project별 지정 | frontend/admin 분리 |

---

## 5. Authentication Design

### 5.1 User Session

사용자 앱은 `frontend/src/lib/api.ts`의 `tokenStore`가 `localStorage`에 access token과 refresh token을 저장한다. E2E에서는 UI 로그인을 매 테스트마다 반복하지 않고, setup project가 API 로그인 후 동일 key에 token을 주입한 `storageState`를 저장한다.

```
POST {E2E_API_URL}/auth/login/email
  body: { email, password }
  ↓
tokens.access_token / tokens.refresh_token
  ↓
localStorage:
  domo_access_token
  domo_refresh_token
  ↓
playwright/.auth/user.json
```

실제 key 이름은 구현 단계에서 `frontend/src/lib/api.ts`와 `admin/src/lib/api.ts`의 `TOKEN_KEY`, `REFRESH_KEY`를 확인해 맞춘다. 하드코딩이 불가피하면 `support/auth.ts` 한 곳에 상수화한다.

### 5.2 Admin Session

관리자 인증은 password step과 TOTP verify step으로 분리되어 있다.

```
POST {E2E_API_URL}/auth/admin/login
  body: { email, password }
  ↓
{ totp_required: true, challenge_token }
  ↓
TOTP code = otplib.authenticator.generate(E2E_ADMIN_TOTP_SECRET)
  ↓
POST {E2E_API_URL}/auth/admin/login/verify
  body: { challenge_token, totp_code }
  ↓
tokens
  ↓
playwright/.auth/admin.json
```

TOTP 미등록 관리자 테스트는 별도 fixture 계정 `admin_without_2fa`로 분리한다. 이 계정은 비즈니스 화면 접근 시 `/settings/totp-setup`으로 강제 이동되는지만 smoke에서 검증한다.

### 5.3 Auth Test Coverage

| Case | Project | Method | Expected |
|------|---------|--------|----------|
| 일반 사용자 세션 생성 | `setup:user` | API login | `user.json` 생성 |
| 작가 세션 생성 | `setup:user` | API login | `artist.json` 생성 |
| 관리자 세션 생성 | `setup:admin` | API login + TOTP | `admin.json` 생성 |
| 관리자 UI 로그인 smoke | `admin-smoke` | UI form | `/dashboard` 이동 |
| 2FA 미완료 게이트 | `admin-smoke` | pre-seeded account | `/settings/totp-setup` 이동 |

---

## 6. Test Data Design

### 6.1 Account Fixtures

| Fixture | Role | Required State | Used By |
|---------|------|----------------|---------|
| `e2e_user` | `user` | active, email verified | user smoke, cross-app |
| `e2e_artist` | `artist` | active, artist profile exists | post authoring, cross-app |
| `e2e_admin` | `admin` | active, TOTP enabled with fixed secret | admin smoke |
| `e2e_admin_without_2fa` | `admin` | active, TOTP not enabled | 2FA gate test |
| `e2e_review_user` | `user` | active, no artist profile | artist application flow |

### 6.2 Data Isolation

Plan의 OQ-04=B를 채택해 고유 prefix 데이터를 기본으로 한다.

```
runId = E2E_RUN_ID ?? yyyyMMddHHmmss
email = e2e+{runId}+artist@example.test
title = [E2E:{runId}] Sunrise in Lima
```

반복 실행 안정성을 위해 다음 원칙을 적용한다:

- 테스트가 생성하는 사용자 입력값은 `[E2E:{runId}]` prefix를 붙인다.
- 목록 조회 assertion은 prefix 기반으로 대상 row를 찾는다.
- cleanup은 best-effort로 두되, cleanup 실패가 다음 실행을 깨지 않도록 고유 데이터를 우선한다.
- 운영/스테이징 URL에서는 seed helper 실행을 금지한다.

### 6.3 Seed Strategy

초기 구현은 `API/seed hybrid`로 설계한다.

| Method | Use Case | Notes |
|--------|----------|-------|
| API login | 세션 생성 | 실제 인증 경로 검증 |
| seed helper | 계정/기본 fixture 보장 | 빠르고 반복 가능 |
| UI action | 핵심 사용자 행동 검증 | 작가 신청, 승인, 포스트 제출 등 |

Do 단계에서 선택할 구현 옵션:

- **Option A**: `backend/scripts/seed_e2e.py` 추가 후 실행 스크립트에서 호출
- **Option B**: 테스트 환경 전용 `POST /v1/test/seed` 엔드포인트 추가
- **Option C**: 기존 seed 스크립트 확장

권장: **Option A**. 운영 API surface를 늘리지 않고, 로컬/CI에서 명시적으로 실행하기 쉽다.

---

## 7. Test Suite Design

### 7.1 User Smoke Suite

| ID | File | Scenario | Auth | Assertions |
|----|------|----------|------|------------|
| U-01 | `user-smoke.spec.ts` | guest landing/feed 접근 | none | 주요 nav 또는 로그인 CTA 표시 |
| U-02 | `user-smoke.spec.ts` | user `/feed` 접근 | user | feed heading/list/empty state 표시 |
| U-03 | `user-smoke.spec.ts` | user `/me/account` 접근 | user | 사용자 이메일/프로필 상태 표시 |
| U-04 | `post-authoring.spec.ts` | artist `/posts/new` 접근 | artist | 에디터 form, 발행 CTA 표시 |
| U-05 | `post-authoring.spec.ts` | 일반 포스트 작성 smoke | artist | submit 후 draft/pending/success 상태 |

### 7.2 Admin Smoke Suite

| ID | File | Scenario | Auth | Assertions |
|----|------|----------|------|------------|
| A-01 | `admin-smoke.spec.ts` | admin `/dashboard` 접근 | admin | dashboard shell/nav 표시 |
| A-02 | `admin-smoke.spec.ts` | 주요 메뉴 이동 | admin | `/users`, `/applications`, `/posts` 화면 표시 |
| A-03 | `admin-smoke.spec.ts` | 로그인 실패 UI | none | 오류 메시지 표시 |
| A-04 | `admin-2fa.spec.ts` | 2FA 미완료 보호 라우트 | admin_without_2fa | `/settings/totp-setup` 이동 |
| A-05 | `admin-2fa.spec.ts` | TOTP 로그인 UI | none | password → TOTP → dashboard 이동 |

### 7.3 Cross-App Suite

| ID | File | Scenario | Contexts | Assertions |
|----|------|----------|----------|------------|
| X-01 | `artist-application-review.spec.ts` | 사용자 작가 신청 → 관리자 승인 | user + admin | 사용자 role/status artist 반영 |
| X-02 | `post-review-publish.spec.ts` | 작가 포스트 제출 → 관리자 승인 → 피드 노출 | artist + admin + guest/user | published 상태 노출 |
| X-03 | future | 사용자 신고 → 관리자 처리 | user + admin | warning/report status 반영 |
| X-04 | future | 경매 생성/입찰 → 관리자 거래 확인 | artist + user + admin | transaction row 확인 |

초기 Do 단계에서는 X-01 또는 X-02 중 하나만 필수로 구현한다. 권장 첫 교차 플로우는 **X-01 작가 신청 승인**이다. 결제/미디어 업로드보다 외부 의존성이 적고, MVP 관리자 핵심 가치와 직접 연결된다.

---

## 8. Locator and Selector Policy

### 8.1 Priority

1. `getByRole()` with accessible name
2. `getByLabel()` for form inputs
3. `getByText()` for stable user-facing text
4. `getByTestId()` for dynamic tables, icon buttons, repeated cards
5. CSS selector는 마지막 수단

### 8.2 `data-testid` Policy

다음 경우에만 `data-testid`를 추가한다:

- 동일한 버튼/링크가 반복 리스트에 여러 번 나타나는 경우
- i18n 텍스트 변경 가능성이 높은 경우
- 아이콘 only 버튼처럼 accessible name을 안정적으로 붙이기 어려운 경우
- 비동기 상태 배지처럼 테스트 대상이 명확해야 하는 경우

권장 네이밍:

```
admin-applications-table
admin-application-row-{id}
admin-application-approve-button
post-editor-submit-button
artist-application-status-badge
```

---

## 9. Error Handling and Debugging

### 9.1 Failure Artifacts

| Artifact | Policy | Purpose |
|----------|--------|---------|
| Trace | retain on failure | step-by-step 재현 |
| Screenshot | only on failure | 최종 화면 상태 확인 |
| Video | retain on failure | 긴 교차 플로우 분석 |
| HTML report | always generated locally | 결과 탐색 |
| Console logs | collect on failure | frontend/admin runtime error 확인 |

### 9.2 Common Failure Categories

| Failure | Detection | Handling |
|---------|-----------|----------|
| 서버 미기동 | `webServer` timeout | 명확한 stderr와 README troubleshooting |
| 로그인 실패 | setup project failure | credential/env 검증 메시지 |
| TOTP mismatch | admin setup failure | secret/time sync 체크 안내 |
| selector mismatch | test failure trace | role/test id 정책에 따라 수정 |
| fixture 충돌 | seed failure or duplicated row | `E2E_RUN_ID` prefix 확인 |
| API 401/403 | response hook logging | storageState 재생성 |

---

## 10. Security Considerations

- `.env.e2e`와 `playwright/.auth/*.json`은 git에 커밋하지 않는다.
- E2E credential은 로컬 `.env.e2e` 또는 CI secret으로만 주입한다.
- 관리자 2FA는 테스트에서 우회하지 않고 고정 secret으로 실제 TOTP 코드를 생성한다.
- seed helper는 `ENVIRONMENT=e2e` 또는 명시적 `ALLOW_E2E_SEED=true`일 때만 실행한다.
- production/staging URL에 대해 seed helper가 실행되지 않도록 hostname deny/allow list를 둔다.
- trace/video에는 token이 노출될 수 있으므로 CI artifact retention 기간을 짧게 설정한다.

---

## 11. CI Strategy

### 11.1 Initial CI Scope

초기에는 PR마다 smoke만 실행하고, cross-app full suite는 수동 또는 nightly로 둔다.

| Trigger | Suite | Rationale |
|---------|-------|-----------|
| Pull Request | `test:smoke` | 빠른 회귀 감지 |
| Main branch nightly | `test` | 긴 교차 플로우 포함 |
| Manual dispatch | `test:cross` | 릴리즈 전 검증 |

### 11.2 CI Preconditions

- backend test DB 준비
- backend migrations 적용
- frontend/admin dependencies install
- e2e dependencies install
- seed script 실행
- Playwright browser install cache

CI는 별도 Design/Do 후속에서 구체화한다. 이번 Do의 최소 목표는 로컬 실행 가능한 E2E 워크스페이스와 smoke suite다.

---

## 12. Implementation Guide

### 12.1 Implementation Order

1. `v1/e2e` 워크스페이스 생성
2. `@playwright/test`, `dotenv`, `otplib` 설치
3. `.env.e2e.example`, `README.md`, `.gitignore` 항목 추가
4. `playwright.config.ts` 작성
5. `support/env.ts`, `support/api.ts`, `support/auth.ts` 작성
6. `tests/setup/user-auth.setup.ts` 작성
7. `tests/setup/admin-auth.setup.ts` 작성
8. `tests/user/user-smoke.spec.ts` 작성
9. `tests/admin/admin-smoke.spec.ts` 작성
10. `tests/admin/admin-2fa.spec.ts` 작성
11. 첫 cross-app 후보 1개 작성
12. 로컬 3회 반복 실행 후 flaky 여부 확인

### 12.2 Minimal Do Acceptance

Do 단계 최소 완료 기준:

- `cd v1/e2e && npm run test:smoke` 실행 가능
- 사용자 smoke 3개 이상 green
- 관리자 smoke 3개 이상 green
- `playwright-report` 확인 가능
- 실패 시 trace/screenshot 생성 확인
- README에 로컬 실행법과 env 설명 포함

### 12.3 Follow-Up Do Items

다음 항목은 smoke 안정화 후 확장한다:

- `cross-app` suite 전체 구현
- CI workflow 추가
- seed helper를 backend script로 정식화
- 주요 화면에 최소 `data-testid` 추가
- axe 접근성 검사를 Playwright suite로 통합

---

## 13. Open Questions Resolution

Plan의 Open Questions는 Design v1.0에서 다음처럼 채택한다.

| ID | Decision | Selected | Notes |
|----|----------|----------|-------|
| OQ-01 | E2E 파일 위치 | A. `v1/e2e` | 사용자·관리자 교차 플로우 중심 |
| OQ-02 | Playwright package 소유 | C. 별도 `e2e/package.json` | 기존 frontend/admin package 영향 최소화 |
| OQ-03 | 관리자 2FA 처리 | A. fixed TOTP secret | 운영 정책 보존 |
| OQ-04 | DB 초기화 전략 | B. 고유 prefix 데이터 | 반복 실행 안정성 우선 |
| OQ-05 | CI 실행 범위 | A. smoke만 PR | 비용과 안정성 균형 |
| OQ-06 | 모바일 E2E 포함 여부 | A. desktop only first | 첫 구축 범위 축소 |

---

## 14. Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2026-05-11 | Initial design for Playwright-based user/admin E2E workspace | itpe-ince (GPT-5.5) |
