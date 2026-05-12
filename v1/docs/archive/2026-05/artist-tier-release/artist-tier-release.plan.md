---
template: plan
version: 1.0
feature: artist-tier-release
sub-pdca: "#10"
phase: Phase 4 — Artist Tools
date: 2026-05-03
author: itpe-ince (Claude Opus 4.7 + bkit product-manager agent)
project: domo
project_version: v1
parent_roadmap: editor-revamp-roadmap.plan.md
estimate: M (4~5일)
status: oq_resolved
oq_resolved_at: 2026-05-03
---

# artist-tier-release Planning Document

> **Summary**: 작가가 포스트 발행 시 본인의 **구독자(Subscription) / 후원자(Sponsorship) / 팔로워(Follow)** 중 한 계층에게 N시간/일 동안 먼저 공개하고, 기간 만료 후 지정 visibility로 자동 전환되는 우선 공개(Early Access) 기능을 도입한다. `Post.early_access_until` + `Post.early_access_tier` 신규 컬럼 + `_visibility_filter_for_viewer` 확장 + 자동 전환 worker + 프런트엔드 `TierReleasePicker` 컴포넌트로 구성된다.
>
> **Status**: Draft v0.1
> **Sub-PDCA**: #10 (Critical Path) — Phase 4 Artist Tools
> **Parent Roadmap**: [editor-revamp-roadmap.plan.md](./editor-revamp-roadmap.plan.md)

---

## 0. Roadmap Context

`editor-revamp-roadmap.plan.md` §1.B-4에는 작가 기능에 대한 요구사항 3건이 다음과 같이 원문 그대로 명시되어 있다:

> - **가격 책정 보조** (시세 가이드, 추천 시작가) 제공 필요
> - **후원자/단골에게 먼저 공개** 옵션 제공 필요
> - **옥션 종료 알림/홍보 도구** 제공 필요

본 PDCA `#10 artist-tier-release`는 이 중 **"후원자/단골에게 먼저 공개"** 요구사항을 구현하는 **Critical Path의 여섯 번째 단계**이다 (1 → 2 → 3 → 4 → 6 → 8 → **10**). Phase 3 #8 `publish-controls`가 2026-05-03자로 아카이브되어 선행 의존성이 충족되었다.

본 PDCA는 `#8 publish-controls`에서 확립한 `Post.visibility` 시스템(`app/models/post.py:50~53`) 및 `_visibility_filter_for_viewer` helper(`app/api/posts.py:262~294`)를 직접 상속·확장한다. `#8` 설계 시 `String(20)` 컬럼을 채택하고 코드 주석에 "Phase 4 #10 may add 'tier_only' etc."를 명시한 것이 이 확장 경로다.

Phase 4 내에서 `#11 auction-promotion-suite`는 본 PDCA와 독립적으로 병렬 진행 가능하다. `가격 책정 보조(#9)`는 Phase 4.5로 별도 보류 중이다.

---

## 1. Overview

### 1.1 What

| 영역 | 현재 | 목표 |
|------|------|------|
| 우선 공개 | 없음 — 발행 즉시 visibility 대로 모든 자격자에게 동시 공개 | `Post.early_access_until` (만료 시각, UTC) + `Post.early_access_tier` (`subscriber`/`sponsor`/`follower`) 신규 컬럼 추가. 활성 기간 동안 `visibility='tier_only'` 효과 적용 |
| 티어 자격 검증 | 없음 | 매 조회 시 viewer의 active subscription / completed sponsorship / follow 여부를 DB에서 실시간 검증 |
| 자동 전환 | 없음 | `tier_release_jobs.py` cron worker (60초 주기) — `early_access_until <= now()` 포스트의 `early_access_until` 을 null로 설정하여 effective visibility 자동 복귀 |
| UI | 없음 | `TierReleasePicker` 컴포넌트 — tier 선택 + 기간 선택. `FeedItem`/`PostCard`에 잠금 표시 |

### 1.2 Why

- 로드맵 §1.B-4 요구사항 "후원자/단골에게 먼저 공개" 충족
- 작가가 후원자·단골에게 실질적인 혜택(콘텐츠 우선 접근)을 제공 → 구독/후원 관계 강화
- 기존 Sponsorship/Subscription/Follow 모델을 신규 테이블 추가 없이 활용 — 마이그레이션 비용 최소화
- Phase 3 #8의 visibility 시스템이 `String(20)` + 확장 주석으로 이 경로를 명시적으로 준비해 둠

### 1.3 Background

**현재 코드베이스 상태 (검증 완료)**:

