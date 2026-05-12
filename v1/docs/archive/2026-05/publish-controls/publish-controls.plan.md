---
template: plan
version: 1.0
feature: publish-controls
sub-pdca: "#8"
phase: Phase 3 — Publishing System
date: 2026-05-03
author: itpe-ince (Claude Opus 4.7 + bkit product-manager agent)
project: domo
project_version: v1
parent_roadmap: editor-revamp-roadmap.plan.md
estimate: L (1.5주, 8-12일)
status: oq_resolved
oq_resolved_at: 2026-05-03
---

# publish-controls Planning Document

> **Summary**: 작가가 포스트 발행 시점에 (a) 공개 범위, (b) 댓글 허용, (c) 시리즈 묶기, (d) 예약 발행을 통합 제어할 수 있는 `PublishOptionsPanel`을 도입한다. DB 마이그레이션 3개 + 신규 `Series` 모델 + `POST /v1/posts/{id}/publish` 엔드포인트 + 피드/탐색/검색 visibility 필터.
>
> **Status**: Draft v0.1
> **Sub-PDCA**: #8 (Critical Path) — Phase 3 Publishing System
> **Parent Roadmap**: [editor-revamp-roadmap.plan.md](./editor-revamp-roadmap.plan.md)

---

## 0. Roadmap Context

`editor-revamp-roadmap.plan.md` §1.B-3에는 발행 옵션에 대한 요구사항 4건이 다음과 같이 원문 그대로 명시되어 있다:

> - **공개 범위** (전체/팔로워/링크만) 선택 기능 필요
> - **댓글 허용/비허용** 기능 필요
> - **작품 카탈로그(시리즈) 묶기** 기능 필요
> - **예약 발행** 기능 필요

본 PDCA `#8 publish-controls`는 이 4건을 전부 구현하는 **Critical Path의 다섯 번째 단계**이다 (1 → 2 → 3 → 4 → 6-image → **8** → 10). Phase 2 #4 `editor-media-ux` 및 #6-image `editor-image-studio`가 2026-05-03자로 아카이브되어 선행 의존성이 충족되었다.

본 PDCA 완료 후 Phase 4 `#10 artist-tier-release`가 진입 가능하다. `#10`은 **sponsor-only 공개(티어 기반 early access)**를 다루는데, 이 기능은 본 PDCA에서 확립하는 `Post.visibility` 시스템을 직접 상속한다. 따라서 본 PDCA에서 visibility enum 명칭·DB 컬럼·노출 필터 위치를 잘못 설계하면 Phase 4 전체를 재작업해야 한다.

---

## 1. Overview

### 1.1 What

| 영역 | 현재 | 목표 |
|------|------|------|
| 공개 범위 | 없음 — 모든 published 포스트가 피드/탐색/검색에 노출 | `Post.visibility` enum (`public` / `followers_only` / `unlisted`). 피드·탐색·검색·북마크·프로필 게시물 목록에 필터 적용 |
| 댓글 허용 | 없음 — 모든 포스트에 댓글 가능 | `Post.comments_enabled` bool. `false` 시 신규 댓글 `COMMENTS_DISABLED` 403 |
| 시리즈 | 없음 | `Series` 신규 모델 + `post_series_membership` join 테이블. M:N (한 포스트가 여러 시리즈 가능). CRUD API 5개 + `/series/{id}` 페이지 + 작가 프로필 시리즈 탭 |
| 예약 발행 | `Post.scheduled_at` 컬럼 존재 + `schedule_jobs.py` cron worker 동작 (status='scheduled' → 'published' 자동 전환, 60초 주기) — 그러나 **UI 미연결** | `posts/new/page.tsx:357`에서 `scheduled_at`을 payload에 담고는 있으나 UI datetime picker 미구현. `POST /v1/posts/{id}/publish` 신규 엔드포인트로 visibility/comments/series/scheduled_at를 하나의 발행 action으로 통합 |
| PublishOptionsPanel | 없음 | 에디터에 통합 발행 옵션 패널 신규 |

### 1.2 Why

- 로드맵 §1.B-3 요구사항 4건 전부 충족
- Phase 4 `#10 artist-tier-release`의 visibility 시스템 기반 마련
- 작가 자율성 강화 — 플랫폼이 작가의 배포 전략 결정을 지원 (팔로워 선공개, 초대 전용 링크, 예약 발행)
- 현재 모든 발행이 `status='pending_review'`로만 처리 — 공개 범위/댓글 제어 완전 부재

### 1.3 Background

**현재 코드 베이스 상태** (검증 완료):

