---
name: editor-image-studio Step 8 complete
description: Step 8 (Save wiring via patchMediaTransform) shipped; Step 9 (i18n audit) is next
type: project
---

Step 8 enabled the Save button in ImageEditor and wired `patchMediaTransform`.

**Files modified**:
- `v1/frontend/src/lib/hooks/useImageEditor.ts` (204 lines) — added `buildOps()`, `setSaving()`, `setSaveError()` + updated `UseImageEditorReturn` interface; imported `MediaTransformOp/RotateOp/CropOp/MosaicOp/WatermarkOp`
- `v1/frontend/src/components/post-editor/ImageEditor.tsx` (454 lines) — renamed `_onSave` → `onSave`, added `mapTransformError()`, `handleSave()`, `canSave` derived value, real Save button with `aria-busy`, save error `role="alert"` panel, draft-media hint panel
- `v1/frontend/src/lib/api.ts` — added `id?: string` to `CreatePostMedia` (backend MediaAsset.id; undefined for draft media pre-publish)
- `v1/frontend/src/app/posts/new/page.tsx` — strips `id` field alongside `_clientId` in publish payload; updated `onSave` comment
- `v1/frontend/src/i18n/{ko,en,ja,zh,es}.json` — added 9 keys per locale: `saving`, `noIdHint`, `error.{auctionActive,signatureMissing,tooLarge,unsupportedType,notOwner,rateLimit,generic,noMediaId}`; removed `saveDisabledHint`

**media.id investigation (Task 4)**:
`CreatePostMedia` had no `id`. Upload endpoint (`/media/upload`) returns `UploadedMedia` with no `id` — the MediaAsset row is created on publish, not upload. Solution chosen: **Option A+D hybrid** — added `id?: string` to `CreatePostMedia`; when `id` is undefined (draft, not yet published), Save is disabled and `noIdHint` is shown. After transform save, `id` is populated from `MediaTransformResponse.id` for subsequent re-edits.

**apiFetch error format**: Throws `ApiClientError(err.code, ...)` where `err.code` is the backend error code string (e.g. `AUCTION_ACTIVE_MEDIA_LOCKED`). `mapTransformError` matches on `Error.message` which equals the code. Works correctly.

**saveDisabledHint**: Removed from all 5 locales — replaced by dynamic `noIdHint` (shows only when `media.id` is undefined AND user has made edits).

**5 integration points — all Pass**:
1. useDraftAutosave — triggers on `formState` identity change (line 208); `setMedia(prev => prev.map(...))` creates new array reference → autosave fires within 2s. Pass.
2. DraftRestoreDialog — calls `resetFromDraft(restored)` which replaces full media array including `crop_meta`; `useImageEditor.useEffect` re-reads `initialOps` on next open. Pass.
3. Multi-tab sync — `crop_meta` is plain JSON; round-trips through `JSON.stringify`/`JSON.parse` cleanly. Pass.
4. useArtistGate — controls `type` fallback and application status only; zero coupling to EditButton or ImageEditor. Pass.
5. Role-gating — SortableMediaCard EditButton checks only `media.type === "image"` and `!isGif`; no post type or role check. Pass.

**Why:** Step 7b wired signature upload modal; Step 8 is the final production wiring. Step 9 = full i18n audit of all ~44 keys for consistency.

**How to apply:** Step 9 should audit all keys under `post.editor.media.studio.*` across all 5 locales for completeness and translation quality. Step 10 = regression testing plan.
