---
template: plan
version: 1.0
feature: domo-phase12-roadmap
date: 2026-05-08
author: itpe-ince (Claude Sonnet 4.6)
project: domo
project_version: v1
parent_roadmap: Phase 12 (안정성 강화 + Admin 콘솔 완성 + 인증 확장, 옵션 D 균형 진행)
status: Draft (Roadmap)
---

# Domo Phase 12 — 로드맵 (Master Plan)

> **Summary**: Phase 11 종결(7/8 sub-PDCA 완료, 96.9% 가중 Match Rate, 12개 carry-over 식별, 2026-05-08) 후
> 옵션 D(균형 진행, ~10주)로 Wave A/B/C 3단계 진행. Wave A: 안정성 강화(테스트 refactor + ML 실험 제어 API, ~3주).
> Wave B: 조건부 분기(거래 ≥ 100건 시 K-6 AI 가격 추천, 미달 시 admin audit/analytics/payouts UI 3개, ~4주).
> Wave C: 인증 확장 + 단축키 확장(password reset + GitHub OAuth + 단축키 패턴, ~3주).
> 총 7~8 sub-PDCAs, ~10주 예상. alembic 0086~0088 사전 배정.
>
> **Project**: domo (v1)
> **Author**: itpe-ince
> **Date**: 2026-05-08
> **Status**: Roadmap (Sub-PDCA 인덱스. 각 항목은 별도 plan 문서로 본격 진입)

---

## 0. Phase 12 배경 & 전략적 의미

### Phase 11 종결 성과 요약

Phase 11은 Admin 콘솔 UI 4개(A-1 Featured Artist 큐, A-2 AI 컬렉션 큐, B-1 실험 결과, B-2 Diversity 튜닝) + Carry-over 청산 3개(D-1 단축키, D-2 audit_logs DB, D-3 이메일 가입)를 완료했다. 주요 성과:

- **Admin 콘솔 운영 UI 완성**: K-4/K-7 검수 큐 즉시 운영 가능 (수동 DB 조작 → 0건)
- **ML 운영 가시성 확보**: K-8 A/B 결과 + K-2 Diversity 튜닝 Admin에서 직접 조작
- **이메일 가입 추가**: Google OAuth 1종 → 2종 (신흥 시장 접근성 개선)
- **audit_logs DB 구축**: alembic 0084, 운영 이력 추적 시작
- **K-6 정당 이월**: 거래 < 100건(약 30~40건) 조건 미충족
- **12개 carry-over 식별**: 우선도별 Phase 12 배분 완료
- **누적 지표**: Tests 657 → 694 (+37), alembic 0083 → 0085, cron 23 → 24, tsc 0 errors

### Phase 12가 중요한 이유

Phase 11에서 두 가지 중요한 미완성 사항이 식별됐다:

**1. 테스트 안정성 부채**: 17개 over-mocked tests가 skipped 상태로 남아 있다. `freezegun` + `testcontainers` 미도입으로 인한 것으로, 계속 방치하면 CI 신뢰도가 낮아진다.

**2. 인증 플로우 미완성**: D-3에서 이메일+비밀번호 가입을 구현했으나 password reset 플로우가 미구현이다. 사용자가 비밀번호를 잊었을 때 복구 수단이 없다는 UX 치명적 결함이다.

```
[Phase 11 결과]
  D-3 이메일 가입 완성 → password reset 미구현 (로그인 복구 불가)
  17 over-mocked tests skip → CI 신뢰도 저하
  B-1 PATCH endpoint 미구현 → 실험 일시정지 기능 없음
      ↓
[Phase 12 Wave A] 안정성 강화 (tests refactor + B-1 PATCH endpoint)
      ↓ (병행)
[Phase 12 Wave B] Admin 분기 (K-6 조건부 OR admin UI 3개)
      ↓
[Phase 12 Wave C] 인증 완성 + 단축키 확장
```

---

## 1. 비즈니스 컨텍스트

### Phase 11 → Phase 12 전환

Phase 11에서 "운영자가 ML 결과를 보고 조율할 수 있는 Admin 제어판"이 완성됐다. Phase 12는 **플랫폼 신뢰성 완성**(테스트 안정화 + 인증 플로우 완성)과 **거래 데이터 기반 AI 도입**(K-6 가격 추천)이 목표다.

```
Phase 11까지의 Domo: Admin 콘솔 운영 가능, 이메일 가입 가능, 비밀번호 찾기 불가
Phase 12의 Domo: 완전한 인증 플로우(가입→로그인→재설정→OAuth 다양화) + 테스트 신뢰도 회복
```

### Phase 12가 README 비전을 완성하는 이유

| README 비전 | Phase 11 달성 | Phase 12 달성 |
|-------------|:----------:|:----------:|
| **"동유럽이든 남미든 동아시아든 — 꿈과 희망"** | D-3 이메일 가입 추가 ✅ | C-1 password reset → 비밀번호 잊어도 복구 가능 |
| **"유저들이 늘어나야 소비자들도 늘어남"** | B-1 A/B 결과 분석 ✅ | C-2 GitHub OAuth + 매직링크 → 개발자/기술직 사용자 유입 확대 |
| **"신진 작가들의 거래 이루어지면 인덱스 만들고"** | K-4 Featured Artist 검수 큐 ✅ | B-1k K-6 AI 가격 추천(거래 100건+ 시) → 경매 등록 진입 장벽 ↓ |
| **"AI 세상으로 가면 갈수록 예술가들이 제일 먼저 굶어 죽음"** | K-6 이월 준비 중 | B-1k 진입 시: AI 추천가로 적정 reserve_price 안내 → 낙찰률 ↑ |
| **"히스토리를 두세 개 만든다"** | A-2 컬렉션 운영자 편집 ✅ | B-2 admin analytics 대시보드 → 성공 작가 스토리 데이터 기반 발굴 |
| **"컬렉터들한테는 회비 1년에 10분씩"** | A-2 AI 컬렉션 큐 ✅ | B-3 admin payouts → Stripe Connect 정산 관리 → 컬렉터 결제 투명성 ↑ |

---

## 2. Phase 11 결과 → Phase 12 매핑

| Phase 11 carry-over | 우선도 | Phase 12 Wave | sub-PDCA |
|---------------------|:------:|:------------:|:--------:|
| #2: 17 over-mocked tests refactor | Should | Wave A | **A-1** |
| #3: B-1 ML A/B PATCH endpoint (pause/complete) | Should | Wave A | **A-2** |
| #1: K-6 AI 가격 추천 (C-1 이월) | Must (조건부) | Wave B — 거래 ≥ 100건 | **B-1k** |
| #6: admin audit log 조회 UI | Should | Wave B — 거래 < 100건 | **B-1a** |
| #7: /admin/analytics 통합 대시보드 | Should | Wave B — 거래 < 100건 | **B-2** |
| #8: /admin/payouts 정산 관리 UI | Should | Wave B — 거래 < 100건 | **B-3** |
| #4: D-3 password reset 플로우 | Should | Wave C | **C-1** |
| #5: D-3 GitHub OAuth + 매직링크 가입 | Should | Wave C | **C-2** |
| #10: D-1 단축키 확장 (`g h`, `n`, `/` 등) | Should | Wave C | **C-3** |
| #9: /admin/system cron 모니터 | Could | Phase 13 | — |
| #11: audit_logs 파티셔닝 | Could | Phase 13 | — |
| #12: 모바일 Native (iOS/Android) | Should | Phase 13+ | — |

### Phase 11 → Phase 12 주요 전환점

