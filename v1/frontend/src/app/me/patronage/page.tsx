"use client";

/**
 * Artist Patronage Dashboard — /me/patronage
 *
 * 5 sections:
 *   1. Header: title + artist name + settings link
 *   2. Summary cards: supporters / monthly revenue / active subscriptions / tier distribution
 *   3. Revenue chart: daily (30d) or monthly (12mo) toggle
 *   4. Supporters table: paginated with active/churned/all filter
 *   5. Payout section: balance + "Request payout" button → modal
 */

import { useState } from "react";
import Link from "next/link";
import { useMe } from "@/lib/useMe";
import { useI18n } from "@/i18n";
import {
  usePatronageSummary,
  usePatronageRevenue,
  usePatronageSupporters,
  type RevenueGranularity,
  type SupporterFilter,
} from "@/lib/hooks/usePatronageDashboard";
import { SummaryCard } from "@/components/patronage/SummaryCard";
import { TierDistribution } from "@/components/patronage/TierDistribution";
import { RevenueChart } from "@/components/patronage/RevenueChart";
import { SupportersTable } from "@/components/patronage/SupportersTable";
import dynamic from "next/dynamic";

// PayoutRequestModal — 정산 요청 모달. 버튼 클릭 시에만 마운트되므로
// dynamic import로 초기 번들에서 제외 (G''-6 번들 최종화)
const PayoutRequestModal = dynamic(
  () =>
    import("@/components/patronage/PayoutRequestModal").then(
      (m) => ({ default: m.PayoutRequestModal })
    ),
  {
    ssr: false,
    loading: () => null,
  }
);
import { ChurnList } from "@/components/sponsorships/ChurnList";
import { SettingsIcon, BluebirdIcon } from "@/components/icons";
import { CohortRetentionChart } from "@/components/patronage/CohortRetentionChart";
import { CouponRedemptionStats } from "@/components/patronage/CouponRedemptionStats";
import { NewsletterStats } from "@/components/patronage/NewsletterStats";
import { ConversionFunnel } from "@/components/patronage/ConversionFunnel";
import { DmEngagementCard } from "@/components/patronage/DmEngagementCard";
import { usePatronageAnalytics } from "@/lib/hooks/usePatronageAnalytics";

function formatCents(cents: number): string {
  const usd = cents / 100;
  if (usd >= 10000) return `$${(usd / 1000).toFixed(1)}k`;
  return `$${usd.toLocaleString("en-US", { minimumFractionDigits: 0, maximumFractionDigits: 2 })}`;
}

function computeDelta(current: number, previous: number): { label: string; dir: "positive" | "negative" | "neutral" } {
  if (previous === 0) {
    if (current === 0) return { label: "", dir: "neutral" };
    return { label: "+100%", dir: "positive" };
  }
  const pct = ((current - previous) / previous) * 100;
  const rounded = Math.round(pct);
  const label = rounded >= 0 ? `+${rounded}%` : `${rounded}%`;
  return { label, dir: rounded >= 0 ? "positive" : "negative" };
}

