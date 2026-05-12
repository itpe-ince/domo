"use client";

import { AnalyticsPeriod } from "@/lib/api";
import { useAnalyticsNewsletterOpenRate } from "@/lib/hooks/useAnalytics";
import { SVGLineChart } from "./SVGLineChart";

const POSTHOG_BASE = process.env.NEXT_PUBLIC_POSTHOG_INSIGHTS_BASE_URL;

interface NewsletterOpenRateCardProps {
  period: AnalyticsPeriod;
  bust?: boolean;
}

function CardSkeleton() {
  return (
    <div className="rounded-lg border border-admin-border bg-admin-surface overflow-hidden animate-pulse">
      <div className="px-4 py-3 border-b border-admin-border bg-admin-surface-2">
        <div className="h-4 w-40 bg-admin-border rounded" />
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

export function NewsletterOpenRateCard({ period, bust = false }: NewsletterOpenRateCardProps) {
  const { data, loading, error, refetch } = useAnalyticsNewsletterOpenRate(period, bust);

  if (loading) return <CardSkeleton />;

  if (error) {
    return (
      <article className="rounded-lg border border-admin-border bg-admin-surface overflow-hidden">
        <header className="px-4 py-3 border-b border-admin-border bg-admin-surface-2">
          <span className="text-[13px] font-semibold text-admin-fg">Newsletter Open Rate</span>
        </header>
        <div className="p-4 flex flex-col items-center justify-center gap-3 h-40 text-center">
          <p className="text-[12px] text-admin-muted">{error}</p>
          <button
            onClick={() => refetch()}
            className="px-3 py-1 text-[11px] border border-admin-border rounded text-admin-muted hover:text-admin-fg hover:bg-admin-surface-2 transition-colors"
          >
            다시 시도
          </button>
        </div>
      </article>
    );
  }

  const series = data?.data.series ?? [];
  const summary = data?.data.summary;

  const chartSeries = [
    {
      label: "오픈율",
      color: "#10b981",
      data: series.map((p) => ({ date: p.date, value: p.open_rate })),
    },
    {
      label: "클릭율",
      color: "#f59e0b",
      data: series.map((p) => ({ date: p.date, value: p.click_rate })),
    },
  ];

  return (
    <article className="rounded-lg border border-admin-border bg-admin-surface overflow-hidden">
      <header className="flex items-center justify-between px-4 py-3 border-b border-admin-border bg-admin-surface-2">
        <span className="text-[13px] font-semibold text-admin-fg">Newsletter Open Rate</span>
        <span className="text-[10px] text-admin-muted bg-admin-border/60 px-2 py-0.5 rounded-full">
          발송 {summary?.total_issues ?? 0}호
        </span>
      </header>

      <div className="p-4">
        {POSTHOG_BASE ? (
          <iframe
            src={`${POSTHOG_BASE}/newsletter-open-rate`}
            sandbox="allow-scripts allow-same-origin"
            className="w-full"
            style={{ height: 160, border: "none" }}
            title="PostHog Newsletter Insights"
          />
        ) : (
          <SVGLineChart
            series={chartSeries}
            yUnit="%"
            height={160}
            ariaLabel="Newsletter 오픈율/클릭율 시계열 차트"
          />
        )}
      </div>

      <footer className="flex items-center gap-6 px-4 py-2 border-t border-admin-border">
        <div className="flex flex-col">
          <span className="text-[10px] text-admin-muted">평균 오픈율</span>
          <span className="text-[14px] font-semibold text-admin-fg">
            {summary != null ? `${(summary.avg_open_rate * 100).toFixed(1)}%` : "—"}
          </span>
        </div>
        <div className="flex flex-col">
          <span className="text-[10px] text-admin-muted">평균 클릭율</span>
          <span className="text-[14px] font-semibold text-admin-fg">
            {summary != null ? `${(summary.avg_click_rate * 100).toFixed(1)}%` : "—"}
          </span>
        </div>
      </footer>
    </article>
  );
}
