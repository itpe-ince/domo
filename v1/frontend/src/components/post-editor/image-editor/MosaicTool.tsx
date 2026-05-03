"use client";

import { useState } from "react";
import { Rect } from "react-konva";

import { useI18n } from "@/i18n";
import type { MosaicRegion } from "@/lib/api";

// ─── Control bar ──────────────────────────────────────────────────────────────

interface MosaicToolControlsProps {
  pixelSize: 10 | 20 | 40;
  setPixelSize: (s: 10 | 20 | 40) => void;
  regionCount: number;
  clearRegions: () => void;
}

export function MosaicToolControls({
  pixelSize,
  setPixelSize,
  regionCount,
  clearRegions,
}: MosaicToolControlsProps) {
  const { t } = useI18n();
  const sizes = [10, 20, 40] as const;

  return (
    <div
      className="flex items-center gap-2 bg-surface/95 px-3 py-2 rounded shadow-lg"
      role="toolbar"
      aria-label={t("post.editor.media.studio.image.tool.mosaic.label")}
    >
      <span className="text-xs text-text-muted">
        {t("post.editor.media.studio.image.tool.mosaic.strength")}:
      </span>
      {sizes.map((s) => (
        <button
          key={s}
          type="button"
          onClick={() => setPixelSize(s)}
          aria-pressed={pixelSize === s}
          className={`px-2 py-1 text-xs rounded transition-colors ${
            pixelSize === s ? "bg-primary text-white" : "hover:bg-surface-hover"
          }`}
        >
          {s}
        </button>
      ))}
      <button
        type="button"
        onClick={clearRegions}
        disabled={regionCount === 0}
        className="ml-2 px-2 py-1 text-xs rounded hover:bg-surface-hover disabled:opacity-50 transition-colors"
      >
        {t("post.editor.media.studio.image.tool.mosaic.clearAll")} ({regionCount})
      </button>
    </div>
  );
}

// ─── Stage layer ──────────────────────────────────────────────────────────────

interface FittedRect {
  x: number;
  y: number;
  w: number;
  h: number;
}

interface DrawState {
  startX: number;
  startY: number;
  endX: number;
  endY: number;
}

interface MosaicToolStageProps {
  regions: MosaicRegion[];           // source-image pixels
  pixelSize: 10 | 20 | 40;
  fittedRect: FittedRect;
  imageEl: HTMLImageElement | null;
  active: boolean;
  addRegion: (r: MosaicRegion) => void;
  removeRegion: (idx: number) => void;
}

export function MosaicToolStage({
  regions,
  pixelSize,
  fittedRect,
  imageEl,
  active,
  addRegion,
  removeRegion,
}: MosaicToolStageProps) {
  const [drawing, setDrawing] = useState<DrawState | null>(null);

  if (!active || !imageEl) return null;

  const scale = fittedRect.w / imageEl.naturalWidth;
  const inv = imageEl.naturalWidth / fittedRect.w;

  function isInsideImage(x: number, y: number): boolean {
    return (
      x >= fittedRect.x &&
      x <= fittedRect.x + fittedRect.w &&
      y >= fittedRect.y &&
      y <= fittedRect.y + fittedRect.h
    );
  }

  return (
    <>
      {/*
       * Drawing surface — rendered BEHIND region rects (listed first in JSX).
       * Region rects cancel bubble on click so draw events don't fire when
       * clicking an existing region.
       */}
      <Rect
        x={fittedRect.x}
        y={fittedRect.y}
        width={fittedRect.w}
        height={fittedRect.h}
        fill="transparent"
        onMouseDown={(e) => {
          const stage = e.target.getStage();
          if (!stage) return;
          const pos = stage.getPointerPosition();
          if (!pos || !isInsideImage(pos.x, pos.y)) return;
          setDrawing({ startX: pos.x, startY: pos.y, endX: pos.x, endY: pos.y });
        }}
        onMouseMove={(e) => {
          if (!drawing) return;
          const stage = e.target.getStage();
          if (!stage) return;
          const pos = stage.getPointerPosition();
          if (!pos) return;
          const cx = Math.max(fittedRect.x, Math.min(pos.x, fittedRect.x + fittedRect.w));
          const cy = Math.max(fittedRect.y, Math.min(pos.y, fittedRect.y + fittedRect.h));
          setDrawing({ ...drawing, endX: cx, endY: cy });
        }}
        onMouseUp={() => {
          if (!drawing) return;
          const x1 = Math.min(drawing.startX, drawing.endX);
          const y1 = Math.min(drawing.startY, drawing.endY);
          const w = Math.abs(drawing.endX - drawing.startX);
          const h = Math.abs(drawing.endY - drawing.startY);
          if (w < 10 || h < 10) {
            setDrawing(null);
            return;
          }
          addRegion({
            x: Math.round((x1 - fittedRect.x) * inv),
            y: Math.round((y1 - fittedRect.y) * inv),
            w: Math.round(w * inv),
            h: Math.round(h * inv),
            strength: pixelSize,
          });
          setDrawing(null);
        }}
        onMouseLeave={() => setDrawing(null)}
      />

      {/* Existing regions — click to remove (cancelBubble prevents draw trigger) */}
      {regions.map((r, i) => (
        <Rect
          key={i}
          x={fittedRect.x + r.x * scale}
          y={fittedRect.y + r.y * scale}
          width={r.w * scale}
          height={r.h * scale}
          fill="rgba(0, 0, 0, 0.35)"
          stroke="white"
          strokeWidth={1}
          dash={[3, 3]}
          onClick={(e) => {
            e.cancelBubble = true;
            removeRegion(i);
          }}
          onTap={(e) => {
            e.cancelBubble = true;
            removeRegion(i);
          }}
        />
      ))}

      {/* Live drawing preview */}
      {drawing && (
        <Rect
          x={Math.min(drawing.startX, drawing.endX)}
          y={Math.min(drawing.startY, drawing.endY)}
          width={Math.abs(drawing.endX - drawing.startX)}
          height={Math.abs(drawing.endY - drawing.startY)}
          fill="rgba(255, 255, 0, 0.25)"
          stroke="yellow"
          strokeWidth={1}
          listening={false}
        />
      )}
    </>
  );
}
