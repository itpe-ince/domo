---
name: dynamic-og-card G'-6 complete
description: Phase 7 G'-6 dynamic OG card implementation — 4 opengraph-image.tsx routes + lib/og/utils.ts + 3 metadata layouts; tsc 0 errors
type: project
---

Phase 7 G'-6 (dynamic-og-card) shipped. All frontend-only, no backend changes.

**Files created (8 new files, 1743 LOC total)**:
- `/v1/frontend/src/lib/og/utils.ts` (172 LOC) — OG_BRAND tokens, OG_SIZE/contentType, tierLabel/tierColors, countryFlag, scorePercent, ogFetch helpers (fetchOgUserProfile/fetchOgArtistRanking/fetchOgPost/fetchOgSponsorship)
- `/v1/frontend/src/app/users/[id]/opengraph-image.tsx` (378 LOC) — Artist profile OG: avatar + name + country flag (left) / tier badge + rank + score bar + followers (right)
- `/v1/frontend/src/app/users/[id]/timeline/opengraph-image.tsx` (397 LOC) — Timeline OG (A-7 carry-over): artist header + 3-milestone timeline preview + Domo branding
- `/v1/frontend/src/app/posts/[id]/opengraph-image.tsx` (236 LOC) — Post detail OG: media thumbnail (left 55%) / title + author + tags + branding (right 45%)
- `/v1/frontend/src/app/me/sponsorships/[id]/opengraph-image.tsx` (311 LOC) — Sponsor success OG: anonymous-safe, bluebird count + amount + artist avatar
- `/v1/frontend/src/app/users/[id]/layout.tsx` (78 LOC) — Server metadata wrapper for artist profile
- `/v1/frontend/src/app/users/[id]/timeline/layout.tsx` (93 LOC) — Server metadata wrapper for timeline
- `/v1/frontend/src/app/posts/[id]/layout.tsx` (78 LOC) — Server metadata wrapper for post detail

**Key decisions**:
- Edge runtime on all 4 OG routes (fast cold start)
- layout.tsx pattern for metadata (non-invasive — existing "use client" pages untouched)
- next/og ImageResponse with inline JSX styles (no external CSS)
- 5-minute revalidate cache (next: { revalidate: 300 }) on all API fetches
- Sponsor OG: privacy-safe fallback when sponsorship not found; is_anonymous flag hides supporter identity

**C-2/C-4 dependencies satisfied**: OG infrastructure for external sharing is live; C-3 multi-language-story can build on this.

Why: Next.js 15 requires metadata in Server Components; existing page.tsx files are all "use client". Layout wrappers are the minimal non-destructive approach.

**tsc**: 0 errors. Backend tests: 227 passed (baseline 207+).
