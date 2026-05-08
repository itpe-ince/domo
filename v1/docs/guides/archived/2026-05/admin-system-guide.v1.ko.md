# Domo 관리자 시스템 운영 가이드

> 운영자 · 큐레이터 · 모더레이터를 위한 Domo Admin 콘솔 사용 가이드

본 문서는 admin 권한을 가진 운영자가 Domo를 운영하는 방법을 설명합니다.
사용자 가이드는 [user-system-guide.ko.md](./user-system-guide.ko.md)를 참고하세요.

- 대상: admin / curator / moderator
- 권한 모델: RBAC (admin / curator / moderator / user)
- 최종 갱신: Phase 10 Wave A/B 종결 시점 (2026-05)

---

## 목차

1. [관리자 시스템 개요](#1-관리자-시스템-개요)
2. [관리자 인증 — 2FA · WebAuthn](#2-관리자-인증--2fa--webauthn)
3. [사용자 관리](#3-사용자-관리)
4. [콘텐츠 모더레이션](#4-콘텐츠-모더레이션)
5. [Featured Artist 큐레이션](#5-featured-artist-큐레이션)
6. [AI 컬렉션 검수 (K-7)](#6-ai-컬렉션-검수-k-7)
7. [ML A/B 테스트 운영 (K-8)](#7-ml-ab-테스트-운영-k-8)
8. [Diversity Reranking 튜닝 (K-2)](#8-diversity-reranking-튜닝-k-2)
9. [분석 대시보드 · 코호트 알림](#9-분석-대시보드--코호트-알림)
10. [정산 · KYC · Stripe Connect](#10-정산--kyc--stripe-connect)
11. [외부 통합 — RSS · OG · Newsletter](#11-외부-통합--rss--og--newsletter)
12. [데이터 보존 · GDPR · 운영 정책](#12-데이터-보존--gdpr--운영-정책)
13. [트러블슈팅 · 로그 · cron 운영](#13-트러블슈팅--로그--cron-운영)

---

## 1. 관리자 시스템 개요

Domo의 관리자 시스템은 다음 4가지 역할을 분리하여 권한을 부여합니다.

| 역할 | 권한 범위 |
|------|----------|
| **admin** | 모든 권한 (사용자 관리, 정산, ML 운영, 시스템 설정) |
| **curator** | Featured Artist + AI 컬렉션 검수 / publish / archive |
| **moderator** | 콘텐츠 신고 처리, 사용자 정지 (영구 ban 제외) |
| **user** | 일반 사용자 (admin 콘솔 접근 불가) |

### 1.1 관리 콘솔 진입

- URL: `/admin/dashboard` (admin / curator / moderator만 접근)
- 일반 사용자가 진입 시도 시 → `403 FORBIDDEN`
- 모든 admin 엔드포인트는 `require_admin_with_2fa` 의존성 적용

### 1.2 메뉴 구성

```
/admin/
├── dashboard              # 핵심 KPI 요약
├── users/                 # 사용자 관리
├── moderation/            # 신고 / 자동 차단 큐
├── featured-artist/       # Featured Artist (수동 + AI 자동) 큐레이션
├── ai-collections/        # AI 컬렉션 검수 큐
├── experiments/           # ML A/B 테스트
├── diversity-config/      # 다양성 설정 튜닝
├── analytics/             # 코호트 / engagement / newsletter 분석
├── payouts/               # 정산 / Stripe Connect
└── system/                # cron 모니터, 환경변수, 알림 webhook
```

---

## 2. 관리자 인증 — 2FA · WebAuthn

관리자 권한은 일반 사용자보다 강화된 인증을 강제합니다.

### 2.1 2FA (TOTP)

- Google Authenticator / Authy / 1Password 등 호환
- 등록: `/me/security/2fa` → QR 코드 스캔 → 6자리 코드 입력
- 로그인 시 비밀번호 + 6자리 코드
- 백업 코드 8개 발급 (1회용)

### 2.2 WebAuthn (보안 키 / 지문)

- USB 보안 키(YubiKey, Solo Key) 또는 플랫폼 인증(Touch ID, Windows Hello)
- 등록: `/admin/auth/webauthn/register` → 보안 키 / 지문 등록
- 로그인 시 비밀번호 + 보안 키 터치 / 지문
- WebAuthn 라이브러리 미설치 시 graceful skip (admin_webauthn router 자동 비활성화)

### 2.3 admin_dependencies

- `require_admin`: 일반 admin 검증 (2FA 우회 가능)
- `require_admin_with_2fa`: 2FA 강제 — 모든 민감 작업
- 세션 만료: 30분 미사용 시 재인증

### 2.4 배포 환경

- production: WebAuthn 강제 활성화
- staging: 2FA 권장
- 자세한 내용: [admin-auth-production-deployment.md](./admin-auth-production-deployment.md)

---

## 3. 사용자 관리

`/admin/users`

### 3.1 사용자 검색

- 이름 / 이메일 / ID로 검색
- 필터: 상태(active/suspended/deleted), 역할, 가입일, KYC 상태
- 정렬: 가입일 / 후원 누적 / engagement

### 3.2 사용자 상세 (`/admin/users/[id]`)

확인 가능한 정보:
- 프로필, 가입 경로, 최근 로그인 IP
- 활동 통계 (포스트 수, 후원 수, 경매 참여 수)
- KYC 상태 + 제출 서류 (관리자만 열람 가능)
- 신고 이력 (받은/한 신고)
- artist_index_rank (글로벌 작가 인덱스 순위)

### 3.3 상태 변경

| 상태 | 의미 | 효과 |
|------|------|------|
| `active` | 정상 | 모든 기능 사용 가능 |
| `suspended` | 일시 정지 | 로그인 가능, 게시 / 후원 / 경매 불가 |
| `banned` | 영구 차단 | 로그인 불가, 모든 콘텐츠 비공개 |
| `deleted` | GDPR 삭제 | 30일 grace 후 영구 삭제 |

상태 변경 시:
- 사유 입력 필수 (감사 로그)
- 사용자에게 이메일 알림 발송 (선택)
- 활성 후원 / 경매 자동 처리 (환불 또는 보류)

### 3.4 KYC 승인

- KYC 제출 사용자 큐 (`/admin/users/kyc-pending`)
- 신분증 / 본인 사진 검토 → 승인 / 거부
- 승인 시 정산 활성화 (Stripe Connect onboarding 자동 트리거)
- 거부 시 사유 + 재제출 안내

---

## 4. 콘텐츠 모더레이션

`/admin/moderation`

### 4.1 신고 큐

사용자 신고 우선순위:
1. **자동 감지 (auto_block)**: profanity / spam / NSFW 자동 비공개 → 검토 큐 진입
2. **사용자 신고**: 신고 사유별 (스팸 / 욕설 / 저작권 / NSFW / 기타)

### 4.2 처리 액션

| 액션 | 효과 |
|------|------|
| **승인 (정상)** | 신고 무효 처리, 콘텐츠 정상 노출 |
| **숨김** | `visibility=private` 강제, 작가는 알림 받음 |
| **삭제** | soft delete (deleted_at), 복구 가능 (30일) |
| **사용자 경고** | 작가에게 경고 메시지 + 1회 경고 카운트 |
| **사용자 정지** | 7일 / 30일 / 영구 정지 (3.3 참고) |

### 4.3 자동 차단 규칙

`/admin/moderation/rules` — 정규식 / ML 기반 룰 관리:
- profanity 사전 (한국어 + 영어 + 5개 언어)
- 스팸 패턴 (URL 무한 반복, 동일 작가에게 동일 메시지 N회 등)
- NSFW 이미지 분류 (외부 ML 서비스 통합, 옵션)

### 4.4 댓글 / DM 모더레이션

- 댓글: 동일 처리 흐름
- DM: 신고 시에만 모더레이터 검토 (privacy 우선, 일반 모더레이터는 메시지 본문 직접 열람 불가)
- WebAuthn 인증된 admin만 DM 본문 열람 가능

---

## 5. Featured Artist 큐레이션

홈 / 탐색 페이지 상단 추천 작가 운영.

### 5.1 수동 큐레이션 (Phase 8 G'-7)

`/admin/featured-artist/manual`

- 작가 검색 → "Featured에 추가" → 노출 기간 / 우선순위 설정
- 5명 동시 노출 (회전 알고리즘)
- 다양성 자동 보정 (동일 장르 / 지역 중복 방지)

### 5.2 AI 자동 추천 (Phase 10 K-4)

`/admin/featured-artist/queue` — 매주 월요일 06:00 UTC 자동 생성된 후보 5명 검수

**선정 기준** (composite_score):
- 30% × engagement (post_engagement_cache 최근 14일)
- 30% × artist_index_rank (신진작가 우선)
- 20% × diversity (장르/지역 분산)
- 20% × new_artist_bonus (후원자 0건 우선)

**검수 워크플로우**:
1. 큐에서 후보 5명 확인 (선정 사유 JSONB 함께 표시)
2. 각 후보별 액션:
   - **Approve**: status='approved' (publish 별도)
   - **Publish**: G'-7 featured_artists 테이블에 INSERT (즉시 노출)
   - **Reject**: 사유 입력 → status='rejected' + reasoning JSONB merge
3. autopublish=OFF (기본): 안전 우선, admin 명시 승인 필수

**Slack 알림**:
- 후보 < 3명 시 자동 Slack 알림 (manual 모드 제안)
- 임계값 미달 시 cohort_alert_jobs와 통합 (Phase 9 L-F)

### 5.3 노출 정책 튜닝

`/admin/featured-artist/policy`:
- 회전 주기 (7일 / 14일)
- 동일 작가 재노출 cooldown (4주)
- 지역 다양성 강제 (≥ 2개 국가 동시 노출)

---

## 6. AI 컬렉션 검수 (K-7)

`/admin/ai-collections/queue` — Editor's Pick 자동 컬렉션 검수

### 6.1 자동 생성 사이클

- 매주 월요일 09:00 UTC (K-4 06:00 UTC 후 3시간)
- 5개 컬렉션 자동 생성:
  1. post_embeddings 클러스터링 (sklearn KMeans 또는 metadata grouping fallback)
  2. 클러스터별 주제 추출 (장르/지역/신진성 분석)
  3. LLM 호출 → 제목/설명 생성 (한국어, gemma4-e4b)
  4. translation cache 활용 → 5개 언어 자동 번역
  5. 대표 작품 + 작품 10~20개 매핑

### 6.2 검수 작업

각 컬렉션 카드에서:
- 제목 / 설명 미리보기 (5개 언어 토글)
- 포함 작품 그리드 (cover_post_id + 10~20 작품)
- LLM 모델 버전 + 생성 시각

**액션**:
- **Publish**: status='published' → 공개 (즉시 `/explore/collections` 노출)
- **Edit**: 제목 / 설명 수동 수정 (한국어 원본 + 5 locale 재번역 트리거)
- **Archive**: status='archived' (숨김, 통계 보존)
- **Reject**: 완전 삭제 (사유 입력 → 향후 ML 학습 negative signal)

### 6.3 LLM 비용 한도

- 일 한도: $5 (`AI_CURATION_DAILY_BUDGET` env)
- 한도 초과 시 cron skip + Slack alert
- translation_cache 재사용으로 비용 절감 (K-3 / K-5와 공유)

### 6.4 수동 컬렉션 생성

- `/admin/ai-collections/new`에서 admin이 직접 컬렉션 생성 가능
- 작품 검색 → 추가 → 제목/설명 직접 작성 → publish
- AI 자동 생성과 동일하게 노출

---

## 7. ML A/B 테스트 운영 (K-8)

`/admin/experiments`

### 7.1 활성 실험 목록

기본 운영 실험: `feed_v2_rollout`
- v1 (legacy chronological) vs v2 (K-1 ML)
- 분배: 50:50 (PostHog feature flag)
- 측정 기간: 14일
- 측정 지표: feed_ctr, precision_at_10, session_duration, sponsorship_conversion

### 7.2 실험 생성

`POST /api/admin/experiments`
- 이름 (UNIQUE), 분배 비율 (JSONB: `{"v1": 0.5, "v2": 0.5}`)
- 가설 (hypothesis) 자유 텍스트
- 측정 지표 (target_metric)
- 시작 / 종료 일시 (자동 또는 수동)

### 7.3 실험 결과 분석

`GET /api/admin/experiments/{name}/results`:
- variant별 사용자 수, 이벤트 수, 전환율
- PostHog Insights URL (외부 dashboard 링크)
- 통계적 유의성 (p-value, chi-square 또는 t-test)

### 7.4 결과 해석 가이드

| 지표 | 목표 | 해석 |
|------|------|------|
| feed_ctr | v2 ≥ v1 + 10% | 피드 클릭률 |
| precision_at_10 | v2 ≥ v1 + 5% | 상위 10개 중 사용자 관심 비율 |
| session_duration | v2 ≥ v1 | 세션 체류 시간 |
| sponsorship_conversion | v2 ≥ v1 | 후원 전환율 (가장 중요) |
| p < 0.05 | 통계 유의성 | 통과 시 v2 100% rollout 권장 |

### 7.5 실험 종료 후 운영

- 결과 양호 시: `ML_FEED_DEFAULT_ALGO=v2`로 전체 rollout
- 결과 부진 시: v1 유지 + 가설 재검토 → 새 실험
- 90일 후 ml_experiments 자동 archive (운영 정책)

---

## 8. Diversity Reranking 튜닝 (K-2)

`/admin/diversity-config`

### 8.1 활성 설정 (`feed_default`)

기본값:
| 파라미터 | 기본값 | 의미 |
|---------|--------|------|
| `emerging_artist_boost` | 1.20 | 신진작가 score × 1.20 |
| `genre_min_diversity` | 3 | top-20 unique genres ≥ 3종 강제 |
| `region_min_diversity` | 2 | top-20 unique regions ≥ 2종 강제 |
| `top_k_window` | 20 | reranking 적용 윈도우 |

### 8.2 튜닝 워크플로우

1. PostHog 분석으로 다양성 지표 측정:
   - `diversity_emerging_artist_ratio` (목표: ≥ 30%)
   - `diversity_genre_count_top20` (목표: ≥ 3)
   - `diversity_region_count_top20` (목표: ≥ 2)
2. 지표 미달 시 boost 또는 quota 증가
3. 14일 운영 후 결과 검토

### 8.3 PATCH 엔드포인트

`PATCH /api/admin/diversity-config/{name}`
- body: `{emerging_artist_boost, genre_min_diversity, region_min_diversity, top_k_window}`
- 유효성:
  - boost: 1.0 ~ 2.0
  - genre/region: 1 ~ 10
  - window: 10 ~ 50
- Redis 캐시 5분 TTL → 5분 후 자동 적용

### 8.4 실험적 설정

- `DIVERSITY_RERANKING_ENABLED=false` env로 전체 비활성화 (긴급 fallback)
- 새 설정명 (예: `feed_experimental`)을 만들어 A/B 테스트 가능 (K-8 통합)

---

## 9. 분석 대시보드 · 코호트 알림

`/admin/analytics`

### 9.1 핵심 KPI 대시보드

- DAU / MAU
- 신규 가입 (일/주/월)
- 후원 통계 (활성 후원자, 신규 후원, 해지율)
- 경매 통계 (입찰 / 낙찰 / 환불)
- Feed CTR (algo별)
- AI 캡션 / 도슨트 / 컬렉션 클릭률

### 9.2 코호트 분석 (Phase 8 G''-4)

`post_engagement_cache` + cohort retention metric:
- D1 / D7 / D30 retention
- 가입 코호트별 활성 사용자 비율
- Featured Artist 노출 코호트 분석

### 9.3 코호트 자동 알림 (Phase 9 L-F)

매일 06:00 UTC 자동 측정:
- D7 retention < 30% → Slack 자동 알림 (`status='sent'`)
- D30 retention < 15% → Slack 알림
- min_cohort_size = 10 (통계 신뢰도)
- 24h cooldown UNIQUE INDEX → 같은 날 중복 알림 차단

`/admin/analytics/cohort-alerts` — 알림 이력 조회 + 임계값 튜닝

env 변수:
- `COHORT_ALERT_7D_THRESHOLD` (기본 0.30)
- `COHORT_ALERT_30D_THRESHOLD` (기본 0.15)
- `SLACK_WEBHOOK_URL` (미설정 시 log-only Mock 모드)

### 9.4 Newsletter Open Rate (Phase 9 L-B)

`/admin/analytics/newsletter`:
- 발송 수 / open / click
- 1x1 픽셀 트래킹 + 클릭 트래킹
- 사용자별 open rate (high engagement 식별)
- newsletter_events 테이블 90일 보존

### 9.5 OpenTelemetry 트레이싱 (Phase 8 G''-1)

운영 환경에서 분산 트레이싱:
- 모든 API endpoint span 자동 생성
- DB query / Redis / 외부 API span
- Jaeger / Tempo / Honeycomb 연동 (OTEL_EXPORTER_OTLP_ENDPOINT)
- 미설정 시 NoOp tracer (graceful)

---

## 10. 정산 · KYC · Stripe Connect

`/admin/payouts`

### 10.1 KYC 큐 (`/admin/users/kyc-pending`)

3.4 참고. 신분증 검토 + 승인.

### 10.2 정산 운영

매월 1일 자동 정산 cron:
- KYC 승인된 작가 대상
- 후원금 + 경매 낙찰액 합산
- Stripe Connect transfer 자동 실행
- 환불 / 분쟁 차감 후 net 금액

### 10.3 Stripe Connect onboarding

작가가 KYC 승인 후:
- Stripe Connect Express 계정 자동 생성
- 작가에게 onboarding 링크 이메일 발송
- 은행 계좌 / 신분증 추가 검증 (Stripe 직접 처리)
- 완료 후 정산 활성화 (`account.charges_enabled=true`)

### 10.4 환불 / 분쟁

- 사용자 환불 요청 → admin 검토 → Stripe refund 발행
- 분쟁 (chargeback) 자동 알림 → 작가 정산 보류 → 증빙 제출
- 분쟁 해결 시 자동 재정산

### 10.5 정산 보고서

월별 PDF / CSV 자동 생성:
- 작가별 후원 / 경매 / 수수료 / net 금액
- 세금 신고용 (1099-K 등 — 미국 작가)
- AWS SES로 작가에게 자동 발송

---

## 11. 외부 통합 — RSS · OG · Newsletter

### 11.1 RSS Auto-Fetch (Phase 9 L-B)

`/admin/external/rss`:
- 외부 매체 RSS 소스 등록 (블로그, 매거진, 포털)
- 1시간 주기 자동 수집 (rss_fetch_worker)
- 작가 이름 매칭 (단순 검색 + LLM 보조 옵션)
- 매칭된 기사 작가 프로필에 자동 표시

env: `RSS_FETCH_WORKER_ENABLED`, `LLM_ARTIST_MATCH_ENABLED`

### 11.2 OG Auto-Thumbnail (Phase 9 L-B)

`POST /api/og/preview` — 외부 링크 OG 메타 자동 추출:
- 작가가 본문에 외부 링크 첨부 시 자동 미리보기
- httpx + beautifulsoup4 (미설치 시 graceful)
- Redis 24h cache (LRU 512 entries fallback)

### 11.3 Newsletter 운영 (Phase 7 C-5)

`/admin/newsletter`:
- 주간 / 격주 자동 발송
- 사용자 세그먼트별 콘텐츠 (팔로우 작가 신작 등)
- 1x1 픽셀 + 클릭 트래킹 (L-B 통합)
- AWS SES 발송 (`AWS_SES_REGION` env)
- 발송 실패 / bounce 자동 처리 (Phase 8 H'-5)

### 11.4 Press Kit (Phase 7 C-2)

작가별 보도자료 자동 생성:
- 작가 bio + 대표작 + 매체 노출 이력 + 인터뷰
- PDF 다운로드 (Phase 8 추가)
- 외부 매체 직접 링크 가능

---

## 12. 데이터 보존 · GDPR · 운영 정책

### 12.1 데이터 보존 정책

| 데이터 | 보존 기간 | 처리 |
|--------|----------|------|
| user activity log | 90일 | 자동 삭제 (gdpr_cron) |
| ml_experiments | 90일 | archive 후 영구 삭제 (cleanup_old_experiments) |
| translation_cache | 90일 미사용 시 | cleanup cron |
| newsletter_events | 90일 | 자동 삭제 |
| dm_messages | 사용자 삭제 시 | soft delete (deleted_at) |
| posts | 사용자 삭제 시 | soft delete + 30일 grace |
| user accounts | GDPR 삭제 요청 시 | 30일 grace 후 영구 삭제 |

상세: [../operations/ml-experiments-policy.md](../operations/ml-experiments-policy.md)

### 12.2 GDPR 요청 처리

`/admin/privacy/requests`:
- 사용자 데이터 export 요청 → JSON ZIP 생성 → 이메일 발송
- 계정 삭제 요청 → 30일 grace 알림 → 자동 영구 삭제
- 동의 철회 → 마케팅 / 분석 / 쿠키 옵트아웃 즉시 적용

### 12.3 감사 로그

- 모든 admin 액션은 `audit_logs` 테이블에 기록
- 사용자 정지 / 삭제 / Featured publish / 환불 / KYC 승인 등
- 보존 기간: 7년 (한국 개인정보보호법)
- admin 본인이 본인 액션 확인 가능 (다른 admin은 super_admin만)

---

## 13. 트러블슈팅 · 로그 · cron 운영

### 13.1 cron worker 모니터링

`/admin/system/crons` — 21개 worker 실시간 상태:

| # | worker | 주기 | env guard |
|:-:|--------|------|-----------|
| 1 | auction_cron_loop | 5min | - |
| 2 | gdpr_cron_loop | 1h | - |
| ... | (16개 생략) | ... | ... |
| 17 | embedding_cron_loop (L-A) | 60s + 24h | EMBEDDING_WORKER_ENABLED |
| 18 | rss_fetch_cron_loop (L-B) | 1h | RSS_FETCH_WORKER_ENABLED |
| 19 | cohort_alert_cron_loop (L-F) | 24h | COHORT_ALERT_WORKER_ENABLED |
| 20 | ml_training_cron_loop (K-1) | 24h | ML_TRAINING_WORKER_ENABLED |
| 21 | artwork_caption_cron_loop (K-3) | 60s + 24h | ARTWORK_CAPTION_WORKER_ENABLED |
| 22 | featured_artist_cron_loop (K-4) | 7d | FEATURED_ARTIST_WORKER_ENABLED |
| 23 | ai_curation_cron_loop (K-7) | 7d | AI_CURATION_WORKER_ENABLED |

각 worker:
- R-5 isolation 패턴 (독립 AsyncSessionLocal)
- env 변수로 disable 가능 (graceful degradation)
- 로그 + Slack 알림 (실패 시)

### 13.2 환경변수 관리

`/admin/system/env` (super_admin만):
- 일부 토글성 env 변수는 UI에서 직접 변경 가능
- 변경 시 즉시 cron worker / API 재로드
- 민감 정보 (API 키 등)는 UI 노출 안 함, .env 파일 직접 수정 필수

주요 env:
```
# 인증
JWT_SECRET, REFRESH_SECRET
WEBAUTHN_RP_ID, WEBAUTHN_ORIGIN

# 결제
STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET
STRIPE_CONNECT_CLIENT_ID

# 외부 서비스
LLM_GATEWAY_API_KEY, LLM_GATEWAY_URL  # tuzigroup
POSTHOG_API_KEY, POSTHOG_HOST
SLACK_WEBHOOK_URL
AWS_SES_REGION, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY
OPEN_EXCHANGE_RATES_APP_ID
FCM_SERVER_KEY, APNS_KEY_ID

# Cron toggles (모두 default true, false로 disable)
EMBEDDING_WORKER_ENABLED, RSS_FETCH_WORKER_ENABLED
COHORT_ALERT_WORKER_ENABLED, ML_TRAINING_WORKER_ENABLED
ARTWORK_CAPTION_WORKER_ENABLED, FEATURED_ARTIST_WORKER_ENABLED
AI_CURATION_WORKER_ENABLED

# ML 토글
ML_FEED_DEFAULT_ALGO=v1  # or v2 or auto
ML_FEED_V2_ENABLED=false
DIVERSITY_RERANKING_ENABLED=true

# 비용 한도
AI_CURATION_DAILY_BUDGET=5  # USD
COHORT_ALERT_7D_THRESHOLD=0.30
COHORT_ALERT_30D_THRESHOLD=0.15

# 인프라
REDIS_URL, DATABASE_URL
EMBEDDING_MODEL_PATH  # sentence-transformers
```

### 13.3 로그 분석

운영 환경에서 로그 위치:
- API: stdout (Docker 로그) + Sentry (옵션)
- DB: PostgreSQL slow query log
- Cron: stdout + 실패 시 Slack 알림

zero-script QA 방식 (Phase 4):
- 구조화 JSON 로그 (logfmt 또는 JSON)
- Docker compose logs 실시간 모니터링
- LLM 비용 / API latency / DB query duration 모두 로그

### 13.4 일반 트러블슈팅

| 증상 | 원인 | 해결 |
|------|------|------|
| ML 피드가 v2로 안 바뀜 | `ML_FEED_DEFAULT_ALGO=v1` | env `=v2` 또는 PostHog flag |
| AI 컬렉션 안 생성됨 | LLM Gateway 미설정 | LLM_GATEWAY_API_KEY 확인 |
| Featured Artist 후보 < 3 | 데이터 부족 | manual 모드 + 작가 인덱스 갱신 |
| 코호트 알림 미발송 | Slack webhook 미설정 | SLACK_WEBHOOK_URL 확인 |
| WebSocket 메시지 지연 | Redis 미연결 (multi-pod) | REDIS_URL 설정 |
| 정산 실패 | KYC 미승인 또는 Stripe Connect 미완료 | KYC 큐 + Stripe onboarding 확인 |
| 환율 환산 오류 | exchange_rates 캐시 만료 | exchange_rate_cron 강제 재실행 |
| 임베딩 미생성 | EMBEDDING_MODEL_PATH 미설정 | sentence-transformers 모델 경로 확인 |

### 13.5 긴급 fallback

서비스 장애 시 즉시 적용 가능한 env 토글:
- `ML_FEED_V2_ENABLED=false` → v1 chronological만 사용
- `DIVERSITY_RERANKING_ENABLED=false` → K-2 비활성
- `RSS_FETCH_WORKER_ENABLED=false` → 외부 fetch 중단
- `AI_CURATION_DAILY_BUDGET=0` → LLM 비용 0
- `COHORT_ALERT_WORKER_ENABLED=false` → Slack 알림 중단

ML 모델 / LLM / 외부 서비스 모두 graceful degradation 설계되어 있어,
**서비스 핵심 (회원가입 / 게시 / 후원 / 경매)은 외부 의존성 없이 동작 가능**.

---

## 14. 추가 자료

- 사용자 시스템 가이드: [user-system-guide.ko.md](./user-system-guide.ko.md)
- 어드민 인증 배포: [admin-auth-production-deployment.md](./admin-auth-production-deployment.md)
- ML 운영 정책: [../operations/ml-experiments-policy.md](../operations/ml-experiments-policy.md)
- Phase 10 Plan: [../01-plan/features/domo-phase10-roadmap.plan.md](../01-plan/features/domo-phase10-roadmap.plan.md)
- TESTING_NOTES (skipped 사유): [../../backend/docs/TESTING_NOTES.md](../../backend/docs/TESTING_NOTES.md)

문의 / 이슈: ops@domo.example (실제 운영 채널은 별도 안내)

---

**버전 이력**

| 버전 | 날짜 | 변경 |
|------|------|------|
| 1.0 | 2026-05-06 | Phase 10 Wave A/B 종결 시점 초기 작성. 13개 운영 섹션 통합. 21개 cron worker 매트릭스 + env 변수 카탈로그 포함. |
