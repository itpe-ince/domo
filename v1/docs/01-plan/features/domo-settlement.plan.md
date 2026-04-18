# Plan — Domo Settlement (정산 배치 시스템)

**Feature**: domo-settlement
**Created**: 2026-04-18
**Phase**: Plan
**Status**: Draft

---

## 1. Problem Statement

현재 정산은 **콜렉터 검수 완료 즉시** 처리(`Order.settled_at = NOW()`).
고객 요구: **주간/월간 정산 주기**로 작가에게 지급 + 정산 내역 관리.

현재:
```
콜렉터 검수 → settled_at 기록 → (정산 완료로 간주)
```

필요:
```
콜렉터 검수 → 정산 대기 풀(pool) 진입
    ↓
주간/월간 배치 → 작가별 정산 금액 집계
    ↓
관리자 확인 → 정산 실행 (은행 이체 또는 Stripe Payout)
    ↓
정산 완료 → 작가 알림
```

---

## 2. Goals

1. **정산 대기 풀**: 검수 완료된 주문을 정산 대기 상태로 관리
2. **작가별 정산 집계**: 주기별(주간/월간) 정산 금액 자동 계산
3. **정산 배치 생성**: `settlements` 테이블에 배치 레코드 생성
4. **관리자 정산 실행**: admin 앱에서 정산 확인 + 실행
5. **정산 이력**: 작가가 자신의 정산 내역 조회

---

## 3. Data Model

### settlements (신규)

```sql
CREATE TABLE settlements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    artist_id UUID REFERENCES users(id) NOT NULL,
    period_start DATE NOT NULL,          -- 정산 기간 시작
    period_end DATE NOT NULL,            -- 정산 기간 종료
    order_count INT NOT NULL DEFAULT 0,  -- 포함된 주문 수
    gross_amount NUMERIC(12,2) NOT NULL, -- 총 판매금액
    platform_fee NUMERIC(12,2) NOT NULL, -- 플랫폼 수수료 합계
    net_amount NUMERIC(12,2) NOT NULL,   -- 작가 지급액 (gross - fee)
    currency VARCHAR(3) DEFAULT 'USD',
    status VARCHAR(20) DEFAULT 'pending',
    -- 'pending' | 'approved' | 'paid' | 'failed'
    approved_by UUID REFERENCES users(id),
    approved_at TIMESTAMPTZ,
    paid_at TIMESTAMPTZ,
    payout_reference VARCHAR(200),       -- 송금 참조번호
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_settlements_artist ON settlements(artist_id, period_end DESC);
```

### settlement_items (신규)

```sql
CREATE TABLE settlement_items (
    settlement_id UUID REFERENCES settlements(id) ON DELETE CASCADE,
    order_id UUID REFERENCES orders(id),
    PRIMARY KEY (settlement_id, order_id)
);
```

### Order 상태 확장

기존 `settled` 상태를 세분화:
- `inspection_complete` → 검수 완료, 정산 대기
- `settled` → 정산 배치에 포함됨
- `paid_out` → 작가에게 실제 지급 완료

---

## 4. 정산 주기

| 주기 | 정산일 | 대상 기간 |
|---|---|---|
| **주간** | 매주 월요일 | 전주 월~일 검수 완료 주문 |
| **월간** | 매월 1일 | 전월 1~말일 검수 완료 주문 |

system_settings에서 `settlement_cycle: "weekly" | "monthly"` 관리.
관리자가 런타임에 변경 가능.

---

## 5. API

### 작가 API
```
GET /settlements/mine         → 내 정산 내역 목록
GET /settlements/{id}         → 정산 상세 (포함 주문 목록)
```

### 관리자 API
```
GET /admin/settlements                → 정산 대기/완료 목록
POST /admin/settlements/generate      → 배치 생성 (수동)
POST /admin/settlements/{id}/approve  → 정산 승인
POST /admin/settlements/{id}/pay      → 정산 실행 (paid 처리)
```

### 크론잡
```python
async def settlement_cron_loop():
    """주간(월요일) 또는 월간(1일) 자동 배치 생성"""
```

---

## 6. 플로우

```
1. 콜렉터 검수 완료 (POST /orders/{id}/inspect)
       ↓
   Order.status = 'inspection_complete'  (기존 'settled' → 변경)
       ↓
2. 정산 배치 생성 (크론 또는 관리자 수동)
       ↓
   작가별 집계 → settlements 레코드 생성
   Order.status = 'settled' (배치에 포함됨)
       ↓
3. 관리자 승인
       ↓
   Settlement.status = 'approved'
       ↓
4. 정산 실행 (은행 이체 / Stripe Payout)
       ↓
   Settlement.status = 'paid'
   Order.status = 'paid_out'
   작가 알림
```

---

## 7. 구현 순서

| Step | 작업 | 작업량 |
|---|---|---|
| 1 | 마이그레이션 (settlements + settlement_items + Order 상태 변경) | S |
| 2 | 모델 (Settlement, SettlementItem) | S |
| 3 | 정산 배치 생성 로직 (서비스) | M |
| 4 | 작가 API (mine, detail) | S |
| 5 | 관리자 API (list, generate, approve, pay) | M |
| 6 | 크론잡 (주간/월간) | S |
| 7 | 관리자 admin 앱 정산 페이지 | M |
| 8 | 프론트 작가 정산 페이지 | S |
| 9 | system_settings에 settlement_cycle 추가 | S |

---

## 8. Dependencies

- Order 에스크로 플로우 (✅ 이미 구현: ship → inspect → settle)
- Stripe Payout API (글로벌 지급 — 외부 의존성, Mock으로 선행)
- 은행 이체 API (한국 — 외부 의존성, Mock으로 선행)

---

## 9. Next Step

✅ `/pdca design domo-settlement` → MockPayout으로 구현 착수
