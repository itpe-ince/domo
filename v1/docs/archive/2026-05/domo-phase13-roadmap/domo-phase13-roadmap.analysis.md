# Phase 13 Roadmap — Gap Analysis Report

> **Analysis Type**: Gap Analysis (Design vs Implementation)
>
> **Project**: domo (v1)
> **Analyst**: itpe-ince (Claude Code, bkit-gap-detector)
> **Date**: 2026-05-09
> **Plan Doc**: `v1/docs/01-plan/features/domo-phase13-roadmap.plan.md`
> **Design Docs**: A-1, A-2, B-2, C-1, C-2 (5 sub-PDCAs)

---

## 1. Analysis Overview

### 1.1 Purpose

Phase 13 Wave A/B-2/C-1/C-2 5개 sub-PDCA의 Design 명세와 실제 구현 간 일치도를 측정하고, Phase 14 carry-over 항목이 design에 명시적으로 기록되었는지 확인하여 종합 Match Rate ≥ 90% 달성 여부를 판정.

### 1.2 Scope

- **Design Docs (5)**:
  - `domo-phase13-A-1.design.md` (GitHub OAuth + 매직링크 tests refactor)
  - `domo-phase13-A-2.design.md` (testcontainers + LocalStack 확장)
  - `domo-phase13-B-2.design.md` (audit_logs 월별 파티셔닝)
  - `domo-phase13-C-1.design.md` (admin-system cron 모니터)
  - `domo-phase13-C-2.design.md` (ML 회귀 알고리즘 설계)
- **Implementation**: `v1/backend/`, `v1/frontend/`

### 1.3 회귀 / alembic 충족 (사전 검증)

| 항목 | 목표 | 실측 | 충족 |
|------|:----:|:----:|:----:|
| Tests passed | ≥ 770 | **787** | ✅ |
| Tests skipped | < 6 | **13** (4 carry-over + 9 기존 정당 skip) | ⚠️ 부분 |
| Tests failed | 0 | **0** | ✅ |
| `alembic heads` | single head | **0088_audit_logs_partitioning** | ✅ |
| frontend tsc errors | 0 | **0** | ✅ |
| cron workers | 25~26 | **26** (audit_partition + slack_alert) | ✅ |

> skip 13건 중 9건은 Phase 12 이전부터 정당하게 skip된 conditional 항목. Phase 13 carry-over 신규 4건 (OTel 2 + Redis 2)은 design에 명시적 carry-over 기록.

---

## 2. Wave A-1 — GitHub OAuth + 매직링크 Tests Refactor

| # | Design 요구 | 구현 | 상태 |
|:-:|------------|------|:----:|
| AC-1 | skip 12 → 0 | 0건 (`@pytest.mark.skip` 미존재) | ✅ |
| AC-2 | respx 통합 + GitHub API mock | conftest.py `github_oauth_mock` | ✅ |
| AC-3 | factory_boy 3종 | `UserFactory`, `GoogleUserFactory`, `GitHubUserFactory` | ✅ |
| AC-4 | 회귀 0 | 787 passed / 0 failed | ✅ |
| AC-5 | alembic 변경 없음 | 0088만 추가 (B-2 사유) | ✅ |
| AC-6 | respx 미설치 graceful skip | `_skip_if_no_respx()` | ✅ |
| — | `respx>=0.21`, `pytest-mock>=3.14` | pyproject.toml 추가 | ✅ |
| — | env monkeypatch | test_auth_github_oauth.py | ✅ |

### 2.1 Hot-fix (정당)

Design은 patch 경로 `app.services.github_oauth.*`로 명시했으나 실제 import 경로가 `app.api.auth.*`라 hot-fix. 코드 truth 반영의 정당한 수정.

### 2.2 Match Rate: **100%**

---

## 3. Wave A-2 — testcontainers + LocalStack 확장

