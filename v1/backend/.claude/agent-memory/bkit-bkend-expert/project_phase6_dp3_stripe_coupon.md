---
name: Phase 6 D'-3 Stripe Coupon Foundation
description: D'-3 완료: alembic 0046, AppliedCoupon model, CouponProvider ABC+Mock+Stripe, 5 endpoints, SubscriptionCard badge, 13 tests
type: project
---

D'-3 stripe-coupon-foundation 완료 (2026-05-04)

**Why:** Phase 5 B-5 CancelSubscriptionModal win-back placeholder("준비 중" badge) 실제 coupon 발행 인프라 구축. D' 단계 5번째 sub-PDCA.

**How to apply:** D' 단계 6/6 완료 (D'-1~D'-5 + D'-3). A 단계 진입 가능.

## Backend 완료 목록
- alembic 0046_applied_coupons (20ch): applied_coupons 테이블 + 3 인덱스
- app/models/coupon.py: AppliedCoupon SQLAlchemy model
- app/services/payments/coupon.py: CouponProvider ABC + MockCouponProvider + StripeCouponProvider
- app/services/payments/factory.py: get_coupon_provider() 추가
- app/schemas/coupon.py: AdminCreateCouponRequest (model_validator cross-field), CouponOut, ApplyCouponRequest, AppliedCouponOut
- app/api/admin_coupons.py: POST/GET/DELETE /admin/coupons (admin-only + rate_limit)
- app/api/me_coupons.py: POST /me/coupons/apply + GET /me/coupons
- app/core/rate_limit.py: admin_coupons_write(60/min), me_coupons_apply(5/min), me_coupons_read(60/min)
- app/main.py: admin_coupons_router + me_coupons_router 등록
- tests/integration/test_coupons.py: 13 tests (baseline 158 → 171)

## Frontend 완료 목록
- lib/api.ts: CouponView, AppliedCouponView, AdminCreateCouponInput + 5 API 함수
- lib/hooks/useMyCoupons.ts: 사용자 coupon hook
- lib/hooks/useAdminCoupons.ts: admin coupon hook
- components/admin/CreateCouponModal.tsx: 신규 발행 form
- components/admin/CouponsList.tsx: admin 목록 테이블
- app/admin/coupons/page.tsx: admin 전용 page (auth gate)
- app/me/coupons/page.tsx: 사용자 coupon 적용 page
- components/sponsorships/SubscriptionCard.tsx: activeCoupon prop + 🎟 badge (B-3 booster)
- 5 locale JSON: ~21 coupon.* 키 각 locale

## Carry-over (Phase 6.5+)
- B-5 win-back coupon 자동 발행 endpoint (POST /subscriptions/{id}/winback-coupon): 시간 부족 carry-over
- Stripe webhook handler for coupon events: D'-6 deferred
- Coupon analytics dashboard: A-1 통합 예정
