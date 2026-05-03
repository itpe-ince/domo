"use client";

import { useI18n } from "@/i18n";

interface RotateToolProps {
  rotation: 0 | 90 | 180 | 270;
  setRotation: (r: 0 | 90 | 180 | 270) => void;
}

export function RotateTool({ rotation, setRotation }: RotateToolProps) {
  const { t } = useI18n();

  const next = (delta: 90 | 180 | 270): 0 | 90 | 180 | 270 =>
    (((rotation + delta) % 360) as 0 | 90 | 180 | 270);

  return (
    <div
      className="flex items-center gap-2 bg-surface/95 px-3 py-2 rounded shadow-lg"
      role="toolbar"
      aria-label={t("post.editor.media.studio.image.tool.rotate.label")}
    >
      <button
        type="button"
        onClick={() => setRotation(next(90))}
        className="px-3 py-1 text-sm rounded hover:bg-surface-hover transition-colors"
      >
        {t("post.editor.media.studio.image.tool.rotate.90")}
      </button>
      <button
        type="button"
        onClick={() => setRotation(next(180))}
        className="px-3 py-1 text-sm rounded hover:bg-surface-hover transition-colors"
      >
        {t("post.editor.media.studio.image.tool.rotate.180")}
      </button>
      <button
        type="button"
        onClick={() => setRotation(next(270))}
        className="px-3 py-1 text-sm rounded hover:bg-surface-hover transition-colors"
      >
        {t("post.editor.media.studio.image.tool.rotate.270")}
      </button>
      <span className="text-xs text-text-muted ml-2 tabular-nums">
        {t("post.editor.media.studio.image.tool.rotate.current")}: {rotation}°
      </span>
    </div>
  );
}
