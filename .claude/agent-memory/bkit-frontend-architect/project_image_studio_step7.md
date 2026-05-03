---
name: editor-image-studio Step 7 complete
description: Step 7 (4 tool components + hotkeys + i18n) shipped; Step 7b (signature upload modal) and Step 8 (patchMediaTransform wiring) are next
type: project
---

Step 7 shipped all 4 tool components for PDCA #6-image editor-image-studio.

**Files created**:
- `v1/frontend/src/components/post-editor/image-editor/RotateTool.tsx` (48 lines)
- `v1/frontend/src/components/post-editor/image-editor/CropTool.tsx` (199 lines) — two exports: CropToolControls (floating bar) + CropToolStage (Konva Rect+Transformer)
- `v1/frontend/src/components/post-editor/image-editor/MosaicTool.tsx` (202 lines) — drag-draw regions; click existing region to remove
- `v1/frontend/src/components/post-editor/image-editor/WatermarkTool.tsx` (160 lines) — text+opacity controls; signature slot is placeholder

**Files modified**:
- `v1/frontend/src/components/post-editor/ImageEditor.tsx` (352 lines) — rotation pivot fixed to center (offsetX/Y), hotkeys 1/2/3/4, stageToImage/imageToStage helpers, tool wiring
- `v1/frontend/src/i18n/{ko,en,ja,zh,es}.json` — 18 new keys each under `post.editor.media.studio.image.tool.*`

**Coordinate convention**: All crop/mosaic/watermark coords stored in source-image pixels. stageToImage/imageToStage helpers in ImageEditor.tsx.

**Why:** Save button STILL disabled — Step 8 wires patchMediaTransform. Signature upload UI is placeholder — Step 7b.

**How to apply:** Step 7b adds signature upload modal (replaces `watermark.signature.uploadFirst` placeholder). Step 8 enables Save by calling `patchMediaTransform` with `buildCropMeta()` output.