| Phase 11 산출물 | Phase 12 활용 | sub-PDCA |
|----------------|:------------|:--------:|
| D-2 `audit_logs` 테이블 (alembic 0084) + 미들웨어 | B-1a Admin audit log 조회 UI (`/admin/audit-logs`) | B-1a |
| D-3 이메일+비밀번호 가입 (alembic 0085) | C-1 password reset 플로우 (password_reset_tokens 추가) | C-1 |
| D-1 `useGlobalHotkeys` hook + HOTKEY_REGISTRY | C-3 단축키 확장 (`g h`/`n`/`/`/`b`/`Esc` 패턴) | C-3 |
| B-1 `/admin/experiments` 조회 UI (Phase 11) | A-2 PATCH endpoint 추가 → pause/complete 버튼 활성화 | A-2 |
| K-7 `ai_collections`, K-8 `ml_experiments` 통계 | B-2 analytics 대시보드 데이터 소스 | B-2 |
| Phase 9 L-B newsletter + Phase 10 K-8 A/B | B-2 analytics retention + CTR 집계 | B-2 |
| settlement_jobs.py (기존 정산 백엔드) | B-3 admin payouts UI 데이터 소스 | B-3 |

---

## 3. README 비전 직접 매핑

> README 원문 직접 인용 → Phase 12 구현 매핑

| README 원문 | Phase 12 sub-PDCA | 구현 방식 |
|------------|:----------------:|----------|
| **"동유럽이든 남미든 동아시아든 — 꿈과 희망"** | **C-1** | password reset 플로우 구현 → 이메일 가입자 비밀번호 분실 복구 가능 → 글로벌 사용자 이탈 방지 |
| **"유저들이 늘어나야 소비자들도"** | **C-2** | GitHub OAuth + 매직링크 → 개발자/기술 종사자 신규 유입 채널 추가. 매직링크는 비밀번호 없는 가입 |
| **"신진 작가들의 거래 이루어지면 인덱스 만들고"** | **B-1k** | AI 가격 추천으로 reserve_price 진입 불안 해소 → 경매 등록률 ↑ → 낙찰 건수 ↑ → 인덱스 정교화 |
| **"AI 세상으로 가면 갈수록 예술가들이 제일 먼저 굶어 죽음"** | **B-1k** | AI 추천가로 적정 경매가 안내 → 낙찰률 ↑ → 작가 수익 |
| **"히스토리를 두세 개 만든다"** | **B-2** | analytics 대시보드 → 성공 작가 지표 데이터 → 언론 보도 가능한 수치 확보 |
| **"컬렉터들한테는 회비 1년에 10분씩"** | **B-3** | Stripe Connect 정산 대시보드 → 작가 정산 투명성 ↑ → 컬렉터 신뢰도 향상 |
| **"그로스해킹인가 이런 분석법 — 깔대기 모양"** | **B-2** | analytics 코호트 retention + CTR 퍼널 → 사용자 증가 병목 식별 → 그로스 실험 방향 결정 |

---

## 4. Sub-PDCA 상세 (7~8개, Wave A/B/C)

---

### Wave A — 안정성 강화 (~3주, 즉시 진입, 2 agents 병렬)

Phase 11에서 발생한 기술 부채(over-mocked tests + PATCH endpoint 미구현)를 즉시 청산한다. 거래 카운트 확인과 무관하게 Day 0부터 진입한다.

---

#### A-1: testing-stability-refactor (17 over-mocked tests → freezegun + testcontainers)

**Feature ID**: `testing-stability-refactor`
**우선순위**: Should (CI 신뢰도 직결)
**Wave**: Wave A (즉시 진입)
**예상 기간**: ~10일
**의존성**: 없음 (독립)
**alembic**: 없음 (테스트 코드만 변경)
**담당 agent**: bkend-expert

**Goal**

Phase 11에서 over-mocked으로 skip된 17개 테스트를 실제 테스트 환경 기반으로 refactor한다. `freezegun`(시간 기반 픽스처)과 `testcontainers`(PostgreSQL + Redis 통합 컨테이너)를 도입해 CI에서 실제 DB와 시간 조건을 사용한 통합 테스트로 전환한다.

**대상 카테고리 및 전환 전략**

| 카테고리 | 개수 | 현재 문제 | 전환 방법 |
|----------|:---:|----------|----------|
| `audit_log_cleanup` 시간 mock | 3 | `datetime.now()` 하드 mock → 시간 흐름 미검증 | `freezegun.freeze_time()` 도입 |
| `admin_audit_integration` | 4 | before/after JSONB 실제 DB 비교 불가 | testcontainers PostgreSQL 픽스처 |
| `ai_collections week_start` | 2 | 주차 기반 필터링 시간 검증 불가 | `freezegun` + 실제 쿼리 검증 |
| `auth_email_password SES` | 3 | SES mock 불완전 → 실제 메일 발송 미검증 | LocalStack SES 또는 SMTP stub (OQ-2 권장: testcontainers) |
| 기타 (UI mock, WebSocket stub) | 5 | 실제 컨넥션 미검증 | 픽스처 전환 + integration 패턴 통일 |

**Scope**

- `pytest.ini` 또는 `conftest.py`에 `testcontainers` PostgreSQL + Redis fixture 등록
  - `@pytest.fixture(scope="session")` 세션 단위 컨테이너 (빌드 시간 최소화)
  - `alembic upgrade head`를 test 컨테이너 DB에 자동 적용
- `freezegun` 의존성 추가: `requirements-test.txt`에 `freezegun>=1.4.0`
- 4개 카테고리 17개 테스트 각각 refactor:
  - `@freeze_time("2026-05-08 00:00:00")` 데코레이터 적용
  - `@pytest.mark.integration` 마킹으로 unit test와 분리
  - skip 마커 제거 (`@pytest.mark.skip` 삭제)
- CI (GitHub Actions) `pytest.yml` 업데이트:
  - testcontainers 실행 위해 `docker` 서비스 활성화 확인
  - `--run-integration` flag 또는 `PYTEST_INTEGRATION=1` env로 선택적 실행
- 목표: 17 skipped → 0 skipped (또는 < 5 — 불가피한 경우만 주석 필수)

**Acceptance Criteria**

- [ ] `testcontainers` PostgreSQL fixture 설정 확인 (`conftest.py` session scope)
- [ ] `freezegun` 패키지 `requirements-test.txt` 추가 확인
- [ ] `audit_log_cleanup` 3개 테스트: freeze_time → cron 로직 정상 동작 확인
- [ ] `admin_audit_integration` 4개 테스트: 실제 DB JSONB before/after 비교 확인
- [ ] `ai_collections week_start` 2개 테스트: 주차 필터링 시간 검증 확인
- [ ] `auth_email_password SES` 3개 테스트: LocalStack 또는 stub으로 메일 발송 확인
- [ ] 17 → 0 skipped (또는 < 5) 확인
- [ ] 전체 테스트 회귀 0건 확인
- [ ] CI `pytest.yml` testcontainers docker 실행 확인

**Risks**

| 리스크 | 영향 | 대응 |
|--------|:----:|------|
| testcontainers CI 빌드 시간 증가 | 중간 | session-scope fixture로 컨테이너 1회 시작 (테스트별 재시작 금지) |
| LocalStack SES 복잡도 | 중간 | OQ-2 권장: SMTP LocalStack 대신 in-memory stub 우선 (실제 SES는 E2E에서만) |
| alembic 마이그레이션과 test DB 불일치 | 높음 | fixture에서 `alembic upgrade head` 자동 실행 |

**KPIs**

- 17 skipped tests → 0 (또는 < 5)
- CI 통합 테스트 pass rate: 100%
- 전체 테스트 회귀: 0건

---

#### A-2: ml-experiment-control-api (B-1 PATCH endpoint 보완)

**Feature ID**: `ml-experiment-control-api`
**우선순위**: Should
**Wave**: Wave A (A-1과 병렬)
**예상 기간**: ~7일
**의존성**: Phase 11 B-1 `/admin/experiments` UI (완성), `ml_experiments` 테이블 (alembic 0080)
**alembic**: 없음 (기존 `ml_experiments` 테이블 status 컬럼 확장만)
**담당 agent**: bkend-expert + frontend-architect

**Goal**

Phase 11 B-1에서 `/admin/experiments` 조회 UI를 구현했으나 실험 제어(pause/complete) PATCH endpoint를 미구현했다. 이를 보완해 운영자가 Admin 콘솔에서 실험을 일시정지하고 종료할 수 있게 한다.

