# Domo Phase 4 Plan — Production Hardening

> **작성일**: 2026-04-11
> **선행 문서**: [phase3.analysis.md](../03-analysis/phase3.analysis.md), [domo.report.md](../04-report/domo.report.md)
> **목표**: Phase 0~3 프로토타입(96% 매칭)을 **실 서비스 가능 수준**으로 전환
> **단계**: Plan (PDCA Plan Phase)

---

## 1. 배경

Phase 0~3 4주 일정으로 Domo 프로토타입이 완성되었고, 종합 매칭률 96% + 시연 시나리오 5/5 통과 + E2E 86/86으로 **고객 시연 가능 상태**입니다. 그러나 프로토타입에는 의도적으로 OOS 처리한 항목들이 있어 **실 서비스 출시 전 반드시 처리해야 할 항목 6개(Must)** 가 있습니다. 또한 Should/Could 백로그도 함께 정리하여 Phase 4 이후 로드맵을 명확히 합니다.

## 2. Phase 4 목표

| 목표 | 측정 지표 |
|------|----------|
| 실제 결제 처리 가능 | Stripe 라이브 모드에서 실제 결제 성공 1건 |
| 컴플라이언스 준수 | GDPR + 미성년자 정책 + 개인정보 처리방침 준비 |
| 보안 강화 | OWASP Top 10 점검 + Rate limiting + JWT 회전 |
| 미디어 안정성 | S3/Minio 전환 + CDN 서빙 |
| 운영 가시성 | Sentry + Prometheus + cron 실패 알림 |

## 3. Must 6개 (P0 — 실 서비스 출시 전 필수)

### M1. 실 Stripe 연동 (5~7일)

**범위**:
- `services/payments/stripe_real.py` — `PaymentProvider` 인터페이스 구현 (이미 mock으로 검증된 스펙 그대로)
- `PAYMENT_PROVIDER=stripe` 환경변수 분기
- Stripe Payment Intent / Subscription / Webhook 시그니처 검증 (`stripe.Webhook.construct_event`)
- 환불 처리 (`POST /admin/orders/{id}/refund`)
- 결제 영수증 이메일 발송 (M2와 함께)
- 다중 통화 미적용 (KRW만)

**리스크**:
- Stripe 키 발급 + 비즈니스 검증 + 사업자 등록증 필요
- Webhook URL을 외부에 노출해야 함 (서버 도메인 + HTTPS 필수)

**선행 조건**: 사업자 등록, 도메인 + SSL

**산출물**:
- `services/payments/stripe_real.py`
- `app/api/admin.py`에 refund 엔드포인트
- Stripe Dashboard webhook 설정 가이드 (`docs/runbook/stripe.md`)

---

### M2. JWT Refresh 토큰 회전 + 서버측 무효화 (2일)

**범위**:
- `refresh_tokens` 테이블 신규 (id, user_id, token_hash, family_id, expires_at, revoked_at)
- `/auth/refresh` 호출 시 기존 토큰 → revoked + 새 토큰 발급 (token rotation)
- `/auth/logout`에서 refresh token 명시적 revoke
- 작가 승인 즉시 기존 토큰 무효화 (현재는 만료까지 대기)
- Refresh token 재사용 탐지 시 family 전체 revoke (탈취 대응)

**리스크**: 기존 사용자 강제 재로그인 필요 (마이그레이션 0006)

**산출물**:
- 마이그레이션 0006_auth_refresh_tokens
- `services/auth_tokens.py`
- 보안 이벤트 알림 (탈취 의심 시)

---

### M3. GDPR / 개인정보 보호 (3~4일)

**범위**:
- `users.deleted_at` 컬럼 + 30일 grace period soft delete
- `POST /users/me/delete` (사용자 자체 요청)
- `GET /users/me/export` — JSON 다운로드 (자기 데이터 전체)
- 쿠키 배너 컴포넌트 (`CookieConsent.tsx`)
- `/legal/privacy` + `/legal/terms` 정적 페이지 (한/영)
- `gdpr_consent_at` 필드 활용 (이미 존재) — 가입 시 강제 동의
- 개인정보 처리방침 문서 (법률 자문 후 확정)

**리스크**: 법률 자문 비용 + 시간

**산출물**:
- 마이그레이션 0007_gdpr_soft_delete
- `app/api/me.py` (export, delete)
- `frontend/src/components/CookieConsent.tsx`
- `frontend/src/app/legal/{privacy,terms}/page.tsx`
- `docs/legal/privacy_policy_v1.md`

---

### M4. 미디어 스토리지 S3/Minio 전환 (3일)

**범위**:
- `services/storage/base.py` — `StorageProvider` 인터페이스
- `services/storage/s3.py` (boto3) + `services/storage/minio.py` 옵션
- Presigned URL 업로드 패턴 — 클라이언트가 직접 S3 PUT, 백엔드는 URL만 발급
- `media_assets.url`을 CDN URL로 저장
- 기존 `/v1/media/files/*` 핸들러는 deprecated 표시
- 이미지 EXIF 제거 + 썸네일 생성 (Pillow) → S3에 별도 저장
- Path traversal 자체가 사라짐 (S3 키 기반)

