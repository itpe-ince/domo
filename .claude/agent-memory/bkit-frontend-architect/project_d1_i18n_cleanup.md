---
name: editor-i18n-cleanup-v3 D-1 complete
description: Phase 5 D-1 tech debt cleared — 4 carry-over i18n issues resolved, tsc 0 errors
type: project
---

D-1 (editor-i18n-cleanup-v3) shipped as Phase 5 D 단계 first sub-PDCA.

**Why:** Phase 4 editor-revamp left 4 i18n carry-overs: Korean hardcodes in non-wizard components, dead key, mobile uploading inline, share.* namespace duplication.

**How to apply:** These issues are resolved. The `share.*` namespace is fully removed from all 5 locale files. The `auction.shareCard.*` namespace is now canonical for AuctionShareCard.tsx.

## Changes made

### New i18n keys (5 locales × 7 keys = 35 entries added)
Under `post.*`:
- `post.auctionBadge` — auction badge label in PostPreviewCard
- `post.locationPrompt` — prompt string for location entry
- `post.genreLabel` — "Genre: {{value}}" pattern
- `post.buyNowPriceLabel` — "Buy Now: ${{price}}" pattern

Under `auction.shareCard.*` (3 new keys added to existing namespace):
- `auction.shareCard.retry` — error state retry button
- `auction.shareCard.errorUnauthorized` — UNAUTHORIZED error message

### Keys removed (5 locales × 10 keys = 50 entries deleted)
`share.*` namespace entirely removed: title, generate, download, copyLink, copied, errorOwnerOnly, errorActiveOnly, errorRateLimit, errorGenerate, loading

### Dead key resolved
`post.editor.media.uploading` — previously dead (0 uses), now wired to EditorStepContent.tsx mobile path (#4 m-3)

## Files modified
- `v1/frontend/src/i18n/{ko,en,ja,zh,es}.json` — 5 locale files
- `v1/frontend/src/components/post-editor/EditorWorkspace.tsx` — 5 hardcodes removed
- `v1/frontend/src/components/post-editor/ProductFields.tsx` — 8 hardcodes removed, useI18n added
- `v1/frontend/src/components/post-editor/PostPreviewCard.tsx` — 3 hardcodes removed
- `v1/frontend/src/components/post-editor/wizard/EditorStepContent.tsx` — 2 hardcodes removed
- `v1/frontend/src/components/AuctionShareCard.tsx` — all share.* → auction.shareCard.*, 2 inline hardcodes wired

## Verification
- tsc --noEmit: 0 errors
- Zero `share.*` key calls remaining in codebase
- Zero Korean hardcodes in 5 target components
- `post.editor.media.uploading` now has 1 usage (no longer dead)
