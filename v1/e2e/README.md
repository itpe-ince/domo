# Domo E2E Tests

Domo 사용자 웹앱(`frontend`)과 관리자 콘솔(`admin`)을 Playwright로 검증하는 E2E 워크스페이스입니다.

## Prerequisites

다음 서버가 실행 중이어야 합니다.

| Service | Default URL | Example command |
|---------|-------------|-----------------|
| Backend API | `http://localhost:3710/v1` | `cd ../backend && uvicorn app.main:app --host 0.0.0.0 --port 3710 --reload` |
| User Web | `http://localhost:3000` | `cd ../frontend && NEXT_PUBLIC_API_URL=http://localhost:3710/v1 npm run dev` |
| Admin Web | `http://localhost:3800` | `cd ../admin && NEXT_PUBLIC_API_URL=http://localhost:3710/v1 npm run dev` |

현재 로컬 작업 환경에서 사용자 앱을 `3700` 포트로 띄운 경우 `E2E_FRONTEND_URL=http://localhost:3700`을 지정하세요.

## Install

```bash
cd v1/e2e
npm install
npx playwright install chromium
```

## Seed E2E Accounts

실제 인증 smoke를 실행하려면 백엔드 DB에 E2E 계정을 준비해야 합니다.

```bash
cd v1/backend
alembic upgrade head
ALLOW_E2E_SEED=true python -m scripts.seed_e2e
```

기본 계정:

| Role | Email | Password |
|------|-------|----------|
| user | `e2e-user@domo.example.com` | `DomoE2EUser!2026` |
| artist | `e2e-artist@domo.example.com` | `DomoE2EArtist!2026` |
| admin | `e2e-admin@domo.example.com` | `DomoE2EAdmin!2026` |

기본 admin TOTP secret:

```text
JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP
```

`seed_e2e.py`는 `ALLOW_E2E_SEED=true`가 없으면 실행을 거부합니다.

## Environment

`.env.e2e.example`을 참고해 `.env.e2e`를 만들 수 있습니다. 값을 파일에 저장하지 않고 명령 앞에 직접 붙여 실행해도 됩니다.

```bash
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

## Commands

| Command | Purpose |
|---------|---------|
| `npm test` | 전체 E2E suite 실행 |
| `npm run test:smoke` | 사용자/admin smoke suite 실행 |
| `npm run test:user` | 사용자 앱 smoke만 실행 |
| `npm run test:admin` | 관리자 앱 smoke만 실행 |
| `npm run test:cross` | cross-app suite 실행 |
| `npm run test:headed` | headed browser로 디버깅 |
| `npm run test:debug` | Playwright Inspector 실행 |
| `npm run report` | HTML report 열기 |

## Artifacts

실패 시 다음 산출물이 생성됩니다.

| Path | Description |
|------|-------------|
| `test-results/` | trace, screenshot, video |
| `playwright-report/` | HTML report |
| `playwright/.auth/` | generated storageState |

위 경로와 `.env.e2e`는 git에 커밋하지 않습니다.

Trace 확인:

```bash
npx playwright show-trace test-results/<failed-test>/trace.zip
```

## Current Coverage

현재 구현된 기본 smoke:

- guest landing page render
- authenticated user feed render
- authenticated user account page render
- authenticated admin dashboard render
- authenticated admin users page render
- authenticated admin applications page render

아직 남은 주요 확장:

- 사용자 작가 신청 → 관리자 승인 → 사용자 상태 반영 cross-app E2E
- 관리자 `/login` UI + TOTP 입력 E2E
- 주요 화면 heading/nav/CTA assertion 강화
