---
template: analysis
version: 1.0
feature: user-admin-e2e-tests
date: 2026-05-11
author: itpe-ince (GPT-5.5)
project: domo
status: Draft
matchRate: 68
phase: check
---

# 사용자·관리자 페이지 E2E 테스트 Gap Analysis

> **Summary**: Playwright 기반 E2E 워크스페이스와 실제 인증 smoke 검증은 완료되었으나, Design에서 요구한 cross-app 플로우, README, CI, 일부 테스트 케이스가 아직 남아 있다.
>
> **Design Doc**: [user-admin-e2e-tests.design.md](../02-design/features/user-admin-e2e-tests.design.md)
> **Plan Doc**: [user-admin-e2e-tests.plan.md](../01-plan/features/user-admin-e2e-tests.plan.md)
> **Check Date**: 2026-05-11

---

## 1. Overall Result

| 항목 | 결과 |
|------|------|
| Match Rate | **68%** |
| Do 최소 기준 기준 | **83%** |
| 실제 실행 결과 | **8 passed (5.7s)** |
| 다음 PDCA | **Act / Iterate 권장** |

Design의 핵심 기반인 `v1/e2e` Playwright 워크스페이스, 인증 setup, 사용자 smoke, 관리자 smoke, E2E seed는 구현되었다. 또한 실제 user/artist/admin credential과 TOTP를 사용한 smoke 테스트가 통과했다.

다만 Design에서 명시한 `cross-app` suite, `README.md`, `support/routes.ts`, `support/selectors.ts`, fixture helper 분리, CI 전략 반영, 관리자 2FA UI 테스트는 아직 구현되지 않았다. 따라서 완료 보고서 단계로 가기에는 이르며, 우선 누락된 핵심 플로우를 보강하는 Iterate 단계가 적합하다.

---

## 2. Matched Items

### 2.1 Architecture / Workspace

| Design Requirement | Implementation | Status |
|--------------------|----------------|--------|
| `v1/e2e` 별도 워크스페이스 | `v1/e2e/package.json`, `package-lock.json` | ✅ |
| Playwright runner 구성 | `v1/e2e/playwright.config.ts` | ✅ |
| user/admin/cross-app project 정의 | `setup:user`, `setup:admin`, `user-smoke`, `admin-smoke`, `cross-app` project 존재 | ✅ |
| trace/screenshot/video/report 설정 | `trace: retain-on-failure`, `screenshot: only-on-failure`, `video: retain-on-failure`, HTML reporter | ✅ |
| E2E 산출물 git 제외 | `v1/.gitignore`에 `e2e/.env.e2e`, `playwright-report`, `test-results`, `.auth` 추가 | ✅ |

### 2.2 Authentication / Storage State

| Design Requirement | Implementation | Status |
|--------------------|----------------|--------|
| 사용자 `storageState` 생성 | `tests/setup/user-auth.setup.ts`, `support/auth.ts` | ✅ |
| 작가 `storageState` 생성 | `tests/setup/user-auth.setup.ts`, `playwright/.auth/artist.json` 경로 지원 | ✅ |
| 관리자 TOTP `storageState` 생성 | `tests/setup/admin-auth.setup.ts`, `support/auth.ts` | ✅ |
| localStorage token key 정합성 | `domo_access_token`, `domo_refresh_token` 사용 | ✅ |
| E2E credential 누락 시 guest smoke fallback | 빈 storageState 생성 | ✅ |

### 2.3 Test Data / Seed

| Design Requirement | Implementation | Status |
|--------------------|----------------|--------|
| E2E 전용 계정 seed | `backend/scripts/seed_e2e.py` | ✅ |
| seed 실행 안전장치 | `ALLOW_E2E_SEED=true` 없으면 실행 거부 | ✅ |
| user/artist/admin 계정 생성 | `e2e-user`, `e2e-artist`, `e2e-admin` | ✅ |
| artist profile fixture | `ArtistApplication`, `ArtistProfile` 생성 | ✅ |
| admin fixed TOTP secret | `E2E_ADMIN_TOTP_SECRET` 기반 설정 | ✅ |

