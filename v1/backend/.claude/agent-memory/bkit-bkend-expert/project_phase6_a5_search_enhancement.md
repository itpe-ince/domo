---
name: Phase 6 A-5 Search Enhancement
description: A-5 완료: alembic 0048 search_history, SearchHistory 모델, /search v2 + /search/popular + /me/search/history, 8 unit tests, search.v2.* i18n 100키, PostHog 3 신규 events
type: project
---

A-5 search-enhancement 구현 완료 (2026-05-04).

## Backend 구현

- `alembic/versions/0048_search_history.py` — search_history 테이블, 2개 인덱스 (user_active, searched_at)
- `app/models/search_history.py` — SearchHistory 모델 (id, user_id, query, result_count, searched_at, deleted_at)
- `app/models/__init__.py` — SearchHistory 등록
- `app/schemas/search.py` — sanitize_query(), SearchHistoryOut, PopularSearchItem, PopularSearchesOut, SearchHistoryListOut
- `app/api/search.py` — search_router (/search, /search/popular) + me_search_router (/me/search/history CRUD)
- `app/core/rate_limit.py` — search 60/min, search_popular 60/min, search_history_read/write/delete scopes
- `app/main.py` — search_router, me_search_router 등록

## Algorithm
ILIKE + ranking score (Title×3 + Tag×2 + Content×1 + Bio×1). pg_trgm Phase 7 carry-over.

## Search API 명세
- GET /search?q=&type=artists|artworks|posts|all&sort=relevance|latest|popular&price_min=&price_max=&region=&active=&cursor=&limit=
- GET /search/popular?limit=10
- GET /me/search/history?limit=10
- DELETE /me/search/history/{id}
- DELETE /me/search/history

## Tests
- `tests/unit/test_search_v2.py` — 8 unit tests (sanitize_query, _like, _resolve_viewer, schema serialization)

## Frontend 구현

- `lib/api.ts` — searchV2(), fetchSearchHistory(), deleteSearchHistoryEntry(), clearSearchHistory(), fetchPopularSearches(), 타입 정의
- `lib/analytics/events.ts` — SearchFilterAppliedEvent, SearchHistoryClickEvent, SearchPopularClickEvent (union에 추가)
- `lib/hooks/useSearchHistory.ts` — 서버 검색 이력 + 인기 검색어 훅
- `app/search/page.tsx` — History dropdown, price/region/active 필터, PostHog 3 events, i18n search.v2.*

## i18n
search.v2.* namespace: 19키 × 5 locale = 95 entries.

## Carry-over to Phase 7+
- pg_trgm fuzzy match (DB extension dependency)
- Semantic vector search (ML)
- Saved searches
- Search analytics dashboard

**Why:** 알림: alembic 0048을 A-8에서도 사용했는지 확인 필요 — A-8이 이미 0048을 사용했을 경우 conflict 가능성.
**How to apply:** 다음 구현 시 alembic revision 순번 확인 필수.