- `app/models/post.py:50~53` — `Post.visibility: String(20)` default `'public'`. 값: `public` / `followers_only` / `unlisted`. `String(20)` 여유 공간으로 `'tier_only'`(10자) 수용 가능
- `app/models/post.py:55~58` — `Post.comments_enabled: Boolean` default `True`
- `app/models/post.py` — `Post.early_access_until` 컬럼 **없음** (신규 추가 필요)
- `app/models/post.py` — `Post.early_access_tier` 컬럼 **없음** (신규 추가 필요)
- `app/api/posts.py:262~294` — `_visibility_filter_for_viewer` helper. 현재 `public` / `followers_only` / `unlisted` 3값만 처리. `tier_only` 분기 **없음** (확장 필요)
- `app/api/posts.py:179~256` — `publish_post` endpoint. `body.visibility` 를 그대로 저장. early_access 필드 **없음** (확장 필요)
- `app/models/sponsorship.py:22~51` — `Sponsorship` (일회성 후원): `sponsor_id`, `artist_id`, `status='completed'` 완료 조건
- `app/models/sponsorship.py:54~85` — `Subscription` (정기 구독): `sponsor_id`, `artist_id`, `status='active'`, `current_period_end` 만료 조건
- `app/models/post.py:164~176` — `Follow`: `follower_id`, `followee_id`, `created_at`
- `app/services/schedule_jobs.py` — `publish_scheduled_posts_once()` 60초 cron 패턴 이미 동작 중 — tier_release_jobs도 동일 패턴 적용

**#8에서 확립된 재사용 인프라**:
- `_visibility_filter_for_viewer` helper — tier_only 분기 추가 시 최소 수정으로 확장 가능
- `POST /v1/posts/{id}/publish` endpoint — `early_access_until` / `early_access_tier` 필드 추가로 확장
- `ix_posts_visibility_status_created` 복합 인덱스 — `tier_only` 값 추가해도 인덱스 재생성 불필요

### 1.4 Related Documents

