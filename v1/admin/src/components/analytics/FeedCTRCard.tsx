"use client";

import { AnalyticsPeriod } from "@/lib/api";
import { useAnalyticsFeedCTR } from "@/lib/hooks/useAnalytics";
import { SVGBarChart } from "./SVGLineChart";

interface FeedCTRCardProps {
  period: AnalyticsPeriod;
  bust?: boolean;
}

const ALGO_COLORS: Record<string, string> = {
  default: "#6366f1",
  v1: "#22d3ee",
  v2: "#10b981",
};

function CardSkeleton() {
  return (
    <div className="rounded-lg border border-admin-border bg-admin-surface overflow-hidden animate-pulse">
      <div className="px-4 py-3 border-b border-admin-border bg-admin-surface-2">
        <div className="h-4 w-36 bg-admin-border rounded" />
      </div>
      <div className="p-4">
        <div className="h-40 bg-admin-border/40 rounded" />
      </div>
      <div className="px-4 py-2 border-t border-admin-border flex gap-6">
        <div className="h-3 w-32 bg-admin-border rounded" />
      </div>
    </div>
  );
}

export function FeedCTRCard({ period, bust = false }: FeedCTRCardProps) {
  const { data, loading, error, refetch } = useAnalyticsFeedCTR(period, bust);

  if (loading) return <CardSkeleton />;

  if (error) {
    return (
      <article className="rounded-lg border border-admin-border bg-admin-surface overflow-hidden">
        <header className="px-4 py-3 border-b border-admin-border bg-admin-surface-2">
          <span className="text-[13px] font-semibold text-admin-fg">Feed CTR by Algorithm</span>
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

  const algos = data?.data.algos ?? [];
  const summary = data?.data.summary;

  const barItems = algos.map((a) => ({
    label: a.name,
    value: a.ctr,
    color: ALGO_COLORS[a.name] ?? "#94a3b8",
  }));

  const maxCtr = algos.length ? Math.max(...algos.map((a) => a.ctr)) : 1;
  const deltaSign = (summary?.delta_v2_vs_v1 ?? 0) >= 0 ? "+" : "";

  return (
    <article className="rounded-lg border border-admin-border bg-admin-surface overflow-hidden">
      <header className="flex items-center justify-between px-4 py-3 border-b border-admin-border bg-admin-surface-2">
        <span className="text-[13px] font-semibold text-admin-fg">Feed CTR by Algorithm</span>
        {summary?.best_algo && (
          <span className="text-[10px] text-admin-muted bg-admin-border/60 px-2 py-0.5 rounded-full">
            최고: {summary.best_algo}
          </span>
        )}
      </header>

      <div className="p-4">
        {algos.length === 0 ? (
          <div className="flex items-center justify-center h-40 text-[12px] text-admin-muted">
            실험 데이터가 없습니다
          </div>
        ) : (
          <SVGBarChart
            items={barItems}
            maxValue={maxCtr}
            height={algos.length * 36 + 8}
            ariaLabel="알고리즘별 Feed CTR 바 차트"
          />
        )}
      </div>

      <footer className="flex items-center gap-6 px-4 py-2 border-t border-admin-border">
        <div className="flex flex-col">
          <span className="text-[10px] text-admin-muted">v2 vs v1 차이</span>
          <span
            className={[
              "text-[14px] font-semibold",
              (summary?.delta_v2_vs_v1 ?? 0) >= 0 ? "text-admin-success" : "text-admin-danger",
            ].join(" ")}
          >
            {summary != null
              ? `${deltaSign}${(summary.delta_v2_vs_v1 * 100).toFixed(2)}pp`
              : "—"}
          </span>
        </div>
      </footer>
    </article>
  );
}
