"use client";

import { useState, useEffect } from "react";
import { Image as KonvaImage, Text as KonvaText } from "react-konva";

import { useI18n } from "@/i18n";
import type { WatermarkMeta } from "@/lib/api";
import type { UseSignatureReturn } from "@/lib/hooks/useSignature";
import { SignatureUploadModal } from "../SignatureUploadModal";
import { SignaturePreview } from "../SignaturePreview";

// ─── Control bar ──────────────────────────────────────────────────────────────

interface WatermarkToolControlsProps {
  watermark: WatermarkMeta | null;
  setWatermark: (w: WatermarkMeta | null) => void;
  /** Lifted from ImageEditor to avoid double-fetching. */
  sig: UseSignatureReturn;
}

export function WatermarkToolControls({
  watermark,
  setWatermark,
  sig,
}: WatermarkToolControlsProps) {
  const { t } = useI18n();
  const [text, setText] = useState(watermark?.text ?? "");
  const [opacity, setOpacity] = useState(watermark?.opacity ?? 0.7);
  const [uploadOpen, setUploadOpen] = useState(false);

  function applyText() {
    if (!text.trim()) {
      setWatermark(null);
      return;
    }
    setWatermark({
      source: "text",
      text: text.trim(),
      position: { x: 0, y: 0 },
      size: 24,
      opacity,
    });
  }

  function handleOpacityChange(o: number) {
    setOpacity(o);
    if (watermark) setWatermark({ ...watermark, opacity: o });
  }

  return (
    <div
      className="flex flex-col gap-2 bg-surface/95 px-3 py-2 rounded shadow-lg w-64 max-h-[38vh] overflow-y-auto"
      role="toolbar"
      aria-label={t("post.editor.media.studio.image.tool.watermark.label")}
    >
      {/* Text input row */}
      <div className="flex items-center gap-2">
        <input
          type="text"
          value={text}
          onChange={(e) => setText(e.target.value)}
          onBlur={applyText}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              applyText();
            }
          }}
          maxLength={100}
          placeholder={t("post.editor.media.studio.image.tool.watermark.text.placeholder")}
          className="px-2 py-1 text-sm rounded bg-surface border border-border flex-1 min-w-0"
          aria-label={t("post.editor.media.studio.image.tool.watermark.text.label")}
        />
        <button
          type="button"
          onClick={applyText}
          className="px-2 py-1 text-xs rounded bg-primary text-white hover:bg-primary-hover transition-colors"
        >
          {t("post.editor.media.studio.image.tool.watermark.apply")}
        </button>
      </div>

      {/* Opacity slider */}
      <div className="flex items-center gap-2">
        <span className="text-xs text-text-muted">
          {t("post.editor.media.studio.image.tool.watermark.opacity")}:
        </span>
        <input
          type="range"
          min="0.1"
          max="1"
          step="0.05"
          value={opacity}
          onChange={(e) => handleOpacityChange(Number(e.target.value))}
          className="flex-1"
          aria-label={t("post.editor.media.studio.image.tool.watermark.opacity")}
        />
        <span className="text-xs tabular-nums w-10 text-right">
          {(opacity * 100).toFixed(0)}%
        </span>
      </div>

      {/* Signature section */}
      {sig.loading ? (
        <div className="flex items-center gap-2 pt-2 border-t border-border">
          <span className="text-xs text-text-muted">
            {t("post.editor.media.studio.image.tool.watermark.signature.loading")}
          </span>
        </div>
      ) : sig.signatureUrl ? (
        <div className="flex flex-col gap-2">
          <SignaturePreview
            signatureUrl={sig.signatureUrl}
            loading={sig.mutating}
            onChange={() => setUploadOpen(true)}
            onDelete={() => sig.remove()}
          />
          {/* Toggle: use signature as watermark source */}
          <div className="flex items-center gap-2">
            <label className="flex items-center gap-2 text-xs cursor-pointer">
              <input
                type="checkbox"
                checked={watermark?.source === "signature"}
                onChange={(e) => {
                  if (e.target.checked) {
                    setWatermark({
                      source: "signature",
                      position: { x: 0, y: 0 },
                      opacity,
                    });
                  } else {
                    setWatermark(null);
                  }
                }}
              />
              {t("post.editor.media.studio.image.tool.watermark.signature.useToggle")}
            </label>
          </div>
        </div>
      ) : (
        <div className="flex items-center gap-2 pt-2 border-t border-border">
          <span className="text-xs text-text-muted">
            {t("post.editor.media.studio.image.tool.watermark.signature.label")}:
          </span>
          <button
            type="button"
            onClick={() => setUploadOpen(true)}
            className="px-2 py-1 text-xs rounded bg-primary text-white hover:bg-primary-hover"
          >
            {t("post.editor.media.studio.image.tool.watermark.signature.upload")}
          </button>
        </div>
      )}

      {/* Upload modal — z-[60] renders above ImageEditor modal (z-50) */}
      <SignatureUploadModal
        open={uploadOpen}
        uploading={sig.mutating}
        errorKey={sig.error}
        onUpload={async (file) => {
          await sig.upload(file);
          setUploadOpen(false);
        }}
        onClose={() => setUploadOpen(false)}
      />

      {/* Remove watermark button */}
      {watermark && (
        <button
          type="button"
          onClick={() => {
            setText("");
            setWatermark(null);
          }}
          className="self-start px-2 py-1 text-xs rounded hover:bg-surface-hover transition-colors"
        >
          {t("post.editor.media.studio.image.tool.watermark.remove")}
        </button>
      )}
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

interface WatermarkToolStageProps {
  watermark: WatermarkMeta | null;
  fittedRect: FittedRect;
  imageEl: HTMLImageElement | null;
  /** Signature image URL from useSignature (hoisted in ImageEditor). */
  signatureUrl: string | null;
  active: boolean;
}

export function WatermarkToolStage({
  watermark,
  fittedRect,
  imageEl,
  signatureUrl,
}: WatermarkToolStageProps) {
  const [sigImg, setSigImg] = useState<HTMLImageElement | null>(null);

  // Load signature image element when source = "signature"
  useEffect(() => {
    if (watermark?.source !== "signature" || !signatureUrl) {
      setSigImg(null);
      return;
    }
    const img = new window.Image();
    img.crossOrigin = "anonymous"; // keep canvas taint-free for Step 8 Save
    img.onload = () => setSigImg(img);
    img.src = signatureUrl;
    return () => {
      img.onload = null;
    };
  }, [watermark?.source, signatureUrl]);

  if (!watermark || !imageEl) return null;

  const x = fittedRect.x + 12;
  const y = fittedRect.y + 12;

  if (watermark.source === "text") {
    return (
      <KonvaText
        x={x}
        y={y}
        text={watermark.text ?? ""}
        fontSize={watermark.size ?? 24}
        fill={`rgba(255, 255, 255, ${watermark.opacity})`}
        stroke="black"
        strokeWidth={0.5}
        listening={false}
      />
    );
  }

  if (watermark.source === "signature" && sigImg) {
    // Render at max 80px wide, preserving aspect ratio
    const maxW = 80;
    const ar = sigImg.naturalWidth / sigImg.naturalHeight;
    const w = Math.min(maxW, sigImg.naturalWidth);
    const h = w / ar;
    return (
      <KonvaImage
        image={sigImg}
        x={x}
        y={y}
        width={w}
        height={h}
        opacity={watermark.opacity}
        listening={false}
      />
    );
  }

  return null;
}
