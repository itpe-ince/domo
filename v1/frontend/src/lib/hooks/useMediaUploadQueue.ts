"use client";

/**
 * useMediaUploadQueue — editor-media-ux PDCA #4 (Step 4).
 *
 * Parallel upload queue with real-time per-file progress (OQ-2 = B,
 * OQ-D-3 = B). Each call to `enqueue()` adds files to the queue and
 * launches them concurrently via `Promise.allSettled` + the XHR-based
 * `uploadMediaFileWithProgress()` from api.ts.
 *
 * upload-retry-ui (D-2):
 *   - `retryTask(taskId)` — restarts an errored/cancelled task from the
 *     beginning (progress reset to 0, status → uploading). Noop if the
 *     task is currently uploading or already succeeded.
 *   - `cancelTask(taskId)` — aborts the in-flight XHR for a pending or
 *     uploading task, transitioning it to status='error' with code
 *     UPLOAD_CANCELLED. Noop for done/error tasks.
 *   - Stable task IDs: retrying reuses the same task slot; no new entries
 *     are created, so the queue never grows unboundedly (R-FE-7 mitigation).
 *
 * Returns:
 *   - queue: live UploadTask[] for MediaUploadProgress + per-card overlays
 *   - enqueue(files, isMakingVideo): Promise<CreatePostMedia[]> — resolves
 *     to successful uploads only; failed tasks remain in the queue with
 *     status='error' so the UI can surface them
 *   - enqueueGif: same flow for a single GIF file
 *   - retryTask(taskId): restart a failed/cancelled task
 *   - cancelTask(taskId): abort an active upload
 *   - clearCompleted: remove success+error tasks from the queue
 *   - isUploading: any task currently in 'uploading' status
 */
import { useCallback, useMemo, useRef, useState } from "react";

import {
  ApiClientError,
  type CreatePostMedia,
  type UploadedMedia,
  uploadMediaFileWithProgress,
} from "@/lib/api";

export interface UploadTask {
  /** crypto.randomUUID() — also used as CreatePostMedia._clientId on success */
  id: string;
  file: File;
  status: "queued" | "uploading" | "success" | "error";
  /** 0-100 (XHR onprogress) */
  progress: number;
  error?: string;
  /** HTTP status from the server response, if available */
  errorHttpStatus?: number;
  result?: UploadedMedia;
}

export interface UseMediaUploadQueueReturn {
  queue: UploadTask[];
  enqueue: (
    files: FileList | File[],
    isMakingVideo?: boolean
  ) => Promise<CreatePostMedia[]>;
  enqueueGif: (file: File) => Promise<CreatePostMedia | null>;
  retryTask: (taskId: string) => void;
  cancelTask: (taskId: string) => void;
  clearCompleted: () => void;
  isUploading: boolean;
}

function uploadedToCreate(
  uploaded: UploadedMedia,
  clientId: string
): CreatePostMedia {
  return {
    _clientId: clientId,
    type: uploaded.type,
    url: uploaded.url,
    thumbnail_url: uploaded.thumbnail_url,
    size_bytes: uploaded.size_bytes,
    external_source: uploaded.external_source,
    external_id: uploaded.external_id,
    is_making_video: uploaded.is_making_video,
  };
}

/** Run a single upload for a given task, updating queue state throughout. */
async function runUpload(
  task: UploadTask,
  isMakingVideo: boolean,
  updateTask: (id: string, patch: Partial<UploadTask>) => void,
  registerAbort: (taskId: string, abortFn: () => void) => void,
  unregisterAbort: (taskId: string) => void
): Promise<CreatePostMedia | null> {
  updateTask(task.id, { status: "uploading", progress: 0, error: undefined, errorHttpStatus: undefined });
  try {
    const uploaded = await uploadMediaFileWithProgress(
      task.file,
      isMakingVideo,
      (e) => updateTask(task.id, { progress: e.percent }),
      (abortFn) => registerAbort(task.id, abortFn)
    );
    unregisterAbort(task.id);
    updateTask(task.id, { status: "success", progress: 100, result: uploaded });
    return uploadedToCreate(uploaded, task.id);
  } catch (err) {
    unregisterAbort(task.id);
    const msg =
      err instanceof ApiClientError
        ? err.message
        : err instanceof Error
          ? err.message
          : "업로드 실패";
    const httpStatus =
      err instanceof ApiClientError
        ? (err as ApiClientError & { httpStatus?: number }).httpStatus
        : undefined;
    updateTask(task.id, {
      status: "error",
      error: msg,
      errorHttpStatus: httpStatus,
    });
    return null;
  }
}

