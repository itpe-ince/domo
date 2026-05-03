"use client";

/**
 * ImageEditor — editor-image-studio PDCA #6-image (Step 7).
 *
 * COORDINATE SYSTEM CONVENTION (Step 7):
 *   All crop, mosaic, and watermark coordinates are stored in SOURCE-IMAGE PIXELS
 *   (post-rotate), NOT in Stage display (CSS) pixels. This matches the backend
 *   Pydantic CropRect/MosaicRegion schema and survives Stage size changes.
 *   Two helpers below convert between Stage-local (CSS px) ↔ source-image px.
 *
 * ROTATION PIVOT:
 *   KonvaImage uses offsetX/offsetY = fitted.w/2, fitted.h/2 so that rotation
 *   is around the image center rather than the top-left corner. The x/y position
 *   is the center of the fitted rect (not top-left) to compensate.
 *
 * TOOL HOTKEYS (OQ-D-2 = A):
 *   1 → rotate  2 → crop  3 → mosaic  4 → watermark
 *   (skipped when focus is inside an input or textarea)
 *
 * IMPORTANT: This file imports react-konva at the top level, which references
 * browser globals (window, HTMLCanvasElement). It must NEVER be imported
 * directly; always use ImageEditorLazy (dynamic ssr:false wrapper) instead.
 *
 * Step 7 changes vs Step 6:
 *   - Replaced placeholder hints with real tool UI (RotateTool, CropTool,
 *     MosaicTool, WatermarkTool).
 *   - Fixed rotation pivot to image center.
 *   - Added hotkey handler (keys 1/2/3/4).
 *   - Added stageToImage / imageToStage coordinate helpers.
 * Step 7b changes:
 *   - useSignature hoisted here (single GET on mount; no double-fetch).
 *   - sig passed down to WatermarkToolControls and WatermarkToolStage.
 *   - WatermarkToolStage renders KonvaImage for signature source.
 * Save button STILL disabled — wired in Step 8.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { Stage, Layer, Image as KonvaImage } from "react-konva";
import type Konva from "konva";

import { useI18n } from "@/i18n";
import type { CreatePostMedia, CropMeta } from "@/lib/api";
import { patchMediaTransform } from "@/lib/api";
import { useImageEditor, type ImageTool } from "@/lib/hooks/useImageEditor";
import { useSignature } from "@/lib/hooks/useSignature";

import { RotateTool } from "./image-editor/RotateTool";
import { CropToolControls, CropToolStage } from "./image-editor/CropTool";
import {
  MosaicToolControls,
  MosaicToolStage,
} from "./image-editor/MosaicTool";
import {
  WatermarkToolControls,
  WatermarkToolStage,
} from "./image-editor/WatermarkTool";

// ─── Coordinate helpers ───────────────────────────────────────────────────────

/**
 * Stage-local coords (CSS pixels, pre-DPR) → source-image pixels.
 * Returns null when the point is outside the fitted image rect.
 *
 * Note: Stage scaleX/Y = DPR, but getPointerPosition() already returns
 * CSS pixels (not DPR-scaled), so this math "just works".
 */
export function stageToImage(
  stagePoint: { x: number; y: number },
  fittedRect: { x: number; y: number; w: number; h: number },
  imageEl: HTMLImageElement
): { x: number; y: number } | null {
  const rx = stagePoint.x - fittedRect.x;
  const ry = stagePoint.y - fittedRect.y;
  if (rx < 0 || ry < 0 || rx > fittedRect.w || ry > fittedRect.h) return null;
  const scale = imageEl.naturalWidth / fittedRect.w;
  return { x: Math.round(rx * scale), y: Math.round(ry * scale) };
}

/** Source-image pixels → Stage-local coords (CSS pixels). */
export function imageToStage(
  imagePoint: { x: number; y: number },
  fittedRect: { x: number; y: number; w: number; h: number },
  imageEl: HTMLImageElement
): { x: number; y: number } {
  const scale = fittedRect.w / imageEl.naturalWidth;
  return {
    x: fittedRect.x + imagePoint.x * scale,
    y: fittedRect.y + imagePoint.y * scale,
  };
}

// ─── Component ────────────────────────────────────────────────────────────────

export interface ImageEditorProps {
  media: CreatePostMedia;
  initialOps?: CropMeta;
  onSave: (updated: CreatePostMedia) => void;
  onCancel: () => void;
}

