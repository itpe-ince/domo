---
template: plan
version: 1.2
feature: real-auth
date: 2026-04-26
author: itpe-ince (Claude Opus 4.7)
project: domo
version: v1
---

# real-auth Planning Document

> **Summary**: Mock 로그인을 폐기하고, 실제 Google OAuth + 이메일/비밀번호 회원가입·로그인·이메일 인증·비밀번호 재설정·학생(학교 이메일) 인증을 단계적으로 구현한다.
>
> **Project**: domo (v1)
> **Version**: v1 (Phase 4 in progress)
> **Author**: itpe-ince
> **Date**: 2026-04-26
> **Status**: Draft

---

## 1. Overview

### 1.1 Purpose

현재 `v1/frontend`는 6곳에서 `loginWithMockEmail`을 호출하는 dev-mode 인증만 제공한다.
백엔드 `User.password_hash`는 `admin 전용` 주석이 붙어 있어 일반 사용자 자격증명 인증 경로가 존재하지 않는다.
서비스 오픈을 위해 다음을 충족시킨다:
- 실제 Google ID Token 기반 SNS 로그인 (백엔드는 이미 `GOOGLE_CLIENT_ID` 분기 보유 → 프런트 연동만 필요)
- 이메일 + 비밀번호 회원가입/로그인 (백엔드 신규)
- 이메일 인증 필수 정책 시행
- 비밀번호 재설정 플로우
- 회원가입 시 "학생" 구분을 선택한 사용자에 대한 학교 이메일 인증 필수
- mock 경로 제거 (또는 `NODE_ENV !== 'production'` 가드 + 기능 분리)

### 1.2 Background

- v1/backend의 `User` 모델은 `password_hash`, `password_changed_at`, `failed_login_count`, `locked_until` 컬럼을 이미 갖고 있으나, 회원/일반 사용자에게는 미사용 (admin TOTP 플로우만 구현됨).
- `verify_google_id_token()`는 `GOOGLE_CLIENT_ID` 미설정 시 `mock:<email>` 폴백을 허용 — 즉시 실모드 전환 가능.
- 학생 분류는 현재 **artist application 단계**의 `edu_email`/`edu_email_verified_at` 컬럼으로만 추적됨. 회원가입 단계의 학생 구분 로직은 미존재.
- `@tuzigroup.com` Google Workspace 보유 → 발신 도메인 `noreply@tuzigroup.com` 사용 가능.

### 1.3 Related Documents

