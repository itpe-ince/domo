---
name: publish-controls #8 Step 4 completion
description: Tasks 4.1–4.8 done; series public pages + dnd-kit reorder + cover_url upload; 14 new keys×5 locales; reorder save is local-only (carry-over)
type: project
---

Step 4 of publish-controls PDCA #8 complete (2026-05-04).

Tasks completed:
- 4.1: `src/components/SeriesCard.tsx` (NEW, 48 lines) — cover + first-post thumbnail fallback (OQ-4=C)
- 4.2: `src/app/series/[id]/page.tsx` (NEW, 346 lines) — dnd-kit reorder, owner edit mode, delete
- 4.3: `src/app/users/[id]/series/page.tsx` (NEW, 97 lines) — author series gallery (OQ-D-4=A separate route)
- 4.4: `src/app/users/[id]/page.tsx` (MODIFIED) — added series "View series" link + `useI18n` import
- 4.5: `src/components/post-editor/SeriesCreateModal.tsx` (MODIFIED, 260 lines) — cover_url upload via `uploadMediaFile` (no new endpoint)
- 4.6: `src/components/icons.tsx` (MODIFIED) — `LockClosedIcon` added (Step 5 preview; `LinkIcon` already existed)
- 4.7: i18n — 14 new keys × 5 locales = 70 entries (10 top-level + 4 new modal keys per locale)
- 4.8: tsc --noEmit → zero errors; all 5 JSON files valid

**Reorder save carry-over**: local-only drag reorder UI works. Persist requires a backend series reorder endpoint (not yet available). Save button exits edit mode without API call. Step 5 or future PDCA to add backend endpoint.

**Why:** `setPostSeriesIds` replaces the entire series list for a post, so per-post iteration would drop other series memberships.

**How to apply:** If user requests reorder persistence in Step 5, need backend `POST /v1/series/{id}/reorder` endpoint first.

Step 5 hand-off:
- VisibilityBadge + comments_disabled UI + 5 integration point regression + final tsc clean
- Keys to add: `post.feed.indicator.*` (3 keys ×5 locales = 15 entries)
