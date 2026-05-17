"use client";

/**
 * Top-level error boundary. Next.js renders this only when RootLayout
 * itself throws (e.g., I18nProvider crash, PostHogProvider hydration fail).
 * Must include <html> and <body> because it replaces the entire document.
 *
 * Keep dependencies near zero — no imports from src/i18n, src/components,
 * or src/lib because those might be the source of the crash.
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
    /Failed to fetch dynamically imported module/i.test(msg)
  );
}

export default function GlobalError({
  error,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  const isChunk = isChunkLoadError(error);

  useEffect(() => {
    // eslint-disable-next-line no-console
    console.error("[GlobalError]", error);

    if (isChunk && typeof window !== "undefined") {
      const attempted = sessionStorage.getItem(RELOAD_FLAG);
      if (!attempted) {
        sessionStorage.setItem(RELOAD_FLAG, String(Date.now()));
        window.location.reload();
      }
    }
  }, [error, isChunk]);

  return (
    <html lang="ko">
      <body
        style={{
          fontFamily: "system-ui, -apple-system, sans-serif",
          background: "#1a1a1a",
          color: "#e5e5e5",
          minHeight: "100vh",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          padding: "2rem",
          margin: 0,
        }}
      >
        <div style={{ maxWidth: "32rem", textAlign: "center" }}>
          <h1 style={{ fontSize: "1.5rem", marginBottom: "0.5rem" }}>
            문제가 발생했어요
          </h1>
          <p style={{ fontSize: "0.875rem", color: "#a0a0a0", marginBottom: "1.5rem" }}>
            {isChunk
              ? "새 버전이 배포된 것 같아요. 페이지를 새로고침할게요."
              : "잠시 후 다시 시도해주세요."}
          </p>
          <button
            type="button"
            onClick={() => {
              if (typeof window !== "undefined") {
                sessionStorage.removeItem(RELOAD_FLAG);
                window.location.reload();
              }
            }}
            style={{
              background: "#A8D76E",
              color: "#1a1a1a",
              border: "none",
              borderRadius: "999px",
              padding: "0.625rem 1.25rem",
              fontWeight: 600,
              fontSize: "0.875rem",
              cursor: "pointer",
            }}
          >
            새로고침
          </button>
        </div>
      </body>
    </html>
  );
}