- `app/models/post.py:43` — `Post.status` (`'draft' | 'pending_review' | 'published' | 'hidden' | 'deleted'`). `'scheduled'` 지원 이미 있음
- `app/models/post.py:48-50` — `Post.scheduled_at: DateTime(timezone=True)` 이미 존재
- `Post.visibility` 컬럼 **없음** (신규 추가 필요)
- `Post.comments_enabled` 컬럼 **없음** (신규 추가 필요)
- `Series` 모델 **없음** (신규 모델 필요)
- `app/services/schedule_jobs.py:21-38` — `publish_scheduled_posts_once()`: `status='scheduled'` AND `scheduled_at <= NOW()` 인 포스트를 `pending_review`(미디어 있음) 또는 `published`(미디어 없음)로 자동 전환. **이미 동작 중** — UI만 연결하면 됨
- `app/api/posts.py:309-386` — `home_feed`: `Post.status == "published"` 필터만 있음, visibility 필터 없음
- `app/api/posts.py:389-426` — `explore_posts`: 동일, visibility 필터 없음
- `app/api/posts.py:429-526` — `search_posts`: 동일, visibility 필터 없음
- `app/api/posts.py:649-672` — `my_bookmarks`: visibility 필터 없음
- `frontend/src/app/posts/new/page.tsx:357` — `scheduled_at: scheduledAt || undefined` 이미 payload에 포함. UI datetime picker만 없음

