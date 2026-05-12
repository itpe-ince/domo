"use client";

import { useState } from "react";

interface PostHogEmbedProps {
  experimentName: string;
  posthogInsightsUrl: string;
}

export function PostHogEmbed({ experimentName, posthogInsightsUrl }: PostHogEmbedProps) {
  const [embedFailed, setEmbedFailed] = useState(false);

  const baseUrl = process.env.NEXT_PUBLIC_POSTHOG_INSIGHTS_BASE_URL;

  if (baseUrl && !embedFailed) {
    const embedSrc = `${baseUrl}/experiments?experiment_name=${encodeURIComponent(experimentName)}`;
    return (
      <div className="mt-3 rounded-lg border border-admin-border overflow-hidden">
        <iframe
          src={embedSrc}
          title={`PostHog Insights — ${experimentName}`}
          sandbox="allow-scripts allow-same-origin allow-popups allow-forms"
          referrerPolicy="strict-origin-when-cross-origin"
          className="w-full rounded-md"
          style={{ height: "480px", display: "block" }}
          onError={() => setEmbedFailed(true)}
        />
      </div>
    );
  }

  // fallback: env 미설정이거나 iframe 로드 실패 시
  return (
    <div className="mt-3 rounded-lg border border-admin-border bg-admin-surface-2 p-5 flex flex-col items-start gap-3">
      <p className="text-sm text-admin-muted">
        PostHog Insights 대시보드 URL이 설정되지 않았습니다.
        {embedFailed && (
          <span className="ml-1">(iframe 로드 실패 — CSP 제한 가능성)</span>
        )}
      </p>
      {posthogInsightsUrl ? (
        <a
          href={posthogInsightsUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1 text-sm text-admin-accent hover:underline border border-admin-accent/30 rounded-md px-3 py-1.5 transition-colors hover:bg-admin-accent/5"
        >
          PostHog Insights 열기 ↗
        </a>
      ) : null}
    </div>
  );
}
