---
name: editor-image-studio Step 9+10 quality gate
description: Key findings and fixes from the i18n audit + viewport/a11y/regression step of PDCA #6-image
type: project
---

Steps 9 and 10 of editor-image-studio PDCA #6-image completed on 2026-05-03.

**Why:** Quality gate before /pdca analyze Match Rate scoring. No new features; only polish and regression verification.

**How to apply:** This record exists for context when analyzing match rate or continuing related PDCAs.

Key findings:
- 4 orphan placeholder keys (tool.rotate/crop/mosaic/watermark.placeholder) removed from all 5 locales atomically (51→47 keys per locale)
- zh.json signature section had Simplified Chinese contamination in an otherwise Traditional Chinese file — corrected to Traditional
- ja.json ratio_original was "元に戻す" (undo) instead of "元のサイズ" (original size) — corrected
- ImageEditor missing focus trap (Tab key escaped modal) — added useCallback handleFocusTrap on the outer dialog div + auto-focus close button on mount
- Tool tab nav lacked overflow-x-auto — added; floating control bar lacked mobile width cap — added max-w-[calc(100vw-2rem)]
- WatermarkToolControls could overflow 375px — capped at w-64 max-h-[38vh] overflow-y-auto
- CropTool preset buttons could overflow on small screens — added flex-wrap + max-w cap
- SignatureUploadModal missing aria-label on file input + close button focus on open — fixed
- tsc: clean (0 errors) throughout
- 5 integration regression: all pass (useDraftAutosave naturally picks up crop_meta via formState.media; DraftRestoreDialog passes restored state through resetFromDraft; storage event listener at page.tsx:229; role-gate at api/posts.py:207; useArtistGate has zero coupling to ImageEditor)
