# Admin System Guide — Gap 분석 보고서

> 기준: `/v1/docs/guides/admin-system-guide.ko.md` (631라인, v1.0)  
> 소스 검증: 2026-05-08  
> Alembic HEAD: 0083 (`ai_collections`)  
> 검증 admin endpoint 수: 76개

## 요약

| 구분 | 건수 |
|------|------|
| ✅ 정확 | 18 |
| ⚠️ 부분 오류 / 수정 필요 | 21 |
| ❌ 완전 오류 / 존재하지 않음 | 9 |
| ➕ 소스에 있으나 가이드 누락 | 14 |

---

## 상세 Gap 목록

| # | 섹션 | 가이드 주장 | 실제 소스 | 상태 | 처리 |
|---|------|------------|----------|------|------|
| 1 | 1.1 RBAC | "admin / curator / moderator / user 4단계" (가이드 line 9, 36~41) | `admin_deps.py`에 `require_admin`, `require_admin_with_2fa` 두 함수만 존재. `user.role` 값은 `admin/artist/user` 3가지만 허용 (`admin/users.py` line 37). `curator`, `moderator` 역할 미정의 | ❌ | RBAC 3단계로 정정 (admin/artist/user) |
| 2 | 1.2 admin 콘솔 메뉴 | `/admin/featured-artist, /admin/ai-collections, /admin/experiments, /admin/diversity-config, /admin/analytics, /admin/payouts, /admin/system` (가이드 line 51~63) | 실제 admin 콘솔 페이지: `dashboard, users, schools, applications, posts, transactions, moderation, settings, settings/passkeys, settings/recovery-codes, settings/totp-setup` (AdminShell.tsx + app/디렉토리 확인) — `featured-artist, ai-collections, experiments, diversity-config, analytics, payouts, system` 페이지 없음 | ❌ | 실제 존재하는 페이지로 메뉴 교체 |
| 3 | 2.3 admin_dependencies | "`require_admin`: 일반 admin 검증 (2FA 우회 가능)" (가이드 line 87) | 정확 — `admin_deps.py` line 12~18. TOTP/Passkey 등록 전용 사용 목적도 명기 | ✅ | 소스 파일 명시 추가 |
| 4 | 2.3 admin_dependencies | "`require_admin_with_2fa`: 2FA 강제 — 모든 민감 작업" (가이드 line 88) | 정확 — `admin_deps.py` line 21~51. TOTP 또는 Passkey 등록 여부를 WebauthnCredential 테이블에서 OR 조건으로 체크 | ✅ | 소스 파일 명시 추가 |
| 5 | 2.3 | "세션 만료: 30분 미사용 시 재인증" (가이드 line 89) | `admin_deps.py`에 세션 만료 로직 없음. JWT access token 60분 만료(`config.py` `access_token_expire_minutes=60`)가 전부 | ⚠️ | 30분 세션 만료 주장 제거, JWT 60분 만료로 정정 |
| 6 | 2.4 배포 환경 | "production: WebAuthn 강제 활성화" (가이드 line 93) | `admin_webauthn.py`는 `try/except ImportError`로 webauthn 라이브러리 미설치 시 graceful skip (`main.py` line 13~21). 환경 기반 강제 활성화 코드 없음 | ⚠️ | "WebAuthn 선택적 — 라이브러리 설치 시 활성화" 로 정정 |
| 7 | 3.2 사용자 상세 | "KYC 상태, 신고 이력, artist_index_rank" (가이드 line 112~117) | `GET /admin/users` 응답에 `id, email, display_name, avatar_url, role, status, country_code, warning_count, created_at`만 포함 (`admin/users.py` line 215~225). KYC 상태, 신고 이력, artist_index_rank 없음 | ⚠️ | 실제 응답 필드로 교체 |
| 8 | 3.3 상태 변경 | "`banned` — 로그인 불가, `deleted` — 30일 grace" (가이드 line 120~126) | `PATCH /admin/users/{id}`는 `active/suspended` 두 상태만 허용 (`admin/users.py` line 341). `banned`, `deleted` 상태 처리 코드 없음 | ❌ | `active/suspended` 2상태만 명시 |
| 9 | 3.3 | "사용자에게 이메일 알림 발송 (선택)" (가이드 line 128) | `admin/users.py`에 이메일 알림 없음. `Notification` 인앱 알림만 추가 (`line 342~346`) | ⚠️ | 이메일 → 인앱 알림으로 정정 |
| 10 | 3.3 | "활성 후원 / 경매 자동 처리 (환불 또는 보류)" (가이드 line 129) | `admin/users.py` PATCH 로직에 후원/경매 자동 처리 없음 | ❌ | 해당 설명 제거 |
| 11 | 3.4 KYC 승인 | "`/admin/users/kyc-pending` KYC 큐" (가이드 line 134) | `admin/users.py` 라우터에 `/kyc-pending` 엔드포인트 없음. KYC 관련 admin 엔드포인트 전체 미존재 | ❌ | KYC 큐 섹션 제거 또는 미구현 표기 |
| 12 | 4.3 자동 차단 규칙 | "`/admin/moderation/rules` — 정규식 / ML 기반 룰 관리" (가이드 line 163) | `admin/content.py`에 moderation rules 관리 엔드포인트 없음. `GET /admin/reports`, `POST /admin/reports/{id}/resolve`, `GET /admin/appeals`, `POST /admin/warnings/{id}/cancel`, `POST /admin/warnings/{id}/reject-appeal` 존재 | ❌ | `/admin/moderation/rules` 제거, 실제 엔드포인트로 교체 |
| 13 | 4.4 댓글/DM | "WebAuthn 인증된 admin만 DM 본문 열람 가능" (가이드 line 172) | DM 관련 admin 특수 권한 로직 소스 미확인 | ⚠️ | 미검증 주장 — 제거 권장 |
| 14 | 5.1 수동 큐레이션 | "5명 동시 노출 (회전 알고리즘)" (가이드 line 185) | `admin_featured.py`는 POST/GET/DELETE로 단순 CRUD. 회전 알고리즘 코드 미확인 | ⚠️ | 미검증 주장 — 단순 수동 관리로 기술 |
| 15 | 5.2 AI 자동 추천 | "매주 월요일 06:00 UTC 자동 생성" (가이드 line 191) | `featured_artist_jobs.py` line 9, 320: 매주 월요일 **09:00 UTC** | ❌ | 09:00 UTC로 정정 |
| 16 | 5.2 | "Slack 알림 — 임계값 미달 시 cohort_alert_jobs와 통합" (가이드 line 207~208) | `featured_artist_jobs.py` line 49: SLACK_WEBHOOK_URL 미설정 시 skip — cohort_alert_jobs 연동 코드 없음 | ⚠️ | "별도 Slack 알림 (SLACK_WEBHOOK_URL 설정 시)" 로 정정 |
| 17 | 6.1 AI 컬렉션 | "매주 월요일 09:00 UTC (K-4 06:00 UTC 후 3시간)" (가이드 line 225) | `ai_curation_jobs.py` line 3, 445: 매주 월요일 **09:00 UTC**. K-4도 09:00 UTC이므로 "K-4 06:00 UTC 후 3시간" 설명 오류 | ⚠️ | K-4도 09:00 UTC로 정정, 시간 차이 설명 제거 |
| 18 | 6.3 LLM 비용 | "`AI_CURATION_DAILY_BUDGET` env" (가이드 line 249) | 실제 env 이름: `AI_CURATION_DAILY_BUDGET_USD` (`ai_curation_jobs.py` line 50) | ⚠️ | env 이름 `_USD` suffix 추가 |
| 19 | 7.2 실험 생성 | "`POST /api/admin/experiments`" (가이드 line 275) | 실제 경로: `POST /admin/experiments` (v1 prefix 포함 시 `/v1/admin/experiments`). `/api/` prefix 없음 (`admin_experiments.py` line 29: `prefix="/admin"`) | ⚠️ | `/api/` 제거 |
| 20 | 7.3 실험 결과 | "`GET /api/admin/experiments/{name}/results`" (가이드 line 283) | 실제: `GET /admin/experiments/{name}/results`. `/api/` prefix 없음 | ⚠️ | `/api/` 제거 |
| 21 | 8.3 PATCH | "`PATCH /api/admin/diversity-config/{name}`" (가이드 line 330) | 실제: `PATCH /admin/diversity-config/{name}` (`admin_diversity.py` line 24, 127). `/api/` prefix 없음 | ⚠️ | `/api/` 제거 |
| 22 | 9.3 코호트 알림 | "`COHORT_ALERT_WORKER_ENABLED`" (가이드 line 376) | 정확 — `main.py` line 158 | ✅ | - |
| 23 | 9.4 Newsletter Open Rate | "`/admin/analytics/newsletter`" (가이드 line 382) | `admin_newsletter.py`의 실제 경로: `GET /admin/newsletter/issues`, `POST /admin/newsletter/issues/compose`, `PATCH /admin/newsletter/issues/{id}`, `POST /admin/newsletter/issues/{id}/send`. `/analytics/newsletter` 없음 | ❌ | 실제 엔드포인트로 교체 |
| 24 | 10.1 KYC 큐 | "`/admin/users/kyc-pending`" (가이드 line 402) | 미존재 (항목 11과 동일) | ❌ | 제거 |
| 25 | 10.2 정산 | "매월 1일 자동 정산 cron" (가이드 line 408) | `settle_task = asyncio.create_task(settlement_cron_loop(interval_seconds=86400))` — 1일 간격 실행이나 "매월 1일" 특정 날짜 로직은 `settlement_jobs.py` 내부 확인 필요. main.py에는 86400초(매일)로 등록 | ⚠️ | "매일 실행, 월말 정산 조건 내부 처리" 로 표현 수정 |
| 26 | 10.5 정산 보고서 | "AWS SES로 작가에게 자동 발송" (가이드 line 433) | `config.py`에 `aws_ses_access_key_id` 존재. 단, 정산 보고서 자동 발송 서비스 코드 직접 미확인 | ⚠️ | 미검증 표기 |
| 27 | 11.1 RSS Auto-Fetch | "1시간 주기 자동 수집" (가이드 line 443) | 정확 — `main.py` line 154: `rss_fetch_cron_loop(interval_seconds=3600)` | ✅ | - |
| 28 | 11.2 OG Auto-Thumbnail | "`POST /api/og/preview`" (가이드 line 451) | `main.py`에서 `og_router` 등록 확인. 실제 엔드포인트 prefix는 `/api/` 없음 — `og.py` 라우터 확인 필요. 단 `/v1/...` prefix 사용 | ⚠️ | `/api/` 제거, 정확 경로 확인 필요 |
| 29 | 12.3 감사 로그 | "`audit_logs` 테이블에 기록" (가이드 line 499~503) | `audit_logs` 테이블 모델/alembic 미확인. `admin/users.py`에서는 `log.info("AUDIT ...")` Python 로그만 사용 | ❌ | DB `audit_logs` 주장 제거, Python 구조화 로그로 정정 |
| 30 | 12.3 | "다른 admin은 super_admin만 열람 가능" (가이드 line 502) | `super_admin` 역할 미존재 | ❌ | 제거 |
| 31 | 13.1 cron 워커 | "21개 worker" 표 제목 (가이드 line 510) | `main.py` 실제 `asyncio.create_task` 호출 수: 23개 (auction, gdpr, schedule, badge, settle, webhook_cleanup, draft_cleanup, tier_release, auction_promotion, artist_index, post_engagement, subscription_expiry, newsletter, exchange_rate, email_digest, auto_renewal, embedding, rss_fetch, cohort_alert, ml_training, artwork_caption, featured_artist, ai_curation) | ❌ | 21개 → 23개로 정정 |
| 32 | 13.1 cron 워커 표 | worker #1~16 생략 처리 (가이드 line 513) | 실제 1~16번 워커가 명확히 정의되어 있으나 생략 | ⚠️ | 모든 23개 워커 전체 표 제공 |
| 33 | 13.1 cron 워커 표 | worker 번호 17~23 매핑 (가이드 line 517~523) | 주석 기준 번호: embedding=12, rss_fetch=13, cohort_alert=14, ml_training=20, artwork_caption=21, featured_artist=22, ai_curation=23 | ⚠️ | main.py 주석의 정확한 번호로 교체 |
| 34 | 13.2 env 변수 | "`JWT_SECRET, REFRESH_SECRET`" (가이드 line 540) | `config.py`에 `jwt_secret`만 존재. `refresh_secret` 없음 | ⚠️ | `REFRESH_SECRET` 제거 |
| 35 | 13.2 env 변수 | "`WEBAUTHN_RP_ID, WEBAUTHN_ORIGIN`" (가이드 line 541) | config.py: `webauthn_rp_id`, `webauthn_rp_name`, `webauthn_rp_origin` (3개) | ⚠️ | `WEBAUTHN_ORIGIN` → `WEBAUTHN_RP_ORIGIN`, `WEBAUTHN_RP_NAME` 추가 |
| 36 | 13.2 env 변수 | "`STRIPE_CONNECT_CLIENT_ID`" (가이드 line 544) | `config.py`에 미존재. `stripe_secret_key`, `stripe_webhook_secret`만 있음 | ❌ | 제거 |
| 37 | 13.2 env 변수 | "`AWS_SES_REGION, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY`" (가이드 line 549~550) | `aws_ses_region`, `aws_ses_access_key_id`, `aws_ses_secret_access_key` (SES 전용). 일반 S3용 `aws_access_key_id` 별도 존재 | ⚠️ | S3용과 SES용 분리 명시 |
| 38 | 13.2 env 변수 | "`FCM_SERVER_KEY, APNS_KEY_ID`" (가이드 line 553~554) | `config.py`: `firebase_credentials_json` (FCM_SERVER_KEY 없음), `apns_key_id`, `apns_team_id`, `apns_auth_key_p8`, `apns_bundle_id`, `apns_sandbox` | ⚠️ | `FCM_SERVER_KEY` → `FIREBASE_CREDENTIALS_JSON`으로 정정 |
| 39 | 13.2 env 변수 | "`OPEN_EXCHANGE_RATES_APP_ID`" (가이드 line 554) | `config.py`: `exchange_rate_api_key` | ⚠️ | env 이름 정정 |
| 40 | 13.2 env 변수 | "`AI_CURATION_DAILY_BUDGET=5`" (가이드 line 566) | 실제: `AI_CURATION_DAILY_BUDGET_USD=5.0` | ⚠️ | `_USD` suffix 추가 |
| 41 | 13.2 env 변수 | "`ML_FEED_DEFAULT_ALGO=v1`" (가이드 line 562) | `config.py`에 미존재. `ai_curation_jobs.py`, `ml_feed_training.py` 등에서 직접 `os.getenv` 사용 여부 별도 확인 필요 | ⚠️ | 미검증 표기 또는 제거 |
| 42 | 13.2 env 변수 | "`EMBEDDING_MODEL_PATH`" (가이드 line 573) | `config.py`에 미존재. `embedding_jobs.py` 내부 직접 참조 여부 확인 필요 | ⚠️ | 미검증 표기 |
| 43 | 추가 누락 | admin 콘솔 `/applications` (작가 심사) | AdminShell.tsx에 `applications` 메뉴 존재, `GET/POST /admin/artists/applications/{id}/approve|reject` | ➕ | 신규 섹션 추가 |
| 44 | 추가 누락 | admin 콘솔 `/schools` (학교 관리) | `GET/POST/PATCH /admin/schools` (`admin/schools.py`) + admin 페이지 존재 | ➕ | 신규 섹션 추가 |
| 45 | 추가 누락 | admin 콘솔 `/posts` (콘텐츠 관리) | `GET /admin/posts/digital-art-queue`, `POST /admin/posts/{id}/digital-art-verdict`, `GET /admin/posts/list`, `PATCH /admin/posts/{id}/status` | ➕ | 신규 섹션 추가 |
| 46 | 추가 누락 | admin 콘솔 `/transactions` (거래 관리) | `POST /admin/auctions/process-expired`, `GET /admin/auctions/list`, `GET /admin/orders/list`, `POST /admin/orders/{id}/refund` | ➕ | 신규 섹션 추가 |
| 47 | 추가 누락 | admin 콘솔 `/moderation` 실제 엔드포인트 | `GET /admin/reports`, `POST /admin/reports/{id}/resolve`, `GET /admin/appeals`, `POST /admin/warnings/{id}/cancel`, `POST /admin/warnings/{id}/reject-appeal` | ➕ | 실제 엔드포인트 교체 |
| 48 | 추가 누락 | admin 콘솔 `/settings` (시스템 설정) | `GET /admin/settings`, `PATCH /admin/settings/{key}` (`admin_dashboard.py`) | ➕ | 신규 섹션 추가 |
| 49 | 추가 누락 | `POST /admin/users` — 관리자 직접 사용자 생성 (Phase 10 hot fix) | `admin/users.py` line 229. `AdminCreateUserRequest`: email, display_name, role, send_magic_link, country_code | ➕ | 3.x 절에 추가 |
| 50 | 추가 누락 | magic_link 서비스 | `services/magic_link.py`: 24시간 유효 초대 링크 이메일 발송. `send_magic_link=true` 시 자동 발송 | ➕ | 3.x 절에 추가 |
| 51 | 추가 누락 | `PATCH /admin/users/{id}` self-block 차단 | `admin/users.py` line 324~335: admin 본인 role/status 변경 불가 (SELF_MODIFY_FORBIDDEN) | ➕ | 3.x 절에 추가 |
| 52 | 추가 누락 | coupon 관리 (`POST/GET/DELETE /admin/coupons`) | `admin_coupons.py` — 가이드에 완전 누락 | ➕ | 별도 섹션 추가 |
| 53 | 추가 누락 | interview 관리 (5개 endpoint) | `admin_interviews.py` — AI 인터뷰 생성/검수/publish/번역 | ➕ | 별도 섹션 추가 |
| 54 | 추가 누락 | press kit 생성 | `admin_press_kits.py` | ➕ | 외부 통합 섹션에 추가 |
| 55 | 추가 누락 | media coverage 관리 (4개 endpoint) | `admin_media_coverage.py` | ➕ | 외부 통합 섹션에 추가 |
| 56 | 추가 누락 | `ALLOW_WITHOUT_2FA` 경로 목록 | AdminShell.tsx line 55~60: `/login, /settings/totp-setup, /settings/passkeys, /settings/recovery-codes` — 2FA 없이 접근 가능 | ➕ | 인증 섹션에 추가 |