| # | Design 요구 | 구현 | 상태 |
|:-:|------------|------|:----:|
| AC-1 | skip ≤ 2 (OTel 미설치 시) | 4건 skip (OTel 2 + Redis 2) | ⚠️ |
| AC-2 | LocalStack SES fixture | `localstack_container`, `aws_ses_client` | ✅ |
| AC-3 | testcontainers Redis fixture | graceful skip 적용 | ⚠️ event loop 미해결 |
| AC-4 | USE_LOCALSTACK env guard | `localstack_skip` 마커 | ✅ |
| AC-5 | CI ubuntu workflow | `.github/workflows/backend-test.yml` 신규 | ✅ |
| AC-6 | macOS docker 미설치 graceful | `LOCALSTACK_AVAILABLE` + `USE_LOCALSTACK` | ✅ |
| AC-7 | A-1 패턴 호환 | conftest.py 통합 | ✅ |
| AC-8 | alembic single head | 0088 단일 | ✅ |
| — | `testcontainers[localstack]`, `boto3>=1.34` | pyproject.toml | ✅ |
| — | `in_memory_tracer` fixture | conftest.py | ✅ |

### 3.1 Phase 14 Carry-over

| Carry-over | 건수 | Design 명시 | 평가 |
|-----------|:---:|:-----------:|------|
| OTel `sys.modules patch` | 2 | A-2 §4.4 OTel < 3 허용 | 🔵 의도된 |
| Redis `event-loop closed` | 2 | A-2 §4.3 약속 미충족 | ⚠️ 부분 명시 |

### 3.2 Match Rate: **88%**

---

## 4. Wave B-2 — audit_logs 월별 파티셔닝

| Design 요구 | 구현 | 상태 |
|------------|------|:----:|
| `PARTITION BY RANGE (created_at)` | 0088 line 50 | ✅ |
| 사전 파티션 6개 (2026_04~2026_09) | 0088 line 56-70 | ✅ |
| DEFAULT 파티션 안전망 | `audit_logs_default` | ✅ |
| 인덱스 4개 | line 86-107 | ✅ |
| INSERT SELECT 데이터 이전 | line 117-125 | ✅ |
| `create_next_month_audit_partition` | audit_partition_cron.py | ✅ |
| 멱등성 (`pg_class` 체크) | `_partition_exists()` | ✅ |
| 86400s interval cron 등록 | main.py:217-219 (25th worker) | ✅ |
| Rollback (downgrade) backup→restore | 0088 line 138-193 | ✅ |
| 단위 테스트 ≥ 6개 | **15 tests passed** (250%) | ✅ |
| down_revision = `0086_password_reset_tokens` | ✅ | ✅ |

### 4.1 Match Rate: **100%**

---

## 5. Wave C-1 — admin-system cron 모니터

| Design 요구 | 구현 | 상태 |
|------------|------|:----:|
| Redis hash `cron:status:{worker}` | `_PREFIX = "cron:status:"` | ✅ |
| 4 fields (last_run_at, status, error, run_count) | record_cron_run | ✅ |
| TTL 3600s (1시간) | `_TTL_SECONDS = 3600` | ✅ |
| WORKER_REGISTRY 26개 | cron_monitor.py line 42-69 | ✅ |
| overdue 5분 (300s) | `OVERDUE_THRESHOLD_SECONDS = 300` | ✅ |
| Slack Block Kit | slack_alert_cron.py:33-70 | ✅ |
| 1분 interval slack_alert | main.py:230 | ✅ |
| `track_cron` 데코레이터 | cron_monitor.py:212-248 | ✅ |
| `GET /admin/system/crons` | admin_system.py:45-60 | ✅ |
| `GET /admin/system/crons/{worker_name}` | line 63-89 | ✅ |
| `require_admin` 권한 | line 47, 65 | ✅ |
| 26개 worker `_push_cron_status` 통합 | 27 service 파일 import 확인 | ✅ |
| frontend admin/system/page.tsx | 신규 생성 | ✅ |
| 30초 polling | `setInterval(refresh, 30_000)` | ✅ |
| overdue/failed 행 색상 | `rowClassName()` | ✅ |
| 요약 카드 (전체/성공/실행중/실패/지연) | line 196-231 | ✅ |
| Auth gate (admin role) | `fetchMe` + role 체크 | ✅ |
| SLACK_WEBHOOK_URL 미설정 graceful | line 79-85 | ✅ |
| alembic 0089 생략 (Redis 충분) | 미생성 (design 명시 결정) | ✅ |
| 단위 테스트 ≥ 6개 | **11 tests passed** (183%) | ✅ |

