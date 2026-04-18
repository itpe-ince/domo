# Design — Domo Settlement (정산 배치)

**Feature**: domo-settlement
**Plan Reference**: [domo-settlement.plan.md](../../01-plan/features/domo-settlement.plan.md)

## 1. 모델: settlements + settlement_items
## 2. Order 상태: settled → inspection_complete (검수 완료) / settled (배치 포함) / paid_out (지급)
## 3. API: 작가 2개 + 관리자 4개 + 크론잡
## 4. system_settings: settlement_cycle (weekly/monthly)
## 5. 구현 순서: 마이그레이션 → 모델 → 서비스 → API → 크론 → 관리자 페이지