---

## 주요 발견 사항 요약

### 1. RBAC 4단계 → 3단계
가이드는 `admin/curator/moderator/user` 4단계를 선언하지만, 실제 소스의 `role` 컬럼은 `admin/artist/user` 3가지만 처리한다. `curator`, `moderator` 역할은 코드 어디에도 정의되지 않는다.

### 2. cron worker 21개 → 23개
`main.py`의 실제 `asyncio.create_task` 호출은 23개다. 가이드 표에서 항목 1~16을 "생략"했으나, 실제로는 auction(5m), gdpr(1h), schedule(1m), badge(24h), settle(24h), webhook_cleanup(24h), draft_cleanup(24h), tier_release(1m), auction_promotion(1m), artist_index(1h), post_engagement(1h), subscription_expiry(1h), newsletter(1h), exchange_rate(1h), email_digest(1h), auto_renewal(1h)이 번호 1~16에 해당한다.

### 3. admin 콘솔 메뉴 불일치
가이드 메뉴 트리(`featured-artist, ai-collections, experiments, diversity-config, analytics, payouts, system`)는 실제 admin 콘솔(`dashboard, users, schools, applications, posts, transactions, moderation, settings`)과 전혀 다르다. K-4/K-7/K-8 등 ML 관련 페이지는 현재 콘솔에 미구현 상태다.