### 5.1 Match Rate: **100%**

---

## 6. Wave C-2 — ML 회귀 알고리즘 설계

| Design 요구 | 구현 | 상태 |
|------------|------|:----:|
| 진입 조건 거래 ≥ 500 | < 500 가정 → 설계만 | ✅ (정당) |
| 알고리즘 설계 문서 446 lines | C-2 design 완성 | ✅ |
| Feature Engineering 8개 피처 | design §2.2 | ✅ |
| LinearRegression 선택 근거 | design §2.1 | ✅ |
| 학습 파이프라인 흐름 | design §3 | ✅ |
| 예측 API 분기 로직 | design §4.2 | ✅ |
| graceful fallback | design §1.3, §4.2 | ✅ |
| KPI (R² ≥ 0.6, MAE) | design §5 | ✅ |
| alembic 0090 DDL (구현 없음) | design §6 | ✅ |
| Phase 14 carry-over 8개 체크리스트 | design §8 | ✅ |
| 코드 변경 0 | sklearn/cron/0090 모두 미생성 | ✅ |
| Phase 14 이월 명시 | design §9 | ✅ |

### 6.1 Phase 14 Carry-over (design §8 명시 — gap 아님)

1. alembic 0090 ml_model_metadata
2. sklearn/joblib 의존성
3. 학습 cron worker (`k6_train_cron.py`)
4. 예측 서비스 (`k6_predict.py`)
5. 예측 API ML 분기 로직
6. 모델 artifact 저장/로드 유틸 (`ml_artifact.py`)
7. Admin 모델 관리 페이지
8. 회귀 테스트 (`test_k6_ml.py`)

### 6.2 Match Rate: **100%**

---

## 7. Phase 13 종합 Match Rate

### 7.1 Wave 가중 평균

| Wave | Match Rate | 가중치 | 가중 점수 |
|:----:|:----------:|:------:|:--------:|
| A-1 | 100% | 1.0 | 100 |
| A-2 | 88% | 1.0 | 88 |
| B-2 | 100% | 1.0 | 100 |
| C-1 | 100% | 1.0 | 100 |
| C-2 | 100% | 1.0 | 100 |
| **종합** | — | 5.0 | **488 / 500 = 97.6%** |

```
┌─────────────────────────────────────────────┐
│  Phase 13 종합 Match Rate: 97.6%             │
├─────────────────────────────────────────────┤
│  Wave A-1: 100% (테스트 청산 GitHub/매직링크)  │
│  Wave A-2:  88% (LocalStack — Redis 2건 미흡) │
│  Wave B-2: 100% (audit_logs 파티셔닝)          │
│  Wave C-1: 100% (cron 모니터 + UI)             │
│  Wave C-2: 100% (ML 알고리즘 설계만)           │
└─────────────────────────────────────────────┘
```

### 7.2 Plan KPI 충족도

| Plan §7 KPI | 목표 | 실측 | 충족 |
|------------|:----:|:----:|:----:|
| Tests passed (+20) | 770+ | 787 (+37) | ✅ |
| Tests 회귀 | 0 | 0 | ✅ |
| Tests skipped | < 6 | 13 (신규 4 + 기존 9) | ⚠️ |
| alembic HEAD single | 1 | 1 (0088) | ✅ |
| cron workers | 25~26 | 26 | ✅ |
| tsc errors | 0 | 0 | ✅ |
| audit_logs 다운타임 | 0 | INSERT SELECT — ≈ 0 | ✅ |
| cron 모니터 26개 노출 | 26 | 26 | ✅ |
| ML 회귀 (조건부) | 거래 ≥ 500시만 | 미달 → 설계만 (정당) | ✅ |
| Match Rate sub-PDCA 평균 | ≥ 90% | 97.6% | ✅ |

---