**재사용 가능한 기존 인프라**:
- `#4 editor-media-ux`의 `_check_auction_media_lock` 패턴 — visibility 변경 시 auction active 검사에 동일 패턴 적용 가능
- `#3 editor-responsive-redesign`의 wizard step 구조 — `PublishOptionsPanel`을 별도 wizard step으로 배치
- `dnd-kit` (#4에서 도입) — 시리즈 내 포스트 순서 drag-reorder에 재사용 가능

### 1.4 Related Documents

- 부모 로드맵: [editor-revamp-roadmap.plan.md](./editor-revamp-roadmap.plan.md) §1.B-3 + §2 Phase 3 + §3 의존성 + §4 row #8
- 선행 아카이브: `docs/archive/2026-05/editor-media-ux/` (#4), `docs/archive/2026-05/editor-image-studio/` (#6-image)
- 후속 PDCA: `#10 artist-tier-release` (본 PDCA의 `Post.visibility` 시스템 위에 구축)

---

## 2. Scope

### 2.1 In Scope

#### A. 공개 범위 (Visibility)

- `Post.visibility` 컬럼 신규 — `String(20)`, default `'public'`
  - `public`: 피드/검색/탐색 모두 노출 (기본값)
  - `followers_only`: 작가를 팔로우한 사용자에게만 노출 (home_feed 팔로잉 파트 + 작가 프로필)
  - `unlisted`: 링크 직접 접근만 가능. 피드/검색/탐색/북마크 제외
- alembic 마이그레이션 `0038_post_visibility.py` (additive, default `'public'`, 기존 포스트 backfill)
- visibility 필터 적용 엔드포인트: `home_feed`, `following_feed` (미구현 시 home_feed와 통합), `explore_posts`, `search_posts`, `my_bookmarks`, `GET /v1/users/{id}/posts` (작가 프로필 게시물 목록)
- DB 인덱스: `posts(visibility, status, created_at DESC)` — 피드 쿼리 성능 보장
- `followers_only`: 비팔로워가 `/posts/{id}` 직접 접근 시 `POST_VISIBILITY_RESTRICTED` 403 (작성자 본인·admin 제외)
- `unlisted`: `/posts/{id}` 직접 접근은 허용 (UUID v4 추측 거의 불가능 — OQ-7 참조)

#### B. 댓글 허용 (Comments Enabled)

- `Post.comments_enabled` 컬럼 신규 — `Boolean`, default `True`
- alembic 마이그레이션 `0039_post_comments_enabled.py` (additive)
- `POST /v1/posts/{id}/comments` — `comments_enabled is False` 시 `COMMENTS_DISABLED` 403
- 기존 댓글 보존 (변경 시점 이후 신규 작성만 차단, 기존 댓글 읽기 정상)
- `GET /v1/posts/{id}/comments` — comments_enabled 관계없이 기존 댓글 조회 가능

#### C. 시리즈 (Series)

- `Series` 신규 모델 (`app/models/series.py`):
  - `id: UUID PK`
  - `author_id: UUID FK(users.id)`
  - `title: String(200) NOT NULL`
  - `description: Text nullable`
  - `cover_url: Text nullable` (수동 업로드 우선, 없으면 첫 번째 포스트 thumbnail 자동 — OQ-4=C)
  - `created_at: DateTime`, `updated_at: DateTime`
- `post_series_membership` 신규 join 테이블:
  - `series_id: UUID FK(series.id, CASCADE)`
  - `post_id: UUID FK(posts.id, CASCADE)`
  - `order_index: Integer default 0`
  - PK: `(series_id, post_id)`
- alembic 마이그레이션 `0040_series_model.py`
- API 엔드포인트:
  - `GET /v1/series?author_id=` — 작가의 시리즈 목록 (공개/비공개 구분 없이 본인에게 반환, 타인은 public 시리즈만)
  - `POST /v1/series` — 시리즈 생성 (인증 필수)
  - `PATCH /v1/series/{id}` — 수정 (소유자만)
  - `DELETE /v1/series/{id}` — 삭제 (소유자만, membership은 CASCADE)
  - `POST /v1/posts/{id}/series` — body: `{series_ids: [UUID]}` — 해당 포스트의 시리즈 소속 일괄 갱신 (기존 제거 + 신규 추가). 빈 배열 = 모든 시리즈에서 제거
- 한 포스트는 여러 시리즈에 속할 수 있음 (M:N)
- selectinload로 N+1 회피
- 신규 프런트엔드 페이지: `/series/[id]` (시리즈 상세 — 포스트 갤러리)
- 작가 프로필에 시리즈 탭 추가 (`/users/[id]?tab=series` 또는 `/users/[id]/series` 별도 라우트)

#### D. 예약 발행 (Scheduled Publish)

- `Post.scheduled_at` 이미 존재 (`app/models/post.py:48-50`)
- `app/services/schedule_jobs.py:21-38` cron worker 이미 동작 (60초 주기, `status='scheduled'` → `published` 자동 전환)
- 신규: `PublishOptionsPanel`에 datetime picker UI (`scheduled_at` 입력)
- 신규 엔드포인트: `POST /v1/posts/{id}/publish` — body:
  ```json
  {
    "publish_at": "ISO8601 datetime | null",
    "visibility": "public | followers_only | unlisted",
    "comments_enabled": true,
    "series_ids": ["uuid", ...]
  }
  ```
  - `draft` / `scheduled` / `pending_review` 상태 포스트를 `published` (또는 `scheduled` — `publish_at` 있을 경우)로 promote
  - visibility / comments_enabled / series 소속 동시에 설정
  - 소유자 + admin만 가능
  - active auction 포스트는 visibility 변경 제한 (`AUCTION_ACTIVE_VISIBILITY_LOCKED` 409 — `_check_auction_media_lock` 패턴 재사용)

#### E. PublishOptionsPanel (프런트엔드)

- 신규 컴포넌트 `PublishOptionsPanel.tsx` (`src/components/post-editor/`)
  - 공개 범위 라디오 3개 (`public` / `followers_only` / `unlisted`) + 각 설명 텍스트
  - 댓글 허용 토글 스위치
  - 시리즈 선택 multi-select dropdown (작가의 기존 시리즈 목록 + "새 시리즈 만들기" 인라인 생성)
  - 예약 발행 datetime picker (선택 시 발행 버튼 텍스트 → "예약 발행")
- `posts/new/page.tsx` 통합 — wizard step 또는 우측 sidebar (OQ-8 결정에 따름)
- `posts/[id]/edit` 통합 — 동일 컴포넌트 재사용
- 피드 카드에 visibility 인디케이터 (followers_only = 잠금 아이콘, unlisted = 링크 아이콘만 표시. public은 표시 없음)

### 2.2 Out of Scope

| 항목 | 이유 / 담당 PDCA |
|------|-----------------|
| Tier-based 공개 (sponsor-only / 후원자 우선 공개) | Phase 4 `#10 artist-tier-release` — `Post.early_access_until` 별도 컬럼 |
| 댓글 신고/숨김/모더레이션 | 별도 콘텐츠 모더레이션 기능 |
| 시리즈 결제/구독 (유료 시리즈) | Phase 4.5 deferred |
| 외부 SNS 자동 공유 | `#11 auction-promotion-suite` 또는 별도 |
| 시리즈 내 포스트 drag-reorder UI | 설계는 지원하나 (`order_index` 컬럼 있음) 드래그 UI는 `#12` 이후 또는 별도 — dnd-kit 재사용 검토 |
| 멤버십/구독 기반 followers_only | `#10`에서 확장. 현재는 단순 팔로우 관계만 |

---

## 3. Requirements

### 3.1 Functional Requirements

| ID | Requirement | Priority |
|----|-------------|:---:|
| FR-01 | `Post.visibility` String(20) 컬럼 신규 (default `'public'`). alembic `0038` | Must |
| FR-02 | `Post.comments_enabled` Boolean 컬럼 신규 (default `True`). alembic `0039` | Must |
| FR-03 | `Series` 모델 + `post_series_membership` join 테이블. alembic `0040` | Must |
| FR-04 | visibility 필터: `home_feed` / `explore_posts` / `search_posts` / `my_bookmarks` / 프로필 게시물 목록 — `followers_only`는 팔로워만, `unlisted`는 피드/검색/탐색 제외 | Must |
| FR-05 | DB 복합 인덱스 `posts(visibility, status, created_at DESC)` (alembic `0038`에 포함) | Must |
| FR-06 | `POST /v1/posts/{id}/comments` — `comments_enabled is False` 시 `COMMENTS_DISABLED` 403 | Must |
| FR-07 | 기존 댓글은 `comments_enabled` 변경과 무관하게 조회 가능 | Must |
| FR-08 | `GET /v1/series?author_id=`, `POST /v1/series`, `PATCH /v1/series/{id}`, `DELETE /v1/series/{id}` CRUD | Must |
| FR-09 | `POST /v1/posts/{id}/series` — body `{series_ids: []}` — 포스트-시리즈 소속 일괄 갱신 | Must |
| FR-10 | `POST /v1/posts/{id}/publish` — visibility + comments_enabled + series_ids + publish_at 통합 발행 엔드포인트 | Must |
| FR-11 | `followers_only` 포스트 비팔로워 직접 접근 → `POST_VISIBILITY_RESTRICTED` 403 | Must |
| FR-12 | active auction 포스트 visibility 변경 → `AUCTION_ACTIVE_VISIBILITY_LOCKED` 409 | Should |
| FR-13 | `PublishOptionsPanel` 컴포넌트 (공개범위 라디오 + 댓글 토글 + 시리즈 multi-select + 예약 datetime picker) | Must |
| FR-14 | `posts/new` 및 `posts/[id]/edit` 에 `PublishOptionsPanel` 통합 | Must |
| FR-15 | `/series/[id]` 신규 페이지 (시리즈 상세 — 포스트 갤러리) | Should |
| FR-16 | 작가 프로필 시리즈 탭 | Should |
| FR-17 | 피드 카드에 `followers_only` / `unlisted` visibility 인디케이터 표시 | Should |
| FR-18 | 5 통합 지점 회귀 0 (autosave / DraftRestoreDialog / 멀티탭 / role-gating / useArtistGate) | Must |
| FR-19 | i18n 신규 키 (~30키 × 5 locale) 누락 0 | Must |
| FR-20 | 시리즈 cover_url: 수동 업로드 우선, 없으면 첫 번째 포스트 thumbnail 자동 사용 (OQ-4=C) | Could |

### 3.2 Non-Functional Requirements

| Category | Criteria |
|----------|----------|
| 성능 | visibility 복합 인덱스 추가 후 피드/탐색/검색 쿼리 응답 시간 기존 대비 저하 없음 |
| N+1 방지 | 시리즈 목록 쿼리 `selectinload` 사용 (membership + posts 일괄 로드) |
| 회귀 | TS 0 에러, ruff 0 에러. 5 통합 지점 + 기존 피드/탐색/검색/북마크 흐름 동일 |
| 보안 | `followers_only` 비팔로워 차단 서버 사이드 강제 (클라이언트 신뢰 불가) |
| i18n | 5 locale (ko/en/ja/zh/es) 신규 키 ~30개 모두 등록 |
| 타임존 | `scheduled_at`은 UTC 저장, 클라이언트 로컬 시간 변환은 프런트에서 처리 (OQ-6 참조) |

---

## 4. Open Questions — ✅ ALL RESOLVED (2026-05-03 사용자 권장 default 일괄 수락)

| ID | 결정 | 영향 |
|----|------|------|
| OQ-1 = A | `public/followers_only/unlisted` enum | DB column type, API filter, UI labels |
| OQ-2 = A | 기존 행 모두 `public` backfill | alembic 마이그레이션 default value |
| OQ-3 = A | `comments_enabled=false` 시 기존 댓글 보존 (읽기 전용) | API: 신규 댓글만 차단, 기존 GET 정상 |
| OQ-4 = C | `cover_url` 수동 우선 + 첫 포스트 thumbnail fallback | DB nullable + 프런트 fallback |
| OQ-5 = A | 시리즈 내 포스트 수동 drag-reorder (`#4 dnd-kit` 재사용) | `/series/[id]` 편집 모드만 |
| OQ-6 = A | `scheduled_at` 5분~1년 범위 | Pydantic 검증 |
| OQ-7 = A | `unlisted` 포스트 URL `/posts/{uuid}` 그대로 | 추가 라우팅 0 |
| OQ-8 = A | PublishOptionsPanel = wizard step + 사이드바 | `#3 + #4` 패턴 재사용 |
| OQ-9 = A | `POST /v1/posts/{id}/publish` 신규 endpoint | semantic clarity, audit log |
| OQ-10 = A | visibility filter SQLAlchemy WHERE + 복합 인덱스 `posts(visibility, status, created_at DESC)` | alembic 0038에 인덱스 함께 |

> 10/10 모두 권장 default 채택. **Plan v1.0 → /pdca design publish-controls 진입 가능.**

---

### OQ 상세 (참고용 보존)

---

### OQ-1: visibility enum 값 명칭

**질문**: DB 컬럼 + API에 저장할 enum 문자열 명칭을 어떻게 할 것인가?

| 옵션 | 값 예시 | 특징 |
|------|---------|------|
| **A** | `public` / `followers_only` / `unlisted` | 영문 명료, 언더스코어 일관성 |
| **B** | `public` / `private` / `link_only` | `private`이 followers 의미로 오해 가능 |
| **C** | `everyone` / `circle` / `link` | 마케팅적이나 DB 식별자로 부적합 |

**권장 A** — `followers_only`는 Phase 4 `#10`의 `early_access_tier`와 직교 개념으로 구분 명확. 기존 코드베이스의 `sponsorship.visibility` 패턴과도 일관.

---

### OQ-2: 기존 게시물(published/draft) backfill 정책

**질문**: alembic 0038 마이그레이션 실행 시 기존 포스트의 `visibility` 값을 어떻게 설정하는가?

| 옵션 | 방식 | 특징 |
|------|------|------|
| **A** | 모두 `'public'` (무조건) | 단순, 기존 사용자 경험 유지 |
| **B** | `status='published'` → `public`, 나머지 → `null` (별도 처리) | 복잡, null 예외 처리 필요 |
| **C** | migration default + 운영 중 재계산 배치 | 운영 복잡도 증가 |

**권장 A** — status와 visibility는 직교 개념. 모두 `public`으로 backfill이 가장 단순하고 기존 동작 보존. 신규 포스트부터 작가가 선택.

---

### OQ-3: `comments_enabled=false` 변경 시 기존 댓글 처리

**질문**: 작가가 댓글 비허용으로 전환 시 이미 달린 댓글을 어떻게 처리하는가?

| 옵션 | 방식 | 특징 |
|------|------|------|
| **A** | 기존 댓글 보존 (읽기 전용, 새 댓글만 차단) | 정보 손실 0, 입찰자 신뢰 보호 |
| **B** | 기존 댓글 일괄 숨김 (`status='hidden'`) | 작가 의도 강하게 반영하나 정보 손실 |
| **C** | 작가에게 선택지 제공 (보존/숨김) | 구현 복잡도 증가, MVP 과잉 |

**권장 A** — `#4 editor-media-ux`의 `_check_auction_media_lock` 정신과 동일: 한 번 공개된 정보(댓글)는 단방향 보존. 입찰 관련 댓글이 있을 경우 숨김 시 신뢰 문제 발생 가능성.

---

### OQ-4: 시리즈 cover_url 자동 생성

**질문**: 시리즈 커버 이미지를 어떻게 결정하는가?

| 옵션 | 방식 | 특징 |
|------|------|------|
| **A** | 작가가 직접 업로드만 | 단순하나 빈 시리즈 표지가 없음 |
| **B** | 첫 번째 포스트 thumbnail 자동 사용 | 별도 업로드 불필요 |
| **C** | 둘 다: 수동 업로드 우선, 없으면 첫 번째 포스트 thumbnail 자동 fallback | 최선 UX |

**권장 C** — `cover_url nullable`로 DB 설계 + 프런트에서 null 시 첫 번째 포스트 thumbnail으로 fallback 렌더. 추가 API 호출 없이 처리 가능.

---

### OQ-5: 시리즈 내 포스트 순서

**질문**: `post_series_membership.order_index` 값을 어떻게 관리하는가?

| 옵션 | 방식 | 특징 |
|------|------|------|
| **A** | 작가 수동 drag-reorder | 의도적 순서 가능. `dnd-kit` (#4에서 도입) 재사용 |
| **B** | 게시물 발행순 자동 정렬 (created_at) | 별도 UI 불필요. 비직관적 시리즈 가능 |
| **C** | 두 모드 토글 (수동 / 발행순) | 구현 복잡도 증가 |

**권장 A** — `dnd-kit`은 이미 `#4 editor-media-ux`에서 설치·검증됨. 시리즈 내 순서는 예술적 서사 흐름에 중요. 단, 드래그 UI는 `/series/[id]` 편집 모드에서만 제공 (본 PDCA `Could`로 처리 — FR-15와 연계).

---

### OQ-6: 예약 발행 `scheduled_at` 시간 범위 제한

**질문**: 예약 발행 시 허용할 최소/최대 시간 범위는?

| 옵션 | 범위 |
|------|------|
| **A** | 최소 5분 이후 ~ 최대 1년 이내 |
| **B** | 즉시 ~ 최대 6개월 이내 |
| **C** | 제한 없음 (작가 자유 입력) |

**권장 A** — 5분 최소: `schedule_jobs.py`가 60초 주기이므로 5분 미만은 즉시 발행과 동일 (사용자 혼란). 1년 최대: 너무 먼 예약은 포스트 맥락이 바뀌는 경우 많음. Pydantic 검증으로 서버 사이드 강제.

---

### OQ-7: `unlisted` 링크 형태

**질문**: `unlisted` 포스트의 URL 구조를 어떻게 할 것인가?

| 옵션 | URL 예시 | 특징 |
|------|----------|------|
| **A** | `/posts/{uuid}` (기존과 동일) | UUID v4 추측 거의 불가능. 추가 구현 0 |
| **B** | `/p/{slug}` 별도 추가 | 짧은 URL 가능하나 slug 생성/중복 관리 필요 |
| **C** | `/posts/{uuid}?token=` 추가 | 토큰 만료 관리, 공유 링크 교체 복잡도 |

**권장 A** — UUID v4는 122비트 랜덤 공간으로 열거 공격 실질적 불가능. 추가 구현 0. Phase 4.5 이후 단축 URL 기능이 추가된다면 그 시점에 확장.

---

### OQ-8: PublishOptionsPanel UI 위치

**질문**: 발행 옵션 패널을 어디에 배치할 것인가?

| 옵션 | 위치 | 특징 |
|------|------|------|
| **A** | 모바일: 새 wizard step / 데스크탑: 우측 sidebar | `#3 responsive-redesign` wizard 패턴 일관성 |
| **B** | 발행 버튼 옆 dropdown | 단순하나 항목 4개로 dropdown이 복잡해짐 |
| **C** | 별도 모달 | 기존 에디터 흐름 단절 |

**권장 A** — `#3 editor-responsive-redesign`에서 확립한 wizard step + `#4 EditorWorkspace` 우측 sidebar 패턴을 그대로 재사용. 구현 비용 낮고 UX 일관성 최고.

---

### OQ-9: `POST /v1/posts/{id}/publish` 신규 vs 기존 `PATCH /v1/posts/{id}` 확장

**질문**: 발행 통합 엔드포인트를 신규로 만들 것인가, 기존 PATCH에 추가할 것인가?

| 옵션 | 방식 | 특징 |
|------|------|------|
| **A** | `POST /v1/posts/{id}/publish` 신규 엔드포인트 | semantic clarity, `draft→published` 상태 천이 명시 |
| **B** | 기존 `PATCH /v1/posts/{id}` 확장 | 엔드포인트 추가 없음. 그러나 상태 천이와 일반 수정이 혼재 |

**권장 A** — 발행은 상태 천이(state transition)이므로 PUT/PATCH보다 POST가 적합. 현재 `app/api/posts.py`에 별도 `PATCH /v1/posts/{id}` 엔드포인트가 없으므로 신규 추가가 더 명확. 또한 audit log 작성, visibility 검증, series 갱신을 하나의 트랜잭션으로 묶기 좋음.

---

### OQ-10: visibility 필터 적용 위치 (Backend)

**질문**: `followers_only` / `unlisted` 필터를 어디서 처리할 것인가?

| 옵션 | 방식 | 특징 |
|------|------|------|
| **A** | SQLAlchemy WHERE 절 (DB 인덱스 활용) | 성능 최적. 인덱스 `posts(visibility, status, created_at)` |
| **B** | Python 응답 후 필터 | 인덱스 미사용, 불필요한 row fetch |
| **C** | 둘 다 (DB WHERE + Python 안전망) | 중복이나 안전. 로직 복잡도 증가 |

**권장 A** — `posts(visibility, status, created_at DESC)` 복합 인덱스를 alembic 0038에 함께 추가하면 WHERE 절이 인덱스를 풀로 활용. Python 후처리는 불필요.

---

## 5. Acceptance Criteria

| ID | 기준 | 검증 방법 |
|----|------|-----------|
| AC-1 | `public` 포스트는 비팔로워 피드/탐색/검색에 정상 노출 | curl + DB 확인 |
| AC-2 | `followers_only` 포스트는 팔로워 피드에만 노출, 비팔로워 피드/탐색/검색에 미노출 | curl (팔로워 토큰 vs 비팔로워 토큰) |
| AC-3 | `followers_only` 포스트 비팔로워 직접 접근(`GET /v1/posts/{id}`) → 403 `POST_VISIBILITY_RESTRICTED` | curl |
| AC-4 | `unlisted` 포스트는 피드/탐색/검색에 미노출, `/posts/{id}` 직접 접근 가능 | curl |
| AC-5 | `comments_enabled=false` 포스트에 댓글 작성 → 403 `COMMENTS_DISABLED` | curl |
| AC-6 | `comments_enabled=false` 전환 후 기존 댓글 `GET /v1/posts/{id}/comments` 정상 조회 | curl |
| AC-7 | `POST /v1/series` 시리즈 생성 → `GET /v1/series?author_id=` 목록 반환 | curl |
| AC-8 | `POST /v1/posts/{id}/series` `{series_ids: [uuid1]}` → 포스트가 시리즈에 소속 | DB 확인 |
| AC-9 | `POST /v1/posts/{id}/series` `{series_ids: []}` → 포스트가 모든 시리즈에서 제거 | DB 확인 |
| AC-10 | `POST /v1/posts/{id}/publish` `{publish_at: "5분후"}` → `status='scheduled'`, `scheduled_at` 설정 | DB 확인 |
| AC-11 | `schedule_jobs.py` cron 실행 후 `scheduled_at` 도달 포스트 자동 `published` 전환 | 통합 테스트 |
| AC-12 | `PublishOptionsPanel` 공개범위 라디오 3개 + 댓글 토글 + 시리즈 multi-select + datetime picker 렌더 | 수동 |
| AC-13 | active auction 포스트 visibility 변경 → 409 `AUCTION_ACTIVE_VISIBILITY_LOCKED` | curl |
| AC-14 | 5 locale 신규 i18n 키 (~30키) 모두 표시, 누락 없음 | 수동 × 5 locale |
| AC-15 | 5 통합 지점 회귀 0 (autosave / DraftRestoreDialog / 멀티탭 / role-gating / useArtistGate) | 수동 체크리스트 |
| AC-16 | DB 복합 인덱스 `posts(visibility, status, created_at DESC)` 생성 확인 | `\d posts` 또는 alembic 로그 |
| AC-17 | TypeScript 0 에러, ruff 0 에러 | CI |

---

## 6. Risks

| ID | Risk | Impact | 완화 방안 |
|----|------|:------:|-----------|
| R-1 | 피드/탐색/검색 쿼리에 visibility WHERE 추가 시 인덱스 없으면 Full Scan으로 성능 저하 | High | alembic `0038`에 복합 인덱스 `posts(visibility, status, created_at DESC)` 반드시 포함. EXPLAIN ANALYZE로 검증 |
| R-2 | `followers_only` 팔로워 판별 쿼리 추가로 home_feed N+1 위험 | Medium | follows 서브쿼리를 IN절로 일괄 처리. 팔로워 수 많은 사용자는 home_feed 이미 follow_result 로드 중 — 재사용 |
| R-3 | 예약 발행 `schedule_jobs.py` cron이 visibility/comments_enabled 신규 컬럼 인식 필요 | Low | cron은 status만 변경. visibility/comments_enabled는 발행 시 이미 설정된 값 유지 — cron 변경 불필요 |
| R-4 | `scheduled_at` 타임존 불일치 (사용자 로컬 vs UTC) | Medium | 서버는 UTC만 수신. 프런트 datetime picker에서 로컬→UTC 변환 + 표시 시 로컬 역변환 명시. OQ-6 최소 5분 제한이 buffer 역할 |
| R-5 | `/series/[id]` Next.js 라우트 충돌 (기존 `/series` 경로 검사 필요) | Low | `find v1/frontend/src/app -name "*.tsx" -path "*/series/*"` 로 기존 라우트 부재 확인 후 신규 생성 |
| R-6 | Phase 4 `#10`이 `Post.visibility` enum을 확장할 경우 본 PDCA 설계 수정 위험 | Medium | OQ-1에서 확장 가능한 `String(20)` 선택. `tier_only` 등 새 값 추가 시 alembic additive migration만 필요 |
| R-7 | 시리즈 무한 nesting — 포스트가 시리즈 자체에 속하는 구조는 모델적으로 불가 (Series ≠ Post), 단 `cover_url`이 포스트 thumbnail을 참조할 때 circular reference 가능성 | Low | cover_url은 단방향 참조 (Series → MediaAsset.thumbnail_url). 역방향 없음 |
| R-8 | `PATCH /v1/series/{id}` 소유자 검증 누락 시 타인의 시리즈 수정 가능 | High | design 단계에서 `check_series_ownership()` 헬퍼 정의 + 테스트 강제 |

---

## 7. Dependencies

| 의존성 | 상태 | 관계 |
|--------|:----:|------|
| Phase 2 `#4 editor-media-ux` | ✅ archived 2026-05-03 | `dnd-kit` 재사용 가능 (시리즈 포스트 reorder). `_check_auction_media_lock` 패턴 재사용 |
| Phase 2 `#6-image editor-image-studio` | ✅ archived 2026-05-03 | 영향 없음 — 미디어 처리와 visibility/comments/series는 직교 |
| Phase 3 `#12 notifications-ux-audit` | 독립 — 병렬 가능 | Phase 3 내에서 `#8`과 독립 진행 가능 |
| Phase 4 `#10 artist-tier-release` | 본 PDCA 완료 후 진입 | `Post.visibility` 시스템 위에 구축 (`posts.early_access_until` 추가) |
| Phase 4 `#11 auction-promotion-suite` | 본 PDCA 완료 후 진입 | 발행 시스템 기반 필요 |

---

## 8. Implementation Order (Phased Delivery)

### PR1 — Backend Foundation (~3일)

1. alembic `0038_post_visibility.py`: `Post.visibility` String(20) default `'public'` + 복합 인덱스 `posts(visibility, status, created_at DESC)` + 기존 게시물 backfill UPDATE
2. alembic `0039_post_comments_enabled.py`: `Post.comments_enabled` Boolean default `True`
3. alembic `0040_series_model.py`: `Series` 테이블 + `post_series_membership` join 테이블
4. `app/models/series.py` 신규 모델
5. `app/schemas/series.py` Pydantic schemas (`SeriesCreate`, `SeriesOut`, `SeriesMembershipIn`)
6. `app/models/post.py` — `visibility` + `comments_enabled` 컬럼 추가
7. `app/schemas/post.py` — `PostOut`에 `visibility` + `comments_enabled` 필드 추가
8. `POST /v1/posts/{id}/comments` — `comments_enabled` 검사 (`COMMENTS_DISABLED` 403)
9. visibility 필터: `home_feed` / `explore_posts` / `search_posts` / `my_bookmarks` 각각 WHERE 절 추가
10. smoke test: `scripts/smoke_test_publish_controls.sh`

**PR1 회귀 체크**: 기존 피드/탐색/검색/북마크 응답 동일. `POST /v1/posts/{id}/comments` 기존 정상 케이스 통과.

### PR2 — Backend Series CRUD + Publish Endpoint (~2일)

1. `app/api/series.py` 신규 라우터 (`GET/POST /v1/series`, `PATCH/DELETE /v1/series/{id}`)
2. `POST /v1/posts/{id}/series` — membership 일괄 갱신
3. `POST /v1/posts/{id}/publish` 엔드포인트 — visibility + comments_enabled + series_ids + publish_at 통합. active auction visibility 변경 차단 (`AUCTION_ACTIVE_VISIBILITY_LOCKED` 409)
4. `app/main.py` 라우터 등록
5. 단위 테스트 + 통합 테스트

**PR2 회귀 체크**: PR1 변경사항 회귀 없음. Series CRUD 소유자 검증 테스트.

### PR3 — Frontend PublishOptionsPanel (~3일)

1. `src/components/post-editor/PublishOptionsPanel.tsx` 신규 컴포넌트
2. `lib/api.ts` 신규 함수: `getSeriesByAuthor()`, `createSeries()`, `publishPost()`
3. `posts/new/page.tsx` — `PublishOptionsPanel` 통합 (OQ-8=A: wizard step 또는 우측 sidebar)
4. `posts/[id]/edit` — 동일 컴포넌트 재사용
5. i18n: 5 locale `post.editor.publish.*` 신규 키 (~30키)

**PR3 회귀 체크**: 5 통합 지점 (autosave / DraftRestoreDialog / 멀티탭 / role-gating / useArtistGate) + 기존 발행 흐름 정상.

### PR4 — Frontend 시리즈 페이지 + 프로필 탭 (~2일)

1. `src/app/series/[id]/page.tsx` 신규 (시리즈 상세 — 포스트 갤러리)
2. 작가 프로필 시리즈 탭 (`/users/[id]?tab=series`)
3. 피드 카드 visibility 인디케이터 (`followers_only` = 잠금 아이콘, `unlisted` = 링크 아이콘)

### PR5 — i18n Cleanup + 회귀 검증 (~1일)

1. 5 locale 신규 키 누락 검사 + cleanup
2. 5 통합 지점 매뉴얼 검증 체크리스트
3. `editor-i18n-cleanup` carry-over 항목 처리 (기존 carry-over 이번 PR5에서 소화 시도)

---

## 9. Carry-over Awareness

본 PDCA 진입 시점에 기존 carry-over 2건이 존재한다:

| Carry-over | 출처 | 처리 방안 |
|-----------|------|-----------|
| `editor-i18n-cleanup` v0.2 | 이전 PDCA 누적 | PR5에서 이번 PDCA i18n 작업과 병행 소화 시도 |
| `upload-retry-ui` | 이전 PDCA 누적 | 본 PDCA scope 외. `#5 editor-rich-content` 또는 별도 minor fix |

본 PDCA 완료 후 Critical Path 상 다음 진입 후보:
- **우선**: `#10 artist-tier-release` (Critical Path 계속)
- **병행 가능**: `#12 notifications-ux-audit` (Phase 3 독립 진행)

---

## 10. Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 0.1 | 2026-05-03 | Initial draft. `#8 publish-controls` plan. B-3 요구사항 4건 + 3 알레믹 마이그레이션 + Series 모델 + publish endpoint + PublishOptionsPanel. OQ 10개 권장 default 포함. | itpe-ince (Claude Opus 4.7 + bkit product-manager agent) |
| 1.0 | 2026-05-03 | OQ 10/10 모두 권장 default 일괄 수락 (사용자 결정). status: draft → oq_resolved. §4 헤더에 결정 echo 표 추가, 상세 OQ 본문은 참고용 보존. /pdca design 진입 가능. | itpe-ince |
