# Design — Domo Search (통합 검색)

**Feature**: domo-search
**Created**: 2026-04-12
**Phase**: Design
**Plan Reference**: [domo-search.plan.md](../../01-plan/features/domo-search.plan.md)

---

## 1. Data Model

### 1.1 검색 로그 테이블 (신규)

```sql
CREATE TABLE search_logs (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID REFERENCES users(id) ON DELETE SET NULL,  -- NULL = 비로그인
    session_id  VARCHAR(64),       -- 비로그인 세션 식별 (쿠키 기반)
    query       VARCHAR(200) NOT NULL,
    tab         VARCHAR(20) NOT NULL,  -- 'artists' | 'artworks' | 'posts'
    result_count INTEGER NOT NULL DEFAULT 0,
    filters     JSONB,             -- {"genre":"painting","sort":"popular"} 등
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_search_logs_user ON search_logs(user_id, created_at DESC);
CREATE INDEX idx_search_logs_query ON search_logs(query, created_at DESC);
```

### 1.2 기존 모델 변경: 없음

검색 대상 컬럼은 이미 존재:
- `users.display_name` (VARCHAR 100)
- `users.bio` (TEXT, nullable)
- `posts.title` (VARCHAR 200, nullable)
- `posts.content` (TEXT, nullable)
- `posts.tags` (ARRAY(TEXT), nullable) — PostgreSQL native array
- `posts.genre` (VARCHAR 50)

### 1.3 인덱스 추가 (프로토타입 → 이후 pg_trgm 전환 대비)

```sql
-- Phase 5에서 pg_trgm GIN 인덱스로 교체할 후보
CREATE INDEX idx_posts_title_lower ON posts(lower(title));
CREATE INDEX idx_users_display_name_lower ON users(lower(display_name));
```

---

## 2. API 설계

### 2.1 POST 검색

```
GET /posts/search
```

**Parameters**:
| Param | Type | Required | Default | Description |
|---|---|---|---|---|
| `q` | string | ✅ | - | 검색어 (2자 이상, max 100) |
| `type` | string | - | (all) | `general` \| `product` |
| `genre` | string | - | (all) | `painting` \| `drawing` \| `photography` \| ... |
| `sort` | string | - | `latest` | `latest` \| `popular` \| `ending_soon` |
| `limit` | int | - | 20 | max 50 |
| `cursor` | string | - | - | 페이지네이션 커서 (post_id) |

**Response**: `200 OK`
```json
{
  "data": [PostView, ...],
  "pagination": {
    "next_cursor": "uuid-or-null",
    "has_more": true
  }
}
```

**SQL 매칭**:
```sql
SELECT * FROM posts
WHERE status = 'published'
  AND (
    title ILIKE '%' || :q || '%'
    OR content ILIKE '%' || :q || '%'
    OR :q = ANY(tags)             -- 정확 태그 매칭
    OR EXISTS (                   -- 부분 태그 매칭
      SELECT 1 FROM unnest(tags) AS tag
      WHERE tag ILIKE '%' || :q || '%'
    )
  )
ORDER BY
  CASE WHEN :sort = 'popular' THEN trending_score END DESC,
  CASE WHEN :sort = 'latest' THEN created_at END DESC,
  CASE WHEN :sort = 'ending_soon' THEN auction_end_at END ASC NULLS LAST
LIMIT :limit
```

**`sort=ending_soon` 처리**:
- `type`을 자동으로 `product`로 강제
- `posts` JOIN `product_posts` JOIN `auctions` (status='active')
- `auctions.end_at ASC` 정렬 — 마감 임박 순
- 경매 없는 포스트 제외

**Rate Limit**: 30 req/min (기존 Redis 인프라)

**Error**:
- `422`: `q` 길이 < 2 또는 `sort` 값 유효하지 않음

### 2.2 유저 검색

```
GET /users/search
```

**Parameters**:
| Param | Type | Required | Default | Description |
|---|---|---|---|---|
| `q` | string | ✅ | - | 검색어 (2자 이상) |
| `role` | string | - | (all) | `user` \| `artist` |
| `limit` | int | - | 20 | max 50 |

**Response**: `200 OK`
```json
{
  "data": [
    {
      "id": "uuid",
      "display_name": "maria_rio",
      "avatar_url": "...",
      "bio": "Oil painter from Lima",
      "role": "artist",
      "follower_count": 234
    }
  ],
  "pagination": { "next_cursor": null, "has_more": false }
}
```