**Scope**

- **백엔드 신규 endpoint 2개**:
  - `PATCH /admin/experiments/{name}/pause` → status `running` → `paused`
  - `PATCH /admin/experiments/{name}/complete` → status → `completed`
  - 요청 body: `{ reason?: string }` (audit_log에 기록)
  - `require_admin_with_2fa` 의존성 적용 (OQ-3 권장)
  - audit_log 기록: `action="experiment.pause"` / `"experiment.complete"`
- **status enum 정리** (`ml_experiments.status`):
  - `draft` / `running` / `paused` / `completed` (Phase 11에서 draft/running/completed 3종, paused 추가)
  - alembic 없음: status는 VARCHAR — 애플리케이션 레벨에서 허용 값 제한
- **프론트엔드 활성화**:
  - Phase 11 B-1에서 disabled tooltip으로 비활성화된 "일시정지" / "종료" 버튼 활성화
  - 버튼 클릭 → confirm dialog("이 실험을 일시정지하시겠습니까?") → PATCH 호출
  - status 변경 후 목록 자동 갱신
- **i18n**: 5 locale 키 `admin.experiments.pause.*` / `admin.experiments.complete.*` (5~8개)
- **unit tests**: `test_experiment_control.py` (pause → status 변경 확인 + audit 로그 기록 확인)

**Acceptance Criteria**

- [ ] `PATCH /admin/experiments/{name}/pause` → status `paused` 변경 확인
- [ ] `PATCH /admin/experiments/{name}/complete` → status `completed` 변경 확인
- [ ] audit_log `experiment.pause` / `experiment.complete` 기록 확인
- [ ] 프론트엔드 비활성화 버튼 → 활성화 + confirm dialog 동작 확인
- [ ] 2FA 없는 admin 호출 시 403 `SECOND_FACTOR_REQUIRED` 확인
- [ ] 5 locale i18n 키 표시 확인
- [ ] tsc 0 errors
- [ ] unit tests: `test_experiment_control.py` (2개 endpoint × 정상/에러)

**Risks**

| 리스크 | 영향 | 대응 |
|--------|:----:|------|
| paused 실험의 PostHog Feature Flag 연동 누락 | 중간 | PATCH 호출 시 PostHog API에 flag disable 연동 (OQ-3 권장) |
| 이미 completed인 실험에 pause 시도 | 낮음 | HTTP 409 `EXPERIMENT_ALREADY_COMPLETED` 반환 |

**KPIs**

- Phase 11 B-1 matchRate 88% → 95%+ 상승 (pause/resume 보완)
- 실험 제어 Admin 콘솔에서 30초 이내 완료 (조회 + 버튼 1클릭)

---

### Wave B — Admin 콘솔 또는 K-6 (조건부 분기, ~4주)

**Day 0 사전 확인 (필수)**:

```sql
SELECT COUNT(*) FROM auctions WHERE status = 'sold';
```

| 결과 | 진입 경로 | sub-PDCA |
|:----:|:--------:|:--------:|
| **≥ 100건** | B-1k (K-6 AI 가격 추천) | 1개 |
| **< 100건** | B-1a + B-2 + B-3 (admin UI 3개) | 3개 (가능성 높음) |

> Phase 11 report 기준 거래 약 30~40건. 거래 < 100건 시나리오가 더 가능성 높다.

---

#### 옵션 B-K6: B-1k — ai-price-recommendation (K-6 AI 가격 추천, 거래 ≥ 100건 시)

**Feature ID**: `ai-price-recommendation`
**우선순위**: Must (조건부 — 거래 100건 미달 시 Phase 13 이월)
**Wave**: Wave B (거래 ≥ 100건 충족 시 즉시 진입)
**예상 기간**: ~14일
**진입 조건**: `SELECT COUNT(*) FROM auctions WHERE status = 'sold'` ≥ 100건
**의존성**: Phase 9 L-A `post_embeddings` pgvector, Phase 5 경매 DB, K-1 ML 스코어
**alembic**: **0086** (B-1k 진입 시)
**담당 agent**: bkend-expert + frontend-architect

**Goal**

작가가 경매를 등록할 때 reserve_price(최저 낙찰가)를 설정하기 어려운 문제를 해결한다. 유사 작품 임베딩 + 과거 낙찰가 중앙값 + 작가 작품 평균가 가중 방식으로 추천 범위(min~max)를 제공한다. Phase 10 및 Phase 11에서 거래 100건 미달로 연속 이월된 항목이다.

**Scope**

- **진입 전 조건 확인 (OQ-1 권장: Day 0 즉시 SQL 확인)**:
  - `SELECT COUNT(*) FROM auctions WHERE status = 'sold'` ≥ 100건 충족 시만 진입
  - 미달 시: Phase 13 이월, B-Admin 경로로 즉시 전환
- **alembic 0086**: `posts` 테이블 확장 또는 별도 추천 로그 테이블
  - `post.recommended_price NUMERIC(12, 2)` (작가 설정 시 참고용)
  - `post.recommendation_metadata JSONB` (추천 근거: 유사 작품 IDs, 신뢰구간, 알고리즘 버전)
- **가격 추천 알고리즘 (OQ-4 권장: 단순 비교 평균가 + 가중)**:
  - 유사 작품 탐색: `post_embeddings` pgvector cosine 유사도 top-5
  - 계산식: `0.4 × 유사작품낙찰가중앙값 + 0.6 × 작가작품평균가`
  - 장르별 시장 배수: 유화 1.8×, 수채화 1.2×, 디지털 아트 0.9×, 기타 1.0×
  - 추천 범위: `[중앙값 × 0.8, 중앙값 × 1.3]` (80% 신뢰구간)
  - Fallback (장르 거래 < 5건): 장르 배수만 사용 (pgvector 탐색 생략)
  - ML 회귀 모델: Phase 13 검토 (OQ-4 권장)
- **API**:
  - `POST /auctions/price-recommend` (작품 ID + 장르 + 재료 → 추천 범위 반환, 2초 이내)
  - 응답: `{ recommended_min, recommended_max, similar_auctions_count, confidence_level }`
  - PostHog 이벤트: `auction_price_recommended`, `auction_price_applied`
  - audit_log 기록: `action="auction.price_recommended"`
- **경매 등록 UI**:
  - reserve_price 입력 필드 옆 "AI 가격 추천" 버튼
  - 추천 범위 + 근거("유사 작품 N개 평균 낙찰가 기준") 표시
  - "추천가 적용" 버튼으로 자동 입력
  - 면책 문구 5 locale: "이 추천은 참고용이며 실제 낙찰가를 보장하지 않습니다"
- **작가 등록 시 자동 추천**: 경매 등록 폼 진입 시 자동으로 추천 API 호출

**Acceptance Criteria**

- [ ] 진입 조건(거래 ≥ 100건) 충족 확인 후 진행
- [ ] alembic 0086 적용 후 `recommended_price` / `recommendation_metadata` 컬럼 확인
- [ ] `POST /auctions/price-recommend` → 추천 범위 반환 2초 이내
- [ ] 유사 작품 pgvector cosine 유사도 top-5 탐색 확인
- [ ] 장르별 배수 적용 확인 (유화/수채화/디지털/기타)
- [ ] Fallback (거래 < 5건 장르) 동작 확인
- [ ] 경매 등록 UI 추천 적용 버튼 → reserve_price 자동 입력 확인
- [ ] 면책 문구 5 locale 표시 확인
- [ ] PostHog `auction_price_recommended` 이벤트 로깅 확인
- [ ] audit_log 기록 확인
- [ ] unit tests: `test_price_recommendation.py`

**Risks**

| 리스크 | 영향 | 대응 |
|--------|:----:|------|
| 거래 데이터 100건 미달 지속 | 높음 | OQ-1: Day 0 즉시 SQL 확인 후 미달 시 B-Admin으로 전환 |
| 낮은 추천가 → 작가 수익 저해 | 중간 | "적정 범위" 명시 + 최저가가 아님 UI 강조 + 추천 후 자유 입력 허용 |
| 가격 앵커링 효과 (추천가 고착) | 중간 | 추천 ≠ 강제, 사용자 입력 우선 |

