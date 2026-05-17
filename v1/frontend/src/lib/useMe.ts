"use client";

import { useEffect, useState } from "react";
import {
  ApiUser,
  AUTH_CHANGED_EVENT,
  fetchMe,
  tokenStore,
} from "@/lib/api";

// Safety-net ceiling (plan D): even with the apiFetch timeout, a chain
// of unexpected setState/effect interactions could in theory leave
// `loading=true` forever. After 20s we force-release so the sidebar shows
// the login button instead of an indefinite skeleton.
const LOADING_SAFETY_MS = 20_000;

/**
 * Reactive "me" hook that loads the current user from /auth/me and
 * automatically refreshes whenever tokenStore.set() / clear() fires
 * AUTH_CHANGED_EVENT, or when the localStorage key changes in another tab.
 */
export function useMe() {
  const [me, setMe] = useState<ApiUser | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    let safetyTimer: ReturnType<typeof setTimeout> | null = null;

    function armSafety() {
      if (safetyTimer) clearTimeout(safetyTimer);
      safetyTimer = setTimeout(() => {
        if (!cancelled) {
          // eslint-disable-next-line no-console
          console.warn(
            "[useMe] loading exceeded %dms — force-releasing to avoid stuck UI",
            LOADING_SAFETY_MS
          );
          setLoading(false);
        }
      }, LOADING_SAFETY_MS);
    }

    function disarmSafety() {
      if (safetyTimer) {
        clearTimeout(safetyTimer);
        safetyTimer = null;
      }
    }

    async function load() {
      if (!tokenStore.get()) {
        if (!cancelled) {
          setMe(null);
          setLoading(false);
          disarmSafety();
        }
        return;
      }
      armSafety();
      try {
        const u = await fetchMe();
        if (!cancelled) setMe(u);
      } catch {
        if (!cancelled) {
          tokenStore.clear();
          setMe(null);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
          disarmSafety();
        }
      }
    }

    void load();

    const handler = () => {
      setLoading(true);
      void load();
    };
    window.addEventListener(AUTH_CHANGED_EVENT, handler);
    window.addEventListener("storage", handler);

    return () => {
      cancelled = true;
      disarmSafety();
      window.removeEventListener(AUTH_CHANGED_EVENT, handler);
      window.removeEventListener("storage", handler);
    };
  }, []);

  return { me, loading };
}