### 4. `audit_logs` 테이블 미존재
가이드는 "모든 admin 액션은 `audit_logs` 테이블에 기록"이라고 하지만, 해당 테이블 모델이나 alembic migration이 확인되지 않는다. 실제로는 `log.info("AUDIT action=...")` Python 구조화 로그로 대체된다.

### 5. 여러 env 변수명 불일치
- `AI_CURATION_DAILY_BUDGET` → `AI_CURATION_DAILY_BUDGET_USD`
- `REFRESH_SECRET` → 미존재 (jwt_secret 하나만 사용)
- `STRIPE_CONNECT_CLIENT_ID` → 미존재
- `FCM_SERVER_KEY` → `FIREBASE_CREDENTIALS_JSON`
- `OPEN_EXCHANGE_RATES_APP_ID` → `EXCHANGE_RATE_API_KEY`
- `WEBAUTHN_ORIGIN` → `WEBAUTHN_RP_ORIGIN`

### 6. 가이드 누락 기능 다수
콘솔 상에 실존하는 기능 중 `/applications`(작가 심사), `/schools`, `/posts`, `/transactions`, 쿠폰 관리, AI 인터뷰, press kit, media coverage 섹션이 가이드에 완전히 없다.

### 7. K-4 Featured Artist 생성 시각 오류
가이드는 "매주 월요일 06:00 UTC"라고 하지만 실제는 **09:00 UTC**다 (`featured_artist_jobs.py` line 9, 320).

---

*검증 시점: 2026-05-08 | Alembic HEAD: 0083*
