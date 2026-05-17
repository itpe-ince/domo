"use client";

/**
 * BuildVersionWatcher (plan C2)
 *
 * Detects "open tab on an old build" after a redeploy and surfaces a
 * non-blocking toast asking the user to reload. Prevents the silent
 * skeleton-stuck-forever class of bugs that happens when an old client
 * tries to fetch chunks the new server no longer ships.
 *
 * Detection strategy:
 *   - Client embeds NEXT_PUBLIC_BUILD_ID at build time.
 *   - On a "wake" event (tab focus, online, periodic poll) we GET
 *     /api/build-id and compare with the embedded value.
 *   - On mismatch we show a toast with a "새로고침" button.
 *
 * Polling: only when the tab is visible — no background battery drain.
 * Interval is 5 minutes by default; raise via NEXT_PUBLIC_BUILD_CHECK_INTERVAL_MS.
 *
 * Intentionally side-effect-only (renders the toast itself, no children).
 * Mount once at the AppShell root.
 */

import { useEffect, useState } from "react";
import { useI18n } from "@/i18n";

const CLIENT_BUILD_ID = process.env.NEXT_PUBLIC_BUILD_ID || null;
const POLL_MS = Number(
  process.env.NEXT_PUBLIC_BUILD_CHECK_INTERVAL_MS || 5 * 60_000
);

async function fetchServerBuildId(signal: AbortSignal): Promise<string | null> {
  try {
    const res = await fetch("/api/build-id", {
      cache: "no-store",
      signal,
    });
    if (!res.ok) return null;
    const json = (await res.json()) as { buildId?: string };
    return typeof json.buildId === "string" ? json.buildId : null;
  } catch {
    return null;
  }
}

export function BuildVersionWatcher() {
  const { t } = useI18n();
  const [stale, setStale] = useState(false);

  useEffect(() => {
    // Skip in dev — buildId is "local-<ts>" and would constantly mismatch
    // across HMR-triggered rebuilds. HMR handles its own refresh signalling.
    if (process.env.NODE_ENV !== "production") return;
    // If neither side has a buildId (env not injected), the comparison is
    // meaningless — bail out rather than spam the user.
    if (!CLIENT_BUILD_ID) return;

    let cancelled = false;
    const ac = new AbortController();

    async function check() {
      if (cancelled || stale) return;
      const serverId = await fetchServerBuildId(ac.signal);
      if (cancelled) return;
      if (serverId && serverId !== "unknown" && serverId !== CLIENT_BUILD_ID) {
        setStale(true);
      }
    }

    const onWake = () => {
      if (document.visibilityState === "visible") void check();
    };

    // Initial check after a small delay to avoid blocking first paint.
    const initial = setTimeout(() => void check(), 3_000);
    const interval = setInterval(onWake, POLL_MS);
    document.addEventListener("visibilitychange", onWake);
    window.addEventListener("online", onWake);
    window.addEventListener("focus", onWake);

    return () => {
      cancelled = true;
      ac.abort();
      clearTimeout(initial);
      clearInterval(interval);
      document.removeEventListener("visibilitychange", onWake);
      window.removeEventListener("online", onWake);
      window.removeEventListener("focus", onWake);
    };
  }, [stale]);

  if (!stale) return null;

  return (
    <div
      role="status"
      aria-live="polite"
      className="fixed bottom-20 md:bottom-4 left-1/2 -translate-x-1/2 z-[100] max-w-sm w-[calc(100%-2rem)] card shadow-xl border-primary/40 bg-background p-4 flex items-start gap-3"
    >
      <div className="text-2xl flex-shrink-0" aria-hidden="true">
        🔄
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-semibold text-text-primary">
          {t("common.newVersionTitle")}
        </p>
        <p className="text-xs text-text-muted mt-0.5">
          {t("common.newVersionMessage")}
        </p>
      </div>
      <button
        type="button"
        onClick={() => {
          try {
            sessionStorage.removeItem("domo_chunk_reload_attempted");
          } catch {
            // ignore
          }
          window.location.reload();
        }}
        className="btn-primary text-xs px-3 py-1.5 flex-shrink-0"
      >
        {t("common.reload")}
      </button>
    </div>
  );
}
