"use client";

/**
 * SortableMediaCard — editor-media-ux PDCA #4 (Step 4).
 *
 * One media item rendered inside `SortableContext`. Drag listeners are
 * attached ONLY to the explicit `<button>` drag handle (never the card
 * container) so the caption textarea below receives keyboard events
 * (Space, Arrow keys) without being intercepted by dnd-kit.
 *
 * Visual states:
 *   - default: 1.0 opacity, image/video/external preview
 *   - dragging: 0.5 opacity, z-50
 *   - uploading: black/40 overlay with progress bar (OQ-D-3 = B real %)
 *   - error: red border + error message overlay
 *
 * Accessibility:
 *   - Drag handle = `<button>` with dnd-kit attributes (role/tabindex/aria-*)
 *   - Card container exposes `aria-label="{index}번째 미디어"` for SR context
 *   - prefers-reduced-motion suppresses the transform transition
 */
import { useEffect, useState } from "react";
import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";

import { useI18n } from "@/i18n";
import type { CreatePostMedia } from "@/lib/api";
import { DragHandleIcon } from "@/components/icons";
import type { UploadTask } from "@/lib/hooks/useMediaUploadQueue";

export interface SortableMediaCardProps {
  /** dnd-kit identifier — equals CreatePostMedia._clientId */
  id: string;
  media: CreatePostMedia;
  /** 1-based for human-friendly aria-label */
  index: number;
  /** Optional progress task (omitted once upload is success) */
  uploadTask?: UploadTask;
  onRemove: (id: string) => void;
  onCaptionChange: (id: string, caption: string) => void;
}

const CAPTION_MAX = 280;
const CAPTION_SOFT_CAP = CAPTION_MAX + 50;

export function SortableMediaCard({
  id,
  media,
  index,
  uploadTask,
  onRemove,
  onCaptionChange,
}: SortableMediaCardProps) {
  const { t } = useI18n();
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id });

  // Respect OS-level reduced-motion preference for the transform tween
  const [reduceMotion, setReduceMotion] = useState(false);
  useEffect(() => {
    if (typeof window === "undefined") return;
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    setReduceMotion(mq.matches);
    const handler = () => setReduceMotion(mq.matches);
    mq.addEventListener?.("change", handler);
    return () => mq.removeEventListener?.("change", handler);
  }, []);

  const style: React.CSSProperties = {
    transform: CSS.Transform.toString(transform),
    transition: reduceMotion ? undefined : transition,
    opacity: isDragging ? 0.5 : 1,
    zIndex: isDragging ? 50 : "auto",
  };

  const captionValue = media.caption ?? "";
  const remaining = CAPTION_MAX - captionValue.length;
  const isOverLimit = remaining < 0;
  const captionInputId = `media-caption-${id}`;

  const isUploading = uploadTask?.status === "uploading" || uploadTask?.status === "queued";
  const isError = uploadTask?.status === "error";

  return (
    <div
      ref={setNodeRef}
      style={style}
      className="flex flex-col gap-1.5"
      aria-label={t("post.editor.media.reorder.aria", { index: String(index + 1) })}
    >
      <div
        className={`relative group aspect-square rounded-lg overflow-hidden bg-surface-hover ${
          isError ? "ring-2 ring-danger" : ""
        }`}
      >
        {/* Drag handle — listeners ONLY here */}
        <button
          type="button"
          {...attributes}
          {...listeners}
          aria-label={t("post.editor.media.dragHandle.aria")}
          className="absolute top-1 left-1 z-20 p-1 bg-black/50 hover:bg-black/70 rounded text-white cursor-grab active:cursor-grabbing transition-colors"
        >
          <DragHandleIcon size={14} />
        </button>

        {/* Media preview */}
        {media.type === "image" ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={media.url}
            alt=""
            className="w-full h-full object-cover"
          />
        ) : media.type === "video" ? (
          <div className="w-full h-full flex items-center justify-center">
            <video src={media.url} className="w-full h-full object-cover" muted />
            <span className="absolute inset-0 flex items-center justify-center text-3xl text-white/80">
              ▶
            </span>
          </div>
        ) : (
          <div className="w-full h-full flex items-center justify-center text-text-muted text-xs p-2">
            {media.external_source || media.type}
          </div>
        )}

        {/* Remove button (top-right) */}
        <button
          type="button"
          onClick={() => onRemove(id)}
          aria-label={t("post.editor.media.remove.aria")}
          className="absolute top-1 right-1 z-20 bg-black/60 hover:bg-black/80 text-white rounded-full w-6 h-6 flex items-center justify-center text-xs opacity-0 group-hover:opacity-100 focus:opacity-100 transition-opacity"
        >
          ✕
        </button>

        {/* Making badge (bottom-left) */}
        {media.is_making_video && (
          <span className="absolute bottom-1 left-1 z-10 bg-primary text-background text-[10px] px-1.5 py-0.5 rounded">
            메이킹
          </span>
        )}

        {/* Upload progress overlay */}
        {isUploading && uploadTask && (
          <div className="absolute inset-0 z-10 bg-black/40 flex flex-col items-center justify-center gap-1.5 pointer-events-none">
            <div className="w-3/4 h-1 bg-white/30 rounded-full overflow-hidden">
              <div
                className="h-full bg-primary"
                style={{ width: `${Math.min(100, Math.max(0, uploadTask.progress))}%` }}
              />
            </div>
            <span className="text-[10px] text-white tabular-nums">
              {uploadTask.progress}%
            </span>
          </div>
        )}

        {/* Error overlay */}
        {isError && uploadTask && (
          <div className="absolute inset-0 z-10 bg-danger/40 flex items-center justify-center text-[11px] text-white text-center px-2">
            {uploadTask.error ?? t("post.editor.media.upload.failed", { n: "1" })}
          </div>
        )}
      </div>

      {/* Caption — visually-hidden label + counter */}
      <label htmlFor={captionInputId} className="sr-only">
        {t("post.editor.media.caption.label")}
      </label>
      <textarea
        id={captionInputId}
        value={captionValue}
        onChange={(e) => onCaptionChange(id, e.target.value)}
        placeholder={t("post.editor.media.caption.placeholder")}
        rows={2}
        maxLength={CAPTION_SOFT_CAP}
        className={`w-full text-xs text-text-primary placeholder:text-text-muted bg-transparent resize-y outline-none border rounded px-2 py-1 ${
          isOverLimit ? "border-danger" : "border-border"
        }`}
      />
      <p
        className={`text-right text-[10px] tabular-nums ${
          isOverLimit ? "text-danger" : "text-text-muted"
        }`}
      >
        {remaining}/{CAPTION_MAX}
      </p>
      {isOverLimit && (
        <p className="text-[10px] text-danger">
          {t("post.editor.media.caption.tooLong")}
        </p>
      )}
    </div>
  );
}
