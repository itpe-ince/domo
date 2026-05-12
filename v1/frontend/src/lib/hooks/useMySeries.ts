"use client";

/**
 * useMySeries — publish-controls PDCA #8.
 *
 * Fetches the current user's series list and exposes optimistic CRUD helpers.
 * Mirror pattern from useSignature.ts: useCallback refresh + optimistic remove
 * with rollback on error.
 */
import { useState, useEffect, useCallback } from "react";
import {
  listMySeries,
  deleteSeries,
  type Series,
  type SeriesCreate,
  type SeriesPatch,
} from "@/lib/api";

// Re-export for consumers that import from this module
export type { Series, SeriesCreate, SeriesPatch };

export interface UseMySeriesReturn {
  series: Series[];
  loading: boolean;
  error: string | null;
  mutating: boolean;
  /** Optimistically prepend a newly created series (call after createSeries succeeds). */
  add: (s: Series) => void;
  /** Optimistically patch a series in the local list (call after patchSeries succeeds). */
  update: (id: string, patch: Partial<Series>) => void;
  /** Optimistically remove a series and DELETE from server; rolls back on error. */
  remove: (id: string) => Promise<void>;
  /** Re-fetch from server. */
  refresh: () => Promise<void>;
}

export function useMySeries(): UseMySeriesReturn {
  const [series, setSeries] = useState<Series[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [mutating, setMutating] = useState(false);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await listMySeries();
      setSeries(data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "fetch_failed");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  function add(s: Series): void {
    setSeries((prev) => [s, ...prev]);
  }

  function update(id: string, patch: Partial<Series>): void {
    setSeries((prev) =>
      prev.map((s) => (s.id === id ? { ...s, ...patch } : s))
    );
  }

  async function remove(id: string): Promise<void> {
    const snapshot = series;
    // Optimistic remove
    setSeries((prev) => prev.filter((s) => s.id !== id));
    setMutating(true);
    try {
      await deleteSeries(id);
    } catch (e) {
      // Roll back
      setSeries(snapshot);
      throw e;
    } finally {
      setMutating(false);
    }
  }

  return { series, loading, error, mutating, add, update, remove, refresh };
}
