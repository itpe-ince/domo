# Gap Analysis — auction-promotion-suite (#11)

**Phase**: Phase 4 — Artist Tools (마지막 Critical Path)
**Date**: 2026-05-04
**Design**: `v1/docs/02-design/features/auction-promotion-suite.design.md` (v1.1, 662L)
**Plan**: `v1/docs/01-plan/features/auction-promotion-suite.plan.md` (v1.0, 535L)

---

## Match Rate: **92%**

| Category | Score | Status |
|----------|:-----:|:------:|
| Backend §B-1 ~ §B-14 (14 items) | 14/14 (100%) | ✅ |
| Frontend §F-1 ~ §F-12 (12 items) | 11/12 (92%) | ⚠️ |
| OQ-D Resolution (5 items) | 3/5 (60%) | ⚠️ |
| 15 ACs | 14/15 (93%) | ⚠️ |
| 5 Backend Risks (R-1~R-5) | 5/5 (100%) | ✅ |
| 7 Frontend Risks (R-FE-1~R-FE-7) | 7/7 (100%) | ✅ |
| **Overall** | **92%** | ✅ Above 90% gate |

**Recommendation**: ≥90% → Ready for `/pdca report`. C-1 + M-1을 fast-follow 또는 iterate로 처리하면 ~96% 도달 가능.

---

## Backend Section Coverage (§B-1 ~ §B-14): 14/14 = 100% ✅

| Section | Spec | Implementation | Status |
|---------|------|----------------|:------:|
| B-1 | 4 work groups (alembic+model+service+endpoint) | All present | ✅ |
| B-2 | Auction +5 columns | 5/5 | ✅ |
| B-3 | alembic 0042 + partial index | rev id 22ch + WHERE 매칭 | ✅ |
| B-4 | ShareCardResponse + AuctionOut +2 | Pydantic schema 일치 | ✅ |
| B-5 | 60s cron + SELECT FOR UPDATE SKIP LOCKED + idempotent UPDATE | Exact spec match | ✅ |
| B-6 | _auto_transition no-winner branch | `auctions.py:95-105` | ✅ |
| B-7 | share-card endpoint 6 steps | All steps present, 정확한 순서 | ✅ |
| B-8 | _generate_share_card Pillow + R-2/R-3/watermark | RGBA watermark + LANCZOS resize 모두 적용 | ✅ |
| B-9~B-10 | Visibility/comment lock 독립성 | 결합 없음 | ✅ |
| B-11 | 5 error codes | 모두 raise + status 매핑 | ✅ |
| B-12 | share_card 10/60sec by user | 일치 | ✅ |
| B-13 | 6 unit + 6 integration + smoke 4-step | 211L+240L+120L 확인 | ✅ |
| B-14 | 5 backend risks 완화 | 모두 코드에 반영 | ✅ |

---

## Frontend Section Coverage (§F-1 ~ §F-12): 11/12 = 92% ⚠️

| Section | Spec | Status |
|---------|------|:------:|
| F-1 | 2 components + ShareIcon + i18n | ⚠️ key audit mismatch |
| F-2 | 7 file changes | ✅ |
| F-3 | TS types incl. PostView.active_auction_end_at | ⚠️ Frontend 선언만 — backend 미공급 (C-1) |
| F-4 | AuctionShareCard z-[60] modal + 7 UX flows | ✅ |
| F-5 | AuctionCountdown 60s/1s adaptive + a11y | ✅ |
| F-6 | PostCard D-1h compact + posts/[id] full | ✅ (post detail는 `auction.end_at` 사용으로 정상 동작) |
| F-7 | ShareIcon SVG | ✅ |
| F-8 | NotificationCard `notification.type.auction.*` 4 keys | ❌ 5 locales 모두 미존재 (M-1) |
| F-9 | 14 i18n keys × 5 = 70 entries | ⚠️ `share.*` 중복 namespace 추가 (m-1) |
| F-10 | 5 integration regression 0 | ✅ tsc 0 + 73 tests pass |
| F-11 | 10-step PR3 implementation order | ✅ |
| F-12 | 7 frontend risks 완화 | ✅ |

---

## OQ-D Resolution: 3/5 ✅, 2/5 ❌

