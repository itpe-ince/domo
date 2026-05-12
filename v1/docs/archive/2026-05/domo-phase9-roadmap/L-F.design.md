---
template: design
version: 1.0
feature: translation-memory-cohort-alert
phase: 9 / L-F
date: 2026-05-05
author: itpe-ince (Claude Sonnet 4.6)
project: domo
project_version: v1
parent_plan: domo-phase9-roadmap.plan.md
alembic: "0071, 0072"
status: Draft
---

# Phase 9 L-F Design — 번역 메모리 + Cohort Retention 자동 Slack 알림

> **Summary**: tuzigroup LLM Gateway(gemma4-e4b)로 번역한 결과를 DB에 영구 저장하고
> Redis에 24h TTL 캐싱해 중복 번역 호출을 차단한다(alembic 0071 `translation_cache`).
> 동시에 Phase 8 B'-5 cohort retention 지표가 임계치 미달 시 Slack Incoming Webhook으로
> 자동 알림을 발송하고 중복 알림을 방지하는 `cohort_alerts` 이력 테이블을 추가한다(alembic 0072).
> API 엔드포인트 추가 없음 — 순수 백엔드 인프라 강화.

---

## 1. 목표 & Acceptance Criteria

### 목표

| # | 목표 | 근거 |
|---|------|------|
| 1 | 번역 메모리 DB 캐싱으로 LLM Gateway 호출 비용 60%↓ | 글로벌 5개 locale × 반복 번역 고비용 해소 |
| 2 | source_hash UNIQUE 인덱스로 O(1) cache lookup | 동일 원문 번역 요청 시 LLM Gateway 미호출 |
| 3 | 90일 미사용 캐시 자동 정리 cron | DB 무한 증가 방지 |
| 4 | 7일/30일 retention 임계치 미달 시 Slack 자동 알림 | 지표 저하를 팀이 즉시 인지 |
| 5 | 24h cooldown으로 Slack 스팸 방지 | cohort_alerts.status 기반 중복 차단 |
| 6 | SLACK_WEBHOOK_URL 미설정 시 log-only Mock 모드 | CI/개발 환경 graceful fallback |

### Acceptance Criteria

- [ ] `translation_cache` 테이블 생성 (alembic 0071 upgrade/downgrade green)
- [ ] `cohort_alerts` 테이블 생성 (alembic 0072 upgrade/downgrade green)
- [ ] 동일 원문+언어 쌍 2회 번역 요청 시 2회차는 LLM Gateway 미호출 (cache hit 로그 확인)
- [ ] cache miss 시 LLM Gateway 호출 후 `translation_cache` INSERT 확인
- [ ] `hit_count` 증가 + `last_used_at` 갱신 (hit 시마다)
- [ ] D7 retention < COHORT_ALERT_7D_THRESHOLD 시 `cohort_alerts` INSERT + Slack 발송 확인
- [ ] 24h 이내 동일 metric_name cohort_alerts 재발송 없음 확인
- [ ] SLACK_WEBHOOK_URL 미설정 시 ERROR 없이 log 출력만 확인
- [ ] 14번째 cron worker `cohort_alert_worker` app startup 등록 확인
- [ ] 기존 번역 호출 경로(story_translator.py) 회귀 없음 (기존 테스트 통과)

---

## 2. Database Schema

### alembic 0071 — `translation_cache`

```
revision: 0071_translation_memory
down_revision: 0070_wcag_aaa_accessibility
```

#### 테이블 정의

