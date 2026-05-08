/**
 * useConversations — polling-based DM conversation list hook.
 *
 * B'-2 dm-messaging: No WebSocket yet (Phase 9+). Polls every 10 seconds
 * when the window is visible to keep the list reasonably fresh.
 */
"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  ConversationView,
  listConversations,
} from "@/lib/api";

const POLL_INTERVAL_MS = 10_000; // 10 seconds

interface UseConversationsReturn {
  conversations: ConversationView[];
  loading: boolean;
  error: string | null;
  refresh: () => void;
  loadMore: () => void;
  hasMore: boolean;
}

export function useConversations(): UseConversationsReturn {
  const [conversations, setConversations] = useState<ConversationView[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [cursor, setCursor] = useState<string | null>(null);
  const [hasMore, setHasMore] = useState(false);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const mountedRef = useRef(true);

  const fetchFirst = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await listConversations(null, 20);
      if (!mountedRef.current) return;
      setConversations(resp.data ?? []);
      setCursor(resp.next_cursor ?? null);
      setHasMore((resp.next_cursor ?? null) !== null);
    } catch (e) {
      if (!mountedRef.current) return;
      setError(e instanceof Error ? e.message : "Failed to load conversations");
    } finally {
      if (mountedRef.current) setLoading(false);
    }
  }, []);

  const refresh = useCallback(() => {
    void fetchFirst();
  }, [fetchFirst]);

  const loadMore = useCallback(async () => {
    if (!cursor || !hasMore) return;
    try {
      const resp = await listConversations(cursor, 20);
      if (!mountedRef.current) return;
      setConversations((prev) => {
        const ids = new Set(prev.map((c) => c.id));
        const newItems = (resp.data ?? []).filter((c) => !ids.has(c.id));
        return [...prev, ...newItems];
      });
      setCursor(resp.next_cursor ?? null);
      setHasMore((resp.next_cursor ?? null) !== null);
    } catch {
      // Ignore pagination errors silently
    }
  }, [cursor, hasMore]);

  // Initial load
  useEffect(() => {
    mountedRef.current = true;
    void fetchFirst();
    return () => {
      mountedRef.current = false;
    };
  }, [fetchFirst]);

  // Polling: refresh first page when window is visible
  useEffect(() => {
    function startPoll() {
      timerRef.current = setInterval(() => {
        if (document.visibilityState === "visible") {
          void fetchFirst();
        }
      }, POLL_INTERVAL_MS);
    }

    function handleVisibility() {
      if (document.visibilityState === "visible") {
        // Immediate refresh on tab focus
        void fetchFirst();
      }
    }

    startPoll();
    document.addEventListener("visibilitychange", handleVisibility);
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
      document.removeEventListener("visibilitychange", handleVisibility);
    };
  }, [fetchFirst]);

  return { conversations, loading, error, refresh, loadMore, hasMore };
}