| ID | Decision | Status |
|----|----------|:------:|
| OQ-D-1 = A | PostView.active_auction_end_at backend 노출 | ❌ Frontend 선언만 — `_serialize_post` 미공급 |
| OQ-D-2 = B | _create_order_for_winner 재사용 + _auto_transition no-winner branch | ✅ |
| OQ-D-3 = A | NotificationCard fallback i18n key | ❌ M-1 |
| OQ-D-4 = A | _generate_share_card sync + run_in_executor | ✅ |
| OQ-D-5 = A | share_card_url 모든 viewer 노출 | ✅ |

---

## 15 Acceptance Criteria: 14/15 = 93%

| AC | Description | Status |
|----|-------------|:------:|
| AC-1 | 5 columns added, NULL on existing rows | ✅ |
| AC-2 | 24h cron sweep creates Notification | ✅ |
| AC-3 | Idempotent (2 sweeps = 1 notification) | ✅ |
| AC-4 | current_winner IS NULL → seller-only | ✅ |
| AC-5 | seller==current_winner → 1 notification (R-4) | ✅ |
| AC-6 | share-card 200 + ShareCardResponse | ✅ |
| AC-7 | Non-owner → 403 | ✅ |
| AC-8 | Cache hit < 1h → cached=true, no Pillow re-execute | ✅ |
| AC-9 | thumbnail fetch fail → text-only fallback (200) | ✅ |
| AC-10 | Modal: PNG preview + download + copy URL | ✅ |
| AC-11 | OQ-7=C adaptive interval (60s/1s) | ✅ |
| AC-12 | **Feed card shows countdown when end_at < 1h** | ❌ **C-1 — backend `active_auction_end_at` 미공급** |
| AC-13 | "경매 종료" text after onEnded | ✅ |
| AC-14 | 5 locale i18n complete, 0 missing keys | ⚠️ M-1 + m-1 |
| AC-15 | 5 integration regression 0 | ✅ |

---

## Risks: 12/12 mitigation in code = 100% ✅

### Backend (R-1 ~ R-5)
- **R-1** cron 중복: SELECT FOR UPDATE SKIP LOCKED + UPDATE WHERE col IS NULL ✅
- **R-2** thumbnail fetch 실패: try/except + fallback rect ✅
- **R-3** Pillow 메모리: convert("RGB") + thumbnail((600,630)) ✅
- **R-4** seller==current_winner: `if winner != seller` 가드 ✅
- **R-5** auction_jobs.py 격리: 별도 파일 + 별도 AsyncSessionLocal ✅

### Frontend (R-FE-1 ~ R-FE-7)
- R-FE-1 시계 오차 / R-FE-2 setInterval leak / R-FE-3 clipboard 미지원 / R-FE-4 이미지 cache (bustUrl) / R-FE-5 종료 후 UI 갱신 / R-FE-6 active_auction_end_at graceful degradation / R-FE-7 D-1h 경계 timing — 모두 ✅

---

## Gaps Found

### 🔴 Critical (1)

**C-1**: `PostView.active_auction_end_at` not populated by backend
- **위치**: `v1/backend/app/api/posts.py:42-74` (`_serialize_post`) + `v1/backend/app/schemas/post.py:90-119` (`PostOut` 누락)
- **영향**: AC-12 실패. 프론트엔드 `PostCard` D-1h compact 카운트다운이 feed/explore/search에서 절대 표시되지 않음. R-FE-6 graceful degradation으로 crash는 없으나 OQ-10=B Feed 가시성 목표 미달
- **수정**: `PostOut` 스키마에 `active_auction_end_at: datetime | None = None` 추가 + `_serialize_post`에서 LEFT JOIN subquery로 active auction의 `end_at` 채우기. 약 0.5일 — Frontend 무수정

### 🟡 Major (1)

**M-1**: 4 `notification.type.auction.{ending.24h,ending.6h,ending.1h,ended}` i18n 키 누락
- **위치**: `v1/frontend/src/i18n/{ko,en,ja,zh,es}.json`
- **영향**: NotificationCard 알림 타입 라벨 미현지화 — 비한국어 사용자가 한국어 title/body 그대로 봄. AC-14 strict 실패
- **수정**: 4 keys × 5 locales = 20 entries 추가. 약 30분

### 🔵 Minor (2)

