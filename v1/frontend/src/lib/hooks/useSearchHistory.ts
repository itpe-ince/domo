"use client";

/**
 * useSearchHistory — A-5 search-enhancement
 *
 * Fetches server-side search history for authenticated users.
 * Falls back gracefully to empty state when unauthenticated.
 */
import { useCallback, useEffect, useState } from "react";
import {
  clearSearchHistory,
  deleteSearchHistoryEntry,
  fetchPopularSearches,
  fetchSearchHistory,
  type PopularSearchItem,
  type SearchHistoryEntry,
} from "@/lib/api";
import { useMe } from "@/lib/useMe";

export function useSearchHistory(limit = 10) {
  const { me: user } = useMe();
  const [history, setHistory] = useState<SearchHistoryEntry[]>([]);
  const [popular, setPopular] = useState<PopularSearchItem[]>([]);
  const [loading, setLoading] = useState(false);

  const loadHistory = useCallback(async () => {
    if (!user) {
      setHistory([]);
      return;
    }
    try {
      const data = await fetchSearchHistory(limit);
      setHistory(data);
    } catch {
      // Non-blocking — ignore errors (e.g. 401 token expiry)
    }
  }, [user, limit]);

  const loadPopular = useCallback(async () => {
    try {
      const data = await fetchPopularSearches(10);
      setPopular(data);
    } catch {
      // Fallback to empty — popular searches are non-critical
    }
  }, []);

  useEffect(() => {
    setLoading(true);
    Promise.all([loadHistory(), loadPopular()]).finally(() =>
      setLoading(false)
    );
  }, [loadHistory, loadPopular]);

  const removeEntry = useCallback(
    async (id: string) => {
      try {
        await deleteSearchHistoryEntry(id);
        setHistory((prev) => prev.filter((e) => e.id !== id));
      } catch {
        // Silently fail — UI already reflects intent
      }
    },
    []
  );

  const clearAll = useCallback(async () => {
    try {
      await clearSearchHistory();
      setHistory([]);
    } catch {
      // Silently fail
    }
  }, []);

  return { history, popular, loading, removeEntry, clearAll, reload: loadHistory };
}
