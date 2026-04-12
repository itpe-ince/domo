"use client";

import { useCallback, useSyncExternalStore } from "react";

const STORAGE_KEY = "domo-recent-searches";
const MAX_ITEMS = 10;
const EMPTY: string[] = [];

let listeners: Array<() => void> = [];
let cachedSnapshot: string[] = EMPTY;

function emitChange() {
  cachedSnapshot = readStorage();
  listeners.forEach((fn) => fn());
}

function readStorage(): string[] {
  if (typeof window === "undefined") return EMPTY;
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return EMPTY;
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : EMPTY;
  } catch {
    return EMPTY;
  }
}

function getSnapshot(): string[] {
  return cachedSnapshot;
}

function getServerSnapshot(): string[] {
  return EMPTY;
}

function save(items: string[]) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(items));
  emitChange();
}

function subscribe(listener: () => void) {
  // Initialize cache on first subscribe
  if (cachedSnapshot === EMPTY && typeof window !== "undefined") {
    cachedSnapshot = readStorage();
  }
  listeners.push(listener);
  return () => {
    listeners = listeners.filter((l) => l !== listener);
  };
}

export function useRecentSearches() {
  const items = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);

  const add = useCallback((q: string) => {
    const trimmed = q.trim();
    if (!trimmed) return;
    const current = readStorage().filter((x) => x !== trimmed);
    save([trimmed, ...current].slice(0, MAX_ITEMS));
  }, []);

  const remove = useCallback((q: string) => {
    save(readStorage().filter((x) => x !== q));
  }, []);

  const clear = useCallback(() => {
    save([]);
  }, []);

  return { items, add, remove, clear };
}
