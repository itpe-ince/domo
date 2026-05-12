---
name: Phase 6 D'-2 Subscription Cancellation Tracking
description: D'-2 완료 — alembic 0044, Subscription +2 컬럼, cancel body 활용 + HTML sanitize + audit log, GET /churn endpoint, ChurnList 보강, 6 tests
type: project
---

Phase 6 D'-2 subscription-cancellation-tracking 완료 (2026-05-04).

**Why:** Phase 5 B-5 carry-over — CancelSubscriptionModal이 4 사유 + feedback을 전달하나 backend 모델에 컬럼 없어 로깅 불가. ChurnList placeholder → 실제 데이터 표시 해소.

**How to apply:** ChurnList + GET /churn 응답 구조 변경 시 ChurnItem schema (patronage.py) + api.ts ChurnListResponse 타입 함께 수정. HTML sanitize는 `_strip_html()` in sponsorships.py 재사용 가능.

주요 변경:
- `alembic/versions/0044_subscription_cancellation.py` — Subscription +cancellation_reason(50) +cancellation_feedback(Text)
- `app/models/sponsorship.py` — Subscription 모델 2 컬럼 추가 (cancelled_at은 기존 존재 → skip)
- `app/schemas/sponsorship.py` — SubscriptionCancelRequest 신규 + SubscriptionOut 2 필드 추가
- `app/api/sponsorships.py` — cancel_subscription: body optional + _strip_html() XSS 방어 + _log_action() audit log
- `app/schemas/patronage.py` — ChurnItem + ChurnListResponse 신규
- `app/api/me_patronage.py` — GET /me/patronage/churn 신규 endpoint (artist-only, 30/min)
- `app/core/rate_limit.py` — patronage_churn scope 30/min 추가
- `tests/integration/test_subscription_cancel_tracking.py` — 6 tests 신규
- Frontend: `lib/api.ts` ChurnItem/ChurnListResponse 타입 확장 + fetchChurnList body 수정
- Frontend: `components/sponsorships/ChurnList.tsx` — color-coded badge (5 variant) + feedback tooltip
- i18n 5 locale: patronage.churn.feedback.preview, patronage.churn.empty.celebrated

alembic 결정: 0043이 마지막 → D'-2가 0044 선점. D'-1은 별도 충돌 없음 확인.
HTML sanitize: regex `<[^>]+>` strip — bleach 불필요.
