---
name: editor-image-studio Step 6 complete
description: Step 6 (ImageEditor modal skeleton + Konva Stage + props drilling + SSR lazy import) shipped for PDCA #6-image
type: project
---

Step 6 of editor-image-studio PDCA (#6-image) is complete. All 5 tasks implemented and verified.

**Why:** Ships a usable modal that opens on EditButton click and renders Konva Stage with source image. 4 tool tabs are UI-only placeholders. Save button is disabled. Isolates SSR/lazy-import risk before Step 7 (actual tool functionality).

**How to apply:** Step 7 wires rotate/crop/mosaic/watermark tool functionality into the already-mounted Konva Stage. Step 8 wires Save button via `patchMediaTransform`.

Files created:
- `v1/frontend/src/lib/hooks/useImageEditor.ts` — state shell, all setters, `buildCropMeta()`, re-entry restore from initialOps
- `v1/frontend/src/components/post-editor/ImageEditor.tsx` — modal with Konva Stage + 4 tab UI shells + disabled Save
- `v1/frontend/src/components/post-editor/ImageEditorLazy.tsx` — `dynamic({ ssr: false })` wrapper (only import this, never ImageEditor directly)

Files modified:
- `MediaPreviewList.tsx` — added `onEditMedia?: (id: string) => void` prop, passed to SortableMediaCard
- `EditorWorkspace.tsx` — added `onEditMedia?` prop, passed to MediaPreviewList
- `EditorMobileWizard.tsx` — added `onEditMedia?` prop, passed to EditorStepContent
- `wizard/EditorStepContent.tsx` — added `onEditMedia?` prop, passed to MediaPreviewList
- `app/posts/new/page.tsx` — `editingMediaId` state + `handleEditMedia` + `editingMedia` lookup + `<ImageEditorLazy>` mount + `onEditMedia={handleEditMedia}` on both wizard+workspace
- `i18n/{ko,en,ja,zh,es}.json` — 10 keys × 5 locales added under `post.editor.media.studio.image`

SSR isolation: only `ImageEditor.tsx` imports from `react-konva`/`konva`. Confirmed via `grep -rn "from \"konva\"\|from \"react-konva\""`.

Step 7 hand-off notes:
- `useImageEditor` exposes `addMosaicRegion`/`removeMosaicRegion`/`setMosaicPixelSize` ready for mosaic drawing tool
- `stageRef` (Konva.Stage) + `imageEl` (HTMLImageElement) are both live in ImageEditor — Step 7 can attach Transformer for crop, Konva.Filters.Pixelate for mosaic
- `editor.state.rotation` is already wired to KonvaImage `rotation` prop
- Save button disabled via `disabled` attr; Step 8 removes that and calls `patchMediaTransform`
