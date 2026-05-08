# Domo 관리자 시스템 운영 가이드 v2

> 운영자를 위한 Domo Admin 콘솔 사용 가이드 — 소스 검증 기반 재작성  
> 대상: admin 계정 보유 운영자  
> 검증 기준: alembic HEAD 0083, 소스 검증일 2026-05-08

---

## 목차

1. [관리자 시스템 개요 — 실제 RBAC](#1-관리자-시스템-개요--실제-rbac)
2. [관리자 인증 — 2FA · WebAuthn (Passkey)](#2-관리자-인증--2fa--webauthn-passkey)
3. [사용자 관리](#3-사용자-관리)
4. [작가 심사 (Applications)](#4-작가-심사-applications)
5. [학교 관리 (Schools)](#5-학교-관리-schools)
6. [콘텐츠 관리 및 모더레이션](#6-콘텐츠-관리-및-모더레이션)
7. [거래 관리 (Auctions · Orders)](#7-거래-관리-auctions--orders)
8. [Featured Artist 큐레이션](#8-featured-artist-큐레이션)
9. [AI 컬렉션 검수 (K-7)](#9-ai-컬렉션-검수-k-7)
10. [ML A/B 테스트 운영 (K-8)](#10-ml-ab-테스트-운영-k-8)
11. [Diversity Reranking 튜닝 (K-2)](#11-diversity-reranking-튜닝-k-2)
12. [분석 대시보드 · 코호트 알림](#12-분석-대시보드--코호트-알림)
13. [뉴스레터 운영](#13-뉴스레터-운영)
14. [쿠폰 관리](#14-쿠폰-관리)
15. [인터뷰 · Press Kit · Media Coverage](#15-인터뷰--press-kit--media-coverage)
16. [외부 통합 — RSS · OG Auto-Thumbnail](#16-외부-통합--rss--og-auto-thumbnail)
17. [데이터 보존 · GDPR · 운영 정책](#17-데이터-보존--gdpr--운영-정책)
18. [cron worker 매트릭스 (23개)](#18-cron-worker-매트릭스-23개)
19. [env 변수 카탈로그 (config.py 기반)](#19-env-변수-카탈로그-configpy-기반)
20. [트러블슈팅](#20-트러블슈팅)
21. [가이드 검증 메타](#21-가이드-검증-메타)

---

## 1. 관리자 시스템 개요 — 실제 RBAC

### 1.1 역할 정의

Domo의 사용자 역할은 `user.role` 컬럼에 String(20) 값으로 저장된다.

| 역할 | 권한 범위 | 비고 |
|------|----------|------|
| **admin** | Admin 콘솔 전체 + 모든 admin 엔드포인트 | 2FA 또는 Passkey 등록 필수 |
| **artist** | 작가 전용 기능 (후원 수취, 경매 등록) | 작가 심사 승인 후 부여 |
| **user** | 일반 사용자 기능 | 가입 시 기본값 |

> 소스: `app/core/admin_deps.py`, `app/models/user.py`, `app/api/admin/users.py:37`

`curator`, `moderator` 역할은 현재 소스에 정의되지 않는다. Admin 계정이 모든 운영 업무를 담당한다.

### 1.2 관리자 의존성 함수

`app/core/admin_deps.py`에 두 가지 의존성이 정의되어 있다.

| 함수 | 조건 | 사용 상황 |
|------|------|----------|
| `require_admin` | `user.role == "admin"` 확인만 | TOTP 등록 전 허용 필요한 엔드포인트 (설정 화면 등) |
| `require_admin_with_2fa` | role 확인 + TOTP 또는 Passkey 중 하나 이상 등록 | **모든 비즈니스 엔드포인트** |

미등록 admin이 `require_admin_with_2fa` 엔드포인트를 호출하면 HTTP 403 `SECOND_FACTOR_REQUIRED` 에러를 반환하며 `{"setup_url": "/settings/totp-setup"}`를 detail에 포함한다.

### 1.3 admin 콘솔 메뉴 구성 (port 3800)

```
/login                        # 이메일 + 비밀번호 + TOTP 인증
/dashboard                    # 핵심 KPI 대시보드
/users                        # 사용자 관리
/applications                 # 작가 심사
/schools                      # 학교 관리
/posts                        # 콘텐츠 관리 (디지털 아트 검수 포함)
/transactions                 # 거래 관리 (경매 · 주문)
/moderation                   # 신고 처리 · 경고 · 항소
/settings                     # 시스템 설정 키-값
/settings/totp-setup          # TOTP 초기 설정 (2FA 미등록 시 강제 리다이렉트)
/settings/passkeys            # WebAuthn Passkey 관리
/settings/recovery-codes      # 복구 코드 관리
```

> 소스: `app/admin/src/components/AdminShell.tsx`, `app/admin/src/app/*/page.tsx`

---

## 2. 관리자 인증 — 2FA · WebAuthn (Passkey)

### 2.1 인증 흐름

```
1. POST /v1/auth/admin/login  { email, password }
   → TOTP 등록된 경우: { totp_required: true, challenge_token: "..." }
   → TOTP 미등록 (최초 로그인): { totp_required: false, totp_setup_required: true, tokens: {...} }

2. POST /v1/auth/admin/login/verify  { challenge_token, totp_code }
   또는                               { challenge_token, recovery_code }
   → { tokens: { access_token, refresh_token }, user: {...} }
```

- 5회 연속 실패 시 15분 잠금 (HTTP 423 `ADMIN_LOCKED`)
- SNS 로그인(Google 등)은 admin 역할에 차단됨 (`app/api/auth.py:69`)

> 소스: `app/api/admin_auth.py:127, 189`

### 2.2 TOTP 설정

```
GET  /v1/auth/admin/totp/setup      # QR 코드 + secret 발급
POST /v1/auth/admin/totp/enable     { totp_code }
POST /v1/auth/admin/totp/disable    { password }   # 비밀번호 재확인 후 비활성화
```

- Google Authenticator / Authy / 1Password 호환
- 복구 코드 8개 일괄 발급 (1회용)
- TOTP secret은 Fernet 대칭 암호화로 DB 저장 (`TOTP_ENCRYPTION_KEY` env)

> 소스: `app/api/admin_auth.py:356, 389, 426`

### 2.3 복구 코드

```
GET  /v1/auth/admin/recovery-codes/status        # 잔여 코드 수 확인
POST /v1/auth/admin/recovery-codes/regenerate   { password }  # 전체 재발급
```

> 소스: `app/api/admin_auth.py:450, 479`

### 2.4 WebAuthn Passkey

- USB 보안 키(YubiKey 등) 또는 플랫폼 인증(Touch ID, Windows Hello) 지원
- webauthn 라이브러리 미설치 시 graceful skip — 엔드포인트 비활성화, 서버 부팅 경고만 출력

```
POST /v1/auth/admin/webauthn/register/begin
POST /v1/auth/admin/webauthn/register/finish
POST /v1/auth/admin/webauthn/authenticate/begin
POST /v1/auth/admin/webauthn/authenticate/finish
GET  /v1/auth/admin/webauthn/credentials
DELETE /v1/auth/admin/webauthn/credentials/{credential_id}
```

> 소스: `app/api/admin_webauthn.py:174, 223, 283, 336, 418, 447`  
> 환경설정: `WEBAUTHN_RP_ID`, `WEBAUTHN_RP_NAME`, `WEBAUTHN_RP_ORIGIN`

### 2.5 2FA 없이 접근 가능한 경로

프론트엔드(`AdminShell.tsx`)에서 2FA 미등록 admin도 접근 가능한 경로:

```
/login
/settings/totp-setup
/settings/passkeys
/settings/recovery-codes
```

나머지 모든 경로는 `require_admin_with_2fa` 백엔드 API가 최종 차단한다.

### 2.6 Access Token 만료

- access_token: **60분** (`config.py: access_token_expire_minutes=60`)
- refresh_token: 30일 (`refresh_token_expire_days=30`)
- 세션 타임아웃(비활성 30분 자동 만료) 기능은 구현되지 않음

---

## 3. 사용자 관리

### 3.1 사용자 목록 조회

```
GET /v1/admin/users
  ?q=<이름 또는 이메일 부분검색>
  &role=user|artist|admin
  &status=active|suspended
  &country=KR
  &limit=20&offset=0
```

응답 필드: `id, email, display_name, avatar_url, role, status, country_code, warning_count, created_at`

> 소스: `app/api/admin/users.py:188`

### 3.2 사용자 상태 및 역할 변경

```
PATCH /v1/admin/users/{user_id}
Body: { status?: "active"|"suspended", role?: "user"|"artist"|"admin", badge_level?: string }
```

| 상태 | 의미 |
|------|------|
| `active` | 정상 |
| `suspended` | 일시 정지 |

> `banned`, `deleted` 상태는 현재 PATCH API에서 지원하지 않는다.

**Self-modify 차단 (자가 수정 방지)**:
- admin이 본인 `role` 변경 시 → `400 SELF_MODIFY_FORBIDDEN`
- admin이 본인 `status=suspended` 변경 시 → `400 SELF_MODIFY_FORBIDDEN`

상태 변경 시 해당 사용자에게 인앱 `Notification` 생성됨. 이메일 알림은 별도 구현 필요.

역할 변경 시 해당 사용자의 모든 기존 토큰이 자동 폐기된다(`revoke_user_tokens`).

> 소스: `app/api/admin/users.py:309`

### 3.3 admin이 직접 사용자 생성

```
POST /v1/admin/users
Body: {
  email: string,          # 이메일 (중복 불가)
  display_name: string,   # 3~50자
  role: "user"|"artist"|"admin",  # 기본값 "user"
  send_magic_link: boolean,       # 기본값 true
  country_code?: string   # ISO 2자리 국가 코드
}
```

- `send_magic_link=true` (기본): 24시간 유효한 초대 링크 이메일 자동 발송
- 임시 비밀번호는 bcrypt hash만 저장, 평문 즉시 폐기 — admin이 볼 수 없음
- 이메일 설정 미완료 시 graceful (로그만, `sent: false` 응답)
- 감사 로그: Python 구조화 로그 `AUDIT action=admin_create_user`

> 소스: `app/api/admin/users.py:229`, `app/services/magic_link.py`

---

## 4. 작가 심사 (Applications)

`/applications` 페이지

### 4.1 심사 대기 목록

```
GET /v1/admin/artists/applications?status=pending|approved|rejected
```

### 4.2 심사 액션

```
POST /v1/admin/artists/applications/{application_id}/approve
Body: { note?: string }
```
- 신청자의 `role`을 `"artist"`로 변경
- `ArtistProfile` 자동 생성 (badge_level: 재학 중 → `student`, 졸업 → `emerging`)
- 기존 토큰 자동 폐기
- 인앱 알림 발송

```
POST /v1/admin/artists/applications/{application_id}/reject
Body: { note?: string }
```
- 인앱 알림 발송 (재신청 안내)

> 소스: `app/api/admin/users.py:64, 83, 148`

---

## 5. 학교 관리 (Schools)

```
GET    /v1/admin/schools          # 목록 조회
POST   /v1/admin/schools          # 학교 추가
PATCH  /v1/admin/schools/{id}     # 학교 정보 수정
```

> 소스: `app/api/admin/schools.py:34, 71, 87`

---

## 6. 콘텐츠 관리 및 모더레이션

### 6.1 디지털 아트 검수 큐

```
GET  /v1/admin/posts/digital-art-queue?limit=50    # status=pending_review, check=pending
POST /v1/admin/posts/{post_id}/digital-art-verdict
Body: { verdict: "approved"|"rejected", note?: string }
```

### 6.2 전체 게시물 관리

```
GET   /v1/admin/posts/list         # 전체 게시물 목록
PATCH /v1/admin/posts/{post_id}/status
Body: { status: string, reason?: string }
```

### 6.3 신고 처리

```
GET  /v1/admin/reports             # 신고 목록
POST /v1/admin/reports/{report_id}/resolve
Body: ReportResolveRequest
```

### 6.4 경고 및 항소

```
GET  /v1/admin/appeals                              # 항소 목록
POST /v1/admin/warnings/{warning_id}/cancel         # 경고 취소
POST /v1/admin/warnings/{warning_id}/reject-appeal  # 항소 거절
```

> 소스: `app/api/admin/content.py:71, 92, 147, 196, 217, 236, 285, 304, 323`

---

## 7. 거래 관리 (Auctions · Orders)

`/transactions` 페이지

### 7.1 경매 관리

```
POST /v1/admin/auctions/process-expired   # 만료 경매 수동 처리 트리거
GET  /v1/admin/auctions/list              # 경매 목록
```

### 7.2 주문 및 환불

```
GET  /v1/admin/orders/list                # 주문 목록
POST /v1/admin/orders/{order_id}/refund   # 환불 처리
```

> 소스: `app/api/admin/transactions.py:45, 55, 93, 136`

---

## 8. Featured Artist 큐레이션

### 8.1 수동 Featured 관리

```
POST   /v1/admin/featured    Body: { artist_id, ... }
GET    /v1/admin/featured
DELETE /v1/admin/featured/{entry_id}
```

> 소스: `app/api/admin_featured.py:41, 103, 133`

### 8.2 AI 자동 후보 검수 큐 (K-4)

매주 **월요일 09:00 UTC** 자동 생성된 후보 목록을 admin이 검수한다.

```
GET  /v1/admin/featured-artist/candidates
     ?week_start=YYYY-MM-DD     # 기본: 이번 주 월요일
     &status=pending|approved|rejected|published

POST /v1/admin/featured-artist/candidates/{id}/approve
POST /v1/admin/featured-artist/candidates/{id}/publish   Body: { notes?: string }
POST /v1/admin/featured-artist/candidates/{id}/reject    Body: { reason: string }
```

**워크플로우**:
1. `GET /candidates` — pending 후보 확인 (composite_score + reasoning JSONB 포함)
2. 검토 후 `approve` → 별도로 `publish` (자동 발행 OFF 정책)
3. 부적합 시 `reject` (사유 입력 필수)

**후보 미달 알림**: 후보 3명 미만 시 `SLACK_WEBHOOK_URL` 설정된 경우 Slack 알림 발송

> 소스: `app/api/admin_featured_artist.py:87, 163, 224, 310`  
> Worker: `app/services/featured_artist_jobs.py` (22번 cron)

---

## 9. AI 컬렉션 검수 (K-7)

매주 **월요일 09:00 UTC** LLM이 자동 생성한 Editor's Pick 컬렉션 5개를 검수한다.

```
GET  /v1/admin/ai-collections/queue       # generating 상태 컬렉션 목록
POST /v1/admin/ai-collections/{id}/publish   Body: { admin_note?: string }
POST /v1/admin/ai-collections/{id}/archive   Body: { admin_note?: string }
```

**컬렉션 생성 파이프라인**:
1. post_embeddings 클러스터링 (KMeans 또는 metadata grouping fallback)
2. LLM 호출로 제목/설명 생성 (한국어 기준, `LLM_MODEL_NAME` env)
3. translation_cache 활용 → 다국어 번역
4. `status='generating'` 상태로 저장 → admin 검수 대기

**LLM 비용 한도**: `AI_CURATION_DAILY_BUDGET_USD` env (기본 `5.0` USD)  
한도 초과 시 해당 주 skip + 로그 기록

> 소스: `app/api/admin_ai_collections.py:36, 85, 136`  
> Worker: `app/services/ai_curation_jobs.py` (23번 cron)

---

## 10. ML A/B 테스트 운영 (K-8)

```
GET  /v1/admin/experiments               # 실험 목록
POST /v1/admin/experiments               # 새 실험 생성
GET  /v1/admin/experiments/{name}/results  # 실험 결과 (PostHog 연동)
```

**실험 생성 body**:
```json
{
  "name": "feed_v2_rollout",
  "allocation": {"v1": 0.5, "v2": 0.5},
  "hypothesis": "자유 텍스트",
  "target_metric": "sponsorship_conversion",
  "start_at": "2026-05-10T00:00:00Z",
  "end_at": "2026-05-24T00:00:00Z"
}
```

**권한**: `require_admin` (2FA 체크 없음 — 실험 관리는 상대적으로 저위험)

> 소스: `app/api/admin_experiments.py:74, 111, 174`

---

## 11. Diversity Reranking 튜닝 (K-2)

```
GET   /v1/admin/diversity-config              # 모든 설정 목록
PATCH /v1/admin/diversity-config/{name}       # 특정 설정 수정
```

**PATCH body (모두 선택적)**:
```json
{
  "emerging_artist_boost": 1.20,   // 1.0 ~ 2.0
  "genre_min_diversity": 3,        // 1 ~ 10
  "region_min_diversity": 2,       // 1 ~ 10
  "top_k_window": 20               // 10 ~ 50
}
```

기본 설정명: `feed_default`

> 소스: `app/api/admin_diversity.py:103, 127`

---

## 12. 분석 대시보드 · 코호트 알림

### 12.1 대시보드 KPI

```
GET /v1/admin/dashboard/stats?days=7|30|90   # 핵심 KPI (사용자, 후원, 경매, 모더레이션)
GET /v1/admin/dashboard/revenue?days=7|30|90 # 매출 분석
```

> 소스: `app/api/admin_dashboard.py:32, 121`

### 12.2 코호트 자동 알림 (L-F)

매일 자동 측정 (24h cron):
- D7 retention < `COHORT_ALERT_7D_THRESHOLD` (기본 0.30) → Slack 알림
- D30 retention < `COHORT_ALERT_30D_THRESHOLD` (기본 0.15) → Slack 알림
- `cohort_alert_min_cohort_size` 미만 코호트는 측정 skip (기본 10명)
- `SLACK_WEBHOOK_URL` 미설정 시 로그 출력만 (Mock 모드)

> 소스: `app/services/cohort_alert_jobs.py`, `app/core/config.py:171~178`

---

## 13. 뉴스레터 운영

```
POST  /v1/admin/newsletter/issues/compose       # 이슈 초안 작성
GET   /v1/admin/newsletter/issues               # 이슈 목록
PATCH /v1/admin/newsletter/issues/{issue_id}    # 이슈 수정
POST  /v1/admin/newsletter/issues/{issue_id}/send  # 발송
```

- 이메일 발송: `EMAIL_PROVIDER` 설정에 따라 Resend / SMTP / Mock 모드
- AWS SES 사용 시: `AWS_SES_ACCESS_KEY_ID`, `AWS_SES_SECRET_ACCESS_KEY`, `AWS_SES_REGION` 설정 필요
- SES bounce/complaint: SNS → `POST /v1/webhooks/ses-bounce` 처리 (`AWS_SNS_TOPIC_ARN` env)

> 소스: `app/api/admin_newsletter.py:60, 94, 120, 175`

---

## 14. 쿠폰 관리

```
POST   /v1/admin/coupons              # 쿠폰 생성
GET    /v1/admin/coupons              # 쿠폰 목록
DELETE /v1/admin/coupons/{coupon_id}  # 쿠폰 삭제
```

> 소스: `app/api/admin_coupons.py:43, 82, 107`

---

## 15. 인터뷰 · Press Kit · Media Coverage

### 15.1 AI 인터뷰 (C-1)

```
POST /v1/admin/interviews/generate         { user_id }  # LLM으로 인터뷰 초안 생성
GET  /v1/admin/interviews                  # 목록
PATCH /v1/admin/interviews/{id}            # 수동 수정
POST /v1/admin/interviews/{id}/publish     # 공개
POST /v1/admin/interviews/{id}/translate   # 다국어 번역 트리거
```

> 소스: `app/api/admin_interviews.py:59, 84, 122, 191, 261`

### 15.2 Press Kit

```
POST /v1/admin/users/{user_id}/press-kit/generate   # 보도자료 자동 생성
GET  /v1/admin/users/{user_id}/press-kit/history    # 생성 이력
```

> 소스: `app/api/admin_press_kits.py:34, 74`

### 15.3 Media Coverage

```
POST   /v1/admin/media-coverage/{user_id}           # 수동 등록
GET    /v1/admin/media-coverage/{user_id}           # 목록
PATCH  /v1/admin/media-coverage/{user_id}/{entry_id}  # 수정
DELETE /v1/admin/media-coverage/{user_id}/{entry_id}  # 삭제
```

> 소스: `app/api/admin_media_coverage.py:38, 77, 123, 161`

---

## 16. 외부 통합 — RSS · OG Auto-Thumbnail

### 16.1 RSS Auto-Fetch (L-B)

- 1시간 주기 자동 수집 (`rss_fetch_cron_loop`, main.py line 154)
- env: `RSS_FETCH_WORKER_ENABLED` (기본 `true`)
- 미설정 시 자동 수집 비활성화

### 16.2 OG Auto-Thumbnail (L-B)

외부 링크 OG 메타 자동 추출 — httpx + beautifulsoup4 (미설치 시 graceful)

> env: Redis 설정 시 24h 캐시 활성화

---

## 17. 데이터 보존 · GDPR · 운영 정책

### 17.1 데이터 보존 정책

| 데이터 | 보존 기간 | cron 처리 |
|--------|----------|----------|
| newsletter_events | 90일 | `gdpr_cron_loop` |
| ml_experiments | 90일 | cleanup 쿼리 |
| translation_cache | 90일 미사용 시 | cleanup |
| dm_messages | 사용자 삭제 시 soft delete | - |
| posts | 사용자 삭제 시 | soft delete + 30일 grace |
| user accounts | GDPR 삭제 요청 시 | gdpr_cron_loop |

### 17.2 감사 로그

별도 `audit_logs` DB 테이블은 없다. 모든 admin 액션은 Python 구조화 로그(`log.info("AUDIT action=...")`)로 기록된다. 로그 집계는 운영 환경의 로그 수집 인프라에 위임한다.

```bash
# 사용자 생성 로그 조회 예시
grep "AUDIT action=admin_create_user" /app/logs/backend.log

# 역할 변경 감사
grep "AUDIT action=admin_role_change" /app/logs/backend.log
```

### 17.3 시스템 설정

```
GET   /v1/admin/settings         # 설정 목록
PATCH /v1/admin/settings/{key}   # 키-값 업데이트
```

> 소스: `app/api/admin_dashboard.py:227, 246`

---

## 18. cron worker 매트릭스 (23개)

`main.py` `asyncio.create_task` 기준 전체 목록. 모든 worker는 R-5 isolation 패턴 (독립 `AsyncSessionLocal`) 적용.

| # | Worker | 주기 | env guard | 설명 |
|:-:|--------|------|-----------|------|
| 1 | `auction_cron_loop` | 5분 | - | 경매 만료/낙찰 처리 |
| 2 | `gdpr_cron_loop` | 1시간 | - | GDPR 삭제, 만료 데이터 정리 |
| 3 | `schedule_cron_loop` | 1분 | - | 예약 발행 처리 |
| 4 | `badge_cron_loop` | 24시간 | - | 배지 갱신 |
| 5 | `settlement_cron_loop` | 24시간 | - | 정산 처리 |
| 6 | `webhook_cleanup_cron_loop` | 24시간 | - | webhook 로그 정리 |
| 7 | `draft_cleanup_cron_loop` | 24시간 | - | 임시저장 정리 |
| 8 | `tier_release_cron_loop` | 1분 | - | 티어 공개 처리 |
| 9 | `auction_promotion_cron_loop` | 1분 | - | 경매 프로모션 처리 |
| 10 | `artist_index_cron_loop` | 1시간 | - | 작가 인덱스 갱신 |
| 11 | `post_engagement_cron_loop` | 1시간 | - | post_engagement_cache 갱신 |
| 12 | `subscription_expiry_cron_loop` | 1시간 | - | 구독 만료 처리 |
| 13 | `newsletter_cron_loop` | 1시간 | - | 뉴스레터 예약 발송 |
| 14 | `exchange_rate_cron_loop` | 1시간 | - | 환율 캐시 갱신 |
| 15 | `email_digest_cron_loop` | 1시간 | - | 이메일 다이제스트 (B'-3) |
| 16 | `auto_renewal_cron_loop` | 1시간 | - | 구독 자동 갱신 (B'-4) |
| 17 | `embedding_cron_loop` | 60초 quick + 24h batch | `EMBEDDING_WORKER_ENABLED` | 게시물 임베딩 생성 (L-A) |
| 18 | `rss_fetch_cron_loop` | 1시간 | `RSS_FETCH_WORKER_ENABLED` | 외부 RSS 수집 (L-B) |
| 19 | `cohort_alert_cron_loop` | 24시간 | `COHORT_ALERT_WORKER_ENABLED` | 코호트 retention 알림 (L-F) |
| 20 | `ml_training_cron_loop` | 24시간 (내부 스케줄링) | `ML_TRAINING_WORKER_ENABLED` | ML 피드 모델 학습 (K-1) |
| 21 | `artwork_caption_cron_loop` | 60초 quick + 24h batch | `ARTWORK_CAPTION_WORKER_ENABLED` (settings) | AI 작품 캡션 생성 (K-3) |
| 22 | `feature_artist_cron_loop` | 매주 월요일 09:00 UTC | `FEATURED_ARTIST_WORKER_ENABLED` | AI 추천 작가 후보 선정 (K-4) |
| 23 | `ai_curation_cron_loop` | 매주 월요일 09:00 UTC | `AI_CURATION_WORKER_ENABLED` | AI 컬렉션 자동 생성 (K-7) |

**모든 env guard 기본값: `true`** (false로 설정 시 해당 worker 비활성화)

**artwork_caption**은 `os.getenv` 대신 `settings.artwork_caption_worker_enabled` (Pydantic Settings)를 사용한다.

> 소스: `app/main.py:127~194`

---

## 19. env 변수 카탈로그 (config.py 기반)

`app/core/config.py`의 Pydantic Settings 필드 전체 목록. env 변수명은 대문자 변환 규칙을 따른다 (예: `jwt_secret` → `JWT_SECRET`).

### 기본 인프라

| env 변수 | 기본값 | 설명 |
|---------|--------|------|
| `ENVIRONMENT` | `development` | 실행 환경 |
| `DATABASE_URL` | `postgresql+asyncpg://...` | PostgreSQL 연결 URL |
| `REDIS_URL` | (미설정) | Redis URL — 미설정 시 in-memory fallback |
| `REDIS_PASSWORD` | - | Redis 비밀번호 |
| `REDIS_MAX_CONNECTIONS` | `50` | Redis 연결 풀 크기 |

### 인증

| env 변수 | 기본값 | 설명 |
|---------|--------|------|
| `JWT_SECRET` | `change_me` | JWT 서명 비밀키 (운영 필수 변경) |
| `JWT_ALGORITHM` | `HS256` | JWT 알고리즘 |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | access token 유효 시간 |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `30` | refresh token 유효 시간 |
| `TOTP_ENCRYPTION_KEY` | (미설정) | TOTP secret Fernet 암호화 키 — 미설정 시 평문 저장 경고 |
| `WEBAUTHN_RP_ID` | `localhost` | WebAuthn Relying Party ID (도메인, scheme 제외) |
| `WEBAUTHN_RP_NAME` | `Domo Admin` | 표시 이름 |
| `WEBAUTHN_RP_ORIGIN` | `http://localhost:3800` | scheme + port 포함 origin |

### 소셜 로그인

| env 변수 | 기본값 | 설명 |
|---------|--------|------|
| `GOOGLE_CLIENT_ID` | `""` | Google OAuth Client ID |
| `GOOGLE_CLIENT_SECRET` | `""` | Google OAuth Client Secret |

### 결제 (Stripe)

| env 변수 | 기본값 | 설명 |
|---------|--------|------|
| `PAYMENT_PROVIDER` | `mock_stripe` | `mock_stripe` 또는 `stripe` |
| `STRIPE_SECRET_KEY` | `""` | Stripe Secret Key |
| `STRIPE_WEBHOOK_SECRET` | `""` | Stripe Webhook 서명 검증 |
| `KYC_PROVIDER` | `mock` | `mock` \| `toss` \| `stripe` |
| `TOSS_CLIENT_ID` | `""` | Toss KYC Client ID |
| `TOSS_CLIENT_SECRET` | `""` | Toss KYC Client Secret |

### 스토리지 (S3)

| env 변수 | 기본값 | 설명 |
|---------|--------|------|
| `STORAGE_PROVIDER` | `local` | `local` 또는 `s3` |
| `UPLOAD_DIR` | `/app/uploads` | 로컬 스토리지 경로 |
| `S3_BUCKET` | `""` | S3 버킷명 |
| `S3_REGION` | `ap-northeast-2` | S3 리전 |
| `CDN_BASE_URL` | `""` | CDN URL |
| `AWS_ACCESS_KEY_ID` | `""` | S3용 AWS 자격증명 |
| `AWS_SECRET_ACCESS_KEY` | `""` | S3용 AWS 자격증명 |

### 이메일

| env 변수 | 기본값 | 설명 |
|---------|--------|------|
| `EMAIL_PROVIDER` | `mock` | `mock` \| `resend` \| `smtp` |
| `RESEND_API_KEY` | `""` | Resend API Key |
| `EMAIL_FROM` | `noreply@domo.tuzigroup.com` | 발신자 주소 |
| `EMAIL_FROM_NAME` | `Domo` | 발신자 이름 |
| `SMTP_HOST` | `""` | SMTP 호스트 (e.g. smtp.gmail.com) |
| `SMTP_PORT` | `587` | SMTP 포트 |
| `SMTP_USER` | `""` | SMTP 사용자 |
| `SMTP_PASSWORD` | `""` | SMTP 비밀번호 (Gmail App Password 등) |
| `SMTP_USE_TLS` | `true` | STARTTLS on 587 |
| `SMTP_USE_SSL` | `false` | SSL on 465 |

### AWS SES (뉴스레터)

> S3용 `AWS_ACCESS_KEY_ID`와 **별도** 자격증명 — least-privilege 분리

| env 변수 | 기본값 | 설명 |
|---------|--------|------|
| `AWS_SES_REGION` | `us-east-1` | SES 리전 |
| `AWS_SES_ACCESS_KEY_ID` | `""` | SES 전용 AWS 자격증명 |
| `AWS_SES_SECRET_ACCESS_KEY` | `""` | SES 전용 AWS 자격증명 |
| `AWS_SES_FROM_ADDRESS` | `noreply@domo.art` | SES 발신자 주소 |
| `AWS_SNS_TOPIC_ARN` | `""` | SES bounce → SNS topic ARN |
| `ADMIN_ALERT_EMAIL` | `""` | complaint 수신 시 alert 이메일 |

### LLM Gateway (tuzigroup)

| env 변수 | 기본값 | 설명 |
|---------|--------|------|
| `LLM_GATEWAY_URL` | `https://llm.tuzigroup.com/v1` | LLM 게이트웨이 URL |
| `LLM_GATEWAY_API_KEY` | `""` | LLM API Key — 미설정 시 Mock 모드 |
| `LLM_MODEL_NAME` | `gemma4-e4b` | 사용 모델명 |

### 번역

| env 변수 | 기본값 | 설명 |
|---------|--------|------|
| `TRANSLATION_PROVIDER` | `auto` | `auto` \| `ollama` \| `google` \| `mock` |
| `GOOGLE_TRANSLATE_API_KEY` | `""` | Google Translate API Key |
| `OLLAMA_URL` | `http://100.75.139.86:11434` | Ollama 서버 URL |
| `OLLAMA_TRANSLATION_MODEL` | `gemma4:latest` | 번역용 모델 |

### 분석 (PostHog)

| env 변수 | 기본값 | 설명 |
|---------|--------|------|
| `POSTHOG_API_KEY` | `""` | PostHog Server-Side API Key — 미설정 시 Mock |
| `POSTHOG_HOST` | `https://us.i.posthog.com` | PostHog 호스트 |

### 관측성 (OpenTelemetry)

| env 변수 | 기본값 | 설명 |
|---------|--------|------|
| `OTEL_ENABLED` | `false` | 분산 트레이싱 활성화 |
| `OTEL_SERVICE_NAME` | `domo-backend` | 서비스 이름 |
| `OTEL_OTLP_ENDPOINT` | (미설정) | OTLP 수집기 주소 (e.g. `localhost:4317`) |
| `OTEL_SAMPLING_RATE` | `0.1` | 샘플링 비율 (운영 10%, 스테이징 1.0 권장) |
| `METRICS_ENABLED` | `false` | Prometheus `/metrics` 활성화 |
| `METRICS_TOKEN` | `""` | /metrics Bearer 토큰 |

### 환율

| env 변수 | 기본값 | 설명 |
|---------|--------|------|
| `EXCHANGE_RATE_API_KEY` | `""` | Open Exchange Rates API Key — 미설정 시 Mock (하드코딩 환율) |

### 푸시 알림 (Firebase FCM · APNs)

| env 변수 | 기본값 | 설명 |
|---------|--------|------|
| `FIREBASE_CREDENTIALS_JSON` | `""` | Firebase 서비스 계정 JSON — 미설정 시 Mock |
| `APNS_KEY_ID` | `""` | APNs 10자리 Key ID |
| `APNS_TEAM_ID` | `""` | APNs 10자리 Team ID |
| `APNS_AUTH_KEY_P8` | `""` | AuthKey_XXXX.p8 파일 내용 |
| `APNS_BUNDLE_ID` | `art.domo.app` | 앱 Bundle ID |
| `APNS_SANDBOX` | `true` | true=샌드박스, false=운영 |

### Cron Worker 토글

| env 변수 | 기본값 | 설명 |
|---------|--------|------|
| `EMBEDDING_WORKER_ENABLED` | `true` | 임베딩 worker (#17) |
| `RSS_FETCH_WORKER_ENABLED` | `true` | RSS 수집 worker (#18) |
| `COHORT_ALERT_WORKER_ENABLED` | `true` | 코호트 알림 worker (#19) |
| `ML_TRAINING_WORKER_ENABLED` | `true` | ML 학습 worker (#20) |
| `ARTWORK_CAPTION_WORKER_ENABLED` | `true` | 캡션 생성 worker (#21) — Settings 객체 사용 |
| `FEATURED_ARTIST_WORKER_ENABLED` | `true` | Featured Artist worker (#22) |
| `AI_CURATION_WORKER_ENABLED` | `true` | AI 컬렉션 worker (#23) |

### ML / AI 파라미터

| env 변수 | 기본값 | 설명 |
|---------|--------|------|
| `AI_CURATION_DAILY_BUDGET_USD` | `5.0` | AI 컬렉션 LLM 일 비용 한도 (USD) |
| `CAPTION_BATCH_SIZE_QUICK` | `20` | 캡션 quick sweep 배치 크기 |
| `CAPTION_BATCH_SIZE_BATCH` | `100` | 캡션 batch sweep 배치 크기 |
| `ARTWORK_CAPTION_DAILY_LIMIT_PER_POST` | `3` | 포스트당 하루 캡션 재생성 한도 |

### 코호트 알림 파라미터

| env 변수 | 기본값 | 설명 |
|---------|--------|------|
| `SLACK_WEBHOOK_URL` | `""` | Slack Incoming Webhook — 미설정 시 로그만 |
| `COHORT_ALERT_7D_THRESHOLD` | `0.30` | D7 retention 경고 임계값 |
| `COHORT_ALERT_30D_THRESHOLD` | `0.15` | D30 retention 경고 임계값 |
| `COHORT_ALERT_MIN_COHORT_SIZE` | `10` | 통계 신뢰도용 최소 코호트 크기 |

### URL / CORS

| env 변수 | 기본값 | 설명 |
|---------|--------|------|
| `FRONTEND_URL` | `http://localhost:3700` | 프론트엔드 URL (CORS allowlist) |
| `ADMIN_URL` | `http://localhost:3800` | Admin 콘솔 URL (CORS allowlist) |
| `API_URL` | `http://localhost:3710/v1` | 백엔드 API 외부 접속 URL |
| `EXTRA_CORS_ORIGINS` | `""` | 추가 CORS 허용 origin (쉼표 구분) |

### DB Connection Pool

| env 변수 | 기본값 | 설명 |
|---------|--------|------|
| `DB_POOL_SIZE` | `20` | 풀 크기 (dev: 5, staging: 10 권장) |
| `DB_MAX_OVERFLOW` | `30` | 초과 연결 허용 수 |
| `DB_POOL_RECYCLE` | `3600` | stale 연결 재생성 주기 (초) |
| `DB_POOL_TIMEOUT` | `30` | 연결 대기 타임아웃 (초) |

---

## 20. 트러블슈팅

### 20.1 일반 장애 대응

| 증상 | 원인 | 해결 |
|------|------|------|
| admin 로그인 불가 (423) | 5회 실패 잠금 | 15분 대기 또는 DB `locked_until` 직접 초기화 |
| `SECOND_FACTOR_REQUIRED` 403 | TOTP/Passkey 미등록 | `/settings/totp-setup` 또는 `/settings/passkeys` 등록 |
| AI 컬렉션 생성 안 됨 | LLM Gateway 미설정 | `LLM_GATEWAY_API_KEY` 확인 |
| Featured Artist 후보 < 3명 | 데이터 부족 | 수동 featured 추가 + 작가 인덱스 갱신 대기 |
| 코호트 알림 미발송 | Slack webhook 미설정 | `SLACK_WEBHOOK_URL` 설정 |
| RSS 수집 중단 | worker disabled | `RSS_FETCH_WORKER_ENABLED=true` 확인 |
| 임베딩 미생성 | worker disabled 또는 LLM 미설정 | `EMBEDDING_WORKER_ENABLED` + LLM 설정 확인 |
| 환율 환산 오류 | exchange_rate worker 장애 | 로그 확인 후 `EXCHANGE_RATE_API_KEY` 점검 |

### 20.2 긴급 fallback env 토글

서비스 안정성 우선 시 즉시 적용 가능한 env 변경:

```bash
# AI/ML 비활성화
AI_CURATION_WORKER_ENABLED=false
ML_TRAINING_WORKER_ENABLED=false
ARTWORK_CAPTION_WORKER_ENABLED=false
FEATURED_ARTIST_WORKER_ENABLED=false

# LLM 비용 0으로 제한 (컬렉션 생성 skip)
AI_CURATION_DAILY_BUDGET_USD=0

# 외부 수집 중단
RSS_FETCH_WORKER_ENABLED=false

# Slack 알림 중단
COHORT_ALERT_WORKER_ENABLED=false
```

서비스 핵심 기능 (회원가입 / 게시 / 후원 / 경매)은 외부 의존성 없이 동작한다.

### 20.3 cron worker 상태 확인

```bash
# 실행 중 worker 확인 (Docker 환경)
docker logs domo-backend --since 5m | grep "cron_loop"

# 특정 worker 실패 확인
docker logs domo-backend --since 24h | grep "ERROR\|WARNING" | grep "cron"
```

---

## 21. 가이드 검증 메타

- **검증 일시**: 2026-05-08
- **Alembic HEAD**: 0083 (`ai_collections`)
- **검증 admin endpoint 수**: 76개 (`grep -rn "@router\."` 결과)
- **검증 파일**:
  - `app/core/admin_deps.py` — RBAC 의존성 정의
  - `app/core/config.py` — env 변수 59개 필드
  - `app/main.py` — cron worker 23개 등록
  - `app/api/admin_auth.py` — 7개 endpoint
  - `app/api/admin_webauthn.py` — 6개 endpoint
  - `app/api/admin_dashboard.py` — 4개 endpoint
  - `app/api/admin/users.py` — 7개 endpoint
  - `app/api/admin/content.py` — 9개 endpoint
  - `app/api/admin/transactions.py` — 4개 endpoint
  - `app/api/admin/schools.py` — 3개 endpoint
  - `app/api/admin_featured.py` — 3개 endpoint
  - `app/api/admin_featured_artist.py` — 4개 endpoint
  - `app/api/admin_ai_collections.py` — 3개 endpoint
  - `app/api/admin_experiments.py` — 3개 endpoint
  - `app/api/admin_diversity.py` — 2개 endpoint
  - `app/api/admin_newsletter.py` — 4개 endpoint
  - `app/api/admin_coupons.py` — 3개 endpoint
  - `app/api/admin_interviews.py` — 5개 endpoint
  - `app/api/admin_press_kits.py` — 2개 endpoint
  - `app/api/admin_media_coverage.py` — 4개 endpoint
  - `app/admin/src/app/*/page.tsx` — 13개 콘솔 페이지
  - `app/admin/src/components/AdminShell.tsx` — 메뉴 + ALLOW_WITHOUT_2FA

---

**추가 자료**:
- 사용자 시스템 가이드: [user-system-guide.ko.md](./user-system-guide.ko.md)
- Gap 분석 보고서: [admin-system-guide.gap-analysis.md](./admin-system-guide.gap-analysis.md)
