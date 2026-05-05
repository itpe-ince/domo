---
name: Phase 6 D'-2 Subscription Cancellation Tracking
description: D'-2 완료 — alembic 0044, Subscription +2 컬럼, cancel body 활용 + HTML sanitize, GET /churn endpoint, ChurnList 보강
type: project
---

Phase 6 D'-2 subscription-cancellation-tracking 완료 (2026-05-04).

**Why:** Phase 5 B-5 carry-over — CancelSubscriptionModal이 4 사유 + feedback을 전달하나 backend 모델에 컬럼 없어 로깅 불가. ChurnList placeholder 해소.

**How to apply:** 다음 Phase에서 ChurnList + GET /churn 응답 구조 변경 시 ChurnItem schema + api.ts ChurnListResponse 타입 함께 수정.

주요 변경:
- `alembic/versions/0044_subscription_cancellation.py` — Subscription +cancellation_reason(50) +cancellation_feedback(Text)
- `app/models/sponsorship.py` — Subscription 모델 2 컬럼 추가 (cancelled_at은 기존 존재)
- `app/schemas/sponsorship.py` — SubscriptionCancelRequest 신규 + SubscriptionOut 2 필드 추가
- `app/api/sponsorships.py` — cancel_subscription: body optional + HTML strip + audit log
- `app/schemas/patronage.py` — ChurnItem + ChurnListResponse 신규
- `app/api/me_patronage.py` — GET /me/patronage/churn 신규 endpoint (artist-only, 30/min)
- `app/core/rate_limit.py` — patronage_churn scope 30/min 추가
- `tests/integration/test_subscription_cancel_tracking.py` — 6 tests 신규
- Frontend: `lib/api.ts` ChurnItem/ChurnListResponse 타입 확장 + fetchChurnList body 수정
- Frontend: `components/sponsorships/ChurnList.tsx` — color-coded badge + feedback tooltip
- i18n 5 locale × 2 keys = 10 entries (patronage.churn.feedback.preview, patronage.churn.empty.celebrated)

alembic 결정: D'-1이 me_sponsor_settings를 rate_limit.py에 추가 확인 → 0044는 D'-2가 선점 가능.
HTML sanitize: `re.compile(r"<[^>]+>")` — bleach 불필요, 간단 strip으로 XSS 방어 충분.

Phase 5 D-6 이전 메모 (archived):
Test result (Phase 5 D-6): 109 baseline + 5 new = 114 passed.
prometheus_client 미설치 시 no-op stubs fallback.