**SQL 매칭**:
```sql
SELECT u.*, COUNT(f.follower_id) AS follower_count
FROM users u
LEFT JOIN follows f ON f.followee_id = u.id
WHERE u.status = 'active'
  AND (u.deleted_at IS NULL)
  AND (
    u.display_name ILIKE '%' || :q || '%'
    OR u.bio ILIKE '%' || :q || '%'
  )
GROUP BY u.id
ORDER BY follower_count DESC, u.created_at DESC
LIMIT :limit
```

### 2.3 검색 로그 저장 (내부, 클라이언트 노출 없음)

검색 API 응답 시 `search_logs` INSERT를 비동기로 실행 (응답 지연 방지):

```python
async def _log_search(
    db, user_id, session_id, query, tab, result_count, filters
):
    db.add(SearchLog(
        user_id=user_id,
        session_id=session_id,
        query=query,
        tab=tab,
        result_count=result_count,
        filters=filters,
    ))
    await db.commit()
```

---

## 3. 프론트엔드 컴포넌트 설계

### 3.1 컴포넌트 계층

```
components/
  SearchBar.tsx           # 재사용 검색창 + 최근 검색 드롭다운
app/search/
  page.tsx                # 결과 페이지 (3탭: 작가/작품/포스트)
lib/
  api.ts                  # searchUsers(), searchPosts() 추가
  useRecentSearches.ts    # localStorage 최근 검색어 10개 관리
```

### 3.2 SearchBar 컴포넌트

```tsx
interface SearchBarProps {
  className?: string;
  compact?: boolean;  // true = 사이드바 축소 모드 (돋보기만)
}
```

**동작**:
1. 포커스 시 최근 검색어 드롭다운 표시 (max 10개)
2. 텍스트 입력 + Enter → `/search?q={value}` 라우팅
3. 최근 검색어 클릭 → 동일하게 라우팅
4. Escape → 드롭다운 닫기 + blur
5. X 버튼 → 입력 클리어
6. 최근 검색어 개별 삭제 (X)

**접근성**:
- `role="searchbox"`, `aria-label="검색"`, `aria-expanded`
- 최근 검색 리스트: `role="listbox"`, `role="option"`
- Arrow key 내비게이션

**반응형**:
- `xl`: 풀 사이즈 (사이드바 로고 아래, 패딩 포함 w-full)
- `md`: `compact=true` → 돋보기 아이콘 버튼, 클릭 시 확장
- `sm` (모바일): 사용 안 함 (MobileTabBar 돋보기 탭이 `/search`로 이동)

### 3.3 SearchPage (/search)

**URL**: `/search?q={keyword}&tab={artists|artworks|posts}`

**구조**:
```
┌──────────────────────────────────────────────────┐
│ [🔍 검색창 (prefilled with q)]          [지우기] │
├──────────────────────────────────────────────────┤
│  작가        작품        포스트                    │ ← 3탭, 활성 탭 언더라인
│  ─────       ─────       ─────                    │
├──────────────────────────────────────────────────┤
│ 결과 목록                                         │
│ ...                                              │
└──────────────────────────────────────────────────┘
```

**탭별 렌더링**:

| 탭 | API | 렌더 카드 | 추가 필터 |
|---|---|---|---|
| 작가 | `searchUsers(q, role?)` | UserCard (아바타+이름+bio+팔로워+팔로우 버튼) | role 필터 (전체/작가만) |
| 작품 | `searchPosts(q, type:"product", genre?, sort?)` | PostCard (이미지+가격+경매 상태) | 장르 칩 + 정렬(최신/인기/마감임박) |
| 포스트 | `searchPosts(q, type:"general", sort?)` | PostCard (이미지+좋아요/댓글) | 정렬(최신/인기) |

**빈 상태 (결과 0건)**:
```
"{q}"에 대한 검색 결과가 없습니다.
────
비슷한 키워드: [painting] [portrait] [oil]     ← 인기 태그 3개 (fetchExplore 기반)
추천 작가:
  @maria_rio · Oil painter from Lima · [팔로우]
  @alex_bkk · Digital art · [팔로우]
  @sofia_sp · Sculpture · [팔로우]
[탐색으로 이동]
```

