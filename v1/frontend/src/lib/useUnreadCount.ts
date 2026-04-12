"use client";

import { useEffect, useState } from "react";
import { AUTH_CHANGED_EVENT, fetchUnreadCount, tokenStore } from "./api";
import { useMe } from "./useMe";

const POLL_INTERVAL_MS = 30000;

export function useUnreadCount() {
  const { me } = useMe();
  const [unread, setUnread] = useState(0);

  useEffect(() => {
    if (!me) {
      setUnread(0);
      return;
    }
    let cancelled = false;
    async function load() {
      try {
        const r = await fetchUnreadCount();
        if (!cancelled) setUnread(r.count);
      } catch {
        /* ignore */
      }
    }
    void load();
    const t = setInterval(load, POLL_INTERVAL_MS);
    const onAuth = () => {
      if (!tokenStore.get()) setUnread(0);
    };
    window.addEventListener(AUTH_CHANGED_EVENT, onAuth);
    return () => {
      cancelled = true;
      clearInterval(t);
      window.removeEventListener(AUTH_CHANGED_EVENT, onAuth);
    };
  }, [me]);

  return unread;
}
