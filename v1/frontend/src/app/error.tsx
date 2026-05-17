"use client";

/**
 * Route-level error boundary. Next.js renders this when a client component
 * inside the route subtree throws — including dynamic-import ChunkLoadError
 * that happens when the user is on a tab with an old JS build after a deploy.
 *
 * On ChunkLoadError we auto-reload exactly once (controlled via sessionStorage
 * to avoid a reload loop if the new server is itself broken).
 *
 * For other errors we render an inline retry UI that resets the boundary.
 *
 * NOTE: Cannot use the I18nProvider here because `error.tsx` may render when
 * the provider is itself broken. Strings are hard-coded Korean (matches the
 * rest of the user-facing copy) — keep it minimal and self-contained.
 */

import { useEffect } from "react";

const RELOAD_FLAG = "domo_chunk_reload_attempted";

function isChunkLoadError(err: unknown): boolean {
  if (!err) return false;
  const e = err as { name?: string; message?: string };
  if (e.name === "ChunkLoadError") return true;
  const msg = e.message || "";
  return (
    /Loading chunk \d+ failed/i.test(msg) ||
    /Loading CSS chunk/i.test(msg) ||
    /ChunkLoadError/.test(msg) ||
    /Failed to fetch dynamically imported module/i.test(msg) ||
    /Importing a module script failed/i.test(msg)
  );
}

export default function RouteError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  const isChunk = isChunkLoadError(error);

  useEffect(() => {
    // Always log so it surfaces in PostHog/console even after auto-reload.
    if (typeof window !== "undefined" && (window as any).posthog?.captureException) {
      try {
        (window as any).posthog.captureException(error, {
          source: "route-error-boundary",
          isChunkLoadError: isChunk,
        });
      } catch {
        // ignore — analytics is non-critical
      }
    }
    // eslint-disable-next-line no-console
    console.error("[RouteError]", error);

    if (isChunk && typeof window !== "undefined") {
      // Guard against reload loop: only auto-reload once per session.
      const attempted = sessionStorage.getItem(RELOAD_FLAG);
      if (!attempted) {
        sessionStorage.setItem(RELOAD_FLAG, String(Date.now()));
        // Hard reload to fetch fresh HTML + new chunk manifest.
        window.location.reload();
      }
    } else {
      // Clear the chunk flag once a non-chunk render succeeds elsewhere.
      sessionStorage.removeItem(RELOAD_FLAG);
    }
  }, [error, isChunk]);

  return (
    <div
      role="alert"
      className="min-h-[50vh] flex flex-col items-center justify-center gap-4 p-8 text-center"
    >
      <h2 className="text-xl font-bold text-text-primary">문제가 발생했어요</h2>
      <p className="text-sm text-text-muted max-w-md">
        {isChunk
          ? "새 버전이 배포된 것 같아요. 페이지를 새로고침할게요."
          : "잠시 후 다시 시도해주세요."}
      </p>
      <div className="flex gap-2">
        <button
          type="button"
          onClick={reset}
          className="btn-secondary"
        >
          다시 시도
        </button>
        <button
          type="button"
          onClick={() => {
            if (typeof window !== "undefined") {
              sessionStorage.removeItem(RELOAD_FLAG);
              window.location.reload();
            }
          }}
          className="btn-primary"
        >
          새로고침
        </button>
      </div>
      {process.env.NODE_ENV !== "production" && (
        <pre className="mt-4 text-[10px] text-text-muted whitespace-pre-wrap max-w-xl overflow-auto">
          {error.message}
          {error.digest ? `\n\ndigest: ${error.digest}` : ""}
        </pre>
      )}
    </div>
  );
}