**KPIs**

- 가격 추천 사용률: 경매 등록 시 ≥ 50%
- 추천가 적용률: ≥ 30%
- 낙찰 성공률 baseline: Phase 12 측정 시작

---

#### 옵션 B-Admin: B-1a — admin-audit-log-ui (거래 < 100건 시, 예상 경로)

**Feature ID**: `admin-audit-log-ui`
**우선순위**: Should
**Wave**: Wave B (거래 < 100건 시 즉시 진입)
**예상 기간**: ~10일
**의존성**: Phase 11 D-2 `audit_logs` 테이블 (alembic 0084) + middleware 완성
**alembic**: 없음 (D-2에서 테이블 완성, 조회 전용)
**담당 agent**: frontend-architect

**Goal**

Phase 11 D-2에서 `audit_logs` 테이블과 middleware를 구축했으나 운영자가 Admin 콘솔에서 감사 기록을 조회할 수 있는 UI가 없다. `/admin/audit-logs` 페이지를 신규 구현해 admin 액션 이력 추적을 운영자 손에 쥐어준다.

**Scope**

- **Admin 콘솔 신규 페이지**: `/admin/audit-logs`
  - `GET /admin/audit-logs` 신규 백엔드 endpoint (cursor-based 페이지네이션, OQ-9 권장: 50건/페이지)
  - 목록 테이블: actor(이름+이메일), action, target_type, target_id, ip_address, created_at
  - 상세 보기: before_data / after_data JSONB diff 표시 (민감 필드 마스킹 유지)
- **필터 (OQ-9 권장)**:
  - actor (이름 또는 이메일 검색)
  - action (드롭다운: 전체 / user.suspend / post.delete / featured.approve / 등)
  - target_type (전체 / user / post / auction / featured_artist / collection)
  - period (오늘 / 7일 / 30일 / 사용자 지정)
- **cursor-based 페이지네이션**: `?cursor=<id>&limit=50` (id DESC 기준)
- **AdminShell 메뉴**: "Security" 또는 "Operations" 그룹에 `/admin/audit-logs` 추가
- **i18n**: 5 locale 키 `admin.audit_logs.*` (10~15개)
- **백엔드 endpoint**: `GET /admin/audit-logs` + `GET /admin/audit-logs/{id}` (상세)
  - `require_admin_with_2fa` 적용
  - 인덱스 활용: `actor_id`, `action`, `target_type+target_id`, `created_at DESC`

**Acceptance Criteria**

- [ ] `GET /admin/audit-logs` endpoint → 50건/페이지 cursor-based 목록 반환 확인
- [ ] actor / action / target_type / period 필터 동작 확인
- [ ] before_data / after_data JSONB diff 표시 확인 (password_hash 마스킹 확인)
- [ ] `/admin/audit-logs/{id}` 상세 페이지 확인
- [ ] AdminShell 메뉴 항목 추가 확인
- [ ] 5 locale i18n 키 표시 확인
- [ ] tsc 0 errors
- [ ] unit tests: `test_audit_log_query.py`

**Risks**

| 리스크 | 영향 | 대응 |
|--------|:----:|------|
| audit_logs 데이터 증가로 쿼리 느려짐 | 낮음 | created_at DESC 인덱스 활용 + cursor 기반으로 OFFSET 회피 |
| before/after JSONB 크기 폭증 시 UI 렌더링 | 낮음 | 펼치기/접기 UI + 최대 5KB 이상 시 "원본 보기" 버튼 |

**KPIs**

- audit_logs 조회 응답: ≤ 100ms (인덱스 기준)
- 필터 동작 정확도: 100%

---

#### 옵션 B-Admin: B-2 — admin-analytics-dashboard (거래 < 100건 시)

**Feature ID**: `admin-analytics-dashboard`
**우선순위**: Should
**Wave**: Wave B (B-1a와 병렬)
**예상 기간**: ~14일
**의존성**: Phase 8 G''-4 코호트 retention, Phase 9 L-B newsletter open rate, Phase 9 K-1 + Phase 10 K-8 feed CTR
**alembic**: 없음 (기존 통계 테이블 집계)
**담당 agent**: frontend-architect + bkend-expert

**Goal**

Plan §10에서 식별된 `/admin/analytics` 통합 대시보드를 구현한다. 코호트 retention, newsletter open rate, feed CTR, PostHog 임베드를 한 화면에서 확인해 그로스 해킹 의사결정을 지원한다.

**Scope**

- **Admin 콘솔 신규 페이지**: `/admin/analytics`
- **데이터 섹션 4개**:
  1. **코호트 Retention** (Phase 8 G''-4 활용):
     - 가입 코호트별 30일/60일/90일 잔존율 표 (가로: 코호트 주, 세로: 경과 주)
     - `GET /admin/analytics/cohort-retention?weeks=12` 백엔드 endpoint
  2. **Newsletter open rate** (Phase 9 L-B 활용):
     - 주간 발송량, 오픈율, 클릭율 차트 (최근 12주)
     - `GET /admin/analytics/newsletter-stats?weeks=12`
  3. **Feed CTR** (K-1 + K-8 활용):
     - v1 vs v2 알고리즘 CTR 비교 (A/B 결과 요약)
     - `GET /admin/analytics/feed-ctr`
  4. **PostHog Insights 임베드** (OQ-10 권장: 5분 캐시):
     - PostHog 대시보드 임베드 iframe (신규 사용자 / DAU / 이벤트별 추세)
     - API_KEY 미설정 시 mock 비활성화 fallback
- **새로고침 주기** (OQ-10 권장: Redis 5분 캐시):
  - 각 endpoint 응답을 Redis `CACHE_TTL=300` 캐싱
  - 캐시 수동 갱신 버튼 ("지금 새로고침")
- **AdminShell 메뉴**: "Analytics" 신규 그룹 또는 기존 그룹에 추가
- **i18n**: 5 locale 키 `admin.analytics.*` (15~20개)

**Acceptance Criteria**

- [ ] `/admin/analytics` 코호트 retention 표 표시 확인
- [ ] newsletter open rate / click rate 차트 표시 확인
- [ ] feed CTR v1 vs v2 비교 표시 확인
- [ ] PostHog 임베드 또는 fallback 표시 확인
- [ ] Redis 5분 캐시 → TTL 이후 갱신 확인
- [ ] 수동 새로고침 버튼 동작 확인
- [ ] AdminShell 메뉴 추가 확인
- [ ] 5 locale i18n 키 확인
- [ ] tsc 0 errors

**Risks**

| 리스크 | 영향 | 대응 |
|--------|:----:|------|
| 코호트 쿼리 성능 (대용량 집계) | 중간 | 야간 cron pre-compute + 캐시 저장 패턴 (실시간 집계 금지) |
| PostHog CSP 제한 | 중간 | iframe 차단 시 PostHog API 직접 fetch + 자체 차트 렌더링 fallback |
| newsletter 통계 테이블 부재 | 낮음 | Phase 9 L-B 통계 집계 쿼리 확인 후 진입 (사전 검증 필요) |

**KPIs**

- analytics 대시보드 로드 시간: < 3초 (캐시 적중 시)
- 코호트 retention 12주 데이터 정확도: 100%

---

#### 옵션 B-Admin: B-3 — admin-payouts-management (거래 < 100건 시)

**Feature ID**: `admin-payouts-management`
**우선순위**: Should
**Wave**: Wave B (B-1a / B-2와 병렬 가능)
**예상 기간**: ~10일
**의존성**: `settlement_jobs.py` 기존 정산 백엔드, Stripe Connect 통합
**alembic**: 없음 (기존 정산 테이블 활용)
**담당 agent**: bkend-expert + frontend-architect

**Goal**

