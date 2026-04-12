# PDCA Completion Report — Domo Search (통합 검색)

**Feature**: domo-search
**Period**: 2026-04-12 (single session)
**Final Match Rate**: 🟢 **96.5%**
**Status**: ✅ Completed

---

## 1. Executive Summary

Domo 프로토타입에 **통합 검색 기능**을 추가한 작업. 사이드바 검색창 + 모바일 검색 탭 +
3탭 결과 페이지 (작가/작품/포스트) + 백엔드 검색 API (ILIKE 매칭, 트렌딩 스코어,
경매 마감임박 정렬) + 검색 로그 수집 + 최근 검색어 관리를 구현했다.

### 핵심 지표

| 지표 | 값 |
|---|---|
| 신규 파일 | 6개 (모델, 마이그레이션, 훅, 컴포넌트, 페이지, .env.local) |
| 수정 파일 | 8개 (API 2, 프론트 3, 설정 3) |
| Match Rate | 80.8% → **96.5%** (1회 iterate) |
| 해결 Gap | 13개 |
| 잔여 Gap | 3개 (낮은 영향도) |

---

## 2. Scope Delivered

### 2.1 Backend

| 파일 | 변경 | 역할 |
|---|---|---|
| `models/search_log.py` | 신규 | SearchLog 모델 + 인덱스 2개 (__table_args__) |
| `alembic/versions/0010_search_logs.py` | 신규 | 마이그레이션: search_logs 테이블 + 인덱스 4개 |
| `models/__init__.py` | 수정 | SearchLog import 추가 |
| `api/users.py` | 수정 | `GET /users/search` — display_name/bio ILIKE, 팔로워 desc, rate limit, user_id 로깅 |
| `api/posts.py` | 수정 | `GET /posts/search` — title/content/tags 매칭, cursor 페이지네이션, sort=ending_soon (Auction JOIN), rate limit, user_id 로깅 |
| `core/rate_limit.py` | 수정 | `search: 30 req/min by IP` 추가 |
| `core/config.py` | 수정 | DB/Redis 포트 localhost:5432/6379, frontend_url 3700 |

### 2.2 Frontend

| 파일 | 변경 | 역할 |
|---|---|---|
| `lib/api.ts` | 수정 | `searchUsers()`, `searchPosts()`, `UserSearchResult` 타입 |
| `lib/useRecentSearches.ts` | 신규 | localStorage 최근 10개 관리, `useSyncExternalStore` (캐시 스냅샷) |
| `components/SearchBar.tsx` | 신규 | 검색창 + 최근 검색 드롭다운, compact 모드, A11y (searchbox/listbox/arrow key) |
| `app/search/page.tsx` | 신규 | 3탭 결과 페이지 (작가/작품/포스트) + 필터/정렬 UI + 빈 상태 (동적 키워드 + 추천 작가) |
| `components/Sidebar.tsx` | 수정 | 로고 아래 SearchBar 삽입 (xl: 풀, md: compact) |
| `components/MobileTabBar.tsx` | 수정 | 탐색 → 검색 교체 (`/search`) |
| `frontend/.env.local` | 신규 | `NEXT_PUBLIC_API_URL=http://localhost:3710/v1` |

### 2.3 인프라/설정

| 파일 | 변경 |
|---|---|
| `.vscode/tasks.json` | 루트 워크스페이스에 생성, DB 포트 5432/6379, 백엔드 3710 |
| `scripts/dev-seed.sh` | 포트 55432 → 5432 |
| `scripts/dev-migrate.sh` | 포트 55432 → 5432 |
| `scripts/dev-backend.sh` | 포트 55432 → 5432, 3710 유지 |
| `styles/globals.css` | Playfair Display 폰트 import + `.font-logo` 클래스 |

---

## 3. Design Decisions

### D1. SQL ILIKE vs Full-Text Search

**선택**: PostgreSQL ILIKE 기반 부분 매칭
**이유**: 프로토타입 데이터 규모 (< 10K 포스트)에서 충분한 성능. pg_trgm GIN 인덱스는 Phase 5에서 전환 예정. Meilisearch/Elasticsearch는 운영 복잡도 대비 과도.

### D2. 검색창 위치 — 사이드바 vs 상단 헤더

**선택**: 데스크탑 사이드바 로고 아래, 모바일 하단 탭 교체
**이유**: X(Twitter) 현재 레이아웃과 동일. 모바일은 5탭 제약으로 탐색을 검색으로 교체 (탐색은 데스크탑 사이드바에서만 접근).

### D3. 3탭 구성 (작가/작품/포스트)

**선택**: 기본 탭 = 작가
**이유**: Domo 핵심 가치가 "신진 작가 발견"이라 검색의 1차 목적도 작가 찾기. 작품(product)과 포스트(general)는 백엔드의 `type` 필드에 1:1 매핑.

### D4. 검색 로그 수집

**선택**: `search_logs` 테이블에 query/tab/result_count/filters/user_id 저장
**이유**: 추천 알고리즘 데이터 선행 수집. GDPR 관점 session_id는 다음 사이클로 deferred.

### D5. useSyncExternalStore로 최근 검색어 관리