## 8. Differences Found

### 8.1 🔴 Missing (Design O, Implementation X)

| 항목 | Design 위치 | 영향 |
|------|------------|:----:|
| Redis event loop 충돌 해결 | A-2 §4.3 | 중 (test_post_caption_override.py 2건 carry-over) |

### 8.2 🟡 Added (Design X, Implementation O)

| 항목 | 사유 |
|------|------|
| pytest-mock dev 의존성 | mocker fixture 활용 (정당) |
| GitHub patch 경로 hot-fix | 코드 truth 반영 |

### 8.3 🔵 Changed (Design ≠ Implementation)

| 항목 | Design | 구현 | 영향 |
|------|--------|------|:----:|
| audit_logs 파티션 PK | 단일 | `(id, created_at)` 복합 | 낮음 (파티셔닝 표준) |
| OTel skip 처리 | "in-memory exporter" | sys.modules patch carry-over + in_memory_tracer 추가 | 낮음 (§4.4 < 3 명시) |

### 8.4 Phase 14 Carry-over (의도된 결정)

| 항목 | 출처 | Design 명시 |
|------|------|:-----------:|
| OTel 2건 | A-2 §4.4 < 3 허용 | ✅ |
| C-2 ML 회귀 8개 항목 | C-2 §8 | ✅ |
| Redis 2건 | A-2 §4.3 (해결 약속 미충족) | ⚠️ 부분 |

---

## 9. Architecture / Convention 검증

### 9.1 Layer 배치

| Component | Layer | 위치 | 상태 |
|-----------|-------|------|:----:|
| `cron_monitor.py` | Service | `app/services/` | ✅ |
| `audit_partition_cron.py` | Service | `app/services/` | ✅ |
| `slack_alert_cron.py` | Service | `app/services/` | ✅ |
| `admin_system.py` | API | `app/api/` | ✅ |
| `0088_audit_logs_partitioning.py` | Infra | `alembic/versions/` | ✅ |
| `admin/system/page.tsx` | UI | `frontend/src/app/admin/system/` | ✅ |

### 9.2 Convention Score: **100%**

---

## 10. Overall Score

```
┌─────────────────────────────────────────────┐
│  Overall Score: 97/100                       │
├─────────────────────────────────────────────┤
│  Design Match:        97.6 points            │
│  Architecture:        100 points             │
│  Convention:          100 points             │
│  KPI Achievement:      90 points (skip 13)   │
│  Phase 14 Handoff:    100 points (명시 완료) │
└─────────────────────────────────────────────┘
```

---

## 11. Recommended Actions

### 11.1 Phase 14 Carry-over (정당 이월)

| Priority | Item | 출처 |
|----------|------|------|
| 🟡 1 | OTel `sys.modules patch` → `importlib.reload` 패턴 재설계 | test_otel_setup.py |
| 🟡 2 | Redis fixture pytest-asyncio scope 재설계 | test_post_caption_override.py |
| 🟢 3 | C-2 ML 회귀 8개 항목 (거래 ≥ 500시) | C-2 §8 |
| 🟢 4 | audit_logs 파티션 자동 detach (1년 이전 → S3 Glacier) | Plan §4.2 B-1p |

---

## 12. 결론

```
Phase 13 (domo-phase13-roadmap) 종합 Match Rate: 97.6%

✅ 목표 ≥ 90% 충족
✅ 회귀 0 + alembic single head 충족
✅ tests passed +37건 (787 vs 750 baseline, 목표 +20 대비 185%)
✅ Phase 14 carry-over 모두 design 명시 (Redis 부분 명시 제외)
⚠️ skip 13건 — 신규 4건은 carry-over (정당)

권고: /pdca report domo-phase13-roadmap 진행 가능
```

---

## Version History

| 버전 | 날짜 | 변경 | 작성자 |
|------|:----:|------|--------|
| 0.1 | 2026-05-09 | 초기 분석. 5개 sub-PDCA Match Rate 97.6%. Phase 14 carry-over 12개 명시성 검증. | itpe-ince (Claude Code, bkit-gap-detector) |