export default function PatronageDashboardPage() {
  const { me } = useMe();
  const { t } = useI18n();

  const [granularity, setGranularity] = useState<RevenueGranularity>("daily");
  const [supporterFilter, setSupporterFilter] = useState<SupporterFilter>("all");
  const [payoutOpen, setPayoutOpen] = useState(false);

  const { summary, loading: sumLoading } = usePatronageSummary();
  const { data: revenueData, loading: revLoading } = usePatronageRevenue(granularity);
  const {
    supporters,
    loading: suppLoading,
    loadingMore,
    hasMore,
    loadMore,
  } = usePatronageSupporters(supporterFilter);
  const { analytics, loading: analyticsLoading, isMock } = usePatronageAnalytics();

  const revDelta = summary
    ? computeDelta(
        summary.current_month_revenue_usd_cents,
        summary.previous_month_revenue_usd_cents
      )
    : { label: "", dir: "neutral" as const };

  return (
    <main className="flex-1 max-w-4xl mx-auto w-full px-4 py-8 flex flex-col gap-8" aria-label={t("patronage.artist.title")}>
      {/* ── 1. Header ── */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-text-primary">
            {t("patronage.artist.title")}
          </h1>
          {me && (
            <p className="text-text-muted text-sm mt-1">@{me.display_name}</p>
          )}
        </div>
        <Link
          href="/me/settings/account"
          className="flex items-center gap-2 text-sm text-text-muted hover:text-text-primary transition-colors"
        >
          <SettingsIcon size={16} />
          <span className="hidden sm:inline">{t("common.settings")}</span>
        </Link>
      </div>

      {/* ── 2. Summary cards 2×2 grid ── */}
      <section aria-label={t("patronage.artist.summary.supporters")}>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <SummaryCard
            label={t("patronage.artist.summary.supporters")}
            value={sumLoading ? "—" : (summary?.total_supporters ?? 0)}
            icon={<BluebirdIcon size={14} />}
            loading={sumLoading}
          />
          <SummaryCard
            label={t("patronage.artist.summary.monthlyRevenue")}
            value={sumLoading ? "—" : formatCents(summary?.current_month_revenue_usd_cents ?? 0)}
            delta={revDelta.label || undefined}
            deltaDir={revDelta.dir}
            loading={sumLoading}
          />
          <SummaryCard
            label={t("patronage.artist.summary.subscribers")}
            value={sumLoading ? "—" : (summary?.active_subscriptions ?? 0)}
            loading={sumLoading}
          />
          {/* Tier distribution card — spans 2 cols on large screens */}
          <div className="col-span-2 lg:col-span-1">
            <TierDistribution
              data={
                summary?.tier_distribution ?? { subscriber: 0, sponsor: 0, follower: 0 }
              }
              loading={sumLoading}
              labels={{
                title: t("patronage.artist.summary.tierDistribution"),
                subscriber: t("patronage.artist.tier.subscriber"),
                sponsor: t("patronage.artist.tier.sponsor"),
                follower: t("patronage.artist.tier.follower"),
              }}
            />
          </div>
        </div>
      </section>

      {/* ── 3. Revenue chart ── */}
      <section aria-label={t("patronage.artist.chart.daily")}>
        <RevenueChart
          data={revenueData}
          loading={revLoading}
          granularity={granularity}
          onGranularityChange={setGranularity}
          labels={{
            daily: t("patronage.artist.chart.daily"),
            monthly: t("patronage.artist.chart.monthly"),
            toggleDaily: t("patronage.artist.chart.toggle.daily"),
            toggleMonthly: t("patronage.artist.chart.toggle.monthly"),
            noData: t("patronage.artist.empty.title"),
          }}
        />
      </section>

      {/* ── 4. Supporters table ── */}
      <section aria-label={t("patronage.artist.supporters.table.title")}>
        <SupportersTable
          supporters={supporters}
          loading={suppLoading}
          loadingMore={loadingMore}
          hasMore={hasMore}
          filter={supporterFilter}
          onFilterChange={setSupporterFilter}
          onLoadMore={loadMore}
          labels={{
            title: t("patronage.artist.supporters.table.title"),
            filterActive: t("patronage.artist.supporters.filter.active"),
            filterChurned: t("patronage.artist.supporters.filter.churned"),
            filterAll: t("patronage.artist.supporters.filter.all"),
            colUsername: t("patronage.artist.supporters.col.username"),
            colTier: t("patronage.artist.supporters.col.tier"),
            colSince: t("patronage.artist.supporters.col.since"),
            colLifetime: t("patronage.artist.supporters.col.lifetime"),
            colStatus: t("patronage.artist.supporters.col.status"),
            empty: t("patronage.artist.supporters.empty"),
            loadMore: t("patronage.artist.supporters.loadMore"),
            loading: t("common.loading"),
          }}
        />
      </section>

      {/* ── 5. Churn section (B-5) ── */}
      <section>
        <h2 className="text-lg font-semibold text-text-primary mb-3">
          {t("retention.churn.title")}
        </h2>
        <ChurnList limit={20} />
      </section>

      {/* ── B'-5 Analytics section ── */}
      <section aria-label={t("patronage.analytics.title")} className="flex flex-col gap-4">
        <h2 className="text-lg font-semibold text-text-primary">
          {t("patronage.analytics.title")}
        </h2>

        {/* Cohort retention */}
        <CohortRetentionChart
          data={analytics?.cohort_retention ?? []}
          loading={analyticsLoading}
          isMock={isMock}
          labels={{
            title: t("patronage.analytics.cohort.title"),
            d1: t("patronage.analytics.cohort.d1"),
            d7: t("patronage.analytics.cohort.d7"),
            d30: t("patronage.analytics.cohort.d30"),
            noData: t("patronage.analytics.noData"),
            mockBadge: t("patronage.analytics.mockBadge"),
          }}
        />

        {/* Conversion funnel */}
        <ConversionFunnel
          data={analytics?.conversion_funnel ?? null}
          loading={analyticsLoading}
          isMock={isMock}
          labels={{
            title: t("patronage.analytics.funnel.title"),
            postClick: t("patronage.analytics.funnel.postClick"),
            sponsorStart: t("patronage.analytics.funnel.sponsorStart"),
            sponsorSuccess: t("patronage.analytics.funnel.sponsorSuccess"),
            active30d: t("patronage.analytics.funnel.active30d"),
            conversionRate: t("patronage.analytics.funnel.conversionRate"),
            noData: t("patronage.analytics.noData"),
            mockBadge: t("patronage.analytics.mockBadge"),
          }}
        />

        {/* Coupon + Newsletter — side by side on large screens */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <CouponRedemptionStats
            data={analytics?.coupon_redemption ?? null}
            loading={analyticsLoading}
            isMock={isMock}
            labels={{
              title: t("patronage.analytics.coupon.title"),
              issued: t("patronage.analytics.coupon.issued"),
              applied: t("patronage.analytics.coupon.applied"),
              cancelReverted: t("patronage.analytics.coupon.cancelReverted"),
              expired: t("patronage.analytics.coupon.expired"),
              redemptionRate: t("patronage.analytics.coupon.redemptionRate"),
              noData: t("patronage.analytics.noData"),
              mockBadge: t("patronage.analytics.mockBadge"),
            }}
          />
          <NewsletterStats
            data={analytics?.newsletter ?? []}
            loading={analyticsLoading}
            isMock={isMock}
            labels={{
              title: t("patronage.analytics.newsletter.title"),
              openRate: t("patronage.analytics.newsletter.openRate"),
              clickRate: t("patronage.analytics.newsletter.clickRate"),
              noData: t("patronage.analytics.noData"),
              mockBadge: t("patronage.analytics.mockBadge"),
            }}
          />
        </div>

        {/* DM engagement */}
        <DmEngagementCard
          data={analytics?.dm_engagement ?? null}
          loading={analyticsLoading}
          isMock={isMock}
          labels={{
            title: t("patronage.analytics.dm.title"),
            firstMessageRate: t("patronage.analytics.dm.firstMessageRate"),
            firstMessageHint: t("patronage.analytics.dm.firstMessageHint"),
            avgResponseTime: t("patronage.analytics.dm.avgResponseTime"),
            avgResponseUnit: t("patronage.analytics.dm.avgResponseUnit"),
            totalThreads: t("patronage.analytics.dm.totalThreads"),
            noData: t("patronage.analytics.noData"),
            mockBadge: t("patronage.analytics.mockBadge"),
          }}
        />
      </section>

      {/* ── 6. Payout section ── */}
      <section className="card p-5 flex items-center justify-between gap-4">
        <div>
          <p className="text-sm font-semibold text-text-primary">
            {t("patronage.artist.payout.balance")}
          </p>
          <p className="text-2xl font-bold text-text-primary tabular-nums mt-1">
            {sumLoading
              ? "—"
              : formatCents(summary?.lifetime_revenue_usd_cents ?? 0)}
          </p>
          <p className="text-xs text-text-muted mt-0.5">
            {t("patronage.artist.payout.balanceHint")}
          </p>
        </div>
        <button
          onClick={() => setPayoutOpen(true)}
          className="px-5 py-2.5 bg-primary text-background rounded-full text-sm font-medium hover:opacity-90 transition-opacity whitespace-nowrap"
        >
          {t("patronage.artist.payout.request")}
        </button>
      </section>

      {/* ── Empty state ── */}
      {!sumLoading && summary?.total_supporters === 0 && (
        <div className="text-center py-12 flex flex-col items-center gap-3">
          <BluebirdIcon size={40} className="text-primary opacity-30" />
          <p className="text-lg font-semibold text-text-secondary">
            {t("patronage.artist.empty.title")}
          </p>
          <p className="text-sm text-text-muted">{t("patronage.artist.empty.cta")}</p>
        </div>
      )}

      {/* ── Payout modal ── */}
      <PayoutRequestModal
        open={payoutOpen}
        onClose={() => setPayoutOpen(false)}
        availableBalanceCents={summary?.lifetime_revenue_usd_cents ?? 0}
        labels={{
          title: t("patronage.artist.payout.modalTitle"),
          balance: t("patronage.artist.payout.balance"),
          amountLabel: t("patronage.artist.payout.amountLabel"),
          methodLabel: t("patronage.artist.payout.methodLabel"),
          methodBank: t("patronage.artist.payout.methodBank"),
          methodStripe: t("patronage.artist.payout.methodStripe"),
          submit: t("patronage.artist.payout.request"),
          submitting: t("common.loading"),
          success: t("patronage.artist.payout.success"),
          cancel: t("common.cancel"),
          placeholder: t("patronage.artist.payout.amountPlaceholder"),
        }}
      />
    </main>
  );
}