| 컬럼 | 타입 | 제약 | 설명 |
|------|------|------|------|
| id | UUID PK | default uuid_generate_v4() | 기본키 |
| source_hash | VARCHAR(64) | NOT NULL | source_text의 SHA-256 hex digest |
| source_lang | VARCHAR(5) | NOT NULL | 원문 언어 코드 (ko/en/ja/zh/es) |
| target_lang | VARCHAR(5) | NOT NULL | 대상 언어 코드 |
| source_text | TEXT | NOT NULL | 원문 전체 (재확인 + audit용) |
| translated_text | TEXT | NOT NULL | 번역 결과 |
| model_version | VARCHAR(50) | NOT NULL | LLM 모델 식별자 (예: gemma4-e4b) |
| hit_count | INTEGER | NOT NULL DEFAULT 0 | cache hit 누적 횟수 |
| created_at | TIMESTAMPTZ | NOT NULL DEFAULT now() | 최초 번역 시각 |
| last_used_at | TIMESTAMPTZ | NOT NULL DEFAULT now() | 마지막 hit 시각 (TTL cleanup 기준) |

#### 인덱스

```sql
-- 조회 기본키 (cache lookup)
UNIQUE INDEX uq_translation_cache_hash_langs
    ON translation_cache (source_hash, source_lang, target_lang);

-- TTL cleanup cron용 (90일 미사용 행 조회)
INDEX ix_translation_cache_last_used_at
    ON translation_cache (last_used_at);
```

#### 설계 결정

- `source_text`를 저장하는 이유: 해시 충돌 방지 + 모델 변경 시 내용 검증 가능
- `model_version` 필드: LLM 모델 업그레이드 시 해당 모델로 캐시된 행만 invalidate 가능
  - 구현: 모델 변경 시 `DELETE FROM translation_cache WHERE model_version != '{new_model}'`
- SHA-256 hex 64자 사용: MD5(32자) 대비 충돌 확률 무시 가능 수준

---

### alembic 0072 — `cohort_alerts`

```
revision: 0072_cohort_alerts
down_revision: 0071_translation_memory
```

#### 테이블 정의

| 컬럼 | 타입 | 제약 | 설명 |
|------|------|------|------|
| id | UUID PK | default uuid_generate_v4() | 기본키 |
| cohort_date | DATE | NOT NULL | 측정 대상 cohort 날짜 (어제) |
| metric_name | VARCHAR(50) | NOT NULL | 지표 이름 (d7_retention / d30_retention) |
| value | NUMERIC(5,4) | NOT NULL | 측정값 (0.0000~1.0000) |
| threshold | NUMERIC(5,4) | NOT NULL | 적용된 임계값 |
| status | VARCHAR(20) | NOT NULL DEFAULT 'pending' | pending / sent / skipped / error |
| slack_message_ts | VARCHAR(50) | NULL | Slack API 응답 ts (메시지 추적용) |
| error_message | TEXT | NULL | 발송 실패 시 에러 메시지 |
| created_at | TIMESTAMPTZ | NOT NULL DEFAULT now() | 알림 생성 시각 |
| sent_at | TIMESTAMPTZ | NULL | 실제 발송 시각 |

#### 인덱스

```sql
-- cooldown 조회 (24h 중복 방지)
INDEX ix_cohort_alerts_metric_created
    ON cohort_alerts (metric_name, created_at DESC);

-- 특정 날짜 cohort 중복 방지
UNIQUE INDEX uq_cohort_alerts_date_metric
    ON cohort_alerts (cohort_date, metric_name);
```

#### status 흐름

```
pending → sent      (Slack 발송 성공)
pending → skipped   (24h cooldown 적용 — 이미 sent 이력 존재)
pending → error     (Slack 발송 실패 — webhook 오류 등)
```

---

## 3. Service Layer

### 3-1. 번역 메모리 — `story_translator.py` 수정

기존 24h 인-메모리 캐시(`_TRANSLATION_CACHE` dict)를 DB + Redis 2-tier 캐시로 교체한다.
인-메모리 dict는 프로세스 재시작 시 소멸되므로 DB 영구 저장이 필요하다.

#### 캐시 조회 흐름