Stripe Connect 기반 정산 관리 UI를 Admin 콘솔에 추가한다. 운영자가 정산 이력을 조회하고, KYC 검수 큐를 처리할 수 있게 한다.

**Scope**

- **Admin 콘솔 신규 페이지**: `/admin/payouts`
- **정산 이력 조회**:
  - `GET /admin/payouts` → 정산 내역 목록 (artist, amount, status, created_at)
  - 필터: status(pending/processing/paid/failed), period, artist
  - cursor-based 페이지네이션 (50건/페이지)
- **KYC 검수 큐**:
  - KYC 미완료 작가 목록 → Stripe Connect 계정 링크 재발송 버튼
  - KYC 완료 / 실패 상태 표시
- **정산 실행 제어** (OQ-11 권장: auto-publish OFF):
  - "수동 정산 실행" 버튼 → confirm dialog → `POST /admin/payouts/trigger`
  - 자동 정산 비활성 (운영자 명시 승인 필수)
- **백엔드 endpoints**:
  - `GET /admin/payouts` (목록 + 필터)
  - `GET /admin/payouts/{id}` (상세)
  - `POST /admin/payouts/trigger` (수동 정산 실행, `require_admin_with_2fa`)
  - `POST /admin/payouts/kyc-link/resend` (KYC 링크 재발송)
  - audit_log 기록: `action="payout.triggered"`, `action="payout.kyc_resent"`
- **AdminShell 메뉴**: "Operations" 그룹 또는 "Finance" 신규 그룹
- **i18n**: 5 locale 키 `admin.payouts.*` (10~15개)

**Acceptance Criteria**

- [ ] `/admin/payouts` 정산 이력 목록 표시 확인
- [ ] status / period / artist 필터 동작 확인
- [ ] KYC 검수 큐 미완료 목록 표시 확인
- [ ] KYC 링크 재발송 동작 확인
- [ ] 수동 정산 실행 → confirm → `POST /admin/payouts/trigger` 확인
- [ ] auto-publish OFF 확인 (자동 실행 없음)
- [ ] audit_log 기록 확인
- [ ] AdminShell 메뉴 추가 확인
- [ ] 5 locale i18n 키 확인
- [ ] tsc 0 errors

**Risks**

| 리스크 | 영향 | 대응 |
|--------|:----:|------|
| settlement_jobs.py 백엔드 완성도 불명확 | 높음 | Phase 12 Wave B 진입 전 settlement_jobs.py 상태 확인 (사전 검증 OQ-11 참고) |
| Stripe Connect API 변경 | 낮음 | Stripe API version 고정 (`2024-06-20` 이상 권장) |
| 정산 수동 실행 오남용 | 높음 | 2FA 필수 + audit_log + confirm dialog 3중 안전장치 |

**KPIs**

- 정산 이력 조회 응답: ≤ 200ms
- KYC 검수 큐 처리 리드타임: admin UI에서 2분 이내

---

### Wave C — 인증 완성 + 단축키 확장 (~3주, Wave B 완료 후 또는 병행)

Phase 11 D-3의 미완성 항목(password reset, GitHub OAuth)을 마무리하고, D-1 기반 단축키를 확장한다. Wave B와 부분 병행 가능 (C-3은 독립).

---

#### C-1: password-reset-flow (D-3 password reset 완성)

**Feature ID**: `password-reset-flow`
**우선순위**: Should (D-3 인증 플로우 완성에 필수)
**Wave**: Wave C (Wave B 완료 후 또는 B 후반부와 병행)
**예상 기간**: ~7일
**의존성**: Phase 11 D-3 이메일+비밀번호 가입 (alembic 0085, ✅ 완성)
**alembic**: **0086** (B-1k 미진입 시) 또는 **0087** (B-1k 진입 시, 번호 조정)
**담당 agent**: bkend-expert + frontend-architect

**Goal**

Phase 11 D-3에서 이메일+비밀번호 가입을 구현했으나 password reset 플로우가 미구현이다. 사용자가 비밀번호를 잊었을 때 복구할 방법이 없다는 치명적 UX 결함을 해소한다.

**Scope**

- **alembic 0086 (또는 0087)**: `password_reset_tokens` 테이블 신규
  ```sql
  password_reset_tokens(
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER REFERENCES users(id) ON DELETE CASCADE,
    token       VARCHAR(64) UNIQUE NOT NULL,  -- crypto.random_bytes(32).hex()
    ip_address  INET,
    used_at     TIMESTAMPTZ,                  -- NULL = 미사용, NOT NULL = 사용됨
    expires_at  TIMESTAMPTZ NOT NULL,         -- OQ-5 권장: 1시간
    created_at  TIMESTAMPTZ DEFAULT NOW()
  )
  ```
  - 인덱스: `token`, `user_id + expires_at`
  - 1회용 + 만료 시간(OQ-5 권장: 1시간) + IP 기록(OQ-8 권장 적용)
- **백엔드 API 2개**:
  - `POST /auth/password/reset-request` → `{ email }` → 토큰 생성 + SES 재설정 메일 발송
    - 존재하지 않는 이메일도 200 반환 (이메일 존재 여부 노출 방지)
    - 동일 이메일 재요청: 기존 토큰 무효화 + 신규 토큰 발급
    - audit_log: `action="password.reset_requested"`
  - `POST /auth/password/reset` → `{ token, new_password }` → 토큰 검증 + 비밀번호 변경
    - 만료 토큰: HTTP 400 `TOKEN_EXPIRED`
    - 사용된 토큰: HTTP 400 `TOKEN_ALREADY_USED`
    - 새 비밀번호 정책: D-3와 동일 (8자+ 3종 이상)
    - 변경 후 `used_at` 기록 + 기존 refresh token 전체 무효화
    - audit_log: `action="password.reset_completed"`
- **프론트엔드**:
  - LoginModal에 "비밀번호를 잊으셨나요?" 링크 활성화 → `/auth/forgot-password` 페이지
  - 재설정 요청 페이지: 이메일 입력 + 발송 완료 안내
  - 재설정 완료 페이지: `/auth/reset-password?token={token}` → 새 비밀번호 입력 2회
  - 토큰 만료/사용됨: 에러 메시지 + "재요청" 링크
- **이메일 템플릿**: 5 locale 비밀번호 재설정 메일
- **i18n**: 5 locale 키 `auth.password_reset.*` (10~15개)

**Acceptance Criteria**

- [ ] alembic 0086(또는 0087) 적용 후 `password_reset_tokens` 테이블 확인
- [ ] `POST /auth/password/reset-request` → 메일 발송 확인 (존재하지 않는 이메일도 200 확인)
- [ ] `POST /auth/password/reset` → 비밀번호 변경 + refresh token 전체 무효화 확인
- [ ] 만료 토큰 → 400 `TOKEN_EXPIRED` 확인
- [ ] 사용된 토큰 → 400 `TOKEN_ALREADY_USED` 확인
- [ ] 1시간 만료 동작 확인 (freezegun 활용 테스트)
- [ ] LoginModal "비밀번호를 잊으셨나요?" 링크 활성화 확인
- [ ] 5 locale i18n 키 확인
- [ ] audit_log `password.reset_requested` / `password.reset_completed` 확인
- [ ] unit tests: `test_password_reset.py` + integration: `test_auth_reset_flow.py`

**Risks**

| 리스크 | 영향 | 대응 |
|--------|:----:|------|
| 토큰 brute-force 공격 | 높음 | 64자 crypto 랜덤 토큰 + 1시간 만료 + 1회용 (OQ-5/OQ-8 권장) |
| 동일 이메일 연속 재설정 요청 남용 | 중간 | 5분 cooldown (기존 토큰 만료 전 재발급 제한) |
| Google OAuth 가입자에게 reset 노출 | 낮음 | `password_hash IS NULL` 사용자는 요청 시 안내 메시지 반환 |

**KPIs**

- password reset 완료율: ≥ 70% (요청 → 메일 클릭 → 변경 완료)
- 재설정 메일 발송 성공율: ≥ 95%
- D-3 이메일 가입 플로우 완성도: reset 포함 시 100%

