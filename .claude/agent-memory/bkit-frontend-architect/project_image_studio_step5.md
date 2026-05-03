---
name: editor-image-studio Step 5 complete
description: Step 5 (deps/types/API client/EditButton entry point) shipped for PDCA #6-image
type: project
---

Step 5 of editor-image-studio PDCA (#6-image) is complete. All 6 tasks implemented and verified.

**Why:** Lightest frontend step — installs konva deps, adds TypeScript types mirroring backend Pydantic schema, adds API client functions, adds inert EditButton entry point.

**How to apply:** Step 6 (ImageEditor modal skeleton + Konva Stage) picks up from here. `onEditMedia` prop on `SortableMediaCard` is optional; Step 6 wires it up via `MediaPreviewList` → `EditorWorkspace`/`EditorStepContent`.

Key decisions made:
- Fixed `apiFetch` for FormData (skip `Content-Type: application/json` when body is FormData) and 204 No Content (short-circuit before `res.json()`).
- `isGif()` helper co-located in SortableMediaCard.tsx, not exported.
- Project has no ESLint config — TypeScript (`npx tsc --noEmit`) is the sole static analysis gate.
