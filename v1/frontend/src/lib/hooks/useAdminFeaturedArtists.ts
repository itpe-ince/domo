"use client";

/**
 * useAdminFeaturedArtists — G'-7 admin-featured-artists
 *
 * Hook for admin to manage the monthly featured artist curations.
 * Wraps adminListFeaturedArtists, adminCreateFeaturedArtist, adminDeleteFeaturedArtist.
 */

import { useCallback, useEffect, useState } from "react";
import {
  FeaturedArtistOut,
  adminCreateFeaturedArtist,
  adminDeleteFeaturedArtist,
  adminListFeaturedArtists,
} from "@/lib/api";

export type AdminFeaturedArtistsState = {
  entries: FeaturedArtistOut[];
  loading: boolean;
  error: string | null;
  creating: boolean;
  createError: string | null;
  create: (params: {
    artist_id: string;
    month: string;
    curation_note?: string;
  }) => Promise<boolean>;
  deactivate: (id: string) => Promise<boolean>;
  reload: () => void;
};

export function useAdminFeaturedArtists(
  opts?: { limit?: number }
): AdminFeaturedArtistsState {
  const [entries, setEntries] = useState<FeaturedArtistOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await adminListFeaturedArtists({ limit: opts?.limit ?? 12 });
      setEntries(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }, [opts?.limit]);

  useEffect(() => {
    void load();
  }, [load]);

  const create = useCallback(
    async (params: {
      artist_id: string;
      month: string;
      curation_note?: string;
    }): Promise<boolean> => {
      setCreating(true);
      setCreateError(null);
      try {
        const newEntry = await adminCreateFeaturedArtist(params);
        setEntries((prev) => {
          // Deactivate any existing active entry for the same month in local state
          const updated = prev.map((e) =>
            e.month.startsWith(params.month.substring(0, 7)) && e.is_active
              ? { ...e, is_active: false }
              : e
          );
          return [newEntry, ...updated];
        });
        return true;
      } catch (e) {
        setCreateError(e instanceof Error ? e.message : "Failed to create");
        return false;
      } finally {
        setCreating(false);
      }
    },
    []
  );

  const deactivate = useCallback(async (id: string): Promise<boolean> => {
    try {
      await adminDeleteFeaturedArtist(id);
      setEntries((prev) =>
        prev.map((e) => (e.id === id ? { ...e, is_active: false } : e))
      );
      return true;
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to deactivate");
      return false;
    }
  }, []);

  return {
    entries,
    loading,
    error,
    creating,
    createError,
    create,
    deactivate,
    reload: load,
  };
}
