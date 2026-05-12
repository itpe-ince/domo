---
name: publish-controls PDCA #8 Step 3 completion
description: Step 3 (largest frontend step) shipped — all tasks 3.1–3.9 complete; hybrid path C chosen for handleSubmit
type: project
---

All 9 tasks done. Zero tsc errors.

**Path chosen for handleSubmit (Task 3.8):** Hybrid path C — existing drafts go directly to `publishPost(draftId, ...)`. New posts call `saveToServer()` first to get a draft ID, then `publishPost`. Legacy `createPost` fallback if `saveToServer` fails.

**Key deviations:**
- cover_url upload in SeriesCreateModal deferred (NULL on creation). Step 4 carry-over.
- DraftPayload extended with `visibility / comments_enabled / series_ids` (backend draft endpoint may ignore extra fields — verify).
- 37 new i18n keys × 5 locales = 185 entries (slightly above 140 target — all were needed).
- `publish-options` wizard step added between `product_meta` and `publish` in both GENERAL_STEPS and PRODUCT_STEPS.

**Step 4 hand-off:**
- `/series/[id]` page + `/users/[id]/series` page
- SeriesCard component
- dnd-kit reorder within a series
- cover_url upload in SeriesCreateModal
- `DraftPayload` backend support for `visibility/comments_enabled/series_ids` fields (may need backend verification)

**Why:** Publish controls (#8) is pre-req for artist tier system (#10). Step 3 ships the full editor integration.

**How to apply:** When resuming Step 4, start with `/series/[id]` page using `getSeriesWithPosts` from api.ts (already defined).
