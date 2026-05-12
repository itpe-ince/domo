"use client";

/**
 * SupporterStats — B-3 supporter-dashboard
 *
 * Header summary bar: artists supported count, lifetime amount, active subscriptions.
 */

import { useI18n } from "@/i18n";
import type { SupporterSummary } from "@/lib/hooks/useMySponsorships";

type Props = {
  summary: SupporterSummary;
  loading: boolean;
};

function StatCard({
  value,
  label,
  loading,
}: {
  value: string;
  label: string;
  loading: boolean;
}) {
  return (
    <div className="flex flex-col items-center gap-1 p-4 card flex-1 min-w-0">
      {loading ? (
        <div className="h-7 w-16 bg-surface-hover animate-pulse rounded" />
      ) : (
        <span className="text-2xl font-bold text-primary">{value}</span>
      )}
      <span className="text-xs text-text-muted text-center">{label}</span>
    </div>
  );
}

export function SupporterStats({ summary, loading }: Props) {
  const { t } = useI18n();

  const lifetimeDollars = (summary.lifetimeAmountCents / 100).toFixed(2);

  return (
    <div className="flex gap-3 flex-wrap sm:flex-nowrap">
      <StatCard
        value={String(summary.artistsCount)}
        label={t("patronage.supporter.summary.artistsCount")}
        loading={loading}
      />
      <StatCard
        value={`$${lifetimeDollars}`}
        label={t("patronage.supporter.summary.lifetimeAmount")}
        loading={loading}
      />
      <StatCard
        value={String(summary.activeSubscriptionsCount)}
        label={t("patronage.supporter.summary.activeSubscriptions")}
        loading={loading}
      />
    </div>
  );
}