export function useMediaUploadQueue(): UseMediaUploadQueueReturn {
  const [queue, setQueue] = useState<UploadTask[]>([]);
  // Latest setQueue ref so updateTask can be a stable callback.
  const setQueueRef = useRef(setQueue);
  setQueueRef.current = setQueue;

  // Map from taskId → abort function, so cancelTask can reach into an
  // in-flight XHR without exposing XHR instances to the rest of the UI.
  const abortMapRef = useRef<Map<string, () => void>>(new Map());

  const registerAbort = useCallback((taskId: string, abortFn: () => void) => {
    abortMapRef.current.set(taskId, abortFn);
  }, []);

  const unregisterAbort = useCallback((taskId: string) => {
    abortMapRef.current.delete(taskId);
  }, []);

  const updateTask = useCallback((id: string, patch: Partial<UploadTask>) => {
    setQueueRef.current((prev) =>
      prev.map((t) => (t.id === id ? { ...t, ...patch } : t))
    );
  }, []);

  const enqueue = useCallback(
    async (
      files: FileList | File[],
      isMakingVideo = false
    ): Promise<CreatePostMedia[]> => {
      const fileArr = Array.from(files);
      if (fileArr.length === 0) return [];

      const newTasks: UploadTask[] = fileArr.map((file) => ({
        id: crypto.randomUUID(),
        file,
        status: "queued",
        progress: 0,
      }));
      setQueue((prev) => [...prev, ...newTasks]);

      const results = await Promise.allSettled(
        newTasks.map((task) =>
          runUpload(task, isMakingVideo, updateTask, registerAbort, unregisterAbort)
        )
      );

      return results
        .filter(
          (r): r is PromiseFulfilledResult<CreatePostMedia> =>
            r.status === "fulfilled" && r.value !== null
        )
        .map((r) => r.value as CreatePostMedia);
    },
    [updateTask, registerAbort, unregisterAbort]
  );

  const enqueueGif = useCallback(
    async (file: File): Promise<CreatePostMedia | null> => {
      const [created] = await enqueue([file], false);
      return created ?? null;
    },
    [enqueue]
  );

  /**
   * Retry a task that is in `error` state. Noop for uploading/success tasks.
   * Re-uses the same task ID so the queue slot is stable (R-FE-7).
   */
  const retryTask = useCallback(
    (taskId: string) => {
      setQueueRef.current((prev) => {
        const task = prev.find((t) => t.id === taskId);
        // Only allow retry for error tasks (covers cancelled = error).
        if (!task || task.status === "uploading" || task.status === "success") {
          return prev;
        }
        // Kick off the upload asynchronously; the queue update is handled by runUpload.
        runUpload(task, false, updateTask, registerAbort, unregisterAbort);
        return prev;
      });
    },
    [updateTask, registerAbort, unregisterAbort]
  );

  /**
   * Cancel an active (queued | uploading) task by calling xhr.abort().
   * The xhr.onabort handler transitions the task to status='error'.
   */
  const cancelTask = useCallback((taskId: string) => {
    const abortFn = abortMapRef.current.get(taskId);
    if (abortFn) {
      abortFn();
      // abortFn triggers xhr.onabort → ApiClientError("UPLOAD_CANCELLED") →
      // runUpload catch → updateTask(error). No manual state update needed here.
    } else {
      // Task is queued but XHR hasn't started yet — mark as cancelled directly.
      setQueueRef.current((prev) => {
        const task = prev.find((t) => t.id === taskId);
        if (!task || task.status === "success" || task.status === "error") {
          return prev;
        }
        return prev.map((t) =>
          t.id === taskId
            ? { ...t, status: "error", error: "업로드 취소됨" }
            : t
        );
      });
    }
  }, []);

  const clearCompleted = useCallback(() => {
    setQueue((prev) =>
      prev.filter((t) => t.status !== "success" && t.status !== "error")
    );
  }, []);

  const isUploading = useMemo(
    () => queue.some((t) => t.status === "uploading" || t.status === "queued"),
    [queue]
  );

  return { queue, enqueue, enqueueGif, retryTask, cancelTask, clearCompleted, isUploading };
}