```
translate_text(text, source_lang, target_lang) 호출
    ↓
1. Redis GET translation:{source_hash}:{source_lang}:{target_lang}
   └─ hit → 즉시 반환 (DB 접근 없음, 최속)
    ↓ miss
2. DB SELECT translation_cache WHERE source_hash=? AND source_lang=? AND target_lang=?
   └─ hit → UPDATE hit_count+1, last_used_at=now()
          → Redis SET (24h TTL)
          → translated_text 반환
    ↓ miss
3. LLM Gateway 호출 (tuzigroup gemma4-e4b)
   └─ DB INSERT translation_cache
   └─ Redis SET (24h TTL)
   └─ translated_text 반환
```

#### 핵심 함수 시그니처

```python
# app/services/story_translator.py 수정 내용

async def _db_cache_get(
    db: AsyncSession,
    source_hash: str,
    source_lang: str,
    target_lang: str,
) -> str | None:
    """DB에서 번역 캐시 조회. hit 시 hit_count, last_used_at 갱신."""

async def _db_cache_set(
    db: AsyncSession,
    source_text: str,
    source_hash: str,
    source_lang: str,
    target_lang: str,
    translated_text: str,
    model_version: str,
) -> None:
    """DB에 번역 결과 저장 (INSERT ON CONFLICT DO NOTHING — 동시 요청 안전)."""

async def translate_with_memory(
    db: AsyncSession,
    text: str,
    source_lang: str,
    target_lang: str,
) -> str:
    """번역 메모리 통합 진입점. Redis → DB → LLM Gateway 순 조회."""
```

#### Redis 키 설계

```
translation:{source_hash}:{source_lang}:{target_lang}
  예: translation:a3f1b2c4...:{ko}:{en}
  TTL: 86400초 (24h)
  값: JSON {"text": "...", "model": "gemma4-e4b"}
```

#### source_hash 계산

```python
import hashlib

def _compute_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
```

#### 기존 in-memory 캐시 하위 호환

`translate_bio_to_all_locales`와 `translate_milestone_text`는 기존 `_cache_get`/`_cache_set` 호출을 `translate_with_memory(db, ...)` 호출로 교체한다. 단, `translate_milestone_text`는 DB session이 없으므로 의존성을 추가하거나 인-메모리 캐시를 유지한다 — 구현 시 결정(OQ 사항).

---

### 3-2. 번역 캐시 cleanup cron (선택적 — 90일 TTL)

```python
# 기존 cron job 중 하나(예: gdpr_jobs.py)에 통합하거나 독립 함수 추가

async def cleanup_translation_cache(db: AsyncSession) -> int:
    """90일 이상 미사용 캐시 행 삭제. 삭제 건수 반환."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=90)
    result = await db.execute(
        delete(TranslationCache).where(TranslationCache.last_used_at < cutoff)
    )
    await db.commit()
    return result.rowcount
```

cleanup은 독립 cron이 아닌 gdpr_cron_loop 내 1일 1회 실행으로 통합한다 (cron 수 최소화).

---

### 3-3. Cohort 자동 알림 — `cohort_alert_jobs.py` (신규)

#### 파일 위치

`/Users/sangincha/dev/domo/v1/backend/app/services/cohort_alert_jobs.py`

#### 핵심 함수

```python
async def check_and_alert_once(db: AsyncSession) -> dict:
    """일 1회 실행. 어제 cohort 지표를 측정하고 임계치 미달 시 Slack 알림 발송.

    Returns:
        {"checked": int, "alerted": int, "skipped": int, "errors": int}
    """

async def _measure_cohort_retention(
    db: AsyncSession,
    cohort_date: date,
    days: int,
) -> float | None:
    """cohort_date에 가입한 사용자의 days일 후 retention 비율 계산.

    retention = (cohort_date 가입 유저 중 days일 후 접속한 유저 수) / (cohort_date 가입 유저 수)
    데이터 부족(cohort_date 가입자 < 10명) 시 None 반환 (측정 불가).
    """

async def _send_slack_alert(
    cohort_date: date,
    metric_name: str,
    value: float,
    threshold: float,
) -> str | None:
    """Slack Incoming Webhook으로 알림 발송.

    SLACK_WEBHOOK_URL 미설정 시: log.warning 출력 후 None 반환 (Mock 모드).
    성공 시: Slack ts 문자열 반환.
    실패 시: HTTPError 재발생.
    """

async def cohort_alert_cron_loop(interval_seconds: int = 86400) -> None:
    """R-5 격리 cron. 매일 06:00 UTC 타겟으로 86400s 간격 실행."""
```

