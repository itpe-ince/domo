"use client";

import { useEffect, useState } from "react";
import {
  ApiUser,
  AUTH_CHANGED_EVENT,
  fetchMe,
  tokenStore,
} from "@/lib/api";

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

    async function load() {
      if (!tokenStore.get()) {
        if (!cancelled) {
          setMe(null);
          setLoading(false);
        }
        return;
      }
      try {
        const u = await fetchMe();
        if (!cancelled) setMe(u);
      } catch {
        if (!cancelled) {
          tokenStore.clear();
          setMe(null);
        }
      } finally {
        if (!cancelled) setLoading(false);
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
      window.removeEventListener(AUTH_CHANGED_EVENT, handler);
      window.removeEventListener("storage", handler);
    };
  }, []);

  return { me, loading };
}
