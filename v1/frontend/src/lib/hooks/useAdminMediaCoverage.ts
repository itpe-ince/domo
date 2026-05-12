"use client";

/**
 * useAdminMediaCoverage — C-4 media-coverage-cms
 *
 * Hook for admin to manage media coverage entries (articles, YouTube, radio, etc.)
 * Wraps adminListMediaCoverage, adminCreateMediaCoverage,
 * adminPatchMediaCoverage, adminDeleteMediaCoverage.
 */

import { useCallback, useEffect, useState } from "react";
import {
  MediaCoverageOut,
  AdminCreateMediaCoverageBody,
  AdminPatchMediaCoverageBody,
  adminCreateMediaCoverage,
  adminDeleteMediaCoverage,
  adminListMediaCoverage,
  adminPatchMediaCoverage,
} from "@/lib/api";

export type AdminMediaCoverageState = {
  entries: MediaCoverageOut[];
  loading: boolean;
  error: string | null;
  saving: boolean;
  saveError: string | null;
  nextCursor: string | null;
  hasMore: boolean;
  create: (body: AdminCreateMediaCoverageBody) => Promise<boolean>;
  patch: (id: string, body: AdminPatchMediaCoverageBody) => Promise<boolean>;
  remove: (id: string) => Promise<boolean>;
  togglePublish: (id: string, current: boolean) => Promise<boolean>;
  reload: () => void;
  loadMore: () => void;
};

export function useAdminMediaCoverage(
  opts?: { type?: string; locale?: string; limit?: number }
): AdminMediaCoverageState {
  const [entries, setEntries] = useState<MediaCoverageOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [nextCursor, setNextCursor] = useState<string | null>(null);

  const limit = opts?.limit ?? 20;

  const load = useCallback(
    async (cursor?: string) => {
      if (!cursor) setLoading(true);
      setError(null);
      try {
        const res = await adminListMediaCoverage({
          type: opts?.type,
          locale: opts?.locale,
          limit,
          cursor,
        });
        const items = res.data ?? [];
        if (cursor) {
          setEntries((prev) => [...prev, ...items]);
        } else {
          setEntries(items);
        }
        setNextCursor(res.next_cursor);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to load");
      } finally {
        setLoading(false);
      }
    },
    [opts?.type, opts?.locale, limit]
  );

  useEffect(() => {
    void load();
  }, [load]);

  const create = useCallback(
    async (body: AdminCreateMediaCoverageBody): Promise<boolean> => {
      setSaving(true);
      setSaveError(null);
      try {
        const created = await adminCreateMediaCoverage(body);
        setEntries((prev) => [created, ...prev]);
        return true;
      } catch (e) {
        setSaveError(e instanceof Error ? e.message : "Failed to create");
        return false;
      } finally {
        setSaving(false);
      }
    },
    []
  );

  const patch = useCallback(
    async (id: string, body: AdminPatchMediaCoverageBody): Promise<boolean> => {
      setSaving(true);
      setSaveError(null);
      try {
        const updated = await adminPatchMediaCoverage(id, body);
        setEntries((prev) => prev.map((e) => (e.id === id ? updated : e)));
        return true;
      } catch (e) {
        setSaveError(e instanceof Error ? e.message : "Failed to update");
        return false;
      } finally {
        setSaving(false);
      }
    },
    []
  );

  const remove = useCallback(async (id: string): Promise<boolean> => {
    try {
      await adminDeleteMediaCoverage(id);
      setEntries((prev) => prev.filter((e) => e.id !== id));
      return true;
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to delete");
      return false;
    }
  }, []);

  const togglePublish = useCallback(
    async (id: string, current: boolean): Promise<boolean> => {
      return patch(id, { is_published: !current });
    },
    [patch]
  );

  const loadMore = useCallback(() => {
    if (nextCursor) {
      void load(nextCursor);
    }
  }, [nextCursor, load]);

  return {
    entries,
    loading,
    error,
    saving,
    saveError,
    nextCursor,
    hasMore: nextCursor !== null,
    create,
    patch,
    remove,
    togglePublish,
    reload: () => void load(),
    loadMore,
  };
}