#### Slack 메시지 형식

```json
{
  "text": ":warning: Cohort Retention 임계치 미달",
  "blocks": [
    {
      "type": "section",
      "text": {
        "type": "mrkdwn",
        "text": "*:warning: Cohort Retention Alert*\n\n*Cohort 날짜*: 2026-05-04\n*지표*: D7 Retention\n*현재값*: 22.3%\n*임계치*: 30.0%\n*차이*: -7.7%p\n\n<https://domo.app/admin/analytics|대시보드 바로가기>"
      }
    }
  ]
}
```

#### 임계치 환경변수

```bash
# .env (기본값: plan.md 기준)
COHORT_ALERT_7D_THRESHOLD=0.30      # 30% — D7 retention 경고 기준
COHORT_ALERT_30D_THRESHOLD=0.15     # 15% — D30 retention 경고 기준
COHORT_ALERT_MIN_COHORT_SIZE=10     # 최소 cohort 크기 (미만 시 측정 skip)
SLACK_WEBHOOK_URL=                  # 미설정 시 Mock 모드
```

> 주의: plan.md §L-F Scope에는 D7 < 50%, D30 < 30%로 기재되어 있으나,
> roadmap.plan.md KPIs 임계치는 보수적으로 잡혀 있다. 사용자 확인 사항(OQ-L-F-1).
> 기본값은 roadmap.plan.md 명시값(D7 < 30%, D30 < 15%)을 따른다.

#### 중복 방지 로직

```python
# UNIQUE INDEX uq_cohort_alerts_date_metric (cohort_date, metric_name) 이용
# 같은 날 같은 지표는 INSERT 시 ON CONFLICT DO NOTHING → status=skipped 처리
```

#### retention 측정 쿼리 개요

```sql
-- cohort_date 가입자 수
SELECT COUNT(*) FROM users
WHERE DATE(created_at AT TIME ZONE 'UTC') = :cohort_date;

-- days일 후 활성 유저 수 (user_sessions 또는 behavioral_history 테이블 이용)
-- Phase 8 H'-6 behavioral_history가 존재하므로 해당 테이블 기반 측정
SELECT COUNT(DISTINCT user_id) FROM behavioral_history
WHERE user_id IN (
    SELECT id FROM users
    WHERE DATE(created_at AT TIME ZONE 'UTC') = :cohort_date
)
AND DATE(created_at AT TIME ZONE 'UTC') = :cohort_date + INTERVAL ':days days';
```

---

## 4. API Endpoints

없음. L-F는 순수 백엔드 인프라:
- 번역 메모리: 기존 번역 호출 경로 내부 변경만
- cohort alert: 일 1회 cron 내부 실행

외부 노출 API 없음 → 프론트엔드 변경 없음.

---

## 5. Frontend Changes

없음.

---

## 6. Mock 모드 Fallback

### LLM Gateway 미설정 (번역 메모리)

```python
# LLMGatewayClient.is_mock == True 시
# translate_text() → "[MOCK {target_lang}] {text[:80]}" 반환
# → translation_cache INSERT 시 model_version="mock-gateway"로 저장
# → 실제 환경 전환 시 DELETE WHERE model_version='mock-gateway' 필요
```

### SLACK_WEBHOOK_URL 미설정 (cohort alert)