추천 작가는 기존 `fetchExplore({type:"product", limit:8})`에서 추출 (RightRail과 동일 로직 재사용).

### 3.4 API 클라이언트

```typescript
// lib/api.ts 추가

export interface UserSearchResult {
  id: string;
  display_name: string;
  avatar_url: string | null;
  bio: string | null;
  role: string;
  follower_count: number;
}

export async function searchUsers(
  q: string,
  opts?: { role?: string; limit?: number }
): Promise<UserSearchResult[]> {
  const qs = new URLSearchParams({ q });
  if (opts?.role) qs.set("role", opts.role);
  qs.set("limit", String(opts?.limit ?? 20));
  return apiFetch<UserSearchResult[]>(`/users/search?${qs}`, { auth: false });
}

export async function searchPosts(
  q: string,
  opts?: {
    type?: string;
    genre?: string;
    sort?: "latest" | "popular" | "ending_soon";
    limit?: number;
  }
): Promise<PostView[]> {
  const qs = new URLSearchParams({ q });
  if (opts?.type) qs.set("type", opts.type);
  if (opts?.genre) qs.set("genre", opts.genre);
  if (opts?.sort) qs.set("sort", opts.sort);
  qs.set("limit", String(opts?.limit ?? 20));
  return apiFetch<PostView[]>(`/posts/search?${qs}`, { auth: false });
}
```

### 3.5 최근 검색어 관리

```typescript
// lib/useRecentSearches.ts

const STORAGE_KEY = "domo-recent-searches";
const MAX_ITEMS = 10;

export function useRecentSearches() {
  // get(): string[]
  // add(q: string): void       — 중복 제거, 최신 앞에
  // remove(q: string): void
  // clear(): void
}
```

localStorage 스키마: `string[]` (JSON array of strings)

---

## 4. 와이어프레임

### 4.1 데스크탑 — 사이드바 검색창

```
┌──────────┬──────────────────────────────────┬──────────────────┐
│ [D Domo] │                                  │                  │
│          │                                  │                  │
│ [🔍     ]│  검색 결과 페이지                  │ 트렌딩 작품       │
│          │                                  │                  │
│ ▢ 홈     │  작가    작품    포스트            │                  │
│ ▢ 팔로잉 │  ─────                            │                  │
│ ▢ 탐색   │                                  │                  │
│ ▢ 알림   │  @maria_rio                      │                  │
│ ▢ 프로필 │  Oil painter from Lima            │                  │
│          │  팔로워 234 · [팔로우]             │                  │
│ ─────    │                                  │                  │
│          │  @alex_bkk                       │                  │
│ [+ 작성] │  Digital art                     │                  │
│          │  팔로워 156 · [팔로우]             │                  │
│          │                                  │                  │
└──────────┴──────────────────────────────────┴──────────────────┘
```

사이드바 `md` (축소):
```
│ [D] │
│ [🔍]│  ← 돋보기 아이콘 버튼, 클릭 → /search 이동
│ [🏠]│
│ ...│
```

### 4.2 모바일 — 검색 탭

```
┌─────────────────────────────┐
│ [🔍 검색어를 입력하세요    ]│ ← 포커스 시 최근 검색 드롭다운
│                             │
│ ┌─────────────────────────┐ │
│ │ 최근 검색                │ │
│ │ sunset         [X]      │ │
│ │ maria          [X]      │ │
│ │ oil painting   [X]      │ │
│ └─────────────────────────┘ │
│                             │
│ (Enter 후 결과 로드)        │
│                             │
│  작가    작품    포스트      │
│  ─────                      │
│                             │
│  @maria_rio                 │
│  Oil painter · 234 팔로워   │
│  [팔로우]                   │
│                             │
├─────────────────────────────┤
│ 🏠   👥   🔍   🔔   👤     │
└─────────────────────────────┘
```

### 4.3 빈 상태

```
┌─────────────────────────────┐
│                             │
│        🔍                   │
│                             │
│  "sunset"에 대한             │
│  검색 결과가 없습니다.       │
│                             │
│  비슷한 키워드:              │
│  [painting] [portrait] [oil]│
│                             │
│  추천 작가:                  │
│  ┌───────────────────────┐  │
│  │ @maria_rio · [팔로우] │  │
│  │ @alex_bkk  · [팔로우] │  │
│  │ @sofia_sp  · [팔로우] │  │
│  └───────────────────────┘  │
│                             │
│  [탐색으로 이동]             │
│                             │
└─────────────────────────────┘
```

