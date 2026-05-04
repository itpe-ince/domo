---
template: plan
version: 1.0
feature: auction-promotion-suite
sub-pdca: "#11"
phase: Phase 4 — Artist Tools (마지막)
date: 2026-05-04
author: itpe-ince (Claude Opus 4.7 + bkit product-manager agent)
project: domo
project_version: v1
parent_roadmap: editor-revamp-roadmap.plan.md
estimate: M (4~5일)
status: oq_resolved
oq_resolved_at: 2026-05-04
---

# auction-promotion-suite Planning Document

> **Summary**: 옥션 종료 N시간 전 자동 알림 (in-app), 공유 카드 자동 생성 (open graph image via Pillow), 카운트다운 위젯 (클라이언트 사이드) 세 가지를 하나의 PDCA로 묶어 `B-4 옥션 종료 알림/홍보 도구` 요구사항을 구현한다. 신규 `auction_promotion_jobs.py` cron worker + `POST /v1/auctions/{id}/share-card` endpoint + `AuctionShareCard` / `AuctionCountdown` 컴포넌트가 주요 산출물이다.
>
> **Status**: Draft v0.1
> **Sub-PDCA**: #11 (Phase 4 마지막 — Critical Path 종결)
> **Parent Roadmap**: [editor-revamp-roadmap.plan.md](./editor-revamp-roadmap.plan.md)

---

## 0. Roadmap Context

`editor-revamp-roadmap.plan.md` §1.B-4에는 작가 기능 요구사항 3건이 다음과 같이 원문 그대로 명시되어 있다:

> - **가격 책정 보조** (시세 가이드, 추천 시작가) 제공 필요
> - **후원자/단골에게 먼저 공개** 옵션 제공 필요
> - **옥션 종료 알림/홍보 도구** 제공 필요

본 PDCA `#11 auction-promotion-suite`는 이 중 **"옥션 종료 알림/홍보 도구"** 요구사항을 구현하는 **Phase 4의 마지막 sub-PDCA**이다.

**Critical Path 현황**:

| # | Feature | 상태 |
|---|---------|:----:|
| #1 editor-role-gating | ✅ archived | |
| #2 editor-draft-autosave | ✅ archived | |
| #3 editor-responsive-redesign | ✅ archived | |
| #4 editor-media-ux | ✅ archived | |
| #6 editor-media-studio (image) | ✅ archived | #6-video 차단 |
| #8 publish-controls | ✅ archived | |
| #10 artist-tier-release | ✅ archived (2026-05-04, Match Rate 99%) | |
| **#11 auction-promotion-suite** | **본 PDCA** | |