```python
async def _send_slack_alert(...) -> str | None:
    webhook_url = settings.slack_webhook_url
    if not webhook_url:
        log.warning(
            "[CohortAlert] Mock mode — SLACK_WEBHOOK_URL 미설정. "
            "metric=%s value=%.4f threshold=%.4f",
            metric_name, value, threshold,
        )
        return None  # Mock 모드: ts=None → cohort_alerts.status='sent' (log-only)
    # 실제 발송 로직 ...
```

Mock 모드에서도 `cohort_alerts` 행은 INSERT되고 status는 'sent'(log-only)로 기록한다.
이렇게 해야 24h cooldown이 동작해 Mock 환경에서도 중복 로그가 발생하지 않는다.

---

## 7. i18n Keys

없음. 번역 메모리는 백엔드 캐시 레이어이고, cohort alert는 Slack 메시지(영어 고정).
프론트엔드 i18n 키 추가 없음.

---

## 8. Test Plan

### 8-1. 번역 메모리 테스트

**파일**: `v1/backend/tests/test_translation_memory.py`

| 테스트 케이스 | 검증 내용 |
|-------------|---------|
| `test_cache_miss_calls_llm` | DB + Redis 모두 없을 때 LLM Gateway 호출 1회 확인 |
| `test_cache_hit_db_no_llm_call` | DB에 캐시 존재 시 LLM Gateway 미호출 확인 |
| `test_cache_hit_redis_no_db_call` | Redis hit 시 DB 조회 없음 확인 |
| `test_hit_count_increments` | DB hit 시 hit_count 1 증가 확인 |
| `test_last_used_at_updated` | DB hit 시 last_used_at 현재 시각으로 갱신 확인 |
| `test_same_source_diff_targets` | 동일 원문 ko→en / ko→ja 별도 캐시 항목 생성 확인 |
| `test_source_hash_consistency` | 동일 텍스트 SHA-256 해시 결정적(deterministic) 확인 |
| `test_cleanup_removes_old_entries` | 90일 초과 last_used_at 행 cleanup 확인 |
| `test_model_version_stored` | INSERT 시 model_version 필드 올바르게 저장 확인 |

**Mock 전략**: LLMGatewayClient.translate_text를 `AsyncMock`으로 패치.
DB는 SQLAlchemy in-memory SQLite (또는 테스트 PostgreSQL).

### 8-2. Cohort Alert 테스트

**파일**: `v1/backend/tests/test_cohort_alert_jobs.py`

| 테스트 케이스 | 검증 내용 |
|-------------|---------|
| `test_alert_triggered_below_threshold` | D7 retention < threshold → cohort_alerts INSERT + Slack 호출 확인 |
| `test_no_alert_above_threshold` | D7 retention >= threshold → cohort_alerts INSERT 없음 확인 |
| `test_cooldown_prevents_duplicate` | 24h 이내 동일 metric_name 알림 2회 요청 시 2회차 skipped 확인 |
| `test_slack_mock_mode_no_error` | SLACK_WEBHOOK_URL="" → 예외 없이 log 출력만 확인 |
| `test_slack_sent_status_recorded` | 발송 성공 시 status='sent', sent_at 기록 확인 |
| `test_small_cohort_skipped` | cohort 크기 < COHORT_ALERT_MIN_COHORT_SIZE 시 측정 skip 확인 |
| `test_d30_retention_alert` | D30 retention < COHORT_ALERT_30D_THRESHOLD → 별도 알림 확인 |
| `test_env_threshold_override` | 환경변수 변경 시 임계값 반영 확인 |

**Mock 전략**: httpx.AsyncClient를 `respx` 또는 `AsyncMock`으로 패치 (Slack webhook).
`_measure_cohort_retention`은 fixture DB에 가입자/활동 데이터 직접 삽입.

### 테스트 총계 목표

L-F 신규: 9 + 8 = **17개 테스트**
기존 번역 경로 회귀: story_translator 기존 테스트 통과 확인 (회귀 없음)

---

