"use client";

/**
 * MediaUploadProgress — editor-media-ux PDCA #4 (Step 4).
 *
 * Compact pill rendered just inside MediaPreviewList (above the grid). Reads
 * the queue from `useMediaUploadQueue` and shows a live "{done}/{total}
 * uploading" label. Self-hides when the queue is empty AND no completion
 * banner is pending.
 *
 * Behavior:
 *   - while uploading: pulsing dot + counter
 *   - all success: "Upload complete" for 2s, then disappears
 *   - any failure: persistent "{n} failed" message (no auto-hide; user must
 *     remove/retry the failing card)
 *
 * Aria-live="polite" so screen readers announce status changes without
 * interrupting the user.
 */
import { useEffect, useState } from "react";

import { useI18n } from "@/i18n";
import type { UploadTask } from "@/lib/hooks/useMediaUploadQueue";

export interface MediaUploadProgressProps {
  queue: UploadTask[];
}

export function MediaUploadProgress({ queue }: MediaUploadProgressProps) {
  const { t } = useI18n();

  const total = queue.length;
  const done = queue.filter((t) => t.status === "success").length;
  const failed = queue.filter((t) => t.status === "error").length;
  const uploading = queue.filter(
    (t) => t.status === "uploading" || t.status === "queued"
  ).length;

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
      className="flex items-center gap-2 text-xs bg-surface rounded-full px-3 py-1.5 w-fit"
    >
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
      {failed > 0 && (
        <span className="text-danger">
          {t("post.editor.media.upload.failed", { n: String(failed) })}
        </span>
      )}
    </div>
  );
}
