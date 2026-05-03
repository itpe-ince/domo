---
name: publish-controls Step 5 complete
description: PR5 (FINAL frontend step) for publish-controls sub-PDCA #8 — VisibilityBadge, PostCard integration, comments_disabled UI, i18n 5×3, regression verified, tsc clean, a11y fixes
type: project
---

All 5 Frontend PRs for publish-controls (#8) are now complete.

Step 5 shipped: VisibilityBadge component (`src/components/VisibilityBadge.tsx`), PostCard integration, comments_disabled message in `posts/[id]/page.tsx`, 3 i18n keys × 5 locales (47 keys each, all matching), radiogroup a11y fix in PublishOptionsPanel, motion-reduce fix in SortablePostCard, datetime-local w-full fix for 375px.

**Why:** Final polish + verification step before `/pdca analyze` on publish-controls.

**How to apply:** Sub-PDCA #8 is complete. Next action is `/pdca analyze` to assess against design v1.1. Known carry-overs: Series reorder save backend endpoint deferred (local-only reorder in Step 4); cover_url upload UI deferred.