---

#### C-2: signup-diversification (GitHub OAuth + 매직링크 가입)

**Feature ID**: `signup-diversification`
**우선순위**: Should
**Wave**: Wave C (C-1 완료 후 또는 병행)
**예상 기간**: ~10일
**의존성**: Phase 11 D-3 이메일+비밀번호 가입 (alembic 0085), 기존 Google OAuth 패턴
**alembic**: 없음 (alembic 0085 `users` 테이블 기존 컬럼으로 충분)
**담당 agent**: bkend-expert + frontend-architect

**Goal**

Phase 11 D-3 OQ-5에서 Phase 12로 이월한 GitHub OAuth와 매직링크 가입을 구현한다. LoginModal에 Google + 이메일/비번 + GitHub + 매직링크 4가지 옵션을 통합 표시한다.

**Scope**

- **GitHub OAuth** (`POST /auth/sns/github`):
  - 기존 Google OAuth 패턴 준용 (`app/api/auth.py` SNS 섹션)
  - GitHub App OAuth scope (OQ-6 권장: `read:user + user:email` 최소 권한)
  - GitHub 계정 이메일과 기존 계정(Google/이메일) 중복 처리: 409 + 통합 안내
  - `users` 테이블: `github_id BIGINT` 컬럼 (alembic 없이 기존 `sns_accounts` 테이블 활용 — 사전 확인 필요)
  - audit_log: `action="auth.github_signup"` / `"auth.github_login"`
- **매직링크 가입** (`POST /auth/magic-link/request`):
  - 이메일만 입력 → 매직링크 메일 발송 → 클릭 → 자동 가입 + JWT 발급
  - `password_reset_tokens`와 유사한 `magic_link_tokens` 테이블 (또는 공용화):
    - 만료 (OQ-8 권장: 24시간)
    - 1회용 + IP 검증 (OQ-8)
  - 가입 완료 후 온보딩 마법사 진입 (기존 Google OAuth 패턴과 동일)
  - 비밀번호 없음 → 추후 설정 가능 (`/settings/security`에서 비밀번호 설정)
- **LoginModal 통합**:
  - 4가지 옵션 표시: Google / GitHub / 이메일+비번 / 매직링크
  - 매직링크: "이메일만으로 간편 가입" 설명 문구
  - 5 locale i18n 키: `auth.github.*`, `auth.magic_link.*`
- **alembic**: `magic_link_tokens` 테이블이 필요하면 0087(또는 0088) — 사전 검토 후 결정

**Acceptance Criteria**

- [ ] GitHub OAuth 로그인 플로우 end-to-end 확인 (redirect → callback → JWT)
- [ ] GitHub 이메일 중복 → 409 + 통합 안내 확인
- [ ] 매직링크 요청 → 메일 발송 확인
- [ ] 매직링크 클릭 → 자동 가입 + JWT 확인
- [ ] 24시간 만료 + 1회용 확인 (freezegun 활용)
- [ ] LoginModal 4 옵션 통합 표시 확인
- [ ] 5 locale i18n 키 확인
- [ ] audit_log `auth.github_signup` / `auth.magic_link_signup` 확인
- [ ] tsc 0 errors
- [ ] unit tests: `test_github_oauth.py` + `test_magic_link.py`

**Risks**

| 리스크 | 영향 | 대응 |
|--------|:----:|------|
| GitHub OAuth 개인정보 수집 범위 | 높음 | OQ-6 권장: `read:user + user:email` 최소 scope 준수 |
| 매직링크 24h 만료 + IP 검증 복잡도 | 중간 | IP 검증은 optional (동일 네트워크 변경 등으로 실패 가능), 경고만 표시 |
| sns_accounts 테이블 미존재 시 alembic 필요 | 높음 | Wave C 진입 전 `app/models/user.py` sns_accounts 현황 사전 확인 |

**KPIs**

- GitHub OAuth 가입 완료율: ≥ 80%
- 매직링크 클릭률: ≥ 60% (발송 → 클릭)
- 가입 방법 종류: 4종 (Google + 이메일 + GitHub + 매직링크)

---

#### C-3: hotkeys-expansion (D-1 단축키 확장)

**Feature ID**: `hotkeys-expansion`
**우선순위**: Should
**Wave**: Wave C (독립 — B 또는 C와 병행 가능)
**예상 기간**: ~7일
**의존성**: Phase 11 D-1 `useGlobalHotkeys` hook + `HOTKEY_REGISTRY` (✅ 완성)
**alembic**: 없음
**담당 agent**: frontend-architect

**Goal**

Phase 11 D-1에서 구현한 `useGlobalHotkeys` hook과 `HOTKEY_REGISTRY` 확장 구조를 활용해 navigation 단축키 세트와 editor/interaction 단축키를 추가한다.

**Scope**

- **신규 단축키 — Navigation (g 시퀀스)** (OQ-12 권장: 4카테고리 중 navigation):

  | 단축키 | 동작 |
  |--------|------|
  | `g h` | 홈(/) 으로 이동 |
  | `g f` | 피드(/feed) 으로 이동 |
  | `g e` | 탐색(/explore) 으로 이동 |
  | `g m` | 메시지(/messages) 으로 이동 |
  | `g n` | 알림(/notifications) 으로 이동 |
  | `g p` | 내 프로필(/profile) 으로 이동 |

- **신규 단축키 — Actions**:

  | 단축키 | 동작 |
  |--------|------|
  | `n` | 새 포스트 작성 (PostEditor 열기) |
  | `/` | 검색창 포커스 (SearchBar focus) |
  | `b` | 현재 포스트 북마크 토글 |
  | `Esc` | 현재 열린 모달/패널 닫기 (FocusManager와 우선순위 정의) |

- **충돌 방지** (OQ-7 권장):
  - input/textarea/contenteditable 포커스 시 자동 비활성 (D-1 패턴 동일)
  - `g h` 시퀀스: 300ms 이내 두 번째 키 입력 대기 (timeout 후 리셋)
  - `b` (북마크): 포스트 포커스 상태일 때만 활성
- **도움말 모달 카테고리 확장** (OQ-12 권장: 4개):
  - `navigation` / `editor` / `general` / `admin` 카테고리
  - `HOTKEY_REGISTRY` 각 항목에 `category` 필드 추가
  - 도움말 모달: 카테고리별 탭 또는 섹션 구분
- **i18n**: 5 locale 키 `hotkeys.navigation.*` / `hotkeys.actions.*` (10~15개)

**Acceptance Criteria**

- [ ] `g h` → 홈으로 이동 확인 (g 입력 후 300ms 이내 h 대기)
- [ ] `g f`, `g e`, `g m`, `g n`, `g p` → 각 페이지 이동 확인
- [ ] `n` → PostEditor 열기 확인
- [ ] `/` → SearchBar 포커스 확인
- [ ] `b` → 북마크 토글 API 호출 확인
- [ ] `Esc` → 모달 닫기 (FocusManager 충돌 없음 확인)
- [ ] input 내 단축키 비활성화 확인 (D-1 패턴 동일)
- [ ] 도움말 모달 4개 카테고리 표시 확인
- [ ] HOTKEY_REGISTRY category 필드 추가 확인
- [ ] 5 locale i18n 키 확인
- [ ] tsc 0 errors
- [ ] unit tests: `hotkeys-expansion.test.ts` (g 시퀀스 + action 단축키)

**Risks**

| 리스크 | 영향 | 대응 |
|--------|:----:|------|
| `g h` 시퀀스 입력 타이밍 | 낮음 | 300ms timeout + 시각적 힌트("g 입력됨") 표시 고려 |
| `b` 단축키 포스트 컨텍스트 판단 | 중간 | 현재 뷰포트 기준 active 포스트 ID 판단 (D-1 j/k 패턴 준용) |
| `Esc` 우선순위 충돌 (모달 다중) | 중간 | 가장 최근에 열린 모달 우선 닫기 (스택 기반 관리) |

**KPIs**