본 PDCA 완료 시 `editor-revamp-roadmap` **11/12 sub-PDCA 완료** 상태가 된다 (#9 pricing-assist는 Phase 4.5 deferred, #6-video는 ffmpeg 인프라 차단). Phase 4는 본 PDCA로 종결된다.

roadmap §3 의존성상 Phase 4는 Phase 3 완료 후 진입한다. `#8 publish-controls`와 `#10 artist-tier-release`가 모두 archived 상태로 선행 의존성이 충족되었다. `#10`과 `#11`은 독립적이어서 병렬 진행이 가능하나 현재 #10이 먼저 완료된 상태다.

roadmap §4 #11 행: DB = `auctions.notification_jobs` (또는 별도 jobs 테이블), API = `POST /v1/auctions/{id}/share-card` + 알림 스케줄러, Frontend = `AuctionShareCard` + 알림 시스템.

---

## 1. Overview

### 1.1 What

| 영역 | 현재 | 목표 |
|------|------|------|
| 종료 임박 알림 | 없음 — `auction_jobs.py`는 settlement/second_chance만 처리 | 종료 24h·6h·1h 전 자동 in-app 알림 발송 (작가 + 최고입찰자 대상). idempotent 추적 컬럼 3개 |
| 공유 카드 | 없음 | `POST /v1/auctions/{id}/share-card` → Pillow 합성 PNG (작품 thumbnail + 현재가 + 종료까지 남은 시간 + 작가명). `auctions.share_card_url` + `share_card_generated_at` 캐시 |
| 카운트다운 위젯 | 없음 | 옥션 상세 페이지 + feed card(D-1h 이내) 에 실시간 D-N hr / N min / N sec 표시. 클라이언트 사이드 setInterval + 서버 end_at 동기화 |

### 1.2 Why

- roadmap §1.B-4 요구사항 "옥션 종료 알림/홍보 도구" 직접 충족
- 종료 임박 알림으로 입찰자의 반응 시간을 확보 → 입찰 활성도 증가 및 최종 낙찰가 상승
- 공유 카드 다운로드로 작가가 트위터/인스타 등 외부 SNS에 옥션을 홍보 → 플랫폼 외부 유입 채널 확보
- 카운트다운 위젯이 feed에서도 보여 입찰 임박 긴장감 형성 → CTR 개선

### 1.3 Background

**현재 코드베이스 상태 (검증 완료)**:

- `app/models/auction.py:19` — `Auction` 클래스. 컬럼: `status String(20)` (`scheduled`/`active`/`ended`/`cancelled`/`settled`), `start_at DateTime(timezone=True)`, `end_at DateTime(timezone=True)`, `current_winner UUID nullable`, `seller_id UUID`, `current_price Numeric`, `bid_count Integer`
- `app/models/auction.py:57` — `Bid` 클래스. `bidder_id`, `amount`, `status`
- `app/models/notification.py:11` — `Notification` 클래스. `user_id`, `type String(50)`, `title String(200)`, `body Text`, `link Text`, `is_read Boolean`. push/email 통합 dispatch 미존재 — in-app 전용
- `app/services/auction_jobs.py:35` — `process_expired_orders_once()`. settlement/second_chance 처리. `auction_cron_loop()` (5분 주기). 종료 임박 알림 로직 완전 부재
- `app/services/auction_jobs.py:166` — `Notification` 생성 패턴 (type, title, body, link). 동일 패턴 재사용 예정
- `auctions` 테이블 — `notified_24h_at`, `notified_6h_at`, `notified_1h_at`, `share_card_url`, `share_card_generated_at` 컬럼 **없음** (신규 추가 필요)

**재사용 가능 인프라**:

- `auction_jobs.py` — `AsyncSessionLocal` + asyncio cron 패턴. `auction_promotion_jobs.py`에 동일 구조 적용
- `Notification` 모델 — in-app 알림 생성. 추가 인프라 없이 즉시 활용 가능
- Pillow — 기존 `app/services/media_processing.py`의 이미지 변환 파이프라인 활용 가능
- `StorageProvider.put` — 공유 카드 PNG 저장 (기존 미디어 스토리지와 동일 provider)
- `app/api/posts.py` — Follow/Sponsorship 모델 활용 패턴 (#10 tier 자격 검증에서 확립)

### 1.4 Related Documents

- 부모 로드맵: [editor-revamp-roadmap.plan.md](./editor-revamp-roadmap.plan.md) §1.B-4, §2 Phase 4, §3 의존성, §4 #11 행
- 선행 아카이브: `docs/archive/2026-05/artist-tier-release/` (#10 — sponsorship/follow 모델 활용 패턴, Follow.followee_id 활용법)
- 선행 cron 패턴 참조: `app/services/auction_jobs.py`, `app/services/schedule_jobs.py`
- Phase 4.5 보류: `#9 artist-pricing-assist` (데이터 축적 후 별도 진행)
- 차단: `#6-video editor-media-studio` (ffmpeg 인프라)
- Phase 3 독립: `#12 notifications-ux-audit` (본 PDCA와 독립, 병렬 가능)

---

## 2. Scope

### 2.1 In Scope

#### A. 종료 임박 알림 (Notification dispatch)

- 대상 옥션: `status='active'` AND `end_at > now()` 인 옥션
- 알림 발송 시점: 종료 24h 전, 6h 전, 1h 전 (3 시점, OQ-1 권장 A)
- 알림 대상: (i) `auction.seller_id` (작가), (ii) `auction.current_winner` (현재 최고입찰자) — OQ-2 권장 B. 팔로워 알림은 스팸 위험으로 제외
- 채널: in-app `Notification` 행 생성 (기존 `app/models/notification.py:11` 활용) — OQ-3 권장 A. push/email 인프라는 별도 PDCA
- idempotent 추적: `auctions` 테이블에 `notified_24h_at DateTime(timezone=True) nullable`, `notified_6h_at DateTime(timezone=True) nullable`, `notified_1h_at DateTime(timezone=True) nullable` 3개 컬럼 추가 (OQ-4 권장 B). cron에서 `WHERE notified_Xh_at IS NULL AND end_at <= now() + interval 'Xh'` 패턴으로 중복 발송 방지
- 자기 자신 입찰 edge case: `seller_id == current_winner`이면 작가 알림 1건만 발송 (중복 제외, R-4)

**alembic `0042_auction_promotion_columns.py`**: `auctions.notified_24h_at` + `notified_6h_at` + `notified_1h_at` + `share_card_url` + `share_card_generated_at` 5개 컬럼 additive 추가. 기존 행 영향 없음 (all nullable).

**`app/services/auction_promotion_jobs.py` 신규**:
- `dispatch_auction_notifications_once(db: AsyncSession)` — single sweep
- `auction_promotion_cron_loop(interval_seconds: int = 60)` — 60초 주기 (OQ-1 권장 A의 1h 최소 발송 단위 대비 충분한 정밀도)
- `app/main.py` startup에 `asyncio.create_task(auction_promotion_cron_loop())` 등록

#### B. 공유 카드 자동 생성 (Auction Share Card)

- 신규 endpoint: `POST /v1/auctions/{id}/share-card`
- 생성 내용: 작품 thumbnail 이미지 + 현재 최고가 + 종료까지 남은 시간 텍스트 + 작가명 + 도메인 watermark (OQ-9 권장 A)
- 이미지 합성: Pillow (`PIL.Image`, `PIL.ImageDraw`, `PIL.ImageFont`) — 기존 `app/services/media_processing.py` 패턴 활용
- 외부 이미지 fetch 실패 시: fallback to text-only 카드 (작품명 + 현재가 + 종료시각, 배경색만) (R-2)
- 출력 크기: 1200×630 px (OG 표준, OQ-6 권장 A)
- 저장: `StorageProvider.put` 호출 → CDN URL 반환
- 캐시: `auctions.share_card_url` + `auctions.share_card_generated_at` 컬럼. `share_card_generated_at`이 1시간 이내이면 기존 URL 반환 (재생성 생략) — OQ-5 권장 B
- 응답: `AuctionShareCardResponse { share_card_url: str, generated_at: datetime, cached: bool }`
- 권한: 작가 본인(`seller_id`) 또는 관리자만 호출 가능

#### C. 카운트다운 위젯 (Frontend)

- 컴포넌트: `AuctionCountdown.tsx` — `end_at: string (ISO8601)` prop 수신 → 클라이언트 사이드 시계 계산
- 표시 형식: `D-1일 2시간` / `23시간 45분` / `N분 N초` (단계별 포맷)
- update interval: D-1h 이전에는 60초 갱신, D-1h 이내에는 1초 갱신 (OQ-7 권장 C, 배터리 + 정확성 균형)
- 종료 시: `auction.status='ended'` 상태로 표시 전환 (API polling 또는 SSE는 Out of Scope — 새로고침 후 반영)
- 서버 시간 동기화: `end_at`은 서버에서 제공 (UTC ISO8601). 클라이언트 시계 오프셋 보정 — `Date.now()` 기준 계산 (R-3)
- 위치: (i) 옥션 상세 페이지 (`/posts/[id]` — product post with active auction), (ii) feed card (D-1h 이내에만 표시, OQ-10 권장 B)

**`AuctionShareCard.tsx` 컴포넌트**:
- 작가 옥션 상세 페이지에서 "공유 카드 만들기" 버튼
- 클릭 시 `POST /v1/auctions/{id}/share-card` 호출 → 모달에 PNG preview + 다운로드 버튼 + URL 복사 버튼
- 생성 중 skeleton loader, 실패 시 에러 토스트

### 2.2 Frontend 컴포넌트 목록

| 컴포넌트 | 경로 | 용도 |
|---------|------|------|
| `AuctionShareCard` | `src/components/AuctionShareCard.tsx` | 공유 카드 생성 버튼 + 모달 preview |
| `AuctionCountdown` | `src/components/AuctionCountdown.tsx` | 실시간 카운트다운 위젯 |

i18n: 신규 키 ~12개 × 5 locale (ko/en/ja/zh/es) = 60 entries

### 2.3 Out of Scope

| 항목 | 사유 |
|------|------|
| Push notification 인프라 (FCM/APN) | 별도 인프라 PDCA — 기기 토큰 관리 + 플랫폼 등록 포함 |
| Email 발송 인프라 (SES/SMTP) | 기존 SMTP 미연동 시 별도 PDCA. 본 PDCA는 in-app 전용 |
| 팔로워 알림 (OQ-2=B 결정 반영) | 스팸 위험. #12 notifications-ux-audit에서 일관성 검토 후 재고 |
| 외부 SNS 자동 포스팅 (Twitter API 등) | 작가가 공유 카드 수동 다운로드 후 업로드하는 방식. OAuth 연동은 별도 |
| Auction 모델 status/start_at/end_at 변경 | 기존 컬럼 그대로 활용. 컬럼 추가만 |
| 실시간 WebSocket/SSE 종료 push | 클라이언트 시계 기반 카운트다운으로 대체 |
| 입찰 패배자 종료 알림 | OQ-8=B 결정 반영 — 작가 + 최고입찰자(낙찰자)만. 패배자 알림은 spam |
| 카운트다운 서버 polling (API 주기 호출) | 클라이언트 시계로 충분. end_at 기반 계산 |

---

## 3. Requirements

### 3.1 Functional Requirements

| ID | Requirement | Priority |
|----|-------------|:---:|
| FR-01 | `auctions.notified_24h_at DateTime(timezone=True) nullable`, `notified_6h_at`, `notified_1h_at` 3개 컬럼 신규. alembic `0042` | Must |
| FR-02 | `auctions.share_card_url Text nullable`, `auctions.share_card_generated_at DateTime(timezone=True) nullable` 2개 컬럼 신규. alembic `0042` (FR-01과 동일 migration) | Must |
| FR-03 | `auction_promotion_jobs.py` cron worker (60초 주기) — `status='active'` 옥션 중 `end_at <= now() + 24h` 이고 `notified_24h_at IS NULL`인 행 조회 → 알림 발송 + `notified_24h_at = now()` 갱신 | Must |
| FR-04 | cron worker — 6h 시점 동일 로직: `notified_6h_at IS NULL` + `end_at <= now() + 6h` | Must |
| FR-05 | cron worker — 1h 시점 동일 로직: `notified_1h_at IS NULL` + `end_at <= now() + 1h` | Must |
| FR-06 | 알림 대상: `auction.seller_id` (작가) + `auction.current_winner` (최고입찰자). `seller_id == current_winner`이면 1건만 발송 (중복 제거) | Must |
| FR-07 | `current_winner IS NULL` (입찰자 없는 옥션) 시 작가에게만 알림 발송 | Must |
| FR-08 | `POST /v1/auctions/{id}/share-card` — Pillow로 1200×630 PNG 합성. 작품 thumbnail fetch + 현재가 + 종료까지 남은 시간 + 작가명 + 도메인 watermark | Must |
| FR-09 | share-card endpoint — thumbnail fetch 실패 시 text-only fallback 카드 생성 (배경색 + 텍스트만) | Must |
| FR-10 | share-card endpoint — `share_card_generated_at`이 1시간 이내이면 `share_card_url` 재사용 반환 (`cached: true`) | Should |
| FR-11 | share-card endpoint 권한: `seller_id`(작가 본인) 또는 admin만 호출 가능. 타인 호출 → 403 | Must |
| FR-12 | `AuctionCountdown` 컴포넌트 — D-1h 이전 60초 갱신 / D-1h 이내 1초 갱신. 종료 시 종료 텍스트 표시 | Must |
| FR-13 | `AuctionShareCard` 컴포넌트 — `POST /v1/auctions/{id}/share-card` 호출 → 모달 내 PNG preview + 다운로드 버튼 + URL 복사 버튼 | Must |
| FR-14 | feed card에 D-1h 이내 `AuctionCountdown` 표시 | Should |
| FR-15 | 5 locale (ko/en/ja/zh/es) i18n 신규 키 ~12개 누락 0 | Must |
| FR-16 | 5 통합 지점 회귀 0: `#8 publish-controls`, `#10 tier-release`, `#2 draft-autosave`, `#1 role-gating`, 기존 auction settlement cron | Must |
| FR-17 | smoke test 스크립트 `scripts/smoke_test_auction_promotion.sh` | Should |

### 3.2 Non-Functional Requirements

| Category | Criteria |
|----------|----------|
| 알림 N+1 방지 | 단일 cron sweep에서 active 옥션 전체를 IN 절 batch로 조회. 옥션별 개별 쿼리 회피 |
| 공유 카드 생성 지연 | < 2초 (Pillow 합성 + 외부 이미지 fetch 1회). timeout 3초 설정, 초과 시 text-only fallback |
| cron 안전성 | 멱등 (idempotent) — `notified_Xh_at IS NULL` 조건 + `UPDATE WHERE notified_Xh_at IS NULL` 패턴. 중복 실행 무해 |
| 카운트다운 시계 오차 | 서버 `end_at` UTC 기준. `Date.now()` diff 계산. 최대 오차 < 1초 (setInterval 1초 기준) |
| 기존 auction cron 격리 | `auction_promotion_jobs.py`는 `auction_jobs.py`와 완전 독립 프로세스. `auction_jobs.py` 변경 없음 |
| 회귀 | TS 0 에러, ruff 0 에러. 5 통합 지점 기존 동작 유지 |
| 보안 | share-card endpoint는 `seller_id` 또는 admin만 호출. 서버 사이드 검증 |
| i18n | 5 locale 신규 키 ~12개 (ko/en/ja/zh/es) 전부 등록 |
| 스토리지 | 공유 카드 PNG는 기존 `StorageProvider.put` 활용. 별도 버킷 설정 불필요 (기존 미디어 버킷 재사용) |

---

## 4. Open Questions — ✅ ALL RESOLVED (2026-05-04 사용자 권장 default 일괄 수락)

| ID | 결정 | 영향 |
|----|------|------|
| OQ-1 = A | 24h+6h+1h 3 시점 | cron 컬럼 3개 |
| OQ-2 = B | 작가+최고입찰자만 (팔로워 제외) | spam 회피, #12에서 재검토 |
| OQ-3 = A | in-app만 | 인프라 의존성 0 |
| OQ-4 = B | 3개 컬럼 (notified_24/6/1h_at) | idempotent 단순 |
| OQ-5 = B | 1시간 ttl cache | 성능 + price 변동 반영 |
| OQ-6 = A | 1200×630 OG 표준 | 단일 dimension |
| OQ-7 = C | D-1h 이전 60s, 이내 1s | 배터리 + 정확성 균형 |
| OQ-8 = B | 작가+낙찰자만 | 패배자 spam 회피 |
| OQ-9 = A | 자동 watermark (도메인+작가명) | 브랜딩 + 도용 식별 |
| OQ-10 = B | post detail + feed D-1h 이내 | 입찰 임박 강조 |

> 10/10 모두 권장 default 채택. **Plan v1.0 → /pdca design 진입 가능.**

---

### OQ 상세 (참고용 보존)

권장 default 표: 아래 권장 옵션 그대로 수락 시 "권장대로"로 답변하면 일괄 진입 가능.

| ID | 질문 | 옵션 | **권장** | 영향 |
|----|------|------|:--------:|------|
| OQ-1 | 종료 임박 알림 시점 | **A** 24h+6h+1h (3 시점) / **B** 24h+1h (2 시점) / **C** 1h만 | **A** | cron 컬럼 수 (3개 vs 2개 vs 1개), 작가/입찰자 reaction time |
| OQ-2 | 알림 대상 범위 | **A** 작가+최고입찰자+팔로워 / **B** 작가+최고입찰자만 / **C** 작가만 | **B** | 팔로워 알림 쿼리 복잡도 + spam 위험. #12에서 재검토 |
| OQ-3 | 알림 채널 | **A** in-app만 / **B** in-app+email / **C** 전체 (push 포함) | **A** | 인프라 의존성 0. push/email은 별도 PDCA |
| OQ-4 | idempotent 추적 방식 | **A** `auction_notification_jobs` 신규 테이블 / **B** `auctions` 컬럼 3개 (`notified_24h_at`, `notified_6h_at`, `notified_1h_at`) / **C** JSONB column | **B** | 단순성. 컬럼 검색 인덱싱 용이. 신규 테이블 JOIN 불필요 |
| OQ-5 | 공유 카드 cache 정책 | **A** 매 요청 재생성 / **B** `share_card_generated_at` 1시간 TTL 캐시 / **C** 옥션 종료 시점 고정 | **B** | 성능 + 현재가 변동 반영 (1시간 단위 갱신). C는 가격 반영 안 됨 |
| OQ-6 | 공유 카드 크기 | **A** 1200×630 (OG 표준) / **B** 1080×1080 (Instagram 정방형) / **C** 둘 다 (size param) | **A** | OG 표준. Instagram도 crop 가능. C는 Pillow 처리 2배 |
| OQ-7 | 카운트다운 갱신 주기 | **A** 항상 1초 / **B** 항상 30초 / **C** D-1h 이전 60초 + D-1h 이내 1초 | **C** | 배터리 효율 + 임박 시 정확성 균형 |
| OQ-8 | 옥션 종료 시 최종 알림 대상 | **A** 작가+최고입찰자+모든 입찰자 / **B** 작가+최고입찰자(낙찰자)만 / **C** OQ-2와 동일 | **B** | 낙찰자 결제 안내 + 작가 알림. 패배자 알림은 UX spam |
| OQ-9 | 공유 카드 watermark | **A** 자동 (도메인 + 작가명 자동 삽입) / **B** 작가 선택 (토글) / **C** 미적용 | **A** | 브랜딩 일관성 + 무단 도용 출처 식별. B는 UI 추가 복잡도 |
| OQ-10 | 카운트다운 위치 | **A** 옥션 상세 페이지만 / **B** 상세 페이지 + feed card (D-1h 이내 표시) / **C** 사용자 선택 | **B** | 입찰 임박 feed 노출로 입찰자 활성화. D-1h 미만이면 feed 과밀 위험 낮음 |

---

### OQ 상세

#### OQ-1: 알림 시점

**질문**: 종료 몇 시간 전에 알림을 발송할 것인가?

| 옵션 | 시점 |
|------|------|
| **A** | 24h + 6h + 1h (3 시점) — `notified_24h_at`, `notified_6h_at`, `notified_1h_at` |
| **B** | 24h + 1h (2 시점) |
| **C** | 1h만 (1 시점) |

**권장 A** — 24h은 입찰 전략 수립 여유, 6h은 중간 리마인더, 1h은 최후 독촉. B는 중간 리마인더 부재. C는 24h 앞서 알린 참여자가 잊어버리는 케이스 처리 못함. 컬럼 3개 추가 비용은 미미.

---

#### OQ-2: 알림 대상

**질문**: 알림을 누구에게 발송할 것인가?

| 옵션 | 대상 |
|------|------|
| **A** | 작가 + 최고입찰자 + 팔로워 전체 |
| **B** | 작가 + 최고입찰자만 |
| **C** | 작가만 |

**권장 B** — 팔로워(옵션 A)는 팔로워 수 많은 작가의 경우 대량 알림 발송 부담 + spam 인식 위험. 최고입찰자는 가장 직접적 이해관계자. 팔로워 알림은 #12 notifications-ux-audit에서 opt-in 방식으로 재검토. C는 입찰자 알림 누락.

---

#### OQ-3: 알림 채널

**질문**: in-app 알림 외 push/email을 포함할 것인가?

| 옵션 | 채널 |
|------|------|
| **A** | in-app `Notification` 행만 |
| **B** | in-app + email (SES/SMTP) |
| **C** | in-app + email + push (FCM/APN) |

**권장 A** — push(FCM/APN) 인프라 미설정. email은 기존 SMTP 설정 상태 불확실. 인프라 의존성 0으로 즉시 구현 가능. push/email은 인프라 PDCA 완료 후 이 cron에 채널 추가만 하면 됨 (확장 포인트 주석 명시).

---

#### OQ-4: idempotent 추적 방식

**질문**: "이미 발송된 시점 알림"을 어떻게 추적할 것인가?

| 옵션 | 방식 |
|------|------|
| **A** | `auction_notification_jobs` 신규 테이블 (`auction_id`, `notif_type`, `sent_at`) |
| **B** | `auctions` 테이블에 컬럼 3개 추가 |
| **C** | `auctions.notif_sent` JSONB 컬럼 1개 |

**권장 B** — 옥션당 발송 이력이 최대 3개(24h/6h/1h)로 고정적이므로 컬럼 3개가 가장 단순. 신규 테이블(A) JOIN 불필요. JSONB(C)는 인덱싱 불편 + 타입 검증 약함. `UPDATE auctions SET notified_24h_at = now() WHERE id = :id AND notified_24h_at IS NULL` 패턴으로 멱등 보장.

---

#### OQ-5: 공유 카드 cache 정책

**질문**: 동일 옥션에 대한 공유 카드를 매번 재생성할 것인가?

| 옵션 | 정책 |
|------|------|
| **A** | 매 요청 재생성 (cache 없음) |
| **B** | `share_card_generated_at` 기반 1시간 TTL — 이내이면 `share_card_url` 반환 |
| **C** | 종료 시점 고정 생성 — 옥션 active 전환 시 1회 생성 |

**권장 B** — 현재가(`current_price`)가 입찰마다 변동되므로 완전 캐시(C)는 구식 정보 노출 위험. 매 재생성(A)은 Pillow 처리 + 외부 이미지 fetch 비용 반복. 1시간 TTL은 현재가 반영 + 서버 부하 균형.

---

#### OQ-6: 공유 카드 크기

**질문**: 공유 카드 이미지 픽셀 크기를 어떻게 할 것인가?

| 옵션 | 크기 |
|------|------|
| **A** | 1200×630 px (Open Graph 표준) |
| **B** | 1080×1080 px (Instagram 정방형) |
| **C** | 둘 다 (`size` query param으로 선택) |

**권장 A** — Twitter/Facebook/KakaoTalk OG 미리보기 최적 해상도. Instagram도 1200×630을 crop하면 사용 가능. C는 Pillow 처리 2회 + 스토리지 2배 + API 복잡도 증가.

---

#### OQ-7: 카운트다운 갱신 주기

**질문**: `AuctionCountdown`의 `setInterval` 주기를 어떻게 할 것인가?

| 옵션 | 주기 |
|------|------|
| **A** | 항상 1초 갱신 |
| **B** | 항상 30초 갱신 |
| **C** | D-1h 이전: 60초 갱신 / D-1h 이내: 1초 갱신 |

**권장 C** — D-1h 이전에는 분/시간 단위 표시로 충분 (60초 갱신으로 배터리 절약). D-1h 이내에는 초 단위 정확성이 입찰 긴장감에 기여 (1초 갱신). B는 항상 30초로 임박 시 부정확.

---

#### OQ-8: 옥션 종료 시 최종 알림

**질문**: 옥션 status가 `active`→`ended`로 변경될 때 누구에게 알림을 보낼 것인가?

| 옵션 | 대상 |
|------|------|
| **A** | 작가 + 낙찰자 + 모든 입찰자 |
| **B** | 작가 + 낙찰자(최고입찰자)만 |
| **C** | OQ-2와 동일 대상 |

**권장 B** — 낙찰자에게 결제 안내 알림 필수. 작가에게 옥션 종료 + 낙찰자 확정 알림 필수. 패배 입찰자 알림은 spam 인식 위험 + `Bid` 테이블 전체 스캔 비용. 옥션 종료 알림은 `auction_jobs.py`의 settlement 흐름에 hook 가능 (PR1 범위 내 검토).

---

#### OQ-9: 공유 카드 watermark

**질문**: 공유 카드에 watermark를 자동으로 삽입할 것인가?

| 옵션 | 방식 |
|------|------|
| **A** | 자동 삽입 (도메인 URL + 작가명 고정 위치) |
| **B** | 작가가 토글로 선택 |
| **C** | watermark 없음 |

**권장 A** — 외부 SNS 유입 시 출처 표시 필수. 무단 도용 시 출처 식별 가능. B는 UI 추가 + DB 설정 저장 필요. C는 브랜딩 손실. Pillow `ImageDraw.text()` 로 오른쪽 하단 반투명 텍스트 삽입으로 구현 비용 낮음.

---

#### OQ-10: 카운트다운 위치

**질문**: `AuctionCountdown` 위젯을 어디에 표시할 것인가?

| 옵션 | 위치 |
|------|------|
| **A** | 옥션 상세 페이지 (`/posts/[id]`)만 |
| **B** | 상세 페이지 + feed card (D-1h 이내에만 표시) |
| **C** | 사용자 설정 선택 |

**권장 B** — feed card 노출은 입찰자 행동 유도에 직접적 효과. D-1h 미만 제한으로 feed 과밀 방지. C는 설정 UI + 저장 추가 비용. A는 feed 노출 기회 포기.

---

## 5. Acceptance Criteria

| ID | 기준 | 검증 방법 |
|----|------|-----------|
| AC-1 | `auctions` 테이블에 `notified_24h_at`, `notified_6h_at`, `notified_1h_at`, `share_card_url`, `share_card_generated_at` 5개 컬럼 생성. 기존 행 모두 null | `\d auctions` + SELECT 확인 |
| AC-2 | `status='active'` 옥션 중 `end_at <= now() + 24h` 이고 `notified_24h_at IS NULL` 인 행에 cron 실행 후 알림 행 생성 + `notified_24h_at = now()` 갱신 | 통합 테스트 (time mock) |
| AC-3 | AC-2 조건 동일 cron 2회 실행 시 알림 중복 발송 없음 (`notified_24h_at IS NOT NULL` 조건으로 skip) | 멱등 테스트 |
| AC-4 | `current_winner IS NULL` 옥션: 작가에게만 알림 1건 발송 | 통합 테스트 |
| AC-5 | `seller_id == current_winner` 옥션: 알림 1건만 발송 (중복 제거) | 통합 테스트 |
| AC-6 | `POST /v1/auctions/{id}/share-card` — 작가 본인 호출 시 200 + `share_card_url`, `generated_at`, `cached` 반환 | curl |
| AC-7 | `POST /v1/auctions/{id}/share-card` — 타 사용자 호출 시 403 | curl |
| AC-8 | `share_card_generated_at` 1시간 이내 재호출 시 `cached: true` + 동일 `share_card_url` 반환 (Pillow 재실행 없음) | curl × 2 |
| AC-9 | 작품 thumbnail fetch 실패 시 text-only fallback 카드 생성 (200 응답, `share_card_url` 반환) | 통합 테스트 (mock 403 thumbnail) |
| AC-10 | `AuctionShareCard` 모달 — PNG preview, 다운로드 버튼, URL 복사 버튼 렌더 확인 | 수동 |
| AC-11 | `AuctionCountdown` — D-1h 초과 시 60초 interval, D-1h 이내 1초 interval 전환 확인 | 수동 (시간 조작 또는 단위 테스트) |
| AC-12 | feed card에서 `end_at`이 1h 이내인 옥션에 `AuctionCountdown` 표시, 1h 초과 시 미표시 | 수동 |
| AC-13 | 카운트다운 종료 후 종료 텍스트("경매 종료") 표시 | 수동 |
| AC-14 | 5 locale (ko/en/ja/zh/es) i18n 신규 키 ~12개 모두 표시, 누락 없음 | 수동 × 5 locale |
| AC-15 | 5 통합 지점 회귀 0: 기존 `auction_jobs.py` settlement 동작, #8 publish-controls, #10 tier-release, #2 draft-autosave, #1 role-gating | 수동 체크리스트 + smoke_test |

---

## 6. Risks

| ID | Risk | Impact | 완화 방안 |
|----|------|:------:|-----------|
| R-1 | cron worker 중복 실행 — `app/main.py` lifespan에서 동일 job 2회 등록 또는 멀티 프로세스 환경 | High | `UPDATE auctions SET notified_24h_at = now() WHERE id = :id AND notified_24h_at IS NULL` — row-level 조건으로 멱등 보장. PostgreSQL `FOR UPDATE SKIP LOCKED` 패턴 적용 검토 (설계 단계에서 확정) |
| R-2 | 공유 카드 생성 중 작품 thumbnail 외부 URL fetch 실패 (CDN timeout, 삭제된 이미지) | Medium | `httpx.AsyncClient` timeout=3초. 실패 시 text-only fallback 카드 (단색 배경 + 텍스트). 응답은 200 유지, `share_card_url` 정상 반환 |
| R-3 | 카운트다운 클라이언트 시계 오차 — 사용자 기기 시계가 서버와 1분 이상 차이 나는 경우 | Low | 서버에서 `end_at` UTC ISO8601 제공. 클라이언트는 `Date.now()` + `end_at` diff 계산. 기기 시계 오프셋은 허용 오차 (입찰 마감은 서버 사이드 `end_at` 기준). 카운트다운은 UX 참조값 |
| R-4 | 작가 본인이 본인 옥션에 입찰한 경우 — `seller_id == current_winner` → 알림 중복 발송 | Medium | FR-06 및 AC-5: 발송 전 `seller_id == current_winner` 체크 → 1건만 발송. notification type을 seller/winner 구분으로 작성 시 내용 통합 처리 |
| R-5 | 기존 `auction_jobs.py` (5분 cron) 와 신규 `auction_promotion_jobs.py` (60초 cron) 동시 실행 시 DB session 경합 | Low | 두 cron은 완전 독립. 동일 `auctions` 테이블이지만 갱신 컬럼 분리 (`notified_*` vs `status`/`current_winner`). `AsyncSessionLocal` 별도 context로 격리 |
| R-6 | Pillow + 외부 이미지 fetch가 2초 초과하여 endpoint timeout 발생 | Medium | Pillow 합성은 단순 (텍스트 + 이미지 resize + 합성). 외부 이미지 fetch timeout=3초 + fallback. 총 처리 < 5초. endpoint timeout은 30초 기본값으로 여유 충분 |

---

## 7. Dependencies

| 의존성 | 상태 | 관계 |
|--------|:----:|------|
| Phase 3 `#8 publish-controls` | ✅ archived | `Auction` 연결 `post` 의 visibility 필터 기반 제공. 옥션 상세 페이지 접근 경로 확립 |
| Phase 4 `#10 artist-tier-release` | ✅ archived (2026-05-04, Match Rate 99%) | Follow/Sponsorship 모델 활용 패턴. 본 PDCA는 auction 모델 독립 — 직접 의존 없음 |
| `app/models/auction.py` — `Auction` + `Bid` | ✅ 존재 | `seller_id`, `current_winner`, `end_at`, `status`, `current_price` 직접 활용 |
| `app/models/notification.py` — `Notification` | ✅ 존재 | in-app 알림 생성. 신규 마이그레이션 불필요 |
| `app/services/auction_jobs.py` | ✅ 동작 중 (5분 cron) | cron 구조 참조. 직접 수정 없음. `auction_promotion_jobs.py`는 별도 파일 |
| Pillow | ✅ (media_processing.py 의존성 확인 필요) | 공유 카드 이미지 합성. `requirements.txt` 추가 또는 확인 |
| `StorageProvider.put` | ✅ 존재 | 공유 카드 PNG 저장. 기존 미디어 스토리지 재사용 |
| Phase 4.5 `#9 artist-pricing-assist` | 보류 | 본 PDCA와 독립. 영향 없음 |
| `#12 notifications-ux-audit` | Phase 3, 독립 | 알림 UX 전반 감사. 팔로워 알림 포함 여부는 #12에서 재검토 |

---

## 8. Implementation Order (3 PRs)

### PR1 — Backend Foundation (~1.5일)

1. alembic `0042_auction_promotion_columns.py`:
   - `auctions.notified_24h_at DateTime(timezone=True) nullable`
   - `auctions.notified_6h_at DateTime(timezone=True) nullable`
   - `auctions.notified_1h_at DateTime(timezone=True) nullable`
   - `auctions.share_card_url Text nullable`
   - `auctions.share_card_generated_at DateTime(timezone=True) nullable`
   - 인덱스: `ix_auctions_notif_24h` on `(status, end_at, notified_24h_at)` (cron 쿼리 가속)
2. `app/models/auction.py` — `Auction` 클래스에 5개 컬럼 추가
3. `app/schemas/auction.py` (신규 또는 기존):
   - `AuctionShareCardResponse { share_card_url: str, generated_at: datetime, cached: bool }`
   - `AuctionNotifStatus` (admin 확인용 옵션)
4. smoke: `alembic upgrade head` + `\d auctions` 확인

**PR1 회귀 체크**: 기존 Auction API 응답 동일 (신규 컬럼 null로 추가).

### PR2 — Backend Logic + Tests (~1.5일)

1. `app/services/auction_promotion_jobs.py` 신규:
   - `dispatch_auction_notifications_once(db: AsyncSession)` — 3 시점(24h/6h/1h) 각각 batch 처리. `FOR UPDATE SKIP LOCKED` 적용
   - `auction_promotion_cron_loop(interval_seconds: int = 60)` — asyncio loop
   - Notification 생성 (type: `auction_ending_24h` / `auction_ending_6h` / `auction_ending_1h` / `auction_ended`)
   - seller/winner 중복 제거 로직 (`seller_id == current_winner` edge case)
2. `app/api/auctions.py` (신규 또는 기존):
   - `POST /v1/auctions/{id}/share-card` endpoint
   - Pillow 합성 로직 + thumbnail fetch (`httpx.AsyncClient` timeout=3초)
   - text-only fallback
   - 캐시 체크 (`share_card_generated_at` 1시간 이내)
   - `StorageProvider.put` 호출
3. `app/main.py` — startup에 `asyncio.create_task(auction_promotion_cron_loop())` 추가
4. 단위 테스트: cron idempotent, seller==winner edge case, fallback card
5. 통합 테스트: share-card endpoint (정상, 403, cached, fallback)
6. `scripts/smoke_test_auction_promotion.sh` 신규

**PR2 회귀 체크**: `auction_jobs.py` 기존 동작 (`process_expired_orders_once`, `auction_cron_loop`) 변경 없음.

### PR3 — Frontend + 통합 (~2일)

1. `src/components/AuctionCountdown.tsx` 신규:
   - `end_at: string` prop. `setInterval` adaptive (D-1h 이전 60초 / 이내 1초)
   - 종료 후 "경매 종료" 텍스트
2. `src/components/AuctionShareCard.tsx` 신규:
   - "공유 카드 만들기" 버튼 → `POST /v1/auctions/{id}/share-card` 호출
   - 모달: PNG preview (`<img>`) + 다운로드 버튼 + URL 복사 버튼
   - skeleton loader + 에러 토스트
3. 옥션 상세 페이지 (`/posts/[id]` product post) — `AuctionCountdown` + `AuctionShareCard` 통합
4. feed card — `end_at` 1h 이내 조건부 `AuctionCountdown` 표시
5. `src/lib/api.ts` — `createAuctionShareCard(auctionId: string)` 추가
6. i18n: 5 locale (`auction.countdown.*`, `auction.shareCard.*`, `auction.notification.*`) ~12키 추가
7. 5 통합 지점 회귀 수동 체크리스트

**PR3 회귀 체크**: 기존 feed card 렌더 (`#8` visibility 필터, `#10` tier-lock 표시), post 상세 페이지 (`#2` draft restore, `#1` role-gate) 정상 동작.

---

## 9. Carry-over Awareness

본 PDCA 완료 시 `editor-revamp-roadmap` **11/12 sub-PDCA 완료** 상태 (Phase 4 종결).

**기존 carry-over (본 PDCA 이후에도 유지)**:

| Carry-over | 출처 | 처리 방안 |
|-----------|------|-----------|
| `editor-video-studio` (#6-video, ffmpeg 차단) | Phase 2 | ffmpeg 인프라 결정 후 별도 PDCA |
| `upload-retry-ui` | #4 이전 누적 | 별도 minor fix |
| `editor-i18n-cleanup` v0.2 | #3+#4 누적 | PR3 i18n 작업 시 병행 처리 시도 |
| `series reorder persistence endpoint` | #8 publish-controls | #11 또는 minor fix |
| `tier-release enhancements` (#10.1) | #10 deferred | Redis tier cache (성능 이슈 발생 시) |

**후속 PDCA 후보**:

| 후속 | 트리거 |
|------|--------|
| push/email 인프라 통합 (FCM/APN/SES) | 알림 인프라 PDCA. 본 cron에 채널 추가 hook 준비 |
| 팔로워 알림 옵트인 | #12 notifications-ux-audit 완료 후 검토 |
| 외부 SNS 자동 포스팅 (Twitter OAuth) | 비즈니스 우선순위 확정 후 별도 PDCA |
| `#9 artist-pricing-assist` | Phase 4.5 — 거래 데이터 축적 후 |
| `#12 notifications-ux-audit` | Phase 3 독립 — 언제든 진행 가능 |

---

## 10. Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 0.1 | 2026-05-04 | Initial draft. `#11 auction-promotion-suite` plan. B-4 옥션 종료 알림/홍보 도구. 5컬럼 마이그레이션 + auction_promotion_jobs + share-card endpoint + AuctionShareCard/AuctionCountdown. OQ 10개 권장 default 포함. Phase 4 마지막 PDCA. | itpe-ince (Claude Opus 4.7 + bkit product-manager agent) |
