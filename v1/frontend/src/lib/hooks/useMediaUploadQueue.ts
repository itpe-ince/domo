"use client";

/**
 * useMediaUploadQueue — editor-media-ux PDCA #4 (Step 4).
 *
 * Parallel upload queue with real-time per-file progress (OQ-2 = B,
 * OQ-D-3 = B). Each call to `enqueue()` adds files to the queue and
 * launches them concurrently via `Promise.allSettled` + the XHR-based
 * `uploadMediaFileWithProgress()` from api.ts.
 *
 * Returns:
 *   - queue: live UploadTask[] for MediaUploadProgress + per-card overlays
 *   - enqueue(files, isMakingVideo): Promise<CreatePostMedia[]> — resolves
 *     to successful uploads only; failed tasks remain in the queue with
 *     status='error' so the UI can surface them
 *   - enqueueGif: same flow for a single GIF file
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
  result?: UploadedMedia;
}

export interface UseMediaUploadQueueReturn {
  queue: UploadTask[];
  enqueue: (
    files: FileList | File[],
    isMakingVideo?: boolean
  ) => Promise<CreatePostMedia[]>;
  enqueueGif: (file: File) => Promise<CreatePostMedia | null>;
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

export function useMediaUploadQueue(): UseMediaUploadQueueReturn {
  const [queue, setQueue] = useState<UploadTask[]>([]);
  // Latest setQueue ref so updateTask can be a stable callback.
  const setQueueRef = useRef(setQueue);
  setQueueRef.current = setQueue;

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
        newTasks.map(async (task) => {
          updateTask(task.id, { status: "uploading", progress: 0 });
          try {
            const uploaded = await uploadMediaFileWithProgress(
              task.file,
              isMakingVideo,
              (e) => updateTask(task.id, { progress: e.percent })
            );
            updateTask(task.id, {
              status: "success",
              progress: 100,
              result: uploaded,
            });
            return uploadedToCreate(uploaded, task.id);
          } catch (err) {
            const msg =
              err instanceof ApiClientError
                ? err.message
                : err instanceof Error
                  ? err.message
                  : "업로드 실패";
            updateTask(task.id, { status: "error", error: msg });
            throw err;
          }
        })
      );

      return results
        .filter(
          (r): r is PromiseFulfilledResult<CreatePostMedia> =>
            r.status === "fulfilled"
        )
        .map((r) => r.value);
    },
    [updateTask]
  );

  const enqueueGif = useCallback(
    async (file: File): Promise<CreatePostMedia | null> => {
      const [created] = await enqueue([file], false);
      return created ?? null;
    },
    [enqueue]
  );

  const clearCompleted = useCallback(() => {
    setQueue((prev) =>
      prev.filter((t) => t.status !== "success" && t.status !== "error")
    );
  }, []);

  const isUploading = useMemo(
    () => queue.some((t) => t.status === "uploading" || t.status === "queued"),
    [queue]
  );

  return { queue, enqueue, enqueueGif, clearCompleted, isUploading };
}
