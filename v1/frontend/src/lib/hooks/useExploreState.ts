"use client";

/**
 * useExploreState — A-4 Explore Revamp
 *
 * Manages tab + filter state for the Explore page.
 * - URL query param sync (?tab=trending&region=SEA&genre=digital)
 * - localStorage persistence for last-visited tab
 * - captureEvent integration for tab changes
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams, usePathname } from "next/navigation";
import { captureEvent } from "@/lib/analytics/capture";

export type ExploreTab = "trending" | "new" | "region" | "genre" | "pricing";

const LS_KEY = "explore_last_tab";
const DEFAULT_TAB: ExploreTab = "trending";

function readFromStorage(): ExploreTab | null {
  if (typeof window === "undefined") return null;
  try {
    const v = localStorage.getItem(LS_KEY);
    if (
      v === "trending" ||
      v === "new" ||
      v === "region" ||
      v === "genre" ||
      v === "pricing"
    ) {
      return v;
    }
  } catch {
    // ignore
  }
  return null;
}

function writeToStorage(tab: ExploreTab) {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(LS_KEY, tab);
  } catch {
    // ignore
  }
}

export interface ExploreFilters {
  region: string;
  genre: string;
}

export interface UseExploreStateResult {
  tab: ExploreTab;
  filters: ExploreFilters;
  setTab: (tab: ExploreTab) => void;
  setRegion: (region: string) => void;
  setGenre: (genre: string) => void;
}

export function useExploreState(): UseExploreStateResult {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  // Derive initial tab from URL → localStorage → default
  const initialTab = ((): ExploreTab => {
    const fromUrl = searchParams.get("tab");
    if (
      fromUrl === "trending" ||
      fromUrl === "new" ||
      fromUrl === "region" ||
      fromUrl === "genre" ||
      fromUrl === "pricing"
    ) {
      return fromUrl;
    }
    return readFromStorage() ?? DEFAULT_TAB;
  })();

  const initialRegion = searchParams.get("region") ?? "";
  const initialGenre = searchParams.get("genre") ?? "";

  const [tab, setTabState] = useState<ExploreTab>(initialTab);
  const [filters, setFiltersState] = useState<ExploreFilters>({
    region: initialRegion,
    genre: initialGenre,
  });

  // Track if this is the initial mount to avoid double-firing captureEvent
  const mounted = useRef(false);

  // Sync URL when state changes
  const syncUrl = useCallback(
    (newTab: ExploreTab, newFilters: ExploreFilters) => {
      const params = new URLSearchParams();
      params.set("tab", newTab);
      if (newFilters.region) params.set("region", newFilters.region);
      if (newFilters.genre) params.set("genre", newFilters.genre);
      router.replace(`${pathname}?${params.toString()}`, { scroll: false });
    },
    [router, pathname]
  );

  // On first mount — if no tab in URL but we restored from localStorage, sync URL
  useEffect(() => {
    if (!mounted.current) {
      mounted.current = true;
      const fromUrl = searchParams.get("tab");
      if (!fromUrl) {
        syncUrl(tab, filters);
      }
      captureEvent({ type: "explore_view", tab });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const setTab = useCallback(
    (newTab: ExploreTab) => {
      setTabState(newTab);
      writeToStorage(newTab);
      // Reset filters that don't apply to the new tab
      const newFilters: ExploreFilters =
        newTab === "region"
          ? { region: filters.region, genre: "" }
          : newTab === "genre"
          ? { region: "", genre: filters.genre }
          : { region: "", genre: "" };
      setFiltersState(newFilters);
      syncUrl(newTab, newFilters);
      captureEvent({ type: "explore_view", tab: newTab });
    },
    [filters, syncUrl]
  );

  const setRegion = useCallback(
    (region: string) => {
      const newFilters = { ...filters, region };
      setFiltersState(newFilters);
      syncUrl(tab, newFilters);
    },
    [filters, tab, syncUrl]
  );

  const setGenre = useCallback(
    (genre: string) => {
      const newFilters = { ...filters, genre };
      setFiltersState(newFilters);
      syncUrl(tab, newFilters);
    },
    [filters, tab, syncUrl]
  );

  return { tab, filters, setTab, setRegion, setGenre };
}