---

## 5. 사이드바 / 탭바 변경

### 5.1 Sidebar 변경

```
[D Domo]             ← 기존 로고
[🔍 검색             ]  ← 신규: SearchBar (xl: 풀, md: 돋보기 아이콘)
────
▢ 홈
▢ 팔로잉 (needsAuth)
▢ 탐색
▢ 알림 (needsAuth, badge)
▢ 프로필 (needsAuth)
────
▢ 정기 후원 ...       ← secondary (기존 그대로)
```

검색창은 로고 바로 아래, primary nav 위에 배치.

### 5.2 MobileTabBar 변경

현재 탐색(ExploreIcon/돋보기)과 검색이 아이콘이 비슷하므로 정리:

**로그인 시**: 홈 · 팔로잉 · **검색** · 알림 · 프로필
**비로그인 시**: 홈 · **검색** · 프로필(로그인)

- "탐색"을 "검색"으로 교체 (같은 돋보기 아이콘)
- `/search` 진입 시 상단에 검색창 + 하단에 최근 검색 / 결과
- 탐색(`/explore`)은 사이드바에서만 접근 (모바일은 검색으로 통합)
- 또는 탐색 유지 + 검색 추가 → 아이콘 6개 → 너무 많음

**결정**: 모바일은 탐색을 검색으로 교체. 탐색 기능은 검색 페이지의 "브라우징 모드"(검색어 없이 장르 칩만 선택)로 통합 가능. 데스크탑 사이드바에서는 탐색 메뉴 유지.

---

## 6. 구현 순서

| Step | 작업 | 파일 | 의존성 |
|---|---|---|---|
| 1 | SearchLog 모델 + Alembic 마이그레이션 | `models/search_log.py`, `alembic/versions/...` | 없음 |
| 2 | `/users/search` 백엔드 | `api/users.py` 확장 | Step 1 |
| 3 | `/posts/search` 백엔드 (ending_soon 포함) | `api/posts.py` 확장 | Step 1 |
| 4 | `searchUsers()`, `searchPosts()` API 클라이언트 | `lib/api.ts` | Step 2, 3 |
| 5 | `useRecentSearches` 훅 | `lib/useRecentSearches.ts` | 없음 |
| 6 | SearchBar 컴포넌트 | `components/SearchBar.tsx` | Step 5 |
| 7 | SearchPage (3탭 + 빈 상태) | `app/search/page.tsx` | Step 4, 6 |
| 8 | Sidebar에 SearchBar 삽입 | `components/Sidebar.tsx` | Step 6 |
| 9 | MobileTabBar 탐색→검색 교체 | `components/MobileTabBar.tsx` | Step 7 |
| 10 | design.md §4.1/§4.2/§5 갱신 | `docs/02-design/design.md` | Step 9 |

**병렬화 가능**:
- Step 1~3 (백엔드) ∥ Step 5 (프론트 훅)
- Step 6~7 → Step 8~9 순차

---

## 7. 테스트 관점

### 7.1 백엔드

- `q` 2자 미만 → 422 반환
- `q` 100자 초과 → 422 반환
- 빈 결과 → `{ data: [], pagination: { has_more: false } }`
- `type=product`, `genre=painting` 필터 결합
- `sort=ending_soon` → 경매 포스트만, 마감 가까운 순
- `sort=popular` → 트렌딩 스코어 desc
- 삭제된 유저/포스트 제외 (`status != 'deleted'`)
- Rate limit (31번째 요청 → 429)
- SearchLog INSERT 확인

### 7.2 프론트엔드

- 검색창 Enter → `/search?q=...` 라우팅
- 최근 검색어 10개 → 11번째 추가 시 가장 오래된 것 제거
- 최근 검색어 삭제 → localStorage 반영
- 3탭 전환 시 URL `tab` 파라미터 변경 + 재검색
- 빈 상태에서 추천 작가 표시
- 키보드: Arrow key로 최근 검색 이동, Escape 닫기
- 반응형: xl(풀 검색창) / md(돋보기 아이콘) / sm(탭바 검색 탭)

---

## 8. 다음 단계

✅ `/pdca do domo-search`로 구현 착수 → Step 1부터 순차 진행