### 2.4 Smoke Tests

| Design Requirement | Implementation | Status |
|--------------------|----------------|--------|
| 사용자 smoke 3개 이상 | landing, feed, account | ✅ |
| 관리자 smoke 3개 이상 | dashboard, users, applications | ✅ |
| 실제 브라우저 실행 | Playwright Desktop Chrome | ✅ |
| 실제 인증 기반 실행 | user/artist/admin setup 후 smoke 통과 | ✅ |

### 2.5 Migration / Local DB Readiness

| Issue | Implementation | Status |
|-------|----------------|--------|
| `0086_magic_link_tokens` 중복 email index | `email` column의 `index=True` 제거 | ✅ |
| `0088_audit_logs_partitioning` 기존 index 이름 충돌 | 기존 index `DROP INDEX IF EXISTS` 후 새 파티션 index 생성 | ✅ |
| DB head 적용 | `alembic upgrade head` 성공 | ✅ |

---

## 3. Gaps

| ID | Severity | Gap | Evidence | Recommended Action |
|----|----------|-----|----------|--------------------|
| G-01 | High | `cross-app` 테스트 파일이 없음 | `v1/e2e/tests/cross-app/` 미존재, `cross-app` project만 정의됨 | X-01 사용자 작가 신청 → 관리자 승인 → 사용자 상태 확인 플로우 추가 |
| G-02 | High | Design의 첫 교차 플로우 최소 1개가 미구현 | Design §7.3, §12.2 요구. 현재 smoke만 존재 | `artist-application-review.spec.ts` 우선 구현 |
| G-03 | Medium | 관리자 2FA UI 로그인 smoke가 미구현 | `admin-smoke.spec.ts`는 storageState 기반 페이지 접근만 확인 | `/login` password → TOTP → `/dashboard` UI 플로우 추가 |
| G-04 | Medium | smoke assertion이 “fatal render error 없음” 수준으로 얕음 | `user-smoke.spec.ts`, `admin-smoke.spec.ts`가 body visible + error text absence만 확인 | 주요 heading/nav/CTA/계정 정보 assertion 보강 |
| G-05 | Medium | `README.md`가 없어 실행법 문서화가 부족 | `v1/e2e/README.md` 미존재 | 로컬 서버 포트, seed, env, 실행 명령, trace 확인법 문서화 |
| G-06 | Medium | CI 실행 조건 미구현 | GitHub workflow 또는 CI 설정 없음 | smoke는 PR, full/cross는 nightly 또는 manual로 후속 반영 |
| G-07 | Low | Design의 `fixtures/`, `routes.ts`, `selectors.ts` 구조가 미구현 | `support/env.ts`, `api.ts`, `auth.ts`만 존재 | 반복 코드가 늘어나는 시점에 helper 분리 |
| G-08 | Low | `.env.e2e.example`의 TOTP secret 길이가 예전 짧은 값 | `.env.e2e.example`는 `BASE32SECRET` placeholder | 실제 요구 길이에 맞춘 예시 placeholder로 갱신 |
| G-09 | Low | `post-authoring.spec.ts`, `admin-2fa.spec.ts` 파일이 Design 대비 없음 | Design §3.1 파일 구조와 §7.1/7.2 | smoke 안정화 후 파일 분리 또는 현 파일 내 케이스 추가 |

---

## 4. Acceptance Criteria Status

### 4.1 Design §12.2 Minimal Do Acceptance

| Criteria | Status | Evidence |
|----------|--------|----------|
| `cd v1/e2e && npm run test:smoke` 실행 가능 | ✅ | authenticated smoke 실행 성공 |
| 사용자 smoke 3개 이상 green | ✅ | `user-smoke.spec.ts` 3개 통과 |
| 관리자 smoke 3개 이상 green | ✅ | `admin-smoke.spec.ts` 3개 통과 |
| `playwright-report` 확인 가능 | ✅ | HTML reporter 설정 존재 |
| 실패 시 trace/screenshot 생성 확인 | ✅ | 실패 재시도 과정에서 trace 생성 확인 |
| README에 로컬 실행법과 env 설명 포함 | ❌ | `v1/e2e/README.md` 미존재 |

