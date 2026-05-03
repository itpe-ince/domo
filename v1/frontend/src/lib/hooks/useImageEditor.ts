"use client";

/**
 * useImageEditor — editor-image-studio PDCA #6-image (Step 6).
 *
 * State shell for the ImageEditor modal. Step 6 wires rotation/crop/mosaic/
 * watermark setters and the re-entry restore pattern (design §F-9).
 * handleSave API call is NOT here yet — wired in Step 8.
 */

import { useState, useEffect, useRef } from "react";
import type {
  CreatePostMedia,
  CropMeta,
  MosaicRegion,
  WatermarkMeta,
  MediaTransformOp,
  RotateOp,
  CropOp,
  MosaicOp,
  WatermarkOp,
} from "@/lib/api";

export type ImageTool = "rotate" | "crop" | "mosaic" | "watermark";

export interface ImageEditorState {
  rotation: 0 | 90 | 180 | 270;
  cropRect: { x: number; y: number; w: number; h: number } | null;
  cropPreset: "1:1" | "4:3" | "16:9" | "free" | "original";
  mosaicRegions: MosaicRegion[];
  mosaicPixelSize: 10 | 20 | 40;
  watermark: WatermarkMeta | null;
  activeTool: ImageTool;
  showOriginal: boolean;
  saving: boolean;       // wired in Step 8
  saveError: string | null; // wired in Step 8
}

export interface UseImageEditorReturn {
  state: ImageEditorState;
  setRotation: (r: 0 | 90 | 180 | 270) => void;
  setCropRect: (r: ImageEditorState["cropRect"]) => void;
  setCropPreset: (p: ImageEditorState["cropPreset"]) => void;
  setMosaicRegions: (regions: MosaicRegion[]) => void;
  addMosaicRegion: (region: MosaicRegion) => void;
  removeMosaicRegion: (idx: number) => void;
  setMosaicPixelSize: (s: 10 | 20 | 40) => void;
  setWatermark: (w: WatermarkMeta | null) => void;
  setActiveTool: (t: ImageTool) => void;
  toggleShowOriginal: () => void;
  setSaving: (saving: boolean) => void;
  setSaveError: (saveError: string | null) => void;
  buildCropMeta: () => CropMeta;
  buildOps: () => MediaTransformOp[];
  reset: () => void;
}

const INITIAL_STATE: ImageEditorState = {
  rotation: 0,
  cropRect: null,
  cropPreset: "free",
  mosaicRegions: [],
  mosaicPixelSize: 20,
  watermark: null,
  activeTool: "rotate",
  showOriginal: false,
  saving: false,
  saveError: null,
};

export function useImageEditor(
  _media: CreatePostMedia,
  initialOps?: CropMeta
): UseImageEditorReturn {
  const [state, setState] = useState<ImageEditorState>(INITIAL_STATE);

  // Restore from initialOps on mount exactly once (re-entry pattern, design §F-9).
  // useRef prevents double-restore if initialOps identity changes mid-session.
  const restoredRef = useRef(false);
  useEffect(() => {
    if (restoredRef.current) return;
    if (!initialOps) return;
    restoredRef.current = true;
    setState((s) => ({
      ...s,
      rotation: initialOps.rotation ?? 0,
      cropRect: initialOps.crop
        ? { x: initialOps.crop.x, y: initialOps.crop.y, w: initialOps.crop.w, h: initialOps.crop.h }
        : null,
      mosaicRegions: initialOps.mosaic_regions ?? [],
      watermark: initialOps.watermark ?? null,
    }));
  }, [initialOps]);

  const setRotation = (r: 0 | 90 | 180 | 270) =>
    setState((s) => ({ ...s, rotation: r }));

  const setCropRect = (r: ImageEditorState["cropRect"]) =>
    setState((s) => ({ ...s, cropRect: r }));

  const setCropPreset = (p: ImageEditorState["cropPreset"]) =>
    setState((s) => ({ ...s, cropPreset: p }));

  const setMosaicRegions = (regions: MosaicRegion[]) =>
    setState((s) => ({ ...s, mosaicRegions: regions }));

  const addMosaicRegion = (region: MosaicRegion) =>
    setState((s) => ({ ...s, mosaicRegions: [...s.mosaicRegions, region] }));

  const removeMosaicRegion = (idx: number) =>
    setState((s) => ({
      ...s,
      mosaicRegions: s.mosaicRegions.filter((_, i) => i !== idx),
    }));

  const setMosaicPixelSize = (size: 10 | 20 | 40) =>
    setState((s) => ({ ...s, mosaicPixelSize: size }));

  const setWatermark = (w: WatermarkMeta | null) =>
    setState((s) => ({ ...s, watermark: w }));

  const setActiveTool = (t: ImageTool) =>
    setState((s) => ({ ...s, activeTool: t }));

  const toggleShowOriginal = () =>
    setState((s) => ({ ...s, showOriginal: !s.showOriginal }));

  const setSaving = (saving: boolean) =>
    setState((s) => ({ ...s, saving }));

  const setSaveError = (saveError: string | null) =>
    setState((s) => ({ ...s, saveError }));

  function buildCropMeta(): CropMeta {
    return {
      version: 1,
      rotation: state.rotation,
      crop: state.cropRect ? { ...state.cropRect } : undefined,
      mosaic_regions: state.mosaicRegions,
      watermark: state.watermark ?? undefined,
    };
  }

  function buildOps(): MediaTransformOp[] {
    const ops: MediaTransformOp[] = [];

    if (state.rotation !== 0) {
      ops.push({ type: "rotate", degrees: state.rotation } as RotateOp);
    }

    if (state.cropRect) {
      ops.push({
        type: "crop",
        x: state.cropRect.x,
        y: state.cropRect.y,
        w: state.cropRect.w,
        h: state.cropRect.h,
        ratio: state.cropPreset,
      } as CropOp);
    }

    if (state.mosaicRegions.length > 0) {
      ops.push({ type: "mosaic", regions: state.mosaicRegions } as MosaicOp);
    }

    if (state.watermark) {
      ops.push({
        type: "watermark",
        source: state.watermark.source,
        text: state.watermark.text,
        position: state.watermark.position,
        size: state.watermark.size,
        opacity: state.watermark.opacity,
      } as WatermarkOp);
    }

    return ops;
  }

  function reset() {
    restoredRef.current = false;
    setState(INITIAL_STATE);
  }

  return {
    state,
    setRotation,
    setCropRect,
    setCropPreset,
    setMosaicRegions,
    addMosaicRegion,
    removeMosaicRegion,
    setMosaicPixelSize,
    setWatermark,
    setActiveTool,
    toggleShowOriginal,
    setSaving,
    setSaveError,
    buildCropMeta,
    buildOps,
    reset,
  };
}
