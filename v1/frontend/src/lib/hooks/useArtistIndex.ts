"use client";

import { useCallback, useEffect, useState } from "react";
import {
  ArtistIndexEntry,
  ArtistIndexListResponse,
  fetchArtistIndex,
} from "@/lib/api";

interface UseArtistIndexOptions {
  region?: string;
  genre?: string;
  limit?: number;
}

interface UseArtistIndexResult {
  entries: ArtistIndexEntry[];
  loading: boolean;
  error: string | null;
  hasMore: boolean;
  loadMore: () => void;
  reload: () => void;
}

export function useArtistIndex({
  region,
  genre,
  limit = 50,
}: UseArtistIndexOptions = {}): UseArtistIndexResult {
  const [entries, setEntries] = useState<ArtistIndexEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [cursor, setCursor] = useState<string | null>(null);
  const [hasMore, setHasMore] = useState(false);

  const load = useCallback(
    async (reset = false) => {
      setLoading(true);
      setError(null);
      try {
        const res: ArtistIndexListResponse = await fetchArtistIndex({
          region: region || undefined,
          genre: genre || undefined,
          limit,
          cursor: reset ? undefined : (cursor ?? undefined),
        });

        setEntries((prev) => (reset ? res.data : [...prev, ...res.data]));
        setCursor(res.next_cursor);
        setHasMore(res.next_cursor !== null);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to load rankings");
      } finally {
        setLoading(false);
      }
    },
    // Cursor is intentionally excluded from deps — only `region`/`genre`/`limit` drive resets
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [region, genre, limit]
  );

  // Reset + reload when filters change
  useEffect(() => {
    setCursor(null);
    void load(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [region, genre, limit]);

  const loadMore = useCallback(() => {
    if (!loading && hasMore) {
      void load(false);
    }
  }, [loading, hasMore, load]);

  const reload = useCallback(() => {
    setCursor(null);
    void load(true);
  }, [load]);

  return { entries, loading, error, hasMore, loadMore, reload };
}
