"use client";

/**
 * usePatronageDashboard — data fetching + state for artist patronage dashboard.
 *
 * Provides:
 *   - summary (PatronageSummary)
 *   - supporters (SupporterItem[] with cursor pagination)
 *   - revenue (RevenueDataPoint[] with granularity toggle)
 *   - supporter filter state
 */

import { useCallback, useEffect, useRef, useState } from "react";
import {
  fetchPatronageSummary,
  fetchSupporters,
  fetchPatronageRevenue,
  type PatronageSummary,
  type SupporterItem,
  type RevenueDataPoint,
  type SupportersResponse,
} from "@/lib/api";

// ─── Summary ─────────────────────────────────────────────────────────────────

export function usePatronageSummary() {
  const [summary, setSummary] = useState<PatronageSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    fetchPatronageSummary()
      .then((data) => {
        if (!cancelled) setSummary(data);
      })
      .catch((e) => {
        if (!cancelled)
          setError(e?.message ?? "Failed to load summary");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return { summary, loading, error };
}

// ─── Revenue ─────────────────────────────────────────────────────────────────

export type RevenueGranularity = "daily" | "monthly";

export function usePatronageRevenue(granularity: RevenueGranularity = "daily") {
  const [data, setData] = useState<RevenueDataPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    const now = new Date();
    const to = now.toISOString().slice(0, 10);
    let from: string;
    if (granularity === "daily") {
      const d = new Date(now);
      d.setDate(d.getDate() - 29);
      from = d.toISOString().slice(0, 10);
    } else {
      const d = new Date(now);
      d.setMonth(d.getMonth() - 11);
      d.setDate(1);
      from = d.toISOString().slice(0, 10);
    }

    fetchPatronageRevenue({ from, to, granularity })
      .then((res) => {
        if (!cancelled) setData(res.data);
      })
      .catch((e) => {
        if (!cancelled) setError(e?.message ?? "Failed to load revenue");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [granularity]);

  return { data, loading, error };
}

// ─── Supporters ───────────────────────────────────────────────────────────────

export type SupporterFilter = "active" | "churned" | "all";

export function usePatronageSupporters(filter: SupporterFilter = "all") {
  const [supporters, setSupporters] = useState<SupporterItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasMore, setHasMore] = useState(false);
  const cursorRef = useRef<string | null>(null);

  const load = useCallback(
    async (append = false) => {
      if (append) {
        setLoadingMore(true);
      } else {
        setLoading(true);
        cursorRef.current = null;
      }
      setError(null);

      try {
        const params: Parameters<typeof fetchSupporters>[0] = {
          limit: 50,
          filter,
        };
        if (append && cursorRef.current) {
          params.cursor = cursorRef.current;
        }
        const res: SupportersResponse = await fetchSupporters(params);
        if (append) {
          setSupporters((prev) => [...prev, ...res.data]);
        } else {
          setSupporters(res.data);
        }
        setHasMore(res.has_more);
        cursorRef.current = res.next_cursor ?? null;
      } catch (e: unknown) {
        const msg =
          e != null && typeof e === "object" && "message" in e
            ? String((e as { message: unknown }).message)
            : "Failed to load supporters";
        setError(msg);
      } finally {
        setLoading(false);
        setLoadingMore(false);
      }
    },
    [filter]
  );

  useEffect(() => {
    load(false);
  }, [load]);

  const loadMore = useCallback(() => {
    if (hasMore && !loadingMore) load(true);
  }, [hasMore, loadingMore, load]);

  return { supporters, loading, loadingMore, error, hasMore, loadMore };
}
