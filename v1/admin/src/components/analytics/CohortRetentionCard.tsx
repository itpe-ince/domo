"use client";

import { AnalyticsPeriod } from "@/lib/api";
import { useAnalyticsCohortRetention } from "@/lib/hooks/useAnalytics";
import { SVGLineChart } from "./SVGLineChart";

const POSTHOG_BASE = process.env.NEXT_PUBLIC_POSTHOG_INSIGHTS_BASE_URL;

interface CohortRetentionCardProps {
  period: AnalyticsPeriod;
  bust?: boolean;
}

function CardSkeleton() {
  return (
    <div className="rounded-lg border border-admin-border bg-admin-surface overflow-hidden animate-pulse">
      <div className="px-4 py-3 border-b border-admin-border bg-admin-surface-2">
        <div className="h-4 w-32 bg-admin-border rounded" />
      </div>
      <div className="p-4">
        <div className="h-40 bg-admin-border/40 rounded" />
      </div>
      <div className="px-4 py-2 border-t border-admin-border flex gap-6">
        <div className="h-3 w-24 bg-admin-border rounded" />
        <div className="h-3 w-24 bg-admin-border rounded" />
      </div>
    </div>
  );
}

function CardError({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="rounded-lg border border-admin-border bg-admin-surface overflow-hidden">
      <div className="px-4 py-3 border-b border-admin-border bg-admin-surface-2">
        <span className="text-[13px] font-semibold text-admin-fg">코호트 Retention</span>
      </div>
      <div className="p-4 flex flex-col items-center justify-center gap-3 h-40 text-center">
        <p className="text-[12px] text-admin-muted">{message}</p>
        <button
          onClick={onRetry}
          className="px-3 py-1 text-[11px] border border-admin-border rounded text-admin-muted hover:text-admin-fg hover:bg-admin-surface-2 transition-colors"
        >
          다시 시도
        </button>
      </div>
    </div>
  );
}

export function CohortRetentionCard({ period, bust = false }: CohortRetentionCardProps) {
  const { data, loading, error, refetch } = useAnalyticsCohortRetention(period, bust);

  if (loading) return <CardSkeleton />;
  if (error) return <CardError message={error} onRetry={() => refetch()} />;

  const series = data?.data.series ?? [];
  const summary = data?.data.summary;

  // PostHog iframe fallback
  const useIframe = Boolean(POSTHOG_BASE);

  const chartSeries = [
    {
      label: "D7 잔존율",
      color: "#6366f1",
      data: series
        .filter((p) => p.d7_retention != null)
        .map((p) => ({ date: p.date, value: p.d7_retention! })),
    },
    {
      label: "D30 잔존율",
      color: "#22d3ee",
      data: series
        .filter((p) => p.d30_retention != null)
        .map((p) => ({ date: p.date, value: p.d30_retention! })),
    },
  ];

  return (
    <article className="rounded-lg border border-admin-border bg-admin-surface overflow-hidden">
      <header className="flex items-center justify-between px-4 py-3 border-b border-admin-border bg-admin-surface-2">
        <span className="text-[13px] font-semibold text-admin-fg">코호트 Retention</span>
        <span className="text-[10px] text-admin-muted bg-admin-border/60 px-2 py-0.5 rounded-full">
          임계치 미달 기록 기준
        </span>
      </header>

      <div className="p-4">
        {useIframe ? (
          <PostHogIframe src={`${POSTHOG_BASE}/cohort-retention`} />
        ) : (
          <SVGLineChart
            series={chartSeries}
            yUnit="%"
            height={160}
            ariaLabel="코호트 D7/D30 retention 라인 차트"
          />
        )}
      </div>

      <footer className="flex items-center gap-6 px-4 py-2 border-t border-admin-border">
        <div className="flex flex-col">
          <span className="text-[10px] text-admin-muted">D7 잔존율</span>
          <span className="text-[14px] font-semibold text-admin-fg">
            {summary?.latest_d7 != null
              ? `${(summary.latest_d7 * 100).toFixed(1)}%`
              : "—"}
          </span>
        </div>
        <div className="flex flex-col">
          <span className="text-[10px] text-admin-muted">D30 잔존율</span>
          <span className="text-[14px] font-semibold text-admin-fg">
            {summary?.latest_d30 != null
              ? `${(summary.latest_d30 * 100).toFixed(1)}%`
              : "—"}
          </span>
        </div>
      </footer>
    </article>
  );
}

// ── PostHog iframe — env 설정 시 사용 ───────────────────────────────────────

function PostHogIframe({ src }: { src: string }) {
  return (
    <iframe
      src={src}
      sandbox="allow-scripts allow-same-origin"
      className="w-full"
      style={{ height: 160, border: "none" }}
      title="PostHog Insights"
    />
  );
}