- user-system-guide v2 단축키 섹션 구현 일치율: 10/10 (Wave A 4 + Wave C 6+)
- 도움말 모달 카테고리: 4개 완성
- E2E keyboard navigation 테스트: green

---

## 5. Open Questions (OQ 13개, 권장 default 명시)

| # | Open Question | 권장 Default | 근거 |
|:-:|---------------|:------------|------|
| **OQ-1** | Wave B 분기 — K-6 진입 조건 거래 카운트 확인 시점 | **Phase 12 Day 0 즉시 SQL 확인: `SELECT COUNT(*) FROM auctions WHERE status='sold'`** | Phase 11 보고서 기준 30~40건. ≥ 100건 시 B-K6, 미달 시 B-Admin 자동 전환 |
| **OQ-2** | A-1 testcontainers vs LocalStack | **testcontainers (PostgreSQL + Redis 통합 단순)** | Docker 이미지만 필요. LocalStack은 AWS 서비스 전체 mock 필요해 오버헤드 높음. SES는 in-memory stub 사용 |
| **OQ-3** | A-2 PATCH endpoint 권한 수준 | **`require_admin_with_2fa`** | 다른 admin 비즈니스 endpoints와 동일 권한 수준 준수 |
| **OQ-4** | B-1k (K-6) 가격 추천 알고리즘 복잡도 | **단순 비교 평균가 + 작가 작품 평균가 가중 (0.4:0.6)** | 거래 100건 수준에서 ML 회귀는 과적합 위험. Phase 13에서 500건+ 시 회귀 검토 |
| **OQ-5** | C-1 password reset 토큰 만료 시간 | **1시간** | NIST 권장 짧은 만료 + 재요청 허용으로 보완 |
| **OQ-6** | C-2 GitHub OAuth scope | **`read:user + user:email` (최소 권한)** | 이름/아바타/이메일만 필요. 저장소 접근 불필요 |
| **OQ-7** | C-3 단축키 충돌 방지 전략 | **input/textarea/contenteditable 포커스 시 자동 비활성 (D-1 패턴 동일)** | Phase 11 D-1에서 검증된 패턴. 별도 구현 불필요 |
| **OQ-8** | C-2 매직링크 토큰 보안 | **24시간 만료 + 1회용 + IP 기록 (검증은 optional — 경고만)** | 24h는 매직링크 표준. IP 불일치는 차단 아닌 경고로 UX 저해 최소화 |
| **OQ-9** | B-1a audit log UI 페이지네이션 | **cursor-based, 50건/페이지** | OFFSET 기반은 대용량 시 성능 저하. cursor(id DESC) 기반이 안정적 |
| **OQ-10** | B-2 analytics 새로고침 주기 | **Redis 5분 캐시 (TTL=300)** | 실시간 집계는 DB 부하 과도. 5분 지연은 운영 의사결정에 충분 |
| **OQ-11** | B-3 payouts auto-publish 정책 | **OFF (admin 명시 승인 필수)** | 자동 정산 오류 시 복구 불가. 2FA + confirm + audit 3중 안전장치 유지 |
| **OQ-12** | C-3 단축키 도움말 카테고리 | **navigation / editor / general / admin (4개)** | GitHub/Slack 표준 분류. admin 카테고리는 admin 권한 시에만 표시 |
| **OQ-13** | 거래 카운트 < 100건 시 Wave B 분기 자동 선택 | **자동 B-Admin (3 sub-PDCAs) 진입** | Phase 11~12 연속 미달 예상. B-Admin을 기본 경로로 설정하고 100건 달성 시 Phase 13에서 K-6 진입 |

---

## 6. Wave 병렬 위임 전략

```
Phase 12 시작 전 (Day 0)
  ├── [필수 확인] SELECT COUNT(*) FROM auctions WHERE status='sold'
  │   ├── ≥ 100건 → Wave B-K6 (B-1k 1개)
  │   └── < 100건 → Wave B-Admin (B-1a + B-2 + B-3, 3개) — 예상 경로
  └── [환경 확인] alembic head = 0085_email_password_auth 확인

Wave A (Week 1~3, 2 agents 병렬, 즉시 진입)
  ├── [Agent 1: bkend-expert] A-1 17 tests refactor (freezegun + testcontainers)
  └── [Agent 2: bkend-expert + frontend-architect] A-2 PATCH pause/complete endpoint + UI 활성화

↓ (Wave A 완료 확인, ~Week 3)

Wave B — 시나리오 분기
  [시나리오 1: 거래 ≥ 100건]
  Wave B (Week 3~5, 1 agent)
    └── [Agent 1: bkend-expert + frontend-architect] B-1k K-6 AI 가격 추천 (alembic 0086)

  [시나리오 2: 거래 < 100건 — 예상 경로]
  Wave B (Week 3~7, 최대 3 agents 병렬)
    ├── [Agent 1: frontend-architect] B-1a admin audit log 조회 UI
    ├── [Agent 2: frontend-architect + bkend-expert] B-2 admin analytics 대시보드
    └── [Agent 3: bkend-expert + frontend-architect] B-3 admin payouts 관리 UI

↓ (Wave B 완료 확인, ~Week 7)

Wave C (Week 6~10, 최대 3 agents — C-3은 Wave B와 병행 가능)
  ├── [Agent 1: bkend-expert + frontend-architect] C-1 password reset 플로우 (alembic 0086/0087)
  ├── [Agent 2: bkend-expert + frontend-architect] C-2 GitHub OAuth + 매직링크 (병행)
  └── [Agent 3: frontend-architect] C-3 단축키 확장 (Wave B 후반부부터 병행 가능)
```

**병렬화 효율 예상**:
- Wave A: A-1(10일) + A-2(7일) 병렬 = 10일 (순차 17일 대비 41% 단축)
- Wave B-Admin: B-1a(10일) + B-2(14일) + B-3(10일) 병렬 = 14일 (순차 34일 대비 59% 단축)
- Wave C: C-1(7일) + C-2(10일) + C-3(7일) 병렬 = 10일 (순차 24일 대비 58% 단축)
- C-3는 Wave B 후반부부터 병행 시 추가 1주 단축 가능

---

## 7. KPI 정의 (Phase 12 종결 시 측정)

### 7.1 Wave별 KPI 집계

| sub-PDCA | 핵심 KPI | 목표값 | 측정 도구 |
|:--------:|---------|:------:|----------|
| **A-1** | skipped tests | 0 (또는 < 5) | pytest 출력 |
| **A-1** | 전체 테스트 회귀 | 0건 | CI 로그 |
| **A-2** | Phase 11 B-1 matchRate 보완 | 88% → 95%+ | Analysis 재측정 |
| **A-2** | 실험 pause/complete 동작 | 100% | 수동 검증 |
| **B-1k** | 가격 추천 사용률 (K-6 진입 시) | ≥ 50% | PostHog |
| **B-1k** | 추천가 적용률 | ≥ 30% | PostHog |
| **B-1a** | audit log 조회 응답 | ≤ 100ms | 성능 측정 |
| **B-2** | analytics 로드 시간 (캐시 적중) | < 3초 | 브라우저 DevTools |
| **B-3** | 정산 목록 응답 | ≤ 200ms | 성능 측정 |
| **C-1** | password reset 완료율 | ≥ 70% | 가입 funnel |
| **C-2** | GitHub OAuth 가입 완료율 | ≥ 80% | 가입 funnel |
| **C-2** | 매직링크 클릭률 | ≥ 60% | SES 클릭 추적 |
| **C-3** | 단축키 구현 일치율 | 10/10 (D-1 4 + C-3 6+) | 구현 체크리스트 |

### 7.2 통합 KPI (Phase 12 종결)