// ─── Error code mapper ────────────────────────────────────────────────────────

function mapTransformError(rawMessage: string): string {
  if (rawMessage.includes("AUCTION_ACTIVE_MEDIA_LOCKED")) {
    return "post.editor.media.studio.image.editor.error.auctionActive";
  }
  if (rawMessage.includes("WATERMARK_SIGNATURE_NOT_SET")) {
    return "post.editor.media.studio.image.editor.error.signatureMissing";
  }
  if (rawMessage.includes("MEDIA_TRANSFORM_TOO_LARGE")) {
    return "post.editor.media.studio.image.editor.error.tooLarge";
  }
  if (rawMessage.includes("MEDIA_TRANSFORM_UNSUPPORTED_TYPE")) {
    return "post.editor.media.studio.image.editor.error.unsupportedType";
  }
  if (rawMessage.includes("MEDIA_NOT_OWNER")) {
    return "post.editor.media.studio.image.editor.error.notOwner";
  }
  if (rawMessage.includes("RATE_LIMIT")) {
    return "post.editor.media.studio.image.editor.error.rateLimit";
  }
  return "post.editor.media.studio.image.editor.error.generic";
}

// ─── Component ────────────────────────────────────────────────────────────────

export function ImageEditor({
  media,
  initialOps,
  onSave,
  onCancel,
}: ImageEditorProps) {
  const { t } = useI18n();
  const editor = useImageEditor(media, initialOps);
  const sig = useSignature();
  const stageContainerRef = useRef<HTMLDivElement>(null);
  const stageRef = useRef<Konva.Stage>(null);
  const [stageSize, setStageSize] = useState({ width: 0, height: 0 });
  const [imageEl, setImageEl] = useState<HTMLImageElement | null>(null);
  // Focus trap: ref to the modal shell, so we can query focusable children
  const modalRef = useRef<HTMLDivElement>(null);
  // Close-button ref to focus on mount
  const closeBtnRef = useRef<HTMLButtonElement>(null);

  // ─── Load source image ────────────────────────────────────────────────
  useEffect(() => {
    const img = new window.Image();
    img.crossOrigin = "anonymous";
    img.onload = () => setImageEl(img);
    img.src = media.url;
    return () => {
      img.onload = null;
    };
  }, [media.url]);

  // ─── Stage sizing: ResizeObserver + DPR (OQ-D-1 = A) ─────────────────
  useEffect(() => {
    const el = stageContainerRef.current;
    if (!el) return;
    const ro = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (!entry) return;
      const { width, height } = entry.contentRect;
      setStageSize({ width: Math.floor(width), height: Math.floor(height) });
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const dpr =
    typeof window !== "undefined" ? window.devicePixelRatio || 1 : 1;

  // ─── Focus on mount: close button ────────────────────────────────────
  useEffect(() => {
    closeBtnRef.current?.focus();
  }, []);

  // ─── Focus trap: Tab/Shift+Tab must stay inside modal ────────────────
  const handleFocusTrap = useCallback((e: React.KeyboardEvent<HTMLDivElement>) => {
    if (e.key !== "Tab") return;
    const modal = modalRef.current;
    if (!modal) return;
    const focusable = Array.from(
      modal.querySelectorAll<HTMLElement>(
        'button:not([disabled]), input:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
      )
    ).filter((el) => el.offsetParent !== null); // exclude hidden elements
    if (focusable.length === 0) return;
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (e.shiftKey) {
      if (document.activeElement === first) {
        e.preventDefault();
        last.focus();
      }
    } else {
      if (document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    }
  }, []);

  // ─── ESC = cancel ────────────────────────────────────────────────────
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onCancel();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onCancel]);

  // ─── Tool hotkeys 1/2/3/4 (OQ-D-2 = A) ──────────────────────────────
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      const target = e.target as HTMLElement;
      if (target.tagName === "INPUT" || target.tagName === "TEXTAREA") return;
      if (e.key === "1") editor.setActiveTool("rotate");
      else if (e.key === "2") editor.setActiveTool("crop");
      else if (e.key === "3") editor.setActiveTool("mosaic");
      else if (e.key === "4") editor.setActiveTool("watermark");
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [editor]);

  // ─── Fitted image size (object-fit: contain) ─────────────────────────
  const fitted = (() => {
    if (!imageEl || stageSize.width === 0 || stageSize.height === 0) {
      return { w: 0, h: 0 };
    }
    const ar = imageEl.naturalWidth / imageEl.naturalHeight;
    const stageAr = stageSize.width / stageSize.height;
    if (ar > stageAr) {
      return { w: stageSize.width, h: stageSize.width / ar };
    }
    return { w: stageSize.height * ar, h: stageSize.height };
  })();

  // fittedRect in Stage-local (CSS pixel) coords — used by all tool stage components
  const fittedRect = {
    x: (stageSize.width - fitted.w) / 2,
    y: (stageSize.height - fitted.h) / 2,
    w: fitted.w,
    h: fitted.h,
  };

  // KonvaImage x/y = CENTER of the fitted rect (rotation pivot at center via offsetX/Y)
  const imageX = fittedRect.x + fitted.w / 2;
  const imageY = fittedRect.y + fitted.h / 2;

  const tools: ImageTool[] = ["rotate", "crop", "mosaic", "watermark"];

  // ─── Save handler ─────────────────────────────────────────────────────
  async function handleSave() {
    const ops = editor.buildOps();

    // No-op: close without API call when there are no edits
    if (ops.length === 0) {
      onCancel();
      return;
    }

    // media.id is required to call the transform endpoint.
    // Draft media (not yet published) has no MediaAsset row and therefore no id.
    // Show an error rather than crashing.
    if (!media.id) {
      editor.setSaveError("post.editor.media.studio.image.editor.error.noMediaId");
      return;
    }

    editor.setSaving(true);
    editor.setSaveError(null);
    try {
      const updated = await patchMediaTransform(media.id, ops);
      onSave({
        ...media,
        url: updated.url,
        thumbnail_url: updated.thumbnail_url,
        width: updated.width ?? media.width,
        height: updated.height ?? media.height,
        crop_meta: updated.crop_meta,
        id: updated.id,
      });
      // Parent onSave closes the modal via setEditingMediaId(null)
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "save_failed";
      editor.setSaveError(mapTransformError(msg));
    } finally {
      editor.setSaving(false);
    }
  }

  // Whether the Save button should be active:
  // - ops must be non-empty (user did something)
  // - media.id must exist (published media only)
  // - not currently saving
  const hasOps = editor.buildOps().length > 0;
  const canSave = hasOps && !!media.id && !editor.state.saving;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={t("post.editor.media.studio.image.editor.title")}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm"
      onClick={(e) => {
        if (e.target === e.currentTarget) onCancel();
      }}
      onKeyDown={handleFocusTrap}
    >
      {/* Modal shell — desktop max-w-4xl, mobile full-screen */}
      <div
        ref={modalRef}
        className="relative w-full h-full md:w-[90vw] md:h-[90vh] md:max-w-4xl md:rounded-lg overflow-hidden bg-surface flex flex-col"
      >

        {/* Header */}
        <header className="flex items-center justify-between px-4 py-3 border-b border-border flex-shrink-0">
          <h2 className="text-lg font-semibold text-text-primary">
            {t("post.editor.media.studio.image.editor.title")}
          </h2>
          <button
            ref={closeBtnRef}
            type="button"
            onClick={onCancel}
            aria-label={t("common.cancel")}
            className="p-1.5 hover:bg-surface-hover rounded text-text-muted hover:text-text-primary transition-colors"
          >
            ✕
          </button>
        </header>

        {/* Tool tab bar — overflow-x-auto for narrow mobile viewports */}
        <nav className="flex border-b border-border flex-shrink-0 overflow-x-auto" role="tablist">
          {tools.map((tool) => (
            <button
              key={tool}
              type="button"
              role="tab"
              aria-selected={editor.state.activeTool === tool}
              onClick={() => editor.setActiveTool(tool)}
              className={`px-4 py-2 text-sm border-b-2 transition-colors ${
                editor.state.activeTool === tool
                  ? "border-primary text-primary"
                  : "border-transparent text-text-muted hover:text-text-primary"
              }`}
            >
              {t(`post.editor.media.studio.image.tool.${tool}.label`)}
            </button>
          ))}
        </nav>

        {/* Stage + floating control bar */}
        <div
          ref={stageContainerRef}
          className="flex-1 relative bg-surface-hover overflow-hidden"
        >
          {imageEl && stageSize.width > 0 && stageSize.height > 0 && (
            <Stage
              ref={stageRef}
              width={stageSize.width * dpr}
              height={stageSize.height * dpr}
              scaleX={dpr}
              scaleY={dpr}
              style={{ width: stageSize.width, height: stageSize.height }}
            >
              <Layer>
                {/*
                 * Rotation pivot = image center.
                 * x/y = center of the fitted rect; offsetX/Y = half of image dims.
                 * This keeps the image visually centered for all rotation values.
                 */}
                <KonvaImage
                  image={imageEl}
                  x={imageX}
                  y={imageY}
                  width={fitted.w}
                  height={fitted.h}
                  offsetX={fitted.w / 2}
                  offsetY={fitted.h / 2}
                  rotation={editor.state.rotation}
                />

                {/* Crop tool — Rect + Transformer overlay */}
                <CropToolStage
                  cropRect={editor.state.cropRect}
                  setCropRect={editor.setCropRect}
                  preset={editor.state.cropPreset}
                  fittedRect={fittedRect}
                  imageEl={imageEl}
                  active={editor.state.activeTool === "crop"}
                />

                {/* Mosaic tool — draw regions */}
                <MosaicToolStage
                  regions={editor.state.mosaicRegions}
                  pixelSize={editor.state.mosaicPixelSize}
                  fittedRect={fittedRect}
                  imageEl={imageEl}
                  active={editor.state.activeTool === "mosaic"}
                  addRegion={editor.addMosaicRegion}
                  removeRegion={editor.removeMosaicRegion}
                />

                {/* Watermark preview — visible for all active tools */}
                <WatermarkToolStage
                  watermark={editor.state.watermark}
                  fittedRect={fittedRect}
                  imageEl={imageEl}
                  signatureUrl={sig.signatureUrl}
                  active={editor.state.activeTool === "watermark"}
                />
              </Layer>
            </Stage>
          )}

          {/* Floating control bar — switches by activeTool.
              max-w-[calc(100vw-2rem)] prevents overflow on 375px mobile. */}
          <div className="absolute bottom-4 left-1/2 -translate-x-1/2 z-10 max-w-[calc(100vw-2rem)] w-max">
            {editor.state.activeTool === "rotate" && (
              <RotateTool
                rotation={editor.state.rotation}
                setRotation={editor.setRotation}
              />
            )}
            {editor.state.activeTool === "crop" && (
              <CropToolControls
                preset={editor.state.cropPreset}
                setPreset={editor.setCropPreset}
                setCropRect={editor.setCropRect}
              />
            )}
            {editor.state.activeTool === "mosaic" && (
              <MosaicToolControls
                pixelSize={editor.state.mosaicPixelSize}
                setPixelSize={editor.setMosaicPixelSize}
                regionCount={editor.state.mosaicRegions.length}
                clearRegions={() => editor.setMosaicRegions([])}
              />
            )}
            {editor.state.activeTool === "watermark" && (
              <WatermarkToolControls
                watermark={editor.state.watermark}
                setWatermark={editor.setWatermark}
                sig={sig}
              />
            )}
          </div>
        </div>

        {/* Save error display */}
        {editor.state.saveError && (
          <div
            role="alert"
            className="px-4 py-2 text-sm text-red-500 border-t border-border"
          >
            {t(editor.state.saveError)}
          </div>
        )}

        {/* Draft-media hint: no MediaAsset id yet */}
        {!media.id && hasOps && !editor.state.saveError && (
          <div className="px-4 py-2 text-sm text-text-muted border-t border-border">
            {t("post.editor.media.studio.image.editor.noIdHint")}
          </div>
        )}

        {/* Footer */}
        <footer className="flex items-center justify-end gap-2 px-4 py-3 border-t border-border flex-shrink-0">
          <button
            type="button"
            onClick={onCancel}
            className="px-4 py-2 text-sm rounded hover:bg-surface-hover text-text-secondary transition-colors"
          >
            {t("common.cancel")}
          </button>
          <button
            type="button"
            onClick={handleSave}
            disabled={!canSave}
            aria-busy={editor.state.saving}
            className="px-4 py-2 text-sm rounded bg-primary text-white hover:bg-primary-hover disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {editor.state.saving
              ? t("post.editor.media.studio.image.editor.saving")
              : t("common.save")}
          </button>
        </footer>
      </div>
    </div>
  );
}