**선택**: React `useSyncExternalStore` + 모듈 레벨 캐시
**이유**: localStorage를 React 상태와 동기화하면서 SSR 호환. 초기 구현에서 `getServerSnapshot`이 매번 새 배열을 반환해 무한 루프 발생 → 모듈 상수 `EMPTY` + `cachedSnapshot`으로 해결.

---

## 4. Match Rate 추이

```
v1 (초기 분석)     ████████████████░░░░ 80.8%
v2 (iterate 1회)   ███████████████████░ 96.5%  ← 현재
                   └────────────────────┘
                    0%                 100%
```

### Iterate에서 해결한 Gap 13개

| ID | 항목 | 구현 |
|---|---|---|
| M1 | SearchLog 인덱스 | `__table_args__` 2개 |
| M2 | posts/users lower 인덱스 | Alembic 마이그레이션 |
| M3 | Alembic 마이그레이션 | `0010_search_logs.py` |
| M4 | cursor 페이지네이션 | `limit+1` 패턴, `next_cursor` |
| M5 | 부분 태그 매칭 | `Post.tags.any(func.concat("%", q, "%"))` |
| M6 | Rate Limit | `rate_limit("search")` 30 req/min |
| M7 | SearchLog user_id | `_optional_user_id`/`_optional_viewer_id` |
| M8 | 작가 탭 role 필터 | "전체/작가만" 칩 UI |
| M9 | 작품 탭 장르 필터 | 6개 장르 칩 |
| M10 | 정렬 UI | 작품: 최신/인기/마감임박, 포스트: 최신/인기 |
| C1 | SearchLog 비동기 | try/except + warning 로깅 |
| C2 | 팔로우 버튼 | 작가 결과 각 행에 [팔로우] 버튼 |
| C3 | 동적 키워드 추천 | fetchExplore 기반 인기 태그 추출 |

### 잔여 Gap (3개, 낮음)

| ID | 항목 | 비고 |
|---|---|---|
| R1 | 팔로우 버튼 API 연동 | 별도 기능 (API 자체는 이미 존재) |
| R2 | SearchLog session_id | 쿠키 인프라 필요, 다음 사이클 |
| R3 | design.md §5 갱신 | 메인 설계 문서 검색 API 추가 |

---

## 5. Bugs Fixed During Implementation

| 버그 | 원인 | 수정 |
|---|---|---|
| `useSyncExternalStore` 무한 루프 | `getServerSnapshot`/`getSnapshot`이 매번 새 배열 반환 | 모듈 레벨 `EMPTY` 상수 + `cachedSnapshot` 캐시 |
| FastAPI `rate_limit` TypeError | `Depends(rate_limit(...))` 이중 래핑 | `_rl=rate_limit(...)` 기존 패턴 사용 |
| `google-auth` ModuleNotFoundError | tasks.json pip install 목록 누락 | `google-auth`, `requests`, `aioboto3` 추가 |
| DB 접속 실패 (55432) | Docker 전용 포트 하드코딩 | 모든 스크립트/설정을 `localhost:5432` 통일 |
| 프론트엔드 API 미호출 | `NEXT_PUBLIC_API_URL` 환경변수 빌드타임 미주입 | `.env.local` 파일 생성 |

---

## 6. Lessons Learned

### L1. `NEXT_PUBLIC_` 환경변수는 빌드타임에 주입된다

VSCode 태스크의 `options.env`로 넘겨도 이미 빌드된 코드에는 반영 안 됨. `.env.local` 파일이 확실한 방법.

### L2. useSyncExternalStore의 스냅샷은 반드시 참조 안정성 필요

매 호출마다 `JSON.parse`하면 새 배열 → React가 "변경됨"으로 판단 → 무한 리렌더. 모듈 레벨 변수에 캐시하는 패턴이 필수.

### L3. 기존 코드의 패턴을 따르는 게 가장 안전하다

`rate_limit()` 사용법을 기존 코드(moderation.py)에서 확인하지 않고 `Depends()`로 감쌌다가 TypeError 발생. 기존 패턴을 먼저 grep하는 습관이 중요.

### L4. DB 포트 하드코딩은 모든 스크립트에서 동시 변경 필요

seed, migrate, backend, tasks.json 4곳에 분산된 포트를 한 곳만 바꾸면 다른 곳에서 실패. 환경변수 기본값을 config.py 한 곳에서 관리하는 게 이상적.

---

## 7. Artifacts Index

| 문서 | 경로 |
|---|---|
| Plan | `docs/01-plan/features/domo-search.plan.md` |
| Design | `docs/02-design/features/domo-search.design.md` |
| Analysis (v2) | `docs/03-analysis/domo-search.analysis.md` |
| Report (this) | `docs/04-report/domo-search.report.md` |

---

## 8. Sign-off

**Completion Criteria**:
- [x] Match Rate ≥ 90% (96.5%)
- [x] 핵심 Gap 모두 해결 (13/13)
- [x] 시드 데이터 투입 + 피드 로딩 확인
- [x] 백엔드 API 200 응답 확인

**Report Generated**: 2026-04-12
**Next Phase**: `/pdca archive domo-search --summary` 또는 후속 기능 착수