**Minimal Do 기준 Match Rate**: 5/6 = **83%**

### 4.2 Plan / Design Broader Acceptance

| Criteria | Status | Notes |
|----------|--------|-------|
| Playwright 기반 E2E 실행 구조 확정 | ✅ | 별도 `v1/e2e` workspace |
| 사용자 앱 smoke 테스트 3개 이상 작성 및 통과 | ✅ | 실제 인증 setup 포함 |
| 관리자 앱 smoke 테스트 3개 이상 작성 및 통과 | ✅ | 실제 admin TOTP setup 포함 |
| 사용자→관리자 연결 시나리오 1개 이상 작성 및 통과 | ❌ | High gap |
| 테스트용 계정/fixture 생성 방식 반복 실행 가능 | ✅ | `seed_e2e.py` idempotent upsert |
| 실패 리포트(trace/screenshot) 로컬 확인 가능 | ✅ | Playwright 설정 및 실패 artifact 확인 |
| 기존 frontend/admin build/lint 흐름 비파괴 | ⚠️ | package 분리로 영향 낮음. 별도 build/lint 재실행은 미확인 |
| CI 도입 여부와 실행 조건 결정 | ⚠️ | Design에는 정의, 실제 workflow 없음 |

---

## 5. Verification Evidence

### 5.1 Commands

```bash
cd /Users/sangincha/dev/domo/v1/backend
alembic upgrade head

ALLOW_E2E_SEED=true python -m scripts.seed_e2e

cd /Users/sangincha/dev/domo/v1/e2e
E2E_FRONTEND_URL=http://localhost:3700 \
E2E_ADMIN_URL=http://localhost:3800 \
E2E_API_URL=http://localhost:3710/v1 \
E2E_USER_EMAIL=e2e-user@domo.example.com \
E2E_USER_PASSWORD='DomoE2EUser!2026' \
E2E_ARTIST_EMAIL=e2e-artist@domo.example.com \
E2E_ARTIST_PASSWORD='DomoE2EArtist!2026' \
E2E_ADMIN_EMAIL=e2e-admin@domo.example.com \
E2E_ADMIN_PASSWORD='DomoE2EAdmin!2026' \
E2E_ADMIN_TOTP_SECRET=JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP \
npm run test:smoke
```

### 5.2 Result

```text
8 passed (5.7s)
```

---

## 6. Risk Notes

- `seed_e2e.py`는 E2E 계정 비밀번호와 TOTP secret을 deterministic하게 만든다. `ALLOW_E2E_SEED=true` guard가 있으므로 실수 방지는 되어 있지만, 운영 DB에서 실행되지 않도록 실행 환경을 계속 주의해야 한다.
- `TOTP_ENCRYPTION_KEY`가 없는 로컬 환경에서는 TOTP secret이 평문 저장된다. 현재 로컬 E2E 목적에는 허용 가능하지만, staging/production에서는 금지해야 한다.
- 현재 smoke는 인증 state 생성의 성공은 검증하지만, 화면에서 실제 사용자 이메일/관리자 이름이 보이는지까지는 확인하지 않는다.
- migration 수정은 로컬 DB head 적용을 위해 필요했지만, 기존 환경에서 이미 일부 migration이 반쯤 적용된 상태였기 때문에 다른 DB에서도 재확인하는 것이 좋다.

---

## 7. Recommended Next Action

**Match Rate가 90% 미만이므로 `/pdca iterate user-admin-e2e-tests` 권장.**

우선순위:

1. `v1/e2e/README.md` 추가
2. `tests/cross-app/artist-application-review.spec.ts` 추가
3. admin `/login` UI + TOTP smoke 추가
4. smoke assertion을 heading/nav/role 기반으로 강화
5. `.env.e2e.example`의 TOTP placeholder 갱신

위 1~3을 완료하면 Match Rate는 약 90% 이상으로 올라갈 가능성이 높다.