## 9. 위임 Agent

**bkend-expert 단독** (프론트엔드 변경 없음, 순수 백엔드)

| 작업 항목 | 담당 |
|----------|------|
| alembic 0071 `translation_cache` migration | bkend-expert |
| alembic 0072 `cohort_alerts` migration | bkend-expert |
| `TranslationCache` SQLAlchemy 모델 추가 | bkend-expert |
| `CohortAlert` SQLAlchemy 모델 추가 | bkend-expert |
| `story_translator.py` 번역 메모리 통합 | bkend-expert |
| `cohort_alert_jobs.py` 신규 작성 | bkend-expert |
| `app/main.py` 14번째 cron worker 등록 | bkend-expert |
| `app/core/config.py` 환경변수 추가 | bkend-expert |
| `test_translation_memory.py` 작성 | bkend-expert |
| `test_cohort_alert_jobs.py` 작성 | bkend-expert |

---

## 10. Open Questions

| # | 질문 | 기본값 / 권장 |
|---|------|-------------|
| OQ-L-F-1 | D7/D30 임계치: plan.md(D7<50%, D30<30%) vs roadmap KPI(D7<30%, D30<15%) 어느 것이 맞는가? | **roadmap KPI 우선** (D7<30%, D30<15%) — env 변수로 조정 가능 |
| OQ-L-F-2 | `translate_milestone_text` DB session 주입: 함수 시그니처에 `db: AsyncSession` 추가 vs 인-메모리 캐시 유지? | **인-메모리 캐시 유지** (밀스톤 텍스트는 반복 패턴이 적어 DB 캐시 ROI 낮음) |
| OQ-L-F-3 | cleanup cron을 별도 15번째 worker로 추가 vs gdpr_cron_loop 내 통합? | **gdpr_cron_loop 통합** (86400s 기존 주기 재사용, cron 수 최소화) |
| OQ-L-F-4 | Mock 모드 번역 결과(`[MOCK en] ...`)를 DB에 저장할 것인가? | **저장함** (model_version='mock-gateway' 태깅 → 프로덕션 전환 시 일괄 삭제 가능) |

---

## 11. 구현 순서 (권장)

```
Day 1  alembic 0071 + 0072 migration 작성 및 검증
       TranslationCache / CohortAlert SQLAlchemy 모델 추가
       config.py 환경변수(SLACK_WEBHOOK_URL, COHORT_ALERT_*) 추가

Day 2  story_translator.py 번역 메모리 통합 (_db_cache_get/_db_cache_set)
       Redis 2-tier 캐시 연동 (cache.py CacheClient 활용)
       test_translation_memory.py 작성 → all pass

Day 3  cohort_alert_jobs.py 신규 작성
       (_measure_cohort_retention + _send_slack_alert + check_and_alert_once)
       test_cohort_alert_jobs.py 작성 → all pass

Day 4  app/main.py 14번째 cron 등록
       통합 테스트 (기존 story_translator 테스트 회귀 없음 확인)
       smoke test 스크립트 실행 (번역 캐시 hit 확인, Slack Mock 모드 확인)
```

---

## 12. KPI 기준

| 지표 | 목표 | 측정 방법 |
|------|------|---------|
| 번역 캐시 hit rate | ≥ 60% (14일 운영 후) | `SELECT SUM(hit_count) / COUNT(*) FROM translation_cache` |
| LLM Gateway 번역 비용 절감 | ≥ 50% (캐시 미적용 대비 추산) | hit_count 총합 × 평균 토큰 비용 계산 |
| Cohort 알림 발송 정확도 | 100% (임계치 미달 시 누락 0) | cohort_alerts WHERE status='sent' 이력 |
| 알림 중복 발생 | 0건 (24h cooldown) | cohort_alerts WHERE status='skipped' 건수 모니터링 |
| alembic 0071+0072 CI | green (upgrade + downgrade) | GitHub Actions alembic check |