**m-1**: i18n namespace 중복 (`share.*` 와 `auction.shareCard.*`)
- 컴포넌트는 `share.*` 사용, design은 `auction.shareCard.*` 명시 — 거의 동일 문자열 두 namespace 공존
- **수정**: 한 namespace로 통합. 약 30분 — editor-i18n-cleanup carry-over와 묶기 권장

**m-2**: 서버측 알림 title/body 한국어 하드코딩 (`auction_promotion_jobs.py:35-45`)
- 비한국어 사용자가 한국어 push title 받음
- **범위**: Phase 4 외 — 향후 i18n PDCA로 처리

---

## Carry-over (이번 PDCA 외 후속)

1. **C-1 backend `active_auction_end_at` 공급** (0.5d) — AC-12 해결, Match Rate ~96%
2. **M-1 4 × 5 = 20 i18n entries** (30min) — AC-14 해결
3. **m-1 i18n namespace 통합** (30min) — editor-i18n-cleanup carry-over에 합류
4. **m-2 서버측 알림 i18n** — 향후 Phase

---

## Conclusion

92% Match Rate로 90% gate 통과. Backend §B 14/14 perfect, 73 tests pass + tsc 0 + 5 integration regression 0. C-1만이 유일한 Critical (graceful degradation으로 무해) — fast-follow 1d 작업으로 96% 도달 가능. **Phase 4 closure 적합**.

---

## Iteration 1 Result

**Date**: 2026-05-04
**Iteration**: 1/5
**Previous Match Rate**: 92%
**New Match Rate**: **97%**

### Changes Made

| Category | Before | After |
|----------|--------|-------|
| Frontend §F-1~§F-12 | 11/12 (92%) | 12/12 (100%) |
| OQ-D Resolution | 3/5 (60%) | 5/5 (100%) |
| 15 Acceptance Criteria | 14/15 (93%) | 15/15 (100%) |
| Backend §B / Risks | 100% | 100% (unchanged) |
| **Overall** | **92%** | **97%** |

### Gaps Closed

**C-1 (Critical) — `active_auction_end_at` backend supply: CLOSED**
- `PostOut` 스키마에 `active_auction_end_at: datetime | None = None` 추가
- `_serialize_post()` 내 `getattr(post, "_active_auction_end_at", None)` 읽기
- `_attach_active_auction_end_at()` 헬퍼: 단일 bulk 쿼리 (N+1 없음)
- 적용 endpoint: `home_feed`, `explore_posts`, `search_posts`, `my_bookmarks`, `get_post`, `create_post`
- 신규 테스트: 3 unit + 1 integration (총 77 passed ← 73 기준)
- AC-12, F-3, OQ-D-1: 해결

**M-1 (Major) — 4 × 5 = 20 i18n entries: CLOSED**
- `notification.type.auction.{ending.24h, ending.6h, ending.1h, ended}` 5 locale 모두 추가
- JSON 유효성 검증: 5/5 OK
- AC-14, F-8, OQ-D-3: 해결

### Files Modified

**Backend**:
- `v1/backend/app/schemas/post.py` — `PostOut.active_auction_end_at` 필드 추가
- `v1/backend/app/api/posts.py` — `_attach_active_auction_end_at()` 헬퍼 추가 + 6개 endpoint에 적용
- `v1/backend/tests/unit/test_active_auction_end_at.py` — 신규 (3 tests)
- `v1/backend/tests/integration/test_active_auction_end_at_endpoint.py` — 신규 (1 test)

**Frontend**:
- `v1/frontend/src/i18n/ko.json` — `notification.type.auction.*` 4 keys 추가
- `v1/frontend/src/i18n/en.json` — 동일
- `v1/frontend/src/i18n/ja.json` — 동일
- `v1/frontend/src/i18n/zh.json` — 동일
- `v1/frontend/src/i18n/es.json` — 동일

### Test Results

- pytest: **77 passed** (기준 73, 회귀 0)
- tsc --noEmit: **0 errors**

### Remaining Gaps

- **m-1** (minor): i18n namespace 중복 (`share.*` ↔ `auction.shareCard.*`) — editor-i18n-cleanup carry-over
- **m-2** (minor): 서버측 알림 title/body 한국어 하드코딩 — 향후 Phase

### Stop Condition

Match Rate 97% ≥ 95% target → **ITERATION COMPLETE**. `/pdca report auction-promotion-suite` 실행 권장.
