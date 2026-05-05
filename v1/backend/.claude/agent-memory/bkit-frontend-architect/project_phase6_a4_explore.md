---
name: Phase 6 A-4 Explore Revamp status
description: A-4 완료: 5탭 explore revamp + hero card + ranking preview + URL sync + 5 locale i18n 43 keys
type: project
---

A-4 Explore Revamp 완료 (2026-05-04).

**신규/수정 파일:**
- `app/explore/page.tsx` — 전면 재작성 (Suspense + ExploreContent 분리)
- `components/explore/ExploreTabs.tsx` — 5탭 pill nav (role=tablist, aria-selected)
- `components/explore/ExploreFilters.tsx` — region/genre/pricing context dropdowns
- `components/explore/ExploreHeroCard.tsx` — 오늘의 작가 daily rotation (date-seeded)
- `components/explore/ArtistIndexPreview.tsx` — top-5 horizontal scroll strip
- `components/explore/PostsGrid.tsx` — 재사용 가능 grid (skeleton/empty/error)
- `lib/hooks/useExploreState.ts` — tab+filter state + URL query param sync + localStorage
- `lib/api.ts` — `fetchExplorePosts()` 신규 (tab-aware, falls back to /posts/explore)
- `lib/analytics/events.ts` — ExploreHeroViewEvent, ArtistIndexPreviewClickEvent 추가; A-7/A-8 event types도 통합
- `i18n/{ko,en,ja,zh,es}.json` — explore.* namespace ~43 keys × 5 locales

**Why:** A-4 roadmap — 단순 list → 큐레이션 + ranking preview (그로스해킹 깔때기)

**How to apply:** 탭 상태는 useExploreState에서 관리. A-6 useArtistIndex(limit=5) 재사용.
PostHog flag 'feed-algorithm-v2' 활성 시 trending tab → algo=v1 통합은 문서화된 TODO로 남음.

**부가 수정 (pre-existing tsc 수정):**
- `lib/hooks/useSearchHistory.ts` — `@/lib/auth` → `@/lib/useMe` 교체 (A-5 artifact)
- `events.ts` — StoryViewEvent, ExpiryBannerViewEvent 등 A-7/A-8 누락 types 추가

**tsc:** 0 errors
**i18n:** 5 locale × 43 keys valid
