# Phase 13 B-2: audit_logs 테이블 월별 파티셔닝

## 1. 배경 및 목적

Phase 11 D-2에서 도입된 `audit_logs` 테이블은 현재 단일 테이블(unpartitioned)로 운영 중이다.
감사 로그는 INSERT-only + 기간별 DELETE(cleanup) 패턴으로, PostgreSQL 선언적 파티셔닝의
최적 적용 대상이다.

**적용 근거**
- 단조 증가 데이터: 신규 행은 항상 현재 월 파티션에 삽입됨
- cleanup worker가 이미 `created_at` 기반으로 삭제 → 파티션 pruning으로 스캔 범위 극소화
- 월별 DROP PARTITION으로 cleanup 속도 O(n) → O(1) 향상 가능 (Phase 14+ 고려)
- 현재 데이터: 100건 미만(보수적 가정) → zero-downtime 이전 가능

---

## 2. 파티셔닝 전략

### 2.1 파티션 유형

```
PARTITION BY RANGE (created_at)
```

- 기준 컬럼: `created_at` (TIMESTAMPTZ, NOT NULL)
- 파티션 단위: 월(month) — `audit_logs_YYYY_MM`
- 파티션 경계: `[첫째 날 00:00:00 UTC, 다음 달 첫째 날 00:00:00 UTC)`

### 2.2 파티션 명명 규칙

```
audit_logs_2026_04   -- 2026-04-01 ~ 2026-04-30
audit_logs_2026_05   -- 2026-05-01 ~ 2026-05-31
...
audit_logs_default   -- 경계 밖 행 안전망 (DEFAULT PARTITION)
```

### 2.3 사전 생성 파티션 (alembic 0088)

| 파티션명 | FROM | TO |
|---|---|---|
| audit_logs_2026_04 | 2026-04-01 | 2026-05-01 |
| audit_logs_2026_05 | 2026-05-01 | 2026-06-01 |
| audit_logs_2026_06 | 2026-06-01 | 2026-07-01 |
| audit_logs_2026_07 | 2026-07-01 | 2026-08-01 |
| audit_logs_2026_08 | 2026-08-01 | 2026-09-01 |
| audit_logs_2026_09 | 2026-09-01 | 2026-10-01 |
| audit_logs_default | DEFAULT | — |

---

## 3. 마이그레이션 절차 (Zero-Downtime)

### 3.1 전략 선택 근거

현재 데이터 100건 미만(보수적 가정) → **신규 파티션 테이블 생성 + INSERT SELECT 이전** 방식.

100건 초과 환경(프로덕션 대규모)은 ATTACH PARTITION 방식 사용(주석 안내 포함).

### 3.2 단계별 절차

```
단계 1: audit_logs_new 파티션 테이블 생성 (PARTITION BY RANGE)
단계 2: 기본 파티션 6개 + DEFAULT 파티션 생성
단계 3: 인덱스 생성 (각 파티션에 자동 상속)
단계 4: INSERT INTO audit_logs_new SELECT * FROM audit_logs (데이터 이전)
단계 5: audit_logs 테이블 DROP
단계 6: audit_logs_new RENAME → audit_logs
단계 7: 외래키 재생성 불필요 (audit_logs는 참조되는 쪽이 없음)
```

**주의**: `audit_logs`는 다른 테이블에서 FK로 참조하는 테이블이 아니므로
rename 시 dependent FK 재생성 과정이 없어 단순하다.

### 3.3 대규모 데이터 ATTACH PARTITION 방식 (100건+ 환경)

```sql
-- 1. 신규 일반 테이블로 데이터 수집 (무중단)
CREATE TABLE audit_logs_new (LIKE audit_logs INCLUDING ALL);
INSERT INTO audit_logs_new SELECT * FROM audit_logs
  WHERE created_at >= '2026-04-01' AND created_at < '2026-05-01';

-- 2. CHECK 제약 추가 (ATTACH 시 스캔 생략)
ALTER TABLE audit_logs_new
  ADD CONSTRAINT chk_partition CHECK (
    created_at >= '2026-04-01' AND created_at < '2026-05-01'
  );

-- 3. ATTACH (잠금 최소화 — ShareLock만 필요)
ALTER TABLE audit_logs_partitioned
  ATTACH PARTITION audit_logs_new
  FOR VALUES FROM ('2026-04-01') TO ('2026-05-01');
```

