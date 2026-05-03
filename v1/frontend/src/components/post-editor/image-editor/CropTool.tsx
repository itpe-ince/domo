"use client";

import { useEffect, useRef } from "react";
import type Konva from "konva";
import { Rect, Transformer } from "react-konva";

import { useI18n } from "@/i18n";
import type { CropRect } from "@/lib/api";

export type CropPreset = "1:1" | "4:3" | "16:9" | "free" | "original";

// ─── Control bar (renders outside Stage, in floating panel) ──────────────────

interface CropToolControlsProps {
  preset: CropPreset;
  setPreset: (p: CropPreset) => void;
  setCropRect: (r: CropRect | null) => void;
}

export function CropToolControls({
  preset,
  setPreset,
  setCropRect,
}: CropToolControlsProps) {
  const { t } = useI18n();
  const presets: CropPreset[] = ["1:1", "4:3", "16:9", "free", "original"];

  function handlePreset(p: CropPreset) {
    setPreset(p);
    if (p === "original") setCropRect(null); // OQ-D-5 = A: "original" clears crop
  }

  function presetKey(p: CropPreset): string {
    switch (p) {
      case "1:1": return "ratio_1_1";
      case "4:3": return "ratio_4_3";
      case "16:9": return "ratio_16_9";
      case "free": return "ratio_free";
      case "original": return "ratio_original";
    }
  }

  return (
    <div
      className="flex items-center flex-wrap gap-1 bg-surface/95 px-3 py-2 rounded shadow-lg max-w-[calc(100vw-2rem)]"
      role="toolbar"
      aria-label={t("post.editor.media.studio.image.tool.crop.label")}
    >
      {presets.map((p) => (
        <button
          key={p}
          type="button"
          onClick={() => handlePreset(p)}
          aria-pressed={preset === p}
          className={`px-2 py-1 text-xs rounded transition-colors ${
            preset === p
              ? "bg-primary text-white"
              : "hover:bg-surface-hover"
          }`}
        >
          {t(`post.editor.media.studio.image.tool.crop.${presetKey(p)}`)}
        </button>
      ))}
    </div>
  );
}

// ─── Stage layer (renders inside Konva Layer) ─────────────────────────────────

interface FittedRect {
  x: number;
  y: number;
  w: number;
  h: number;
}

interface CropToolStageProps {
  cropRect: CropRect | null;       // source-image pixels
  setCropRect: (r: CropRect) => void;
  preset: CropPreset;
  fittedRect: FittedRect;         // KonvaImage position+size in stage (CSS pixel) coords
  imageEl: HTMLImageElement | null;
  active: boolean;
}

export function CropToolStage({
  cropRect,
  setCropRect,
  preset,
  fittedRect,
  imageEl,
  active,
}: CropToolStageProps) {
  const rectRef = useRef<Konva.Rect>(null);
  const trRef = useRef<Konva.Transformer>(null);

  // Attach/detach transformer when active state or cropRect changes
  useEffect(() => {
    if (!active) {
      trRef.current?.nodes([]);
      return;
    }
    if (rectRef.current && trRef.current) {
      trRef.current.nodes([rectRef.current]);
      trRef.current.getLayer()?.batchDraw();
    }
  }, [active, cropRect]);

  if (!active || !imageEl) return null;

  // Convert source-image cropRect → stage display coords
  const scale = fittedRect.w / imageEl.naturalWidth;
  const displayX = cropRect ? fittedRect.x + cropRect.x * scale : fittedRect.x;
  const displayY = cropRect ? fittedRect.y + cropRect.y * scale : fittedRect.y;
  const displayW = cropRect ? cropRect.w * scale : fittedRect.w;
  const displayH = cropRect ? cropRect.h * scale : fittedRect.h;

  // Aspect ratio to enforce during transform
  const aspect: number | null =
    preset === "1:1" ? 1
    : preset === "4:3" ? 4 / 3
    : preset === "16:9" ? 16 / 9
    : null;

  const inv = imageEl.naturalWidth / fittedRect.w;

  return (
    <>
      <Rect
        ref={rectRef}
        x={displayX}
        y={displayY}
        width={displayW}
        height={displayH}
        stroke="white"
        strokeWidth={2}
        dash={[6, 4]}
        draggable
        dragBoundFunc={(pos) => ({
          x: Math.max(
            fittedRect.x,
            Math.min(pos.x, fittedRect.x + fittedRect.w - displayW)
          ),
          y: Math.max(
            fittedRect.y,
            Math.min(pos.y, fittedRect.y + fittedRect.h - displayH)
          ),
        })}
        onTransformEnd={() => {
          const node = rectRef.current;
          if (!node) return;
          const scaleX = node.scaleX();
          const scaleY = node.scaleY();
          const newW = Math.max(10, node.width() * scaleX);
          const newH = Math.max(10, node.height() * scaleY);
          node.scaleX(1);
          node.scaleY(1);
          node.width(newW);
          node.height(newH);
          // Convert back to source-image pixels
          const ix = Math.round((node.x() - fittedRect.x) * inv);
          const iy = Math.round((node.y() - fittedRect.y) * inv);
          const iw = Math.round(newW * inv);
          const ih = Math.round(newH * inv);
          setCropRect({
            x: Math.max(0, ix),
            y: Math.max(0, iy),
            w: Math.min(imageEl.naturalWidth - Math.max(0, ix), iw),
            h: Math.min(imageEl.naturalHeight - Math.max(0, iy), ih),
          });
        }}
        onDragEnd={() => {
          const node = rectRef.current;
          if (!node) return;
          const ix = Math.round((node.x() - fittedRect.x) * inv);
          const iy = Math.round((node.y() - fittedRect.y) * inv);
          setCropRect({
            x: Math.max(0, ix),
            y: Math.max(0, iy),
            w: cropRect?.w ?? imageEl.naturalWidth,
            h: cropRect?.h ?? imageEl.naturalHeight,
          });
        }}
      />
      <Transformer
        ref={trRef}
        rotateEnabled={false}
        keepRatio={aspect !== null}
        boundBoxFunc={(oldBox, newBox) => {
          if (newBox.x < fittedRect.x || newBox.y < fittedRect.y) return oldBox;
          if (newBox.x + newBox.width > fittedRect.x + fittedRect.w) return oldBox;
          if (newBox.y + newBox.height > fittedRect.y + fittedRect.h) return oldBox;
          if (newBox.width < 20 || newBox.height < 20) return oldBox;
          return newBox;
        }}
      />
    </>
  );
}