| 지표 | 목표 | 비고 |
|------|:----:|------|
| Tests (passed) | 694 → 720+ | A-1 refactor + 신규 +26 이상 |
| Tests (skipped) | 17 → 0 (또는 < 5) | A-1 목표 |
| Tests (회귀) | 0건 | 전체 |
| alembic head | single head (0086 또는 0087 또는 0088) | C-1 + C-2 진행에 따라 결정 |
| 가입 방법 종류 | 4종 (Google + 이메일 + GitHub + 매직링크) | C-2 완료 후 |
| Admin 콘솔 누락 메뉴 해소율 | 7/7 (Phase 11 4 + Phase 12 B-Admin 3) | B-Admin 시나리오 시 |
| Frontend tsc errors | 0 | A-2 + B-1a/B-2/B-3 + C-1/C-2/C-3 모두 |
| 단축키 구현 카테고리 | 4개 (navigation/editor/general/admin) | C-3 완료 후 |

---

## 8. Risks & Mitigation

| 리스크 | 영향 | 가능성 | 대응 |
|--------|:----:|:------:|------|
| **K-6 거래 100건 미달 계속 지속** | 중간 | 높음 | OQ-13 권장: B-Admin 자동 진입. K-6는 Phase 13으로 이월. 거래 촉진 전략은 Phase 12 종결 후 별도 검토 |
| **testcontainers CI 빌드 시간 증가** | 중간 | 중간 | session-scope fixture + Docker layer 캐시 활용. 목표: CI +2분 이내 |
| **alembic 0086~0088 번호 충돌** | 높음 | 낮음 | Wave B-K6 진입 시 0086, 미진입 시 C-1이 0086 사용. Wave C 진입 전 `alembic heads` 확인 필수 |
| **C-2 sns_accounts 테이블 미존재** | 높음 | 중간 | C-2 진입 전 `app/models/user.py` 확인 + 필요 시 alembic 추가 |
| **B-2 analytics 쿼리 성능** | 중간 | 중간 | 코호트 집계는 야간 cron pre-compute 필수. 실시간 집계 금지 |
| **B-3 settlement_jobs.py 완성도 불명확** | 높음 | 중간 | B-3 진입 전 `app/workers/settlement_jobs.py` 코드 검토 + API 현황 확인 |
| **C-1 password reset 토큰 보안 취약점** | 높음 | 낮음 | 64자 crypto 랜덤 + 1h 만료 + 1회용. Brute-force 방어: 5분 cooldown |
| **C-3 g 시퀀스 입력 타이밍** | 낮음 | 낮음 | 300ms timeout 표준. UX 이슈 시 200ms로 조정 |
| **Wave B-Admin 3개 병렬 → 품질 저하** | 중간 | 낮음 | 각 sub-PDCA 독립적이므로 병렬 가능. 단, AdminShell 메뉴 추가 충돌 방지 (순차 merge 권장) |

---

## 9. alembic Migration Chain (0086~0088)

| revision | 시나리오 | sub-PDCA | 테이블 | down_revision |
|----------|:-------:|:--------:|--------|:-------------:|
| `0085_email_password_auth` | 공통 | D-3 (Phase 11) | `users` +4 컬럼 | `0084_audit_logs` |
| **`0086_*`** | **K-6 진입 시**: `price_recommendation_log` | **B-1k** | price 추천 로그 (선택) | `0085` |
| **`0086_*`** | **K-6 미진입 시**: `password_reset_tokens` | **C-1** | `password_reset_tokens` | `0085` |
| **`0087_*`** | K-6 진입 시: `password_reset_tokens` | **C-1** | `password_reset_tokens` | `0086_price` |
| **`0087_*`** | K-6 미진입 시: `magic_link_tokens` (필요 시) | **C-2** | `magic_link_tokens` | `0086_reset` |
| **`0088_*`** | K-6 진입 시: `magic_link_tokens` (필요 시) | **C-2** | `magic_link_tokens` | `0087_reset` |

> **alembic 충돌 방지 원칙**:
> - Wave A (A-1, A-2): alembic 작업 없음 (테스트 + 기존 테이블 컬럼만)
> - Wave B-K6 진입 시: 0086 = B-1k → 0087 = C-1 → 0088 = C-2(선택)
> - Wave B-Admin 진입 시 (예상 경로): 0086 = C-1 → 0087 = C-2(선택)
> - Wave C 진입 전 반드시 `alembic heads` 확인 + 번호 조정
> - Phase 12 종결 목표: **single head** (최종 번호는 시나리오에 따라 0086 또는 0087 또는 0088)

---

## 10. Phase 13 검토 후보

Phase 12 종결 후 운영 데이터 기반으로 우선순위 재평가.

| 후보 | 조건/근거 | 예상 우선순위 |
|------|----------|:------------:|
| **K-6 AI 가격 추천 (B-1k 미진입 시)** | 거래 100건 미달 지속 시 Phase 13 이월 | Must (이월) |
| **K-6 ML 회귀 모델** | 거래 500건+ 축적 후 단순 중앙값 → ML 회귀 전환 | Could |
| **`/admin/system` cron 모니터** | 백엔드 미구현 → Phase 13에서 설계부터 시작 | Could |
| **audit_logs 파티셔닝** | D-2 기반, 데이터 증가 후 created_at 기준 파티션 | Could |
| **모바일 Native (iOS/Android)** | README "주머니 앱" — Phase 13+ | Should |
| **ML 피드 v3 (사용자 맞춤 강화)** | K-8 A/B rollout 완료 후 v3 설계 | Should |
| **글로벌 결제 (PayPal/현지 결제)** | 신흥 시장 접근성 — Stripe 미지원 지역 | Should |
| **작가 인터뷰 자동화** | PostHog + AI로 성공 작가 패턴 자동 발굴 | Could |

---

## 11. Phase 12 타임라인 (~10주)

| 기간 | 활동 | sub-PDCA | 상태 |
|:---:|------|:--------:|:----:|
| **Day 0** | 거래 카운트 확인 → Wave B 분기 결정 + alembic head 확인 | 사전 준비 | ⏳ |
| **W1** | A-1 testcontainers fixture + freezegun 설정 시작 | A-1 | ⏳ |
| **W1** | A-2 PATCH pause/complete endpoint 설계 + 구현 시작 (A-1 병렬) | A-2 | ⏳ |
| **W2** | A-1 17 tests refactor 완료 (freezegun + testcontainers) | A-1 | ⏳ |
| **W2** | A-2 PATCH endpoint + UI 활성화 완료 | A-2 | ⏳ |
| **W3** | Wave A 완료 검토 → Wave B 진입 결정 | Wave A | ⏳ |
| **W3~4** | [B-K6] K-6 AI 가격 추천 설계 + 구현 (alembic 0086) | B-1k | ⏳ |
| **W3~5** | [B-Admin] B-1a admin audit log 조회 UI | B-1a | ⏳ |
| **W3~6** | [B-Admin] B-2 analytics 대시보드 (B-1a 병렬) | B-2 | ⏳ |
| **W3~5** | [B-Admin] B-3 payouts 관리 UI (B-1a/B-2 병렬) | B-3 | ⏳ |
| **W5~6** | C-3 단축키 확장 시작 (Wave B 후반부와 병행 가능) | C-3 | ⏳ |
| **W7** | Wave B 완료 검토 → Wave C 진입 | Wave B | ⏳ |
| **W7~8** | C-1 password reset 플로우 (alembic 0086 또는 0087) | C-1 | ⏳ |
| **W7~9** | C-2 GitHub OAuth + 매직링크 (C-1 병렬) | C-2 | ⏳ |
| **W8~9** | C-3 단축키 확장 완료 | C-3 | ⏳ |
| **W10** | Wave C 완료 검토 + Phase 12 종결 | Wave C | ⏳ |

---

## Version History

| 버전 | 날짜 | 변경사항 | 작성자 |
|------|------|---------|--------|
| 1.0 | 2026-05-08 | Phase 12 초안 (옵션 D 균형 진행, ~10주, Wave A/B/C). 7~8 sub-PDCAs, OQ 13개, alembic 0086~0088 사전 배정. Wave B 조건부 분기(거래 카운트 기준) 명시. Phase 11 carry-over 12개 매핑 완료. | itpe-ince (Claude Sonnet 4.6) |