---

## 4. 자동 Partition 생성 Cron

### 4.1 목적

매월 1일, 다음 달 파티션을 미리 생성. 파티션 누락 시 DEFAULT 파티션으로 fallback되어
데이터 손실은 없지만 쿼리 성능이 저하됨.

### 4.2 스펙

| 항목 | 값 |
|---|---|
| 파일 | `app/services/audit_partition_cron.py` |
| 함수 | `create_next_month_audit_partition(db: AsyncSession)` |
| 실행 주기 | `audit_partition_cron_loop(interval_seconds=86400)` — 매일 00:30 UTC 기준 |
| 멱등성 | 파티션 존재 시 `SKIP` (pg_class 체크) |
| 등록 위치 | `app/main.py` lifespan (25번째 cron worker) |

### 4.3 파티션 이름 생성 규칙

```python
# 다음 달 계산
today = date.today()
if today.month == 12:
    next_month = date(today.year + 1, 1, 1)
else:
    next_month = date(today.year, today.month + 1, 1)

partition_name = f"audit_logs_{next_month.year}_{next_month.month:02d}"
```

---

## 5. 인덱스 전략

파티션 테이블에서 인덱스는 **각 파티션에 로컬 인덱스**로 생성된다.
부모 테이블에 CREATE INDEX → 모든 파티션에 자동 복제.

| 인덱스 | 컬럼 | 목적 |
|---|---|---|
| ix_audit_logs_actor | (actor_id, created_at DESC) | actor별 최신 감사 조회 |
| ix_audit_logs_action | (action, created_at DESC) | action별 최신 감사 조회 |
| ix_audit_logs_target | (target_type, target_id) | 대상 객체별 감사 조회 |
| ix_audit_logs_created | (created_at DESC) | 기간별 조회 + cleanup |

파티션 pruning은 `WHERE created_at >= X AND created_at < Y` 형태의 쿼리에서 자동 동작.

---

## 6. Rollback 전략

### 6.1 alembic downgrade

```
audit_logs (partitioned) → audit_logs_backup 생성 → 데이터 이전 → 파티션 테이블 DROP
→ audit_logs_backup RENAME audit_logs → 인덱스 재생성
```

downgrade() 함수에서 위 절차를 `op.execute()`로 구현.

### 6.2 배포 전 체크리스트

- [ ] `alembic heads` → 단일 head (0088_audit_logs_partitioning)
- [ ] 기존 audit_logs 데이터 백업 확인 (pg_dump -t audit_logs)
- [ ] `PGDATA` 디스크 여유 공간 확인 (기존 테이블 2배 + 인덱스)
- [ ] `audit_partition_cron_loop` 등록 확인 (main.py lifespan)

### 6.3 롤백 결정 기준

| 상황 | 조치 |
|---|---|
| upgrade 중 INSERT SELECT 실패 | alembic downgrade 0086_password_reset_tokens |
| 파티션 누락으로 DEFAULT 파티션 급증 | audit_partition_cron_loop 재시작 |
| 쿼리 성능 저하 (프루닝 미작동) | EXPLAIN ANALYZE로 파티션 pruning 확인 |

---

## 7. 코드 변경 영향 범위

파티션은 PostgreSQL 레벨에서 투명하게 동작한다.
`audit_logs` 테이블명 그대로 INSERT/SELECT/DELETE하는 기존 코드는 변경 불필요.

**변경 없는 파일**
- `app/models/audit_log.py`
- `app/services/audit_log.py`
- `app/services/audit_log_cleanup_jobs.py`
- 모든 router에서의 `AuditLog` 사용처