- 디자인 기준: [v1/docs/02-design/design.md §3.1](../../02-design/design.md) (표준 응답 envelope)
- 기존 인증 구현: [v1/backend/app/api/auth.py](../../../backend/app/api/auth.py), [v1/backend/app/api/admin_auth.py](../../../backend/app/api/admin_auth.py), [v1/backend/app/services/google_auth.py](../../../backend/app/services/google_auth.py)
- 프런트 mock 사용처: `LoginModal.tsx`, `subscriptions/page.tsx`, `me/account/page.tsx`, `orders/page.tsx`, `onboarding/page.tsx`, `warnings/page.tsx`
- 학생/학교 이메일 기존 처리: [v1/backend/app/models/user.py:118-121](../../../backend/app/models/user.py#L118-L121) (ArtistApplication.edu_email)

---

## 2. Scope

### 2.1 In Scope

#### Phase A — 실제 Google OAuth (frontend 연동만)
- [ ] `@react-oauth/google` 또는 GIS(Google Identity Services) 도입
- [ ] `NEXT_PUBLIC_GOOGLE_CLIENT_ID` 도입
- [ ] `LoginModal`에 Google 로그인 버튼 추가 (mock 입력란과 공존, dev에선 둘 다, prod에선 Google만)
- [ ] dev 환경에서는 mock도 함께 동작 (env 가드)
- [ ] 백엔드: 변경 없음 (이미 `verify_google_id_token` 보유)

#### Phase B — 이메일/비밀번호 인증 (백엔드 신규 + 프런트 페이지 신설)
- [ ] DB 마이그레이션: User.password_hash 정책 확장 (admin 전용 주석 제거), `email_verified_at` 컬럼 추가
- [ ] DB 신규 테이블: `email_verification_tokens` (사용 1회, 24h TTL)
- [ ] DB 신규 컬럼: `User.user_type` enum('general'|'student'|'artist_pending') — `role`과 별개로 가입 시 선택, role은 기존대로 'user'/'artist'/'admin' 유지
- [ ] 백엔드 신규 엔드포인트:
  - `POST /auth/email/signup` — 이메일+비밀번호+display_name+user_type, 가입 직후 인증 메일 발송
  - `POST /auth/email/login` — 이메일+비밀번호, 미인증 계정은 401 + `EMAIL_NOT_VERIFIED` 코드
  - `POST /auth/email/verify` — 토큰 검증 + `email_verified_at` 세팅
  - `POST /auth/email/resend-verification` — rate limit 적용
- [ ] 이메일 발송 서비스: 추상 인터페이스 `EmailSender` + Gmail SMTP(App Password) 구현 (Phase B MVP) + 콘솔 출력 fallback (개발용)
- [ ] 프런트 신규 페이지:
  - `/login` (이메일/비밀번호 + Google 버튼)
  - `/signup` (이메일/비번/이름/유저타입 선택)
  - `/verify-email/[token]`
  - `/login`/`/signup` 진입 시 LoginModal은 "/login으로 이동"으로 단순화 (모달 제거 또는 1차 게이트로만 사용)

#### Phase C — 비밀번호 재설정
- [ ] DB 신규 테이블: `password_reset_tokens` (사용 1회, 1h TTL, IP/UA 기록)
- [ ] 백엔드 신규 엔드포인트:
  - `POST /auth/password/forgot` — 이메일 입력, 존재하지 않아도 200 (열거 공격 방지)
  - `POST /auth/password/reset` — 토큰 + 새 비밀번호
- [ ] 프런트 신규 페이지: `/forgot-password`, `/reset-password/[token]`

#### Phase D — Mock 제거 + 학교 이메일 인증
- [ ] User 신규 컬럼: `edu_email`, `edu_email_verified_at` (기존 ArtistApplication 컬럼과 별개로 사용자 레벨 보유)
- [ ] 백엔드 신규 엔드포인트:
  - `POST /me/student-verification/request` — 학교 이메일 입력, 인증 메일 발송 (도메인 화이트리스트 검증: ac.kr/edu/.ac.{국가코드} 등 + 화이트리스트 테이블)
  - `POST /me/student-verification/confirm` — 토큰 검증 + `edu_email_verified_at` 세팅
- [ ] 프런트:
  - `/signup` 시 user_type=student 선택하면 가입 직후 `/onboarding/student-email` 단계 추가 (이메일 인증 완료 전까지는 student 권한 보류)
  - `/me/account`에 학교 이메일 인증 상태 표시 + 재요청 버튼
- [ ] mock 호출 6곳 제거: `LoginModal.tsx`, 5개 페이지 인라인 로그인 → `/login` 리다이렉트로 통일
- [ ] `loginWithMockEmail`은 `process.env.NODE_ENV !== "production"` 가드 + 별도 dev-only 함수로 격리 (or 완전 제거 — Phase D 끝에 결정)

#### 횡단 사항
- [ ] CSRF/세션: refresh token은 현행 localStorage 유지 (별도 PDCA에서 httpOnly cookie로 마이그레이션 — out of scope)
- [ ] Rate limit: 신규 엔드포인트 모두 `rate_limit("auth_*")` 적용
- [ ] 비밀번호 정책: 최소 10자 + 영/숫/특수 중 2종 (zxcvbn 검토 후 결정)
- [ ] 비밀번호 해시: bcrypt cost 12 (admin과 동일)
- [ ] Audit log: `auth_event` 테이블 또는 기존 audit 시스템 재사용 — design 단계에서 확정

### 2.2 Out of Scope

- 추가 SNS 제공자 (Apple / GitHub / Kakao / Naver) → 별도 PDCA
- httpOnly cookie 기반 토큰 전환 → 별도 PDCA
- WebAuthn(passkey)을 일반 사용자에 확대 → 별도 PDCA
- 이메일 발송 인프라를 SES/SendGrid/Resend로 마이그레이션 → 트래픽 증가 시점에 별도 PDCA
- 2FA(TOTP)를 일반 사용자에 확대 → 별도 PDCA
- Magic link 로그인 → 향후 검토
- SAML/SSO → out of scope

---

## 3. Requirements

### 3.1 Functional Requirements

| ID | Requirement | Priority | Phase | Status |
|----|-------------|----------|-------|--------|
| FR-01 | Google ID Token으로 실제 로그인 가능 (mock 없이) | High | A | Pending |
| FR-02 | dev에서는 mock 로그인도 사용 가능 | High | A | Pending |
| FR-03 | 이메일 + 비밀번호로 회원가입 시 인증 메일이 발송된다 | High | B | Pending |
| FR-04 | 이메일 인증 미완료 계정은 로그인이 거부되고 `EMAIL_NOT_VERIFIED` 코드로 안내된다 | High | B | Pending |
| FR-05 | 이메일 인증 토큰은 1회용, 24h TTL | High | B | Pending |
| FR-06 | 이메일 + 비밀번호로 로그인 가능 (미인증 시 차단) | High | B | Pending |
| FR-07 | 비밀번호 재설정 메일 → 토큰 → 새 비밀번호 설정 흐름 동작 | High | C | Pending |
| FR-08 | 비밀번호 재설정 토큰 1회용, 1h TTL | High | C | Pending |
| FR-09 | 가입 시 user_type을 'general' 또는 'student' 중 선택 | High | D | Pending |
| FR-10 | user_type=student는 학교 이메일 인증 후에만 학생 권한(예: 학생 라벨, 미래 혜택) 부여 | High | D | Pending |
| FR-11 | 학교 이메일은 도메인 화이트리스트(예: ac.kr / edu / ac.{cc}) 또는 관리자 등록 도메인만 허용 | High | D | Pending |
| FR-12 | 모든 mock 인라인 로그인이 제거되거나 dev 가드된다 | High | D | Pending |
| FR-13 | `/auth/email/*`, `/auth/password/*`, `/me/student-verification/*` 엔드포인트가 표준 응답 envelope `{data:...}` 또는 `{error:{code,message}}` 형식 준수 | High | B–D | Pending |
| FR-14 | 비밀번호 형식 위반 시 `VALIDATION_ERROR` + 필드별 상세 반환 | Medium | B | Pending |
| FR-15 | 회원가입/로그인/재설정 모든 엔드포인트에 rate limit 적용 (signup: 5/h/IP, login: 10/min/IP, forgot: 3/h/이메일) | High | B–C | Pending |
| FR-16 | 발송 메일은 한국어 기본 + 사용자 `language` 컬럼에 따라 영어 분기 (i18n 키 기반 템플릿) | Medium | B | Pending |
| FR-17 | `/forgot-password` 응답은 항상 200 (이메일 존재 여부 누설 금지) | High | C | Pending |

### 3.2 Non-Functional Requirements

| Category | Criteria | Measurement Method |
|----------|----------|-------------------|
| Security | OWASP A01/A02/A07 준수 (broken auth, crypto fail, identification fail) | 보안 리뷰 / `bkit:security-architect` 호출 |
| Security | 비밀번호 bcrypt cost 12, 평문 저장 금지, 로그 마스킹 | 코드 리뷰 + grep 검증 |
| Security | 토큰(이메일·비번 재설정·학교)은 32 byte URL-safe random + DB에는 SHA-256 해시 저장 | unit test + 코드 리뷰 |
| Security | 열거 공격(enumeration) 방지: forgot/login 응답에서 계정 존재 여부 누설 금지 | 응답 비교 테스트 |
| Performance | 로그인 응답 < 500ms (bcrypt 포함) | `bkit:qa-monitor` 로그 분석 |
| Reliability | 이메일 발송 실패가 사용자 흐름을 차단하지 않음 (큐잉 또는 best-effort + 재시도) | 통합 테스트 |
| UX | 인증 실패 메시지가 "계정 존재 여부"를 누설하지 않으면서 사용자에게 충분히 친절 | UX 리뷰 |
| Compliance | GDPR — 가입 시 약관/개인정보 동의 체크박스 + `gdpr_consent_at`, `privacy_policy_version`, `terms_version` 기록 | 코드 리뷰 |
| Observability | 모든 인증 이벤트(success/fail/rate-limit-hit)에 구조화 로그 (Zero Script QA 호환) | docker logs 검증 |

---

## 4. Success Criteria

### 4.1 Definition of Done

- [ ] Phase A: 실제 Google 계정으로 로그인 → `/users/me` 호출 성공 (browser E2E)
- [ ] Phase B: 신규 계정 가입 → 인증 메일 수신 → 링크 클릭 → 로그인 성공 (browser E2E)
- [ ] Phase B: 미인증 계정 로그인 시도 → 401 + `EMAIL_NOT_VERIFIED` (curl + UI 메시지 확인)
- [ ] Phase C: forgot → 메일 수신 → reset 링크 → 새 비밀번호 → 새 비밀번호로 로그인 성공
- [ ] Phase D: user_type=student 가입 → 학교 이메일 인증 전엔 student 표식 없음 → 인증 후 표식 노출
- [ ] Phase D: prod 빌드에서 mock 함수 호출 시 빌드 실패 또는 런타임 401
- [ ] 백엔드 변경마다 alembic 마이그레이션 + downgrade 동작 확인
- [ ] 프런트 lint/typecheck/build 통과
- [ ] 백엔드 ruff/mypy/pytest 통과
- [ ] OpenAPI 문서 자동 갱신 + `v1/docs/02-design/design.md`의 §3 인증 섹션 갱신

### 4.2 Quality Criteria

- [ ] 신규 엔드포인트 통합 테스트 커버리지 ≥ 80%
- [ ] Zero Script QA: 로그인/가입/재설정 시나리오 도커 로그로 검증 완료
- [ ] gap-detector Match Rate ≥ 90% (Phase D 종료 시점)
- [ ] `bkit:security-architect` 검토 0 critical / 0 high

---

## 5. Risks and Mitigation

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Gmail Workspace SMTP App Password 발송 한도 (~2000/일) 도달 | 고 (가입 차단) | 중 | 큐잉 + 일일 카운터 모니터링; 한도 임박 시 Resend로 즉시 전환 가능하도록 인터페이스 추상화 |
| Google Workspace SMTP가 마케팅성/대량 발송으로 차단 판단 → 발송 정지 | 고 | 중 | 처음부터 Resend/SES와 같은 transactional 전용 인프라로 옮기는 것을 Phase B에서 선택지로 유지. 도메인 DKIM/SPF는 Workspace 콘솔에서 Resend로도 동시 위임 가능 |
| `password_hash` 컬럼이 admin 전용 주석으로 사용되던 것을 일반 사용자에 확대 → 기존 admin 로직과 충돌 | 고 | 낮 | role별 분기 명확화; admin은 여전히 TOTP 강제, 일반 user는 password 단독 허용. 코드 리뷰 + `bkit:security-architect` 검토 |
| 학교 이메일 도메인 검증 누락 → 가짜 학생 가입 | 중 | 중 | 화이트리스트 + 관리자 등록 도메인 + 의심 도메인 수동 승인 큐 |
| 토큰 평문 DB 저장 시 DB 유출 영향 | 고 | 낮 | 토큰은 SHA-256 해시 저장, raw token은 URL/메일에만 노출 |
| Mock 제거 시 기존 dev 환경 깨짐 | 중 | 고 | NODE_ENV 가드 + 별도 dev-only 함수로 격리. CI에서는 mock 사용 가능 유지 |
| 회원가입 race condition (동일 이메일 동시 요청) | 중 | 낮 | DB unique constraint + 트랜잭션 격리 |
| Rate limit 우회 (IP 회전) | 중 | 중 | IP + 이메일 dual-key rate limit, 의심 패턴 감지 시 로깅 |
| GDPR 동의 누락 | 고 | 낮 | 가입 폼 필수 체크박스 + 백엔드에서 동의 버전 누락 시 400 |
| Mailbox provider별 deliverability 차이 (특히 Naver/Daum) | 중 | 고 | DKIM/SPF/DMARC 설정. Workspace SMTP는 기본 SPF만 통과; DMARC 추가 검토 |

---

## 6. Architecture Considerations

### 6.1 Project Level Selection

| Level | Characteristics | Recommended For | Selected |
|-------|-----------------|-----------------|:--------:|
| Starter | Simple structure | 정적 사이트 | ☐ |
| **Dynamic** | Feature-based modules, custom backend | Web apps with backend | **☑** |
| Enterprise | DI, microservices | High-traffic systems | ☐ |

기존 v1 backend가 FastAPI + alembic + custom 구성이므로 Dynamic 레벨 유지.

### 6.2 Key Architectural Decisions

| Decision | Options | Selected | Rationale |
|----------|---------|----------|-----------|
| Frontend OAuth lib | `@react-oauth/google` / GSI script 직접 | `@react-oauth/google` | 유지보수 활발, GSI를 hook으로 래핑 |
| Email sender | Gmail SMTP (App Password) / Workspace SMTP Relay / Resend / SES | **Gmail SMTP (App Password)** for MVP, abstraction으로 Resend 즉시 전환 가능 | 추가 비용 0, 도메인 DNS 변경 불필요. 한도 도달 시 Resend로 마이그레이션 (DKIM 추가만) |
| Password hashing | bcrypt / argon2 | **bcrypt cost 12** | admin과 일관성, passlib 이미 사용 중 |
| Token store (refresh) | localStorage / httpOnly cookie | localStorage 유지 | cookie 전환은 별도 PDCA. CSRF 위험과 트레이드오프 명시 |
| Verification token format | JWT / opaque random | **opaque 32-byte URL-safe random + SHA-256 in DB** | revocable, 길이 짧음, 유출 시 영향 최소 |
| user_type 모델링 | role 확장 / 별도 컬럼 / artist_application 재사용 | **별도 컬럼 (`user_type`)** | role은 권한, user_type은 속성. 의미 분리 |

### 6.3 Folder Structure Preview

```
v1/backend/app/
├── api/
│   ├── auth.py                  (기존 — Google + me + logout)
│   ├── auth_email.py            (신규 — signup/login/verify/resend)
│   ├── auth_password.py         (신규 — forgot/reset)
│   └── student_verification.py  (신규 — Phase D)
├── services/
│   ├── email_sender/
│   │   ├── base.py              (EmailSender interface)
│   │   ├── smtp_gmail.py        (Phase B 구현)
│   │   ├── console.py           (dev fallback)
│   │   └── factory.py
│   ├── auth_email_service.py    (가입/인증/로그인 비즈니스 로직)
│   └── password_reset_service.py
├── models/
│   ├── auth_token.py            (기존)
│   ├── email_verification.py    (신규)
│   ├── password_reset.py        (신규)
│   └── student_verification.py  (신규 또는 user.py 컬럼)
└── schemas/
    └── auth_email.py            (신규)

v1/frontend/src/
├── app/
│   ├── login/page.tsx           (신규)
│   ├── signup/page.tsx          (신규)
│   ├── verify-email/[token]/page.tsx
│   ├── forgot-password/page.tsx
│   └── reset-password/[token]/page.tsx
├── components/
│   ├── LoginModal.tsx           (수정 — Google 버튼 + /login 링크)
│   └── auth/
│       ├── GoogleSignInButton.tsx (신규)
│       ├── EmailLoginForm.tsx
│       └── EmailSignupForm.tsx
└── lib/
    ├── api.ts                   (수정 — 신규 함수 추가)
    └── auth/
        └── google-client.ts     (신규 — @react-oauth/google 래퍼)
```

---

## 7. Convention Prerequisites

### 7.1 Existing Project Conventions

- [x] CLAUDE.md 존재 (한국어 우선 명시)
- [x] alembic 마이그레이션 사용
- [x] FastAPI router 패턴 — `app/api/{domain}.py`에 `router = APIRouter(prefix=...)`
- [x] 응답 envelope: `return {"data": ...}` (auth.py 참조)
- [x] 에러: `raise ApiError("CODE", "message", http_status=...)`
- [x] Frontend: Next.js App Router, Tailwind, TypeScript
- [x] Frontend i18n: `useI18n()` + 한/영 키 분리

### 7.2 Conventions to Define/Verify

| Category | Current State | To Define | Priority |
|----------|---------------|-----------|:--------:|
| **에러 코드 네이밍** | `INVALID_REQUEST`, `UNAUTHORIZED` 등 사용 중 | `EMAIL_NOT_VERIFIED`, `INVALID_CREDENTIALS`, `EMAIL_ALREADY_REGISTERED`, `TOKEN_EXPIRED`, `TOKEN_USED`, `WEAK_PASSWORD`, `EDU_DOMAIN_NOT_ALLOWED` 추가 | High |
| **이메일 템플릿 위치** | 미존재 | `v1/backend/app/services/email_sender/templates/{lang}/{template}.html` | Medium |
| **신규 페이지 라우팅** | App Router 사용 | `app/login`, `app/signup`, `app/verify-email/[token]`, `app/forgot-password`, `app/reset-password/[token]` | High |
| **폼 검증** | 미통일 | react-hook-form + zod 도입 검토 (현재 pure React) | Medium |

### 7.3 Environment Variables Needed

| Variable | Purpose | Scope | New |
|----------|---------|-------|:---:|
| `NEXT_PUBLIC_GOOGLE_CLIENT_ID` | Frontend Google OAuth | Client | ☑ |
| `GOOGLE_CLIENT_ID` | Backend Google ID token verify | Server | (이미 정의됨) |
| `SMTP_HOST` | smtp.gmail.com | Server | ☑ |
| `SMTP_PORT` | 587 | Server | ☑ |
| `SMTP_USER` | noreply@tuzigroup.com | Server | ☑ |
| `SMTP_PASSWORD` | Workspace App Password (16자) | Server | ☑ |
| `EMAIL_FROM` | "Domo <noreply@tuzigroup.com>" | Server | ☑ |
| `EMAIL_VERIFICATION_TTL_HOURS` | 24 | Server | ☑ |
| `PASSWORD_RESET_TTL_HOURS` | 1 | Server | ☑ |
| `PUBLIC_WEB_URL` | https://domo.example.com (메일 링크 베이스) | Server | ☑ |
| `EDU_DOMAIN_WHITELIST` | "ac.kr,edu,ac.uk,..." | Server | ☑ |

### 7.4 이메일 인프라 결정 — Google Workspace `@tuzigroup.com` 활용 방안

| 옵션 | 설정 난이도 | 한도 | 권장 시점 |
|---|---|---|---|
| **Gmail SMTP + App Password** (`smtp.gmail.com:587`) | ⭐ 매우 쉬움 | ~2000/일/계정 | **Phase B MVP 채택** |
| Google Workspace SMTP Relay (`smtp-relay.gmail.com`) | ⭐⭐⭐ IP auth 또는 SMTP-AUTH 설정 필요 | 10000/일/사용자 | 추후 한도 부족 시 |
| Resend / SendGrid (도메인 DKIM 위임) | ⭐⭐ DNS TXT 추가 | Resend 3000/월 free | **트래픽 증가 시 마이그레이션** |
| AWS SES | ⭐⭐⭐⭐ sandbox 해제 + DNS | 가장 저렴 | 대규모 운영 시 |

**채택 근거**:
- App Password는 Workspace 관리 콘솔 → 보안 → 2단계 인증 활성화 후 1분 내 발급. 추가 비용/DNS 변경 없음.
- `EmailSender` 추상화로 향후 Resend 전환 시 1파일 추가 + env 교체로 완료 가능.
- 발송량 임계치 (1500/일 등)에서 Slack 알림 → 마이그레이션 트리거.

### 7.5 Pipeline Integration

| Phase | Status | Document Location | Command |
|-------|:------:|-------------------|---------|
| Phase 1 (Schema) | 부분 | `v1/docs/02-design/design.md` | 신규 테이블 3개 추가 |
| Phase 2 (Convention) | 기존 유지 | — | 신규 에러 코드만 추가 |

---

## 8. Phased Delivery Plan

### Phase A — Real Google OAuth (frontend)
- 예상 기간: 0.5–1일
- 산출물: 실제 Google 계정으로 로그인 가능, mock은 dev에서 유지
- PR 단위: 1개

### Phase B — Email/Password Auth + Verification
- 예상 기간: 3–5일
- 산출물: signup/login/verify/resend 4개 엔드포인트 + 3개 프런트 페이지 + Gmail SMTP 발송
- PR 단위: 백엔드 / 프런트 분리 (2개)

### Phase C — Password Reset
- 예상 기간: 1–2일
- 산출물: forgot/reset 2개 엔드포인트 + 2개 프런트 페이지
- PR 단위: 1개 (백엔드+프런트 묶음, 작은 변경)

### Phase D — Mock Removal + Student Email Verification
- 예상 기간: 2–3일
- 산출물: user_type 컬럼, edu_email 처리, mock 제거, /signup의 student 분기, /onboarding/student-email
- PR 단위: 백엔드 / 프런트 분리

각 Phase 완료 시:
1. `bkit:qa-monitor`로 Zero Script QA 실시
2. `/pdca analyze real-auth`로 gap-detector 실행
3. Match Rate < 90%이면 `/pdca iterate`
4. 모든 Phase 완료 후 `/pdca report real-auth`

---

## 9. Next Steps

1. [ ] 이 plan에 대한 사용자 승인
2. [ ] `/pdca design real-auth` — 상세 설계 문서 작성
3. [ ] Google Workspace 측 작업: `noreply@tuzigroup.com` 메일박스 생성 + 2FA 활성화 + App Password 발급 (사용자 작업 필요)
4. [ ] Google Cloud Console: OAuth 2.0 Client ID 발급 (Web application, redirect URI 등록)
5. [ ] `.env.example` 업데이트
6. [ ] Phase A 구현 시작

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 0.1 | 2026-04-26 | Initial draft (4 phases, Gmail SMTP MVP, student email verification) | itpe-ince / Claude Opus 4.7 |
