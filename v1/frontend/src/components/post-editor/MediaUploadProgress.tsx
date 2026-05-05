"use client";

/**
 * MediaUploadProgress — editor-media-ux PDCA #4 (Step 4).
 *
 * Compact status area rendered just inside MediaPreviewList (above the grid).
 * Reads the queue from `useMediaUploadQueue` and shows a live "{done}/{total}
 * uploading" label. Self-hides when the queue is empty AND no completion
 * banner is pending.
 *
 * upload-retry-ui (D-2): Each error task is rendered as an inline row with
 * a human-readable, HTTP-status-aware error message plus Retry and Cancel
 * action buttons. Active (pending|uploading) tasks show a Cancel (X) button.
 *
 * Behavior:
 *   - while uploading: pulsing dot + counter + per-task cancel buttons
 *   - all success: "Upload complete" for 2s, then disappears
 *   - any failure: persistent per-task error rows with retry + cancel buttons
 *
 * Aria-live="polite" so screen readers announce status changes without
 * interrupting the user.
 */
import { useEffect, useState } from "react";

import { useI18n } from "@/i18n";
import { RefreshIcon, XCircleIcon } from "@/components/icons";
import type { UploadTask } from "@/lib/hooks/useMediaUploadQueue";

export interface MediaUploadProgressProps {
  queue: UploadTask[];
  onRetry?: (taskId: string) => void;
  onCancel?: (taskId: string) => void;
}

/** Map HTTP status / error code to an i18n key under post.editor.media.error.* */
function errorI18nKey(task: UploadTask): string {
  const code = task.error ?? "";
  const status = task.errorHttpStatus;

  if (code === "UPLOAD_CANCELLED") return "post.editor.media.error.cancelled";
  if (status === 413) return "post.editor.media.error.tooLarge";
  if (status === 415) return "post.editor.media.error.unsupportedType";
  if (status === 401 || status === 403) return "post.editor.media.error.authExpired";
  if (status === 429) return "post.editor.media.error.rateLimit";
  if (status !== undefined && status >= 500) return "post.editor.media.error.serverError";
  if (code === "NETWORK_ERROR") return "post.editor.media.error.networkError";
  return "post.editor.media.error.unknown";
}

export function MediaUploadProgress({
  queue,
  onRetry,
  onCancel,
}: MediaUploadProgressProps) {
  const { t } = useI18n();

  const total = queue.length;
  const done = queue.filter((t) => t.status === "success").length;
  const failed = queue.filter((t) => t.status === "error").length;
  const uploading = queue.filter(
    (t) => t.status === "uploading" || t.status === "queued"
  ).length;
  const activeTasks = queue.filter(
    (t) => t.status === "uploading" || t.status === "queued"
  );
  const errorTasks = queue.filter((t) => t.status === "error");

  const allSuccess = total > 0 && done === total && failed === 0;

  // Show "Upload complete" badge for 2 seconds after the last success
  const [showComplete, setShowComplete] = useState(false);
  useEffect(() => {
    if (!allSuccess) return;
    setShowComplete(true);
    const handle = setTimeout(() => setShowComplete(false), 2000);
    return () => clearTimeout(handle);
  }, [allSuccess]);

  // Render nothing if there's nothing to show
  if (total === 0) return null;
  if (uploading === 0 && failed === 0 && !showComplete) return null;

  return (
    <div
      role="status"
      aria-live="polite"
      className="flex flex-col gap-1.5 w-full"
    >
      {/* ── overall progress pill ── */}
      {(uploading > 0 || showComplete) && (
        <div className="flex items-center gap-2 text-xs bg-surface rounded-full px-3 py-1.5 w-fit">
          {uploading > 0 && (
            <>
              <span className="w-2 h-2 rounded-full bg-primary animate-pulse" />
              <span className="text-text-secondary">
                {t("post.editor.media.upload.progress", {
                  done: String(done),
                  total: String(total),
                })}
              </span>
            </>
          )}
          {uploading === 0 && showComplete && failed === 0 && (
            <>
              <span className="w-2 h-2 rounded-full bg-primary" />
              <span className="text-text-secondary">
                {t("post.editor.media.upload.complete")}
              </span>
            </>
          )}
        </div>
      )}

      {/* ── active task cancel buttons ── */}
      {activeTasks.map((task) => (
        <div
          key={task.id}
          className="flex items-center justify-between gap-2 text-xs bg-surface rounded-lg px-3 py-1.5"
        >
          <div className="flex items-center gap-2 min-w-0">
            <span className="w-2 h-2 rounded-full bg-primary animate-pulse flex-shrink-0" />
            <span className="text-text-secondary truncate">{task.file.name}</span>
            <span className="text-text-muted flex-shrink-0">
              {task.progress > 0 ? `${task.progress}%` : "…"}
            </span>
          </div>
          {onCancel && (
            <button
              type="button"
              onClick={() => onCancel(task.id)}
              aria-label={t("post.editor.media.cancel.button")}
              className="text-text-muted hover:text-danger flex-shrink-0 transition-colors"
            >
              <XCircleIcon size={14} />
            </button>
          )}
        </div>
      ))}

      {/* ── per-error rows ── */}
      {errorTasks.map((task) => (
        <div
          key={task.id}
          className="flex items-center justify-between gap-2 text-xs bg-danger/10 border border-danger/20 rounded-lg px-3 py-1.5"
        >
          <div className="flex items-center gap-2 min-w-0">
            <span className="w-2 h-2 rounded-full bg-danger flex-shrink-0" />
            <span className="text-text-secondary truncate">{task.file.name}</span>
            <span className="text-danger flex-shrink-0">
              {t(errorI18nKey(task))}
            </span>
          </div>
          <div className="flex items-center gap-1.5 flex-shrink-0">
            {/* cancelled tasks can also be retried */}
            {onRetry && (
              <button
                type="button"
                onClick={() => onRetry(task.id)}
                aria-label={t("post.editor.media.retry.button")}
                className="flex items-center gap-1 text-primary hover:text-primary/80 transition-colors"
              >
                <RefreshIcon size={12} />
                <span>{t("post.editor.media.retry.button")}</span>
              </button>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