- 부모 로드맵: [editor-revamp-roadmap.plan.md](./editor-revamp-roadmap.plan.md) §1.B-4 + §2 Phase 4 + §3 의존성 + §4 row #10
- 선행 아카이브: `docs/archive/2026-05/publish-controls/` (#8 — visibility 시스템 + publish endpoint)
- 병렬 진행 가능: `#11 auction-promotion-suite` (Phase 4, 독립)
- 후속 가능: `#9 artist-pricing-assist` (Phase 4.5, 별도 보류)

---

## 2. Scope

### 2.1 In Scope

#### A. `Post.early_access_until` + `Post.early_access_tier` 컬럼

- `early_access_until: Mapped[datetime | None]` (`DateTime(timezone=True)`, nullable) — 우선 공개 종료 시각 (UTC)
- `early_access_tier: Mapped[str | None]` (`String(20)`, nullable) — 자격 계층: `subscriber` | `sponsor` | `follower`
  - `subscriber` (가장 좁음): 정기 구독 중(`Subscription.status='active'`) 사용자만
  - `sponsor` (중간): 일회성 후원 완료(`Sponsorship.status='completed'`) 또는 위 구독자
  - `follower` (가장 넓음): 팔로우 중인 사용자 또는 위 모두 (OQ-2 참조)
- 두 컬럼 모두 nullable. null 시 early_access 비활성 — 기존 visibility 그대로 동작
- alembic 마이그레이션 `0041_post_early_access.py`: additive 추가, default null, 기존 행 영향 없음

#### B. Visibility 시스템 확장 (#8 v2)

- `Post.visibility`에 `'tier_only'` 값 허용 확장. DB 컬럼(`String(20)`) 변경 없음 — 값 추가만
- **Effective visibility** 정의:
  - `early_access_until > now()` 이고 `early_access_tier is not null` → effective visibility = `tier_only`
  - 그 외 → effective visibility = `Post.visibility` (기존 값 그대로)
- DB에는 발행 시 지정한 원래 visibility 값을 유지. `tier_only`는 DB에 저장하지 않음 — 조회 시 계산
- `app/api/posts.py` 내 `_visibility_filter_for_viewer` helper 확장:
  - `tier_only` 분기 추가: viewer가 작가의 active subscriber / completed sponsor / follower 중 하나이면 통과
  - OQ-2 계층 포함 여부에 따라 쿼리 조건 구성 (OR 체인)

#### C. 자동 visibility 전환 worker

- `app/services/tier_release_jobs.py` 신규 파일
- `tier_release_once()` 함수: `early_access_until <= now()` AND `early_access_until is not null` 포스트 조회 → `early_access_until = null`, `early_access_tier = null` 로 업데이트
- `app/main.py` startup 시 `schedule_jobs.py`와 동일한 asyncio.create_task 패턴으로 60초 cron 등록
- worker 재시작 안전: 멱등(idempotent) — 이미 null인 행은 WHERE 조건에 걸리지 않음

#### D. API 확장

- `POST /v1/posts/{id}/publish` (`app/api/posts.py:179`) body 확장:
  - `early_access_until: datetime | None = None` (ISO8601 UTC)
  - `early_access_tier: Literal['subscriber', 'sponsor', 'follower'] | None = None`
  - 두 필드 동시에 null이거나 동시에 값이 있어야 함 (Pydantic validator)
- Pydantic schema `PostPublishRequest` (`app/schemas/series.py`) — 위 2필드 추가
- `PostPublishResponse` — `early_access_until`, `early_access_tier` 반환 추가
- `GET /v1/posts/{id}` — `PostOut` 에 `early_access_until`, `early_access_tier`, `is_tier_locked` (viewer 기준 계산) 반환 추가

#### E. 프런트엔드 `TierReleasePicker`

- `src/components/post-editor/TierReleasePicker.tsx` 신규
- `PublishOptionsPanel.tsx` 내 expand 섹션으로 통합 (OQ-8 권장 A)
- tier 선택 (라디오 또는 select): `subscriber` / `sponsor` / `follower` + 각 설명 ("정기 구독자만", "후원자 이상", "팔로워 이상")
- 기간 선택 (preset 5개): `1h` / `6h` / `24h` / `3d` / `7d` (OQ-3 권장 A)
- 비활성 기본값: 체크박스로 활성화 → tier + 기간 선택 표시
- `FeedItem`/`PostCard`: `is_tier_locked=true` 시 `LockClosedIcon` 표시 + tooltip i18n ("후원자만 볼 수 있어요" 등)
- `/posts/[id]` 직접 접근 시 viewer가 tier에 속하지 않으면 403 + 안내 메시지 페이지

### 2.2 Out of Scope

| 항목 | 이유 / 담당 PDCA |
|------|-----------------|
| `artist-pricing-assist` (#9) | Phase 4.5 별도 보류 — 거래 데이터 축적 필요 |
| `auction-promotion-suite` (#11) | Phase 4 별도 PDCA — 독립 진행 |
| 티어 자동 추천 / dynamic pricing | 데이터 없이 추천 정확도 낮음 |
| 티어 진입 유도 알림 ("지금 후원하면 X시간 일찍") | UX 침입적. 별도 notification PDCA에서 검토 |
| 유료 tier / paywall 콘텐츠 판매 | 비즈니스 모델 별도 결정 필요 |
| Redis cache 기반 tier 자격 캐싱 | 단순성 우선 (OQ-10 권장 A). 성능 이슈 발생 시 #10.1에서 도입 |

---

## 3. Requirements

### 3.1 Functional Requirements

| ID | Requirement | Priority |
|----|-------------|:---:|
| FR-01 | `Post.early_access_until DateTime(timezone=True) nullable` 컬럼 신규. alembic `0041` | Must |
| FR-02 | `Post.early_access_tier String(20) nullable` 컬럼 신규 (`subscriber`/`sponsor`/`follower`). alembic `0041` | Must |
| FR-03 | `early_access_until > now()` 이고 `early_access_tier is not null` 인 포스트는 effective visibility = `tier_only` 로 처리 | Must |
| FR-04 | `_visibility_filter_for_viewer` (`app/api/posts.py:262`) 에 `tier_only` 분기 추가 — viewer가 해당 tier 자격 보유 시 포스트 노출 | Must |
| FR-05 | tier 자격 검증 — `subscriber`: `Subscription.status='active'` AND `artist_id=author`, `sponsor`: `Sponsorship.status='completed'` AND `artist_id=author` (또는 subscriber), `follower`: `Follow.followee_id=author` AND `follower_id=viewer` (또는 위 모두) | Must |
| FR-06 | `POST /v1/posts/{id}/publish` body에 `early_access_until` + `early_access_tier` 필드 추가. 두 필드 동시에 null이거나 동시에 값이 있어야 함 (Pydantic validator) | Must |
| FR-07 | `tier_release_jobs.py` cron worker (60초 주기) — `early_access_until <= now()` 포스트의 early_access 필드를 null로 갱신 | Must |
| FR-08 | `GET /v1/posts/{id}` — `PostOut` 에 `early_access_until`, `early_access_tier`, `is_tier_locked` 반환 | Must |
| FR-09 | `tier_only` effective visibility 포스트에 viewer 자격 없으면 `GET /v1/posts/{id}` → `TIER_ACCESS_DENIED` 403 | Must |
| FR-10 | `TierReleasePicker` 컴포넌트 — tier 선택 (3종) + 기간 preset (5종). `PublishOptionsPanel` 내 expand 섹션 | Must |
| FR-11 | `FeedItem`/`PostCard` — `is_tier_locked=true` 시 잠금 아이콘 + tooltip 표시 | Must |
| FR-12 | tier_only 포스트는 피드/탐색/검색에서 자격 없는 viewer에게 미노출 | Must |
| FR-13 | worker 재시작 안전 (멱등) — 이미 null인 early_access 행은 cron에서 재처리 없음 | Must |
| FR-14 | i18n 신규 키 (~12키 × 5 locale = 60 entries) 누락 0 | Must |
| FR-15 | 5 통합 지점 회귀 0 (autosave / DraftRestoreDialog / 멀티탭 / role-gating / useArtistGate) | Must |
| FR-16 | smoke test 스크립트 `scripts/smoke_test_tier_release.sh` | Should |

### 3.2 Non-Functional Requirements

| Category | Criteria |
|----------|----------|
| 성능 | 피드/탐색/검색 visibility 필터 성능 저하 없음. 기존 `ix_posts_visibility_status_created` 인덱스 재사용 가능 — `tier_only` 값이 인덱스에 투명하게 추가됨 |
| N+1 방지 | tier 자격 검증은 단일 OR 쿼리로 처리. 피드 조회 시 tier_only 포스트별 별도 서브쿼리 회피 — followee_ids 패스트패스(`app/api/posts.py:278`) 동일 전략 적용 |
| 회귀 | TS 0 에러, ruff 0 에러. #8 publish-controls 5 통합 지점 기존 동작 유지 |
| 보안 | tier 자격 검증은 서버 사이드 강제. 클라이언트에서 `is_tier_locked=false` 위조 불가 |
| 멱등성 | cron worker 중복 실행 시 이미 처리된 행에 영향 없음 (WHERE `early_access_until IS NOT NULL` 조건) |
| i18n | 5 locale (ko/en/ja/zh/es) 신규 키 ~12개 모두 등록 |

---

## 4. Open Questions — ✅ ALL RESOLVED (2026-05-03 사용자 권장 default 일괄 수락)

| ID | 결정 | 영향 |
|----|------|------|
| OQ-1 = A | tier 종류 = 3-tier (`subscriber/sponsor/follower`) | DB enum, UI labels, 자격 검증 쿼리 3-OR |
| OQ-2 = A | tier 계층 = 자동 포함 (subscriber > sponsor > follower) | 자격 쿼리 `IN (selected_tier...follower)` 형태 |
| OQ-3 = A | 우선 공개 기간 = 5 preset (1h/6h/24h/3d/7d) | UI picker `<select>` 또는 button group |
| OQ-4 = B | tier 자격 검증 = 매 조회 시 실시간 DB | 발행 후 구독 취소/탈퇴 즉시 반영 |
| OQ-5 = A | tier_release_jobs cron = 60초 (schedule_jobs 패턴) | 즉시성, 인프라 0 |
| OQ-6 = A | tier_only ↔ 기존 visibility = 상호 배타적 (tier_only가 기간 중 우선) | 단순성 |
| OQ-7 = B | tier 만료 후 = 발행 시 작가 지정 visibility 복귀 (early_access_until=null → 원래 Post.visibility 사용) | DB에 원래 visibility 보존 + effective visibility 계산 |
| OQ-8 = A | TierReleasePicker UI = PublishOptionsPanel 내 expand | #8 패턴 일관 |
| OQ-9 = A | API endpoint = publish endpoint 확장 (early_access_until + early_access_tier 2 필드) | 단일 발행 흐름 |
| OQ-10 = A | tier 자격 cache = no-cache (매 DB 검사) | 단순성 우선, 성능 측정 후 #10.1 도입 가능 |

> 10/10 모두 권장 default 채택. **Plan v1.0 → /pdca design artist-tier-release 진입 가능.**

---

### OQ 상세 (참고용 보존)

| ID | 질문 | 옵션 | 권장 | 영향 |
|----|------|------|:----:|------|
| OQ-1 | tier 종류 명칭 | **A** `subscriber/sponsor/follower` (3-tier) / **B** `paid/follower` (2-tier) / **C** N-tier custom | **A** | DB 컬럼 값, UI 레이블, 자격 검증 쿼리 |
| OQ-2 | tier 계층 포함 규칙 | **A** 계층 상위 자동 포함 (`subscriber > sponsor > follower`) / **B** 정확히 1개만 / **C** 작가 다중 선택 | **A** | 자격 검증 쿼리 OR 조건 수, UX 복잡도 |
| OQ-3 | 우선 공개 기간 | **A** 5 preset (1h/6h/24h/3d/7d) / **B** 자유 datetime / **C** 둘 다 | **A** | UI picker 구현, 분석 지표 단순화 |
| OQ-4 | tier 자격 검증 시점 | **A** 발행 시 자격자 스냅샷 저장 / **B** 매 조회 시 실시간 DB 검증 | **B** | 자격 변경(구독 취소/해지) 즉시 반영 vs. 저장 복잡도 |
| OQ-5 | tier_release_jobs.py cron 주기 | **A** 60초 (schedule_jobs 패턴 동일) / **B** 5분 / **C** 작가 수동 트리거 | **A** | 기간 만료 지연 허용 범위, 기존 패턴 재사용 |
| OQ-6 | visibility=`tier_only` 와 기존 visibility 관계 | **A** 상호 배타적 (tier_only 기간 중 원래 visibility 덮어씀) / **B** 결합 가능 (tier + unlisted = 링크+tier 자격) | **A** | 모델 단순성, 작가 의도 명확성 |
| OQ-7 | tier 만료 후 visibility | **A** 자동으로 `public` 복귀 / **B** 발행 시 작가가 지정한 visibility 복귀 (early_access_until=null → 원래 Post.visibility 사용) | **B** | 작가 의도 일치, 모델 일관성. DB에 원래 visibility 보존 필요 |
| OQ-8 | TierReleasePicker UI 위치 | **A** `PublishOptionsPanel` 내 expand 섹션 / **B** 별도 모달 / **C** 별도 wizard step | **A** | #8 패턴 일관성, 구현 비용 |
| OQ-9 | API endpoint 통합 방식 | **A** `POST /v1/posts/{id}/publish` 확장 (early_access_until/tier 필드 추가) / **B** 별도 `POST /v1/posts/{id}/tier-release` | **A** | 단일 발행 흐름 유지, 기존 endpoint 재사용 |
| OQ-10 | tier 자격 cache | **A** no-cache (매 조회 DB 검사) / **B** Redis cache (TTL 5분) | **A** | 단순성 우선. 성능 병목 시 #10.1에서 Redis 도입 |

### OQ 상세 (참고용)

---

### OQ-1: tier 종류

**질문**: DB 컬럼 + API에 저장할 tier 명칭과 개수를 어떻게 할 것인가?

| 옵션 | 값 | 특징 |
|------|----|------|
| **A** | `subscriber` / `sponsor` / `follower` | 3개 명확, Domo 비즈니스 모델(Subscription/Sponsorship/Follow)과 1:1 대응. `Subscription.status='active'` / `Sponsorship.status='completed'` / `Follow` 조건 직관적 |
| **B** | `paid` / `follower` | 단순하나 구독/후원 구분 없어짐. 추후 구독 전용 혜택 추가 시 재작업 필요 |
| **C** | N-tier custom | 가장 유연하나 MVP 범위 초과 |

**권장 A** — 기존 모델(`sponsorship.py`, `subscriptions` 테이블)과 직접 대응. 작가가 이해하기 쉬운 명칭.

---

### OQ-2: tier 계층 포함 규칙

**질문**: 작가가 `sponsor` tier를 선택했을 때, `subscriber`(더 높은 tier)도 볼 수 있는가?

| 옵션 | 규칙 |
|------|------|
| **A** | 좁은 → 넓은 순서로 자동 포함: `subscriber` 선택 시 구독자만, `sponsor` 선택 시 구독자+후원자, `follower` 선택 시 팔로워 포함 전부 |
| **B** | 정확히 선택한 1개 tier만 (구독자 선택 시 후원자는 못 봄) |
| **C** | 작가가 다중 선택 (체크박스) |

**권장 A** — `subscriber ⊆ sponsor ⊆ follower` 포함 관계가 사용자 멘탈 모델과 일치. 구독자가 후원자 콘텐츠를 못 보는 상황(B)은 직관에 반함. C는 UI 복잡도 증가.

---

### OQ-3: 우선 공개 기간

**질문**: 기간 입력 방식을 어떻게 할 것인가?

| 옵션 | 방식 |
|------|------|
| **A** | 5개 preset: 1시간 / 6시간 / 24시간 / 3일 / 7일 |
| **B** | 자유 datetime 입력 |
| **C** | preset + 자유 입력 둘 다 |

**권장 A** — UX 단순, 분석 시 기간별 비교 용이. 대부분 작가에게 5가지면 충분. 추후 요청 시 B로 확장.

---

### OQ-4: tier 자격 검증 시점

**질문**: tier 자격을 언제 검증하는가?

| 옵션 | 시점 |
|------|------|
| **A** | 발행 시 자격자 ID 스냅샷 (`PostTierSnapshot` 별도 테이블) |
| **B** | 매 조회 시 실시간 DB 검증 |

**권장 B** — 구독 취소, 후원 환불, 언팔로우 등 자격 변경이 즉시 반영됨. 스냅샷 방식은 별도 테이블 + 동기화 복잡도가 큼. 조회 시 `Subscription`/`Sponsorship`/`Follow` 테이블에 대한 서브쿼리 1회 추가로 충분 (OQ-10과 연계).

---

### OQ-5: cron worker 주기

**질문**: `tier_release_jobs.py` cron 주기를 얼마로 할 것인가?

| 옵션 | 주기 |
|------|------|
| **A** | 60초 (`schedule_jobs.py`와 동일) |
| **B** | 5분 |
| **C** | 작가 수동 트리거 |

**권장 A** — 기존 `app/services/schedule_jobs.py`와 동일 패턴 재사용. 최대 지연 60초는 기간 만료의 허용 오차로 충분. `app/main.py` startup에 동일한 `asyncio.create_task` 방식으로 등록.

---

### OQ-6: tier_only와 기존 visibility 결합 여부

**질문**: early_access 기간 중 포스트의 visibility 처리를 어떻게 할 것인가?

| 옵션 | 방식 |
|------|------|
| **A** | 상호 배타적 — tier_only 활성 기간 중 원래 visibility 무시. 만료 후 원래 visibility로 복귀 |
| **B** | 결합 가능 — `visibility=unlisted + tier_only` = 링크 접근 + tier 자격 모두 필요 |

**권장 A** — 작가 의도 명확. B는 UI/로직 복잡도 급증. 대부분 "tier 기간 지나면 public으로" 패턴이 주류.

---

### OQ-7: tier 만료 후 visibility

**질문**: `early_access_until` 만료 시 포스트 visibility를 어떻게 처리하는가?

| 옵션 | 방식 |
|------|------|
| **A** | 자동으로 `public` | cron에서 `visibility='public'`으로 고정 변경 |
| **B** | 발행 시 지정한 원래 `Post.visibility` 복귀 | `early_access_until=null`로만 설정 → `Post.visibility` 원래 값 자동 사용 |

**권장 B** — DB에서 `early_access_until`만 null로 설정하면 `Post.visibility` 기존 값이 자동으로 effective visibility가 됨. 작가가 발행 시 "만료 후 `followers_only`" 설정 가능. cron worker 로직도 단순 (`visibility` 컬럼 변경 없음, `early_access_until=null`만).

---

### OQ-8: TierReleasePicker UI 위치

**질문**: `TierReleasePicker` 컴포넌트를 어디에 배치하는가?

| 옵션 | 위치 |
|------|------|
| **A** | `PublishOptionsPanel.tsx` 내 expand 섹션 ("우선 공개" 체크박스 → 펼쳐지면 tier + 기간 선택) |
| **B** | 별도 모달 |
| **C** | 별도 wizard step |

**권장 A** — #8에서 확립한 `PublishOptionsPanel` 패턴 일관. expand 섹션은 기본적으로 접혀 있어 기존 발행 흐름 불변. B/C는 wizard step 추가로 발행 마찰 증가.

---

### OQ-9: API endpoint 통합

**질문**: early_access를 기존 `POST /v1/posts/{id}/publish` 에 통합할 것인가, 별도 endpoint를 만들 것인가?

| 옵션 | 방식 |
|------|------|
| **A** | `POST /v1/posts/{id}/publish` body 확장 (early_access_until + early_access_tier 추가) |
| **B** | 별도 `POST /v1/posts/{id}/tier-release` |

**권장 A** — 단일 발행 트랜잭션 내에서 visibility + comments + series + early_access를 함께 처리. 기존 `publish_post` (`app/api/posts.py:179`) 코드 재사용. B는 별도 endpoint + 별도 트랜잭션으로 일관성 위험 증가.

---

### OQ-10: tier 자격 cache

**질문**: 피드 조회 시 tier 자격 검증에 cache를 사용하는가?

| 옵션 | 방식 |
|------|------|
| **A** | no-cache (매 조회마다 DB `Subscription`/`Sponsorship`/`Follow` 검사) |
| **B** | Redis cache (TTL 5분, user_id+artist_id 키) |

**권장 A** — 단순성 우선. 구독 취소 즉시 반영(OQ-4=B)와도 일관. tier_only 포스트가 초기에 많지 않을 것이므로 N+1 위험 낮음. 피드 성능 저하가 실측으로 확인되면 #10.1에서 Redis 도입.

---

## 5. Acceptance Criteria

| ID | 기준 | 검증 방법 |
|----|------|-----------|
| AC-1 | `posts.early_access_until` / `posts.early_access_tier` 컬럼 생성. 기존 행은 모두 null | `\d posts` + SELECT 확인 |
| AC-2 | `POST /v1/posts/{id}/publish` body에 `early_access_until` + `early_access_tier` 포함 시 DB 정상 저장 | curl + DB 확인 |
| AC-3 | `early_access_until` 만 있고 `early_access_tier` 없으면 (또는 반대) Pydantic validation 422 반환 | curl |
| AC-4 | active early_access 포스트를 tier 자격 없는 viewer가 피드/탐색/검색에서 조회 시 미노출 | curl (subscriber 아닌 토큰) |
| AC-5 | tier 자격 있는 viewer가 active early_access 포스트 피드 조회 시 정상 노출 | curl (active subscriber 토큰) |
| AC-6 | `GET /v1/posts/{id}` — tier 자격 없는 viewer → 403 `TIER_ACCESS_DENIED` | curl |
| AC-7 | `GET /v1/posts/{id}` — tier 자격 있는 viewer → 200 + `is_tier_locked=false` | curl |
| AC-8 | `GET /v1/posts/{id}` — tier 자격 없는 viewer → 200 + `is_tier_locked=true` (피드에서는 잠금 표시 전용) | curl |
| AC-9 | `tier_release_jobs.py` cron 실행 후 `early_access_until <= now()` 포스트의 `early_access_until=null`, `early_access_tier=null` 확인 | 통합 테스트 (time mock) |
| AC-10 | tier 만료 후 포스트 visibility는 발행 시 지정한 원래 값으로 복귀 (e.g., `followers_only`) | DB + curl |
| AC-11 | `TierReleasePicker` tier 3종 + 기간 preset 5종 렌더. `PublishOptionsPanel` 내 expand 섹션 위치 확인 | 수동 |
| AC-12 | `FeedItem`/`PostCard` — `is_tier_locked=true` 시 `LockClosedIcon` + 한국어 tooltip 렌더 | 수동 |
| AC-13 | 구독 취소 후 해당 viewer가 tier_only 포스트에 접근 시 403 (실시간 검증) | curl 순서 테스트 |
| AC-14 | 5 locale i18n 신규 키 (~12키) 모두 표시, 누락 없음 | 수동 × 5 locale |
| AC-15 | #8 5 통합 지점 회귀 0 (autosave / DraftRestoreDialog / 멀티탭 / role-gating / useArtistGate) | 수동 체크리스트 |

---

## 6. Risks

| ID | Risk | Impact | 완화 방안 |
|----|------|:------:|-----------|
| R-1 | `Post.visibility` CHECK constraint 또는 application enum 검증이 `tier_only` 값을 거부할 경우 alembic migration 실패 | High | `Post.visibility`는 `String(20)` 으로 CHECK constraint 없음(`app/models/post.py:50`). Pydantic schema의 Literal 타입에 `tier_only` 추가. alembic 0041은 컬럼 추가만 (DDL 변경 없음) |
| R-2 | tier 자격 검증 N+1 쿼리 — 피드에서 tier_only 포스트 수만큼 개별 서브쿼리 | High | `_visibility_filter_for_viewer` 에서 단일 OR 서브쿼리로 통합 처리. 팔로워 패스트패스(`followee_ids`) 동일 전략 — subscription/sponsorship도 viewer별 1회 pre-fetch 후 재사용 |
| R-3 | cron worker 누락 시 tier 만료 지연 (최대 60초 초과 가능성) | Low | 매 조회 시 `early_access_until > now()` 를 DB에서 실시간 계산 — worker가 늦어도 effective visibility는 정확히 처리됨. Worker는 DB cleanup 역할 (성능 최적화), 필수 경로가 아님 |
| R-4 | `TierReleasePicker` UI 복잡도 — `PublishOptionsPanel` 이미 옵션 4개 (visibility/comments/series/scheduled). expand 섹션 추가로 UI 과밀 | Medium | 기본 접힘(collapsed) 상태. "우선 공개" 단일 체크박스만 노출 → 체크 시 tier+기간 expand. 인지 부하 최소화 |
| R-5 | `publish_post` endpoint (`app/api/posts.py:179`) 기존 동작 회귀 — early_access 필드 추가 후 기존 클라이언트(early_access 없이 호출)가 422 받을 위험 | High | `early_access_until: datetime | None = None` (기본값 null). 기존 클라이언트는 필드 미포함 시 null로 처리 — breaking change 없음 |
| R-6 | OQ-2 계층 포함 규칙(A) 구현 시 `sponsor` tier 검증이 `Subscription` + `Sponsorship` 두 테이블 동시 조회 → 쿼리 복잡도 증가 | Medium | 단일 `OR (subscriber_check OR sponsor_check)` 서브쿼리로 처리. `UNION` 대신 OR 체인으로 구성 — PostgreSQL planner가 효율적으로 처리 |

---

## 7. Dependencies

| 의존성 | 상태 | 관계 |
|--------|:----:|------|
| Phase 3 `#8 publish-controls` | ✅ archived 2026-05-03 | `Post.visibility` 시스템 + `_visibility_filter_for_viewer` helper + `POST /v1/posts/{id}/publish` endpoint 기반 제공 |
| `app/models/sponsorship.py` — `Sponsorship` + `Subscription` | ✅ 존재 | tier 자격 검증 쿼리에 직접 활용. 신규 마이그레이션 불필요 |
| `app/models/post.py` — `Follow` | ✅ 존재 | `follower` tier 자격 검증에 직접 활용 |
| `app/services/schedule_jobs.py` | ✅ 동작 중 | `tier_release_jobs.py` 구조 참조 |
| Phase 4 `#11 auction-promotion-suite` | 독립 — 병렬 가능 | 의존 없음 |
| Phase 4.5 `#9 artist-pricing-assist` | 보류 중 | 본 PDCA 완료 후에도 독립 진행 |

---

## 8. Implementation Order (Phased Delivery)

### PR1 — Backend Foundation (~1.5일)

1. alembic `0041_post_early_access.py`: `posts.early_access_until DateTime(timezone=True) nullable` + `posts.early_access_tier String(20) nullable`. 기존 행 null. additive migration
2. `app/models/post.py` — `early_access_until` + `early_access_tier` 컬럼 추가
3. `app/schemas/series.py` — `PostPublishRequest`에 `early_access_until: datetime | None = None` + `early_access_tier: Literal['subscriber','sponsor','follower'] | None = None` + cross-field validator 추가
4. `app/schemas/post.py` — `PostOut`에 `early_access_until`, `early_access_tier`, `is_tier_locked` 필드 추가
5. smoke: `alembic upgrade head` + `\d posts` 확인

**PR1 회귀 체크**: 기존 포스트 API 응답 동일 (신규 필드 null로 추가).

### PR2 — Backend Logic + Worker (~1.5일)

1. `app/api/posts.py` — `_visibility_filter_for_viewer` 확장: `tier_only` effective visibility 분기 추가. `early_access_until > now()` 검사 + tier 계층별 subquery OR 체인 (`Subscription`/`Sponsorship`/`Follow`)
2. `app/api/posts.py` — `publish_post` endpoint 확장: `early_access_until` + `early_access_tier` DB 저장
3. `app/api/posts.py` — `GET /v1/posts/{id}` (또는 `_serialize_post`): `is_tier_locked` 계산 로직 추가
4. `app/services/tier_release_jobs.py` 신규 — `tier_release_once()` + asyncio 60초 loop
5. `app/main.py` — startup에 `tier_release_jobs` task 등록
6. 단위 테스트 + 통합 테스트
7. `scripts/smoke_test_tier_release.sh` 신규

**PR2 회귀 체크**: `publish_post` 기존 동작 (early_access null 케이스) 유지. `_visibility_filter_for_viewer` 기존 public/followers_only/unlisted 분기 유지.

### PR3 — Frontend + 통합 (~1.5일)

1. `src/components/post-editor/TierReleasePicker.tsx` 신규 컴포넌트 — tier radio + 기간 preset select
2. `src/components/post-editor/PublishOptionsPanel.tsx` — `TierReleasePicker` expand 섹션 통합
3. `src/lib/api.ts` — `publishPost()` 에 `earlyAccessUntil` + `earlyAccessTier` 파라미터 추가
4. `FeedItem` / `PostCard` — `is_tier_locked` prop 기반 `LockClosedIcon` + tooltip 렌더
5. i18n: 5 locale `post.editor.tierRelease.*` + `feed.tierLocked.*` 신규 키 (~12키)
6. 5 통합 지점 회귀 수동 체크리스트

**PR3 회귀 체크**: `PublishOptionsPanel` 기존 옵션 (visibility/comments/series/scheduled) 정상 동작. 기존 발행 흐름 (early_access 미사용) 불변.

---

## 9. Carry-over Awareness

본 PDCA 진입 시점 기존 carry-over 현황:

| Carry-over | 출처 | 처리 방안 |
|-----------|------|-----------|
| `editor-video-studio` (#6-video, ffmpeg 차단) | Phase 2 | 별도 PDCA. 본 PDCA 영향 없음 |
| `series reorder persistence endpoint` | #8 publish-controls | `#11` 또는 minor fix. 본 PDCA 영향 없음 |
| `upload-retry-ui` | 이전 누적 | 별도 minor fix |
| `editor-i18n-cleanup` v0.2 | 이전 누적 | PR3 i18n 작업 시 병행 처리 시도 |

본 PDCA 완료 후 진입 가능한 후속:
- **우선**: `#11 auction-promotion-suite` (Phase 4 마지막 — 독립, 병렬 가능)
- **별도**: `#12 notifications-ux-audit` (Phase 3, 독립)
- **추후**: tier 가격 추천 / tier 진입 alert UI (데이터 축적 후)

---

## 10. Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 0.1 | 2026-05-03 | Initial draft. `#10 artist-tier-release` plan. B-4 후원자/단골 우선 공개 요구사항. 2 컬럼 마이그레이션 + visibility 시스템 확장 + tier_release_jobs + TierReleasePicker. OQ 10개 권장 default 포함. | itpe-ince (Claude Opus 4.7 + bkit product-manager agent) |
| 1.0 | 2026-05-03 | OQ 10/10 모두 권장 default 일괄 수락 (사용자 결정). status: draft → oq_resolved. §4 헤더에 결정 echo 표 추가, 상세 OQ 본문은 참고용 보존. /pdca design 진입 가능. | itpe-ince |