**리스크**: AWS 계정 + S3 버킷 + IAM 정책 + CloudFront 설정 필요

**산출물**:
- 마이그레이션 0008_media_storage_url 컬럼 추가
- `services/storage/`
- 마이그레이션 스크립트: 기존 로컬 파일을 S3로 이전

---

### M5. 미성년자 보호자 동의 플로우 (3~4일)

**범위**:
- 회원가입 시 생년월일 입력 → `is_minor` 자동 계산 (이미 필드 있음)
- 미성년자 가입 → 보호자 이메일 입력 → 보호자에게 magic link 발송
- 보호자가 magic link 클릭 → `artist_profiles.guardian_consent = true`
- 미성년 작가 정산 시 보호자 명의 계좌 필수 (UI 가드)
- 미성년자 경매 입찰 금액 상한 (system_settings로 구성)
- 국가별 연령 기준 적용 (KR 14, US 13, EU 16)
- 보호자가 동의 철회 시 작가 비활성화

**리스크**: 매직 링크 발송 = 이메일 시스템(M2의 영수증과 함께) 필요

**산출물**:
- 마이그레이션 0009_minor_guardian
- `services/guardian.py` — magic link 발급/검증
- `app/api/guardian.py` — 동의 처리 엔드포인트
- 미성년 가입 UI 플로우

---

### M6. Rate Limiting (1~2일)

**범위**:
- `slowapi` 또는 자체 Redis 기반 카운터
- 엔드포인트별 한도:
  - `/auth/sns/*`: 분당 10회 (브루트 포스 방지)
  - `/sponsorships`, `/auctions/{id}/bids`, `/products/{id}/buy-now`: 분당 30회
  - `/reports`: 분당 5회
  - 일반 GET: 분당 120회
- `RATE_LIMITED` 에러 코드 응답 (이미 design.md §3.1에 정의됨)
- IP 기반 + JWT sub 기반 이중 카운팅

**리스크**: 낮음

**산출물**:
- `app/core/rate_limit.py`
- 라우터별 데코레이터 적용
- Redis 키 만료 정책

---

## 4. Must 6개 우선순위 + 일정

| 주차 | 작업 | 사유 |
|------|------|------|
| **Week 15** | M2 (JWT 회전) + M6 (Rate limiting) | 보안 기반 — 다른 작업의 전제 조건 |
| **Week 16** | M1 (실 Stripe) | 비즈니스 핵심 — Stripe 키 발급과 병행 가능 |
| **Week 17** | M4 (S3 스토리지) + M3 (GDPR 절반) | 인프라 + 법적 준수 동시 진행 |
| **Week 18** | M3 (GDPR 완료) + M5 (미성년자) | 컴플라이언스 마무리 |

**총 4주 (Phase 4 Must 범위만)**

병렬 가능한 작업:
- M2 + M6 (보안 페어)
- M3 + M5 (컴플라이언스 페어)

---

## 5. Should 9개 (P1 — Phase 5에서 다룸)

| ID | 항목 | 예상 |
|----|------|:----:|
| S1 | WebSocket 실시간 입찰 (현재 2초 폴링) + auction_ending_soon 알림 | 3~4일 |
| S2 | FCM 웹 푸시 + 이메일 발송 (경고/낙찰/결제 영수증) | 3일 |
| S3 | Posts PATCH/DELETE + 작성자 가드 | 1~2일 |
| S4 | `/users/me PATCH` 프로필 편집 | 1일 |
| S5 | Followers/Following 목록 API + UI | 1일 |
| S6 | 이미지 처리 파이프라인 (썸네일/EXIF/CDN) — M4와 통합 가능 | 2~3일 |
| S7 | Explore/Search 공통 필터 (genre/price/currency/sort 통일) | 1~2일 |
| S8 | Observability — Sentry, Prometheus, cron 실패 알림, 구조화 로깅 | 3일 |
| S9 | DB 인덱스 튜닝 + 멱등성 키 (`Idempotency-Key` 헤더) | 2~3일 |

**총 약 17~22일 (Phase 5, ~4주)**

---

## 6. Could 6개 (P2 — Phase 6 이후 백로그)

| ID | 항목 | 예상 |
|----|------|:----:|
| C1 | 작가 인덱스 점수 시스템 (badge_level 자동 갱신) | 5~7일 |
| C2 | ML 기반 피드 추천 (현재 70/30 → 개인화) | 2~4주 |
| C3 | 다국어 i18n (next-intl, ko/en 기본 + 작품 설명 자동 번역) | 1주 |
| C4 | Stripe Tax + 다중 통화 (KRW/USD) | 1~2주 |
| C5 | 대댓글 (2뎁스 활성화) | 1~2일 |
| C6 | 경매 soft close (마감 1분 전 입찰 시 자동 연장) | 1일 |

