---
template: plan
version: 1.2
feature: domo-phase13-roadmap
date: 2026-05-09
author: itpe-ince (Claude Code, bkit-product-manager)
project: domo (v1)
status: Draft
---

# Domo Phase 13 Roadmap — 계획서

> **Summary**: Phase 12 carry-over 7개를 Wave A(테스트 청산) → Wave B(조건부 분기) → Wave C(admin 모니터 + ML 회귀) 3단계로 해소하는 ~8주 균형 진행 계획.
>
> **Project**: domo (v1)
> **Author**: itpe-ince (Claude Code, bkit-product-manager)
> **Date**: 2026-05-09
> **Status**: Draft

---

## 1. Executive Summary

### 1.1 Phase 12 결과 요약

Phase 12는 Wave A/B-Admin/C를 옵션 D(균형 진행)으로 병렬 진행해 **8/8 sub-PDCA 완료, 통합 가중 Match Rate 92.1%** 를 달성했다.
K-6 AI 가격 추천은 거래 < 100건으로 정당 이월(carry-over #1). 12개 테스트 skip(carry-over #2, #3)을 포함한 총 7개 carry-over가 Phase 13으로 이월됐다.

| 지표 | Phase 12 결과 |
|------|:----------:|
| 완료 sub-PDCA | 8/8 (100%) |
| 통합 가중 Match Rate | 92.1% |
| Tests passed | 750 |
| Tests skipped (정당) | 24 |
| alembic HEAD | 0086_password_reset_tokens (single head) |
| cron workers | 24개 |
| API endpoints 신규 | 17개 |
| tsc errors | 0 |

### 1.2 Phase 13 전략 — 옵션 D (균형, ~8주)

사용자가 **옵션 D**를 수락했다. Wave A/B/C 3단계로 carry-over 7개를 순차·조건부 진행한다.

```
Week 1~2  : Wave A — 테스트 안정성 청산 (2 sub-PDCAs)
Week 3~5  : Wave B — 조건부 분기 (거래 카운트 기반, 1~2 sub-PDCAs)
Week 6~8  : Wave C — admin 시스템 모니터 + ML 회귀 (2 sub-PDCAs)
```

---

## 2. Phase 12 Carry-over → Phase 13 매핑

| # | Carry-over 항목 | 출처 | 우선도 | Phase 13 배정 |
|:-:|----------------|------|:------:|:------------:|
| 1 | K-6 AI 가격 추천 (거래 ≥ 100건 시) | Phase 12 §5 | **Must** | Wave B-K6 (B-1k) |
| 2 | 12 GitHub OAuth + 매직링크 tests refactor | Phase 12 §6 Hot Fix #2 | **Should** | Wave A-1 |
| 3 | A-1 잔존 12 over-mocked tests (otel/redis/SES) | Phase 12 §2 A-1 | **Should** | Wave A-2 |
| 4 | 모바일 Native (iOS/Android) | README 비전 | **Should** | Phase 14 이월 |
| 5 | audit_logs 파티셔닝 | Phase 12 Plan §10 | **Could** | Wave B-Partition (B-1p) |
| 6 | /admin/system cron 모니터 | Phase 12 Plan §10 | **Could** | Wave C-1 |
| 7 | ML 회귀 모델 K-6 v2 (거래 ≥ 500건 후) | Phase 12 Plan §10 | **Could** | Wave C-2 (조건부) |

> 모바일 Native(carry-over #4)는 Phase 13 범위 밖, Phase 14 검토 후보로 이관.

---

## 3. README 비전 매핑

| README 원문 | Phase 13 목표 | Wave |
|------------|:------------|:----:|
| "신진작가 거래 AI 추천가" | K-6 AI 가격 추천 — 작가 등록 시 자동 추천 | B-1k |
| "AI 세상 예술가 생존" | K-6 v2 ML 회귀 (거래 ≥ 500건 시 완성) | C-2 |
| "유저들이 늘어나야 소비자들도" | cron 모니터로 운영 안정성 확보 | C-1 |
| "전 세계 아티스트들의 인덱스" | audit_logs 파티셔닝으로 데이터 장기 보존 | B-1p |
| **안정성 강화** | 테스트 skip 0 달성 (Phase 12 carry-over 청산) | A-1/A-2 |

---

## 4. Sub-PDCA 상세 (5~6개)

### 4.1 Wave A — 테스트 안정성 청산 (~2주)

#### A-1: tests-env-mock-refactor

| 항목 | 내용 |
|------|------|
| **목표** | 12 GitHub OAuth + 매직링크 tests skip → 0 (env mock 정확화) |
| **carry-over** | #2 |
| **예상 기간** | ~1주 |
| **alembic** | 없음 |

**범위 (In Scope)**:
- [ ] GitHub API httpx mock 정확화 (respx 라이브러리 통합)
- [ ] SES mock 정확화 (moto 또는 LocalStack SES 연동)
- [ ] factory_boy 패턴 확장 (UserFactory + GitHubUserFactory)
- [ ] 12개 skip tests → `@pytest.mark.skipif` 제거 후 정상 실행 확인
- [ ] CI env 변수 guard (GITHUB_OAUTH_ENABLED 없어도 mock 기반 실행)

**범위 (Out of Scope)**:
- otel / redis / SES 관련 비 GitHub tests (A-2 담당)
- 실제 GitHub sandbox 계정 CI 등록 (respx mock으로 대체)

**기술 접근**:
```
respx (httpx mock) 통합:
  - respx.mock(base_url="https://api.github.com") 패턴
  - 응답 fixture: { "id": "123", "login": "testuser", "email": "test@example.com" }

SES mock (moto):
  - @mock_ses 데코레이터 또는 moto server 방식
  - SES send_email → mock capture + assertion

GitHubUserFactory (factory_boy):
  - class GitHubUserFactory(factory.Factory):
      github_id = factory.Sequence(lambda n: f"gh_{n}")
      email = factory.LazyAttribute(...)
```

**성공 기준**:
- 12개 skip tests → 0 skip (또는 < 2 허용)
- CI pytest 실행 시 회귀 0건

---

#### A-2: testcontainers-localstack-extend

| 항목 | 내용 |
|------|------|
| **목표** | 잔존 12 over-mocked tests refactor (otel/redis/SES) → LocalStack 도입 |
| **carry-over** | #3 |
| **예상 기간** | ~1주 |
| **alembic** | 없음 |

**범위 (In Scope)**:
- [ ] LocalStack 도입 (S3 + SES + Cognito 통합 테스트 환경)
- [ ] testcontainers Compose 통합 (Docker Compose 기반)
- [ ] otel SDK 관련 over-mocked tests refactor (real otel collector 또는 stub)
- [ ] redis event loop tests refactor (testcontainers Redis)
- [ ] SES mock 잔존 tests → LocalStack SES 통합 테스트
- [ ] CI USE_TESTCONTAINERS=1 env guard 유지

**범위 (Out of Scope)**:
- A-1 GitHub/매직링크 tests (A-1 담당)
- 신규 테스트 작성 (리팩터만)

**기술 접근**:
```
LocalStack docker-compose.test.yml:
  services:
    localstack:
      image: localstack/localstack:latest
      environment:
        SERVICES: s3,ses,cognito-idp
      ports: ["4566:4566"]

testcontainers Compose:
  from testcontainers.compose import DockerCompose
  compose = DockerCompose("tests/", compose_file_name="docker-compose.test.yml")

redis event loop (testcontainers):
  from testcontainers.redis import RedisContainer
  with RedisContainer() as redis:
      REDIS_URL = redis.get_connection_url()
```

**성공 기준**:
- 12 over-mocked skip → 0 skip (또는 < 3 허용)
- LocalStack S3/SES/Cognito 통합 테스트 환경 확인
- CI pytest 회귀 0건

---

### 4.2 Wave B — 조건부 분기 (~3주)

#### 분기 결정: Phase 13 Day 0 SQL 즉시 실행

```sql
-- Phase 13 진입 시 즉시 실행
SELECT COUNT(*) AS sold_count
FROM auctions
WHERE status = 'sold';
```

| 조건 | 진행 sub-PDCA | 근거 |
|------|:------------:|------|
| `sold_count >= 100` | **B-1k** (K-6 AI 가격 추천) | K-6 Must carry-over #1 |
| `sold_count < 100` | **B-1p** (audit_logs 파티셔닝) | carry-over #5, 더 가능성 높음 |

> Phase 12 §5 기준: 거래 약 50~70건 수준. B-1p 진입 가능성이 높다.

---

#### 옵션 B-1k: ai-price-recommendation (거래 ≥ 100건 시)

| 항목 | 내용 |
|------|------|
| **목표** | K-6 AI 가격 추천 — 비교 작품 평균가 + 작가 작품 평균가 가중 |
| **carry-over** | #1 (Must) |
| **예상 기간** | ~2~3주 |
| **alembic** | 0088 |

**범위 (In Scope)**:
- [ ] alembic 0088: `posts` 테이블 2개 컬럼 추가
  ```sql
  recommended_price DECIMAL(12, 2) NULLABLE
  recommendation_metadata JSONB NULLABLE
  -- 예: { "basis": "avg_comparable", "comparable_avg": 45000, "artist_avg": 38000, "weight": 0.6 }
  ```
- [ ] 가격 추천 알고리즘 (단순 가중 평균가)
  ```
  recommended = (comparable_avg * 0.6) + (artist_avg * 0.4)
  comparable: 동일 장르 + 유사 사이즈 최근 90일 낙찰가 평균
  artist: 해당 작가 최근 1년 낙찰가 평균
  ```
- [ ] `POST /artworks` 등록 시 자동 추천 실행 (비동기 celery task 또는 sync)
- [ ] 작가 수락/수정 flow: 추천가 표시 → "수락" or "직접 입력"
- [ ] audit_log 기록 (`action = "price_recommendation_generated"`)
- [ ] 추천가 기준 < 3건 데이터 시 graceful fallback (추천 불가 안내)

**범위 (Out of Scope)**:
- ML 회귀 모델 (C-2 담당, 거래 ≥ 500건 시)
- autoaccept (OQ-9 권장: OFF)

**성공 기준**:
- alembic 0088 single head 유지
- 작가 등록 시 추천가 자동 표시
- 추천가 audit_log 기록 확인
- 관련 tests +8개 이상

---

#### 옵션 B-1p: audit-logs-partitioning (거래 < 100건 시)

| 항목 | 내용 |
|------|------|
| **목표** | PostgreSQL DECLARATIVE 파티셔닝 (월별 audit_logs) |
| **carry-over** | #5 (Could) |
| **예상 기간** | ~2~3주 |
| **alembic** | 0088 |

**범위 (In Scope)**:
- [ ] alembic 0088: `audit_logs` 파티셔닝 마이그레이션
  ```sql
  -- 전략: 기존 테이블 → partitioned 전환 또는 audit_logs_v2 별도 생성
  CREATE TABLE audit_logs_partitioned (
      LIKE audit_logs INCLUDING ALL
  ) PARTITION BY RANGE (created_at);

  -- 월별 파티션 (초기 6개월)
  CREATE TABLE audit_logs_2026_01 PARTITION OF audit_logs_partitioned
      FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');
  -- ... 2026_02 ~ 2026_12
  ```
- [ ] dual write 패턴 (서비스 중단 0)
  ```
  Phase 1: 신규 INSERT → 파티션 테이블로 라우팅 (READ는 기존 뷰)
  Phase 2: 데이터 마이그레이션 (배치)
  Phase 3: 기존 테이블 → 파티션 테이블 뷰 교체
  ```
- [ ] cron auto-create 다음 달 파티션 (25번째 cron)
  ```python
  # cron 25: create_next_month_audit_partition
  # 매월 25일 실행 → 다음 달 파티션 자동 생성
  ```
- [ ] 1년 이전 파티션 자동 detach + S3 archive (Glacier 옵션)
- [ ] READ 쿼리 영향 없음 검증 (파티션 pruning 확인)

**범위 (Out of Scope)**:
- audit_logs 외 테이블 파티셔닝
- HASH 파티셔닝 (월별 RANGE로 충분)

**파티셔닝 단위 결정 (OQ-4)**:
- 권장: 월별 (1개월 ≈ 1M rows 가정, rows < 1M이면 분기별 재검토)

**성공 기준**:
- alembic 0088 single head 유지
- dual write 서비스 중단 0
- `EXPLAIN` 쿼리로 파티션 pruning 확인
- 25번째 cron 등록 + 실행 로그 확인
- 기존 audit_logs 조회 API 응답 변화 없음

---

### 4.3 Wave C — admin 모니터 + ML 회귀 (~3주)

#### C-1: admin-system-cron-monitor

| 항목 | 내용 |
|------|------|
| **목표** | `/admin/system` 신규 페이지 — cron 24개 상태 실시간 모니터링 |
| **carry-over** | #6 (Could) |
| **예상 기간** | ~2주 |
| **alembic** | 0089 (선택) |

**범위 (In Scope)**:

백엔드:
- [ ] alembic 0089: `cron_status` 테이블 (선택사항 — Redis hash 충분 시 생략 가능)
  ```sql
  -- 선택: Redis hash 미사용 시 DB 저장
  CREATE TABLE cron_status (
      worker_name VARCHAR(100) PRIMARY KEY,
      last_run_at TIMESTAMPTZ,
      last_status VARCHAR(20),  -- 'success' | 'error' | 'running'
      last_error TEXT NULLABLE,
      run_count INTEGER DEFAULT 0,
      updated_at TIMESTAMPTZ DEFAULT NOW()
  );
  ```
- [ ] `GET /admin/system/cron-status` endpoint
  ```json
  // Response
  {
    "workers": [
      {
        "name": "audit_log_cleanup",
        "last_run_at": "2026-05-09T03:00:00Z",
        "last_status": "success",
        "last_error": null,
        "is_overdue": false  // 5분 이상 미실행 시 true
      },
      ...
    ],
    "total": 24,
    "healthy": 23,
    "overdue": 1
  }
  ```
- [ ] 각 cron job에 status reporter 통합 (Redis hash 기반)
  ```python
  # Redis hash: cron:status:{worker_name}
  # TTL: 1시간 (OQ-6 권장)
  async def report_cron_status(name: str, status: str, error: str = None):
      await redis.hset(f"cron:status:{name}", mapping={
          "last_run_at": datetime.utcnow().isoformat(),
          "last_status": status,
          "last_error": error or "",
      })
      await redis.expire(f"cron:status:{name}", 3600)
  ```
- [ ] Slack alert (5분 이상 overdue 시 — OQ-7 권장)
  ```python
  # 별도 health-check cron (1분 간격) 또는 endpoint 호출 시 체크
  if is_overdue and SLACK_WEBHOOK_URL:
      await send_slack_alert(f"[CRON OVERDUE] {name} 5분 이상 미실행")
  ```

프론트엔드 (admin, port 3800):
- [ ] `/admin/system` 신규 페이지
- [ ] cron 24개 상태 테이블:
  - 컬럼: worker_name, last_run_at, status badge, last_error, is_overdue
  - 상태 badge: green(success) / yellow(running) / red(error/overdue)
- [ ] 30초 자동 갱신 (polling)
- [ ] AdminShell `System` 메뉴에 추가

**범위 (Out of Scope)**:
- prometheus_client 메트릭 노출 (미설치 시 Redis hash로 대체)
- Grafana 연동

**성공 기준**:
- `/admin/system` 페이지 접근 시 24개 cron 상태 표시
- Redis hash TTL 1시간 확인
- Slack alert overdue trigger 테스트
- 관련 tests +6개 이상

---

#### C-2: ml-regression-k6-v2 (조건부 — 거래 ≥ 500건 시)

| 항목 | 내용 |
|------|------|
| **목표** | K-6 단순 평균가 → ML 회귀 모델 (linear regression 우선) |
| **carry-over** | #7 (Could) |
| **예상 기간** | ~2~3주 (조건부) |
| **alembic** | 0090 (C-2 진입 시) |

**진입 조건**:
```sql
SELECT COUNT(*) FROM auctions WHERE status = 'sold';
-- >= 500건 → C-2 진입
-- < 500건  → 알고리즘 설계 단계만 + Phase 14 이월
```

**범위 (거래 ≥ 500건 시, In Scope)**:
- [ ] alembic 0090: ML 모델 메타데이터 테이블
  ```sql
  CREATE TABLE ml_model_metadata (
      id SERIAL PRIMARY KEY,
      model_type VARCHAR(50),  -- 'linear_regression' | 'random_forest'
      feature_names JSONB,
      trained_at TIMESTAMPTZ,
      r2_score DECIMAL(5, 4),
      n_samples INTEGER,
      model_artifact_path TEXT  -- S3 경로
  );
  ```
- [ ] sklearn linear regression 모델
  ```python
  # 입력 피처:
  features = [
      "artist_avg_price",      # 작가 작품 평균가
      "comparable_avg_price",  # 비교 작품 평균가
      "genre_encoded",         # 장르 인코딩 (label encoding)
      "artwork_size_cm2",      # 사이즈 (가로 * 세로)
      "is_high_season",        # 거래 시즌 (Q4 등)
  ]
  # 타깃: actual_sold_price
  from sklearn.linear_model import LinearRegression
  model = LinearRegression()
  ```
- [ ] graceful fallback (sklearn 미설치 시 단순 평균가로 자동 전환)
- [ ] 모델 학습 cron 추가 (주 1회, 월요일 새벽 — OQ-10 권장)
  ```python
  # cron 26: train_price_recommendation_model (월요일 03:00 UTC)
  ```
- [ ] S3 모델 artifact 저장 + 버전 관리 (model_metadata 테이블)

**범위 (거래 < 500건 시, 알고리즘 설계만)**:
- [ ] 피처 엔지니어링 문서 작성 (design 단계)
- [ ] 데이터 품질 평가 (현재 거래 건수 + 피처 분포)
- [ ] Phase 14 이월 계획 수립

**성공 기준 (거래 ≥ 500건 시)**:
- sklearn 모델 R² ≥ 0.6 (목표)
- graceful fallback 동작 확인 (SKLEARN_ENABLED=0 시)
- 모델 학습 cron 등록 확인
- 관련 tests +8개 이상

---

## 5. Open Questions (OQ-13개, 권장 default)

| # | 질문 | 권장 default | 결정 시점 |
|:-:|------|:------------|:--------:|
| **OQ-1** | K-6 진입을 위한 거래 카운트 확인 방법 | Phase 13 Day 0 SQL 즉시 실행 | Day 0 |
| **OQ-2** | A-1 GitHub mock 도구 선택 | respx (httpx mock) 통합 | A-1 설계 |
| **OQ-3** | A-2 LocalStack vs 개별 mock 전략 | LocalStack 통합 (SES + S3 + Cognito 단일 컨테이너) | A-2 설계 |
| **OQ-4** | B-1p 파티셔닝 단위 (월별 vs 분기별) | 월별 (1개월 ≈ 1M rows 가정 기준) | B-1p 설계 |
| **OQ-5** | B-1p 1년 이전 파티션 처리 방식 | detach + S3 archive (Glacier 클래스 옵션) | B-1p 설계 |
| **OQ-6** | C-1 cron status 저장 위치 (Redis vs DB) | Redis hash (TTL 1시간, cron_status DB는 선택사항) | C-1 설계 |
| **OQ-7** | C-1 overdue alert 임계값 및 채널 | 5분 이상 미실행 시 Slack webhook alert | C-1 설계 |
| **OQ-8** | C-2 ML 모델 알고리즘 선택 | linear regression 우선, random forest는 Phase 14 | C-2 설계 |
| **OQ-9** | K-6 추천가 자동 적용(autoaccept) 여부 | autoaccept OFF (작가 검토 후 수동 수락) | B-1k 설계 |
| **OQ-10** | K-6 v2 모델 학습 빈도 | 주 1회 (월요일 새벽 03:00 UTC) | C-2 설계 |
| **OQ-11** | B-1p 마이그레이션 중 서비스 중단 허용 여부 | dual write 패턴 (서비스 중단 0) | B-1p 설계 |
| **OQ-12** | A-1/A-2 PR 통합 vs 분리 전략 | A-1 + A-2 통합 PR (테스트 리팩터 일관성 유지) | Wave A 시작 |
| **OQ-13** | 거래 < 500건 시 C-2 처리 | 알고리즘 설계 단계만 수행 + Phase 14 이월 | Wave C 진입 시 |

---

## 6. Wave 병렬 위임 전략

```
Phase 13 실행 타임라인:

Week 1~2: Wave A (테스트 청산)
┌─────────────────────────────────────────────────────┐
│  A-1: GitHub/매직링크 tests → respx + moto mock       │  ~1주
│  A-2: otel/redis/SES → LocalStack + testcontainers   │  ~1주
│  * A-1 먼저, A-2 overlap (A-1 결과 참조)             │
└─────────────────────────────────────────────────────┘

Week 3~5: Wave B (조건부 분기)
┌─────────────────────────────────────────────────────┐
│  [Day 0 SQL] sold_count 확인                         │
│  ├── sold >= 100: B-1k (K-6 AI 가격 추천)  ~2~3주   │
│  └── sold < 100:  B-1p (audit_logs 파티셔닝) ~2~3주  │
└─────────────────────────────────────────────────────┘

Week 6~8: Wave C (admin + ML)
┌─────────────────────────────────────────────────────┐
│  C-1: admin/system cron 모니터                  ~2주  │
│  C-2: [sold >= 500] ML 회귀 / [<500] 설계만     ~2주  │
│  * C-1과 C-2 병렬 진행 가능                          │
└─────────────────────────────────────────────────────┘
```

### 위임 매트릭스

| Wave | 병렬화 수준 | 의존성 |
|------|:---------:|--------|
| A-1 + A-2 | 부분 병렬 (A-1 먼저, A-2 overlap) | A-1 완료 후 A-2 시작 (mock 패턴 참조) |
| Wave B | 단일 분기 | Day 0 SQL 결과에 따라 B-1k 또는 B-1p |
| C-1 + C-2 | 완전 병렬 | Wave B 완료 후 진입 |

---

## 7. KPI 정의

| KPI | 목표 | 측정 방법 |
|-----|:----:|----------|
| Tests skipped | 24 → **< 6** (목표: 0) | `pytest --tb=short` skipped count |
| Tests passed | 750 → **+20 이상** | pytest passed count |
| Tests 회귀 | **0건** | CI pytest 결과 |
| alembic HEAD | **single head** (0088~0090) | `alembic heads` |
| cron workers | 24 → **25** (B-1p 시) / **26** (C-2 진입 시) | worker registry |
| tsc errors | **0** | `tsc --noEmit` |
| audit_logs 파티셔닝 (B-1p) | **dual write 중단 0** | 마이그레이션 로그 |
| cron 모니터 (C-1) | **24개 상태 노출** | `/admin/system` 응답 |
| K-6 추천가 (B-1k) | **작가 등록 시 자동 표시** | audit_log 기록 확인 |
| ML 회귀 R² (C-2) | **≥ 0.6** (진입 시) | sklearn model.score() |
| Match Rate (sub-PDCA 평균) | **≥ 90%** | PDCA Check 단계 |

---

## 8. Risks & Mitigation

| 리스크 | 영향 | 발생 가능성 | Mitigation |
|--------|:----:|:----------:|------------|
| A-1 respx mock 불완전 (GitHub API 변경) | 중 | 낮음 | respx + fixture JSON 고정, CI env 분리 |
| A-2 LocalStack 빌드 시간 증가 (CI) | 중 | 중간 | `USE_TESTCONTAINERS=1` opt-in 유지, CI 선택적 활성화 |
| B-1p dual write 중 데이터 불일치 | 높음 | 낮음 | Phase 1~3 단계 마이그레이션 + READ 쿼리 검증 |
| B-1p 파티셔닝 중 성능 저하 (lock) | 높음 | 중간 | AccessExclusiveLock → 배치 마이그레이션 새벽 진행 |
| C-1 Redis hash TTL 만료 (cron 미실행 착각) | 중 | 중간 | TTL 1시간 + overdue 기준 5분으로 분리, DB 보조 저장 선택 |
| C-2 sklearn 없이 K-6 실행 | 낮음 | 낮음 | graceful fallback (단순 평균가 자동 전환) |
| Wave B 분기 오판 (SQL 실행 지연) | 중 | 낮음 | Day 0 checklist에 SQL 실행 명시, 72시간 내 결정 |
| alembic 0088~0090 chain 오류 | 높음 | 낮음 | Wave B/C 진입 전 `alembic heads` 검증 필수 |

---

## 9. alembic Migration Chain (0088~0090)

```
현재 HEAD:
0086_password_reset_tokens (Phase 12 C-1, single head)

Phase 13 예정 체인:
0086_password_reset_tokens (Phase 12)
  ↓
0087_github_id (Phase 12 C-2)
  ↓
0088: [분기]
  ├── B-1k: post.recommended_price + recommendation_metadata
  └── B-1p: audit_logs 파티셔닝 (마이그레이션)
  ↓
0089: cron_status 테이블 (C-1 선택사항, Redis hash 충분 시 생략)
  ↓
0090: ml_model_metadata (C-2 진입 시에만)
```

### alembic 배정표

| alembic | 용도 | Wave | 조건 |
|:-------:|------|:----:|:----:|
| **0088** | K-6 추천가 컬럼 (B-1k) 또는 audit_logs 파티셔닝 (B-1p) | B | Day 0 SQL 결과 |
| **0089** | cron_status 테이블 (선택) | C-1 | Redis hash 미충분 시 |
| **0090** | ml_model_metadata | C-2 | 거래 ≥ 500건 시 |

> 검증 원칙: 각 Wave 진입 전 `alembic heads` 단일 head 확인 필수.

---

## 10. Phase 14 검토 후보

| 항목 | 근거 | 예상 규모 |
|------|------|:--------:|
| 모바일 Native (iOS/Android) | carry-over #4, README 비전 | ~12주 |
| K-6 v2 ML 회귀 (거래 < 500건 시 이월) | carry-over #7 조건부 | ~3~4주 |
| Stripe Connect sandbox 연동 (실계정) | Phase 12 B-3 mock fallback 해소 | ~2주 |
| AdminShell 고급 분석 (B-2 확장) | Phase 12 B-2 PostHog 실연동 | ~2주 |
| C-3 단축키 3개 추가 (z z, d, e) | Phase 12 C-3 "coming soon" | ~1주 |
| 글로벌 작가 인덱스 v1 | README 핵심 비전 | ~4~6주 |

---

## 11. Phase 13 타임라인 (~8주)

```
Week 1    Wave A-1 착수: GitHub/매직링크 tests → respx + moto mock
Week 2    Wave A-2 착수(A-1 overlap): otel/redis/SES → LocalStack
          A-1/A-2 통합 PR + CI 검증
          ★ Day 0 SQL: sold_count 확인 → Wave B 분기 결정

Week 3    Wave B 착수 (B-1k 또는 B-1p)
Week 4    Wave B 계속 (alembic 0088 마이그레이션 + 로직 구현)
Week 5    Wave B 완료 + tests + design 문서화

Week 6    Wave C-1 + C-2 병렬 착수
          C-1: /admin/system cron 모니터 백엔드
          C-2: ML 회귀 알고리즘 설계 (또는 구현 진입)
Week 7    C-1: frontend UI + Slack alert
          C-2: sklearn 모델 학습 cron + S3 artifact (진입 시)
Week 8    통합 검증, PDCA Check, report 작성
          Phase 14 handoff 문서화
```

| 주차 | 마일스톤 | 완료 기준 |
|:----:|---------|---------|
| Week 2 end | Wave A 완료 | skip < 6, CI 회귀 0건 |
| Week 3 | Day 0 SQL 확인 | sold_count 기록 + Wave B 분기 결정 |
| Week 5 end | Wave B 완료 | alembic 0088 single head, 기능 동작 확인 |
| Week 8 end | Wave C 완료 | cron 모니터 24개 노출, Match Rate ≥ 90% |

---

## 12. Scope

### In Scope

- [ ] A-1: 12 GitHub OAuth + 매직링크 tests env mock 정확화 (respx + moto)
- [ ] A-2: 12 over-mocked tests (otel/redis/SES) LocalStack 도입 + refactor
- [ ] Wave B 분기: Day 0 SQL 결과에 따라 B-1k(K-6) 또는 B-1p(파티셔닝) 단일 선택
- [ ] C-1: /admin/system cron 모니터 백엔드 + frontend UI
- [ ] C-2: 거래 ≥ 500건 시 ML 회귀 구현 / 미달 시 알고리즘 설계만
- [ ] alembic 0088~0090 chain 관리 (조건부)
- [ ] Phase 13 전체 PDCA Check + report

### Out of Scope

- 모바일 Native iOS/Android (Phase 14)
- Stripe Connect 실계정 sandbox (Phase 14)
- random forest 모델 (Phase 14 C-2 확장)
- AdminShell 고급 분석 B-2 PostHog 실연동 (Phase 14)
- 단축키 3개 추가 (C-3 잔여분, Phase 14)

---

## 13. Non-Functional Requirements

| 카테고리 | 기준 | 측정 방법 |
|----------|------|---------|
| 테스트 커버리지 | 신규 기능 ≥ 80% | pytest --cov |
| 마이그레이션 다운타임 | B-1p dual write: 중단 0 | 마이그레이션 로그 |
| cron 모니터 응답 | < 200ms | API 응답 시간 |
| ML 추론 응답 | B-1k 가격 추천 < 500ms | 비동기 task 허용 |
| alembic 무결성 | single head 항시 유지 | `alembic heads` |
| tsc errors | 0 | `tsc --noEmit` |

---

## 14. Architecture Considerations

### 14.1 Project Level

Dynamic (fullstack with BaaS) — Phase 12와 동일 레벨 유지.

### 14.2 Key Architectural Decisions

| 결정 | 선택 | 근거 |
|------|:----:|------|
| GitHub mock | respx (httpx mock) | Phase 12 C-2 미완성 요인 해소 |
| SES/S3 mock | LocalStack (testcontainers) | 통합 테스트 환경 단일화 |
| cron status 저장 | Redis hash (TTL 1h) | DB 부하 최소화, 빠른 갱신 |
| 파티셔닝 전략 (B-1p) | DECLARATIVE RANGE (월별) | PostgreSQL 네이티브 지원, pruning 자동 |
| ML 모델 저장 | S3 (pkl/joblib) + DB 메타데이터 | artifact 버전 관리 용이 |
| ML 알고리즘 (C-2) | linear regression 우선 | 해석 가능성, 데이터 요구량 적음 |

---

## 15. Related Documents

- Phase 12 Plan: `/Users/sangincha/dev/domo/v1/docs/archive/2026-05/domo-phase12-roadmap/plan.md`
- Phase 12 Report: `/Users/sangincha/dev/domo/v1/docs/archive/2026-05/domo-phase12-roadmap/report.md`
- Admin System Guide: `/Users/sangincha/dev/domo/v1/docs/guides/admin-system-guide.ko.md`
- User System Guide: `/Users/sangincha/dev/domo/v1/docs/guides/user-system-guide.ko.md`
- README 비전: `/Users/sangincha/dev/domo/README.md`

---

## 16. Version History

| 버전 | 날짜 | 변경 | 작성자 |
|------|:----:|------|--------|
| 0.1 | 2026-05-09 | 초기 작성. Phase 12 carry-over 7개 기반. Wave A/B/C 옵션 D 균형 진행. sub-PDCA 5~6개, OQ 13개, alembic 0088~0090. | itpe-ince (Claude Code, bkit-product-manager) |

---

## 부록: Phase 13 Day 0 체크리스트

```
[ ] 1. Wave B 분기 SQL 실행:
        SELECT COUNT(*) FROM auctions WHERE status = 'sold';
        → sold_count 기록 후 B-1k(≥100) 또는 B-1p(<100) 결정

[ ] 2. alembic heads 확인:
        alembic heads
        → single head (0086_password_reset_tokens) 확인

[ ] 3. Tests 기준선 확인:
        pytest --tb=short -q
        → 750 passed, 24 skipped 기준선 확인

[ ] 4. cron workers 기준선:
        24개 모두 등록 확인

[ ] 5. Wave A 착수 (A-1 먼저):
        respx + moto mock 의존성 설치 계획 수립
```
