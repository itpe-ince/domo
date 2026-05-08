"use client";

import { AnalyticsPeriod } from "@/lib/api";
import { useAnalyticsAIFeaturesUsage } from "@/lib/hooks/useAnalytics";
import { SVGBarChart } from "./SVGLineChart";

interface AIFeaturesUsageCardProps {
  period: AnalyticsPeriod;
  bust?: boolean;
}

const FEATURE_LABELS: Record<string, string> = {
  caption: "AI 캡션",
  docent: "AI 도슨트",
  collection: "AI 컬렉션",
};

const FEATURE_COLORS: Record<string, string> = {
  caption: "#8b5cf6",
  docent: "#ec4899",
  collection: "#f97316",
};

function CardSkeleton() {
  return (
    <div className="rounded-lg border border-admin-border bg-admin-surface overflow-hidden animate-pulse">
      <div className="px-4 py-3 border-b border-admin-border bg-admin-surface-2">
        <div className="h-4 w-28 bg-admin-border rounded" />
      </div>
      <div className="p-4">
        <div className="h-32 bg-admin-border/40 rounded" />
      </div>
      <div className="px-4 py-2 border-t border-admin-border">
        <div className="h-3 w-28 bg-admin-border rounded" />
      </div>
    </div>
  );
}

export function AIFeaturesUsageCard({ period, bust = false }: AIFeaturesUsageCardProps) {
  const { data, loading, error, refetch } = useAnalyticsAIFeaturesUsage(period, bust);

  if (loading) return <CardSkeleton />;

  if (error) {
    return (
      <article className="rounded-lg border border-admin-border bg-admin-surface overflow-hidden">
        <header className="px-4 py-3 border-b border-admin-border bg-admin-surface-2">
          <span className="text-[13px] font-semibold text-admin-fg">AI 기능 사용률</span>
        </header>
        <div className="p-4 flex flex-col items-center justify-center gap-3 h-32 text-center">
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

  const features = data?.data.features ?? [];
  const summary = data?.data.summary;

  const maxCount = features.length ? Math.max(...features.map((f) => f.usage_count)) : 1;

  const barItems = features.map((f) => ({
    label: FEATURE_LABELS[f.name] ?? f.name,
    value: f.usage_count,
    color: FEATURE_COLORS[f.name] ?? "#94a3b8",
  }));

  return (
    <article className="rounded-lg border border-admin-border bg-admin-surface overflow-hidden">
      <header className="flex items-center justify-between px-4 py-3 border-b border-admin-border bg-admin-surface-2">
        <span className="text-[13px] font-semibold text-admin-fg">AI 기능 사용률</span>
      </header>

      <div className="p-4">
        {features.length === 0 ? (
          <div className="flex items-center justify-center h-32 text-[12px] text-admin-muted">
            데이터가 없습니다
          </div>
        ) : (
          <SVGBarChart
            items={barItems}
            maxValue={maxCount}
            height={features.length * 36 + 8}
            ariaLabel="AI 기능별 사용 건수 바 차트"
          />
        )}
      </div>

      <footer className="flex items-center gap-4 px-4 py-2 border-t border-admin-border">
        <div className="flex flex-col">
          <span className="text-[10px] text-admin-muted">총 AI 기능 사용</span>
          <span className="text-[14px] font-semibold text-admin-fg">
            {summary != null ? summary.total_ai_usages.toLocaleString() : "—"}건
          </span>
        </div>
      </footer>
    </article>
  );
}