---

## 7. 선행 준비 (Phase 4 시작 전 결정 필요)

| 항목 | 상태 | 결정 필요 시점 |
|------|------|----------------|
| 사업자 등록증 + 통신판매업 신고 | ❌ | M1 시작 전 |
| Stripe 계정 (테스트 → 라이브 승격) | ❌ | M1 시작 전 |
| 도메인 + SSL (`*.tuzigroup.com`) | ✅ Plan에 결정됨 | M1 webhook 설정 시 |
| AWS 계정 + S3 버킷 + CloudFront | ❌ | M4 시작 전 |
| 법률 자문 (개인정보, 미성년, 약관) | ❌ | M3, M5 시작 전 |
| 이메일 발송 서비스 (SES, Mailgun, Resend) | ❌ | M2 보호자 동의, 영수증 발송 시 |
| Sentry / Prometheus 구독 | ⚪ Phase 5 | S8 |

**M1, M3, M5는 외부 의존성이 있어 Week 15에 병렬로 의존성 발주를 시작해야 합니다.**

---

## 8. 리스크 매트릭스

| 리스크 | 영향 | 가능성 | 대응 |
|--------|:----:|:------:|------|
| Stripe 비즈니스 검증 지연 (1~3주) | 높음 | 중 | 사업자 등록 + 검증 자료 사전 준비, M2/M6 먼저 |
| 법률 자문 비용/시간 (1~2주) | 중 | 높음 | 약관 템플릿 구매(예: 로앤컴퍼니) + 1회 검토만 |
| S3 마이그레이션 중 기존 데이터 유실 | 높음 | 낮음 | dual-write 기간 + 검증 후 cutover |
| 미성년자 magic link 이메일 발송 실패 | 중 | 중 | 재시도 큐 + 운영자 수동 재발송 |
| Rate limit이 정상 트래픽 차단 | 낮음 | 중 | 처음엔 monitor-only 모드, 1주 관찰 후 강화 |
| Phase 4 일정 지연 (Week 18 초과) | 중 | 중 | M5 → Phase 5로 이관 가능 (해외 진출 전이면 OK) |

---

## 9. Phase 4 완료 정의 (Definition of Done)

- [ ] M1~M6 모두 구현 + E2E 검증
- [ ] 실 Stripe 테스트 결제 성공 1건 + 환불 1건
- [ ] GDPR export 기능으로 자기 데이터 다운로드 가능
- [ ] 미성년자 가입 → 보호자 동의 → 활성화 플로우 통과
- [ ] Rate limit이 정상 트래픽을 차단하지 않음 (1주 관찰)
- [ ] 모든 미디어가 S3로 서빙되며 CDN 캐시 hit > 80%
- [ ] gap-detector로 Phase 4 분석 → 95%+ 매칭 달성
- [ ] 보안 점검 (OWASP Top 10) — 모든 high/critical 항목 해결

---

## 10. 다음 단계

1. **본 Plan 검토 + 우선순위 확정** (고객/스폰서)
2. **외부 의존성 발주 시작** (사업자 등록, Stripe, AWS, 법률 자문)
3. **`/pdca design domo-phase4`** — 실 Stripe + JWT 회전 + S3 등의 상세 설계
4. **Week 15 착수** — M2 + M6 (보안 페어)

---

## 부록 A — Phase 0~3 요약 (Phase 4 진입 시점 상태)

| Phase | 매칭률 | 핵심 산출물 |
|-------|:------:|------------|
| Phase 0 | 100% | Docker, Next.js+Tailwind, FastAPI+SQLAlchemy, JWT mock, 두쫀쿠 |
| Phase 1 | 98% | posts/media/follows/likes/comments, 작가 심사, 디지털 아트 verdict |
| Phase 2 | 97% | 후원/정기/경매/즉시구매/주문/cron, mock Stripe, system_settings |
| Phase 3 | 95% | reports/warnings/이의제기, dashboard/settings, 알림, 미디어 업로드 |
| **종합** | **96%** | E2E 86/86, 시연 시나리오 5/5 |

## 부록 B — 의도적 OOS → Phase 4 매핑

| 프로토타입 OOS | Phase 4 항목 |
|----------------|-------------|
| 실 Stripe | M1 |
| GDPR 실 구현 | M3 |
| 미성년자 보호자 동의 | M5 |
| S3/Minio 미디어 | M4 |
| Rate limiting | M6 |
| JWT 회전 | M2 |
| FCM/이메일 | S2 (Phase 5) |
| WebSocket 실시간 입찰 | S1 (Phase 5) |
| 작가 인덱스 점수 | C1 (Phase 6) |
| ML 추천 | C2 (Phase 6) |
| 다국어 i18n | C3 (Phase 6) |
| Stripe Tax + 다중 통화 | C4 (Phase 6) |
