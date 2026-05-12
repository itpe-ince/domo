"use client";

/**
 * /me/sponsorships — B-3 후원자(supporter) dashboard
 *
 * Sections:
 *   1. Header + SupporterStats summary
 *   2. Active subscriptions (SubscriptionCard grid)
 *   3. One-time sponsorship history (SponsorshipHistory)
 *   4. Tier benefits educational panel (TierBenefitsPanel)
 */

import Link from "next/link";
import { useMe } from "@/lib/useMe";
import { useI18n } from "@/i18n";
import { useMySponsorships } from "@/lib/hooks/useMySponsorships";
import { useResubscribe } from "@/lib/hooks/useResubscribe";
import { useExpiryBanner } from "@/lib/hooks/useExpiryBanner";
import { SupporterStats } from "@/components/sponsorships/SupporterStats";
import { SubscriptionCard } from "@/components/sponsorships/SubscriptionCard";
import { ExpiryBanner } from "@/components/sponsorships/ExpiryBanner";
import { SponsorshipHistory } from "@/components/sponsorships/SponsorshipHistory";
import { TierBenefitsPanel } from "@/components/sponsorships/TierBenefitsPanel";

export default function MySponsorshipsPage() {
  const { me, loading: meLoading } = useMe();
  const { t } = useI18n();
  const {
    sponsorships,
    subscriptions,
    summary,
    loading,
    error,
    cancellingId,
    cancelError,
    cancelSubscriptionById,
    refresh,
  } = useMySponsorships();

  // B-5: one-click resubscribe for cancelled subscription cards
  const { resubscribe, subscribing: resubscribing, error: resubscribeError } = useResubscribe();

  // A-8: expiry banner — detect active subs expiring within 7 days
  const { expiring: expiryBannerEntries, dismiss: dismissExpiry } = useExpiryBanner({
    subscriptions: subscriptions.filter((s) => s.status === "active"),
  });

  // Auth gate
  if (!meLoading && !me) {
    return (
      <main className="flex-1 min-w-0 max-w-3xl mx-auto px-6 py-12 text-center">
        <p className="text-text-muted mb-4">
          {t("patronage.supporter.loginRequired")}
        </p>
        <Link href="/" className="btn-primary text-sm">
          {t("common.login")}
        </Link>
      </main>
    );
  }

  const activeSubscriptions = subscriptions.filter(
    (s) => s.status === "active" || s.status === "past_due"
  );
  const inactiveSubscriptions = subscriptions.filter(
    (s) => s.status !== "active" && s.status !== "past_due"
  );

  async function handleResubscribe(artistId: string) {
    await resubscribe({ artistId });
    // Refresh list so the new active subscription appears
    refresh();
  }

  return (
    <main className="flex-1 min-w-0 max-w-3xl mx-auto px-4 sm:px-6 py-8 space-y-8" aria-label={t("patronage.supporter.title")}>
      {/* ── Section 1: Header ── */}
      <div>
        <h1 className="text-2xl font-bold text-text-primary mb-1">
          {t("patronage.supporter.title")}
        </h1>
        <p className="text-sm text-text-muted">
          {t("patronage.supporter.subtitle")}
        </p>
      </div>

      {/* ── Stats bar ── */}
      <SupporterStats summary={summary} loading={loading} />

      {/* ── A-8: Expiry banners (active subs expiring in 7 days) ── */}
      {!loading && expiryBannerEntries.length > 0 && (
        <div className="space-y-2">
          {expiryBannerEntries.map((entry) => (
            <ExpiryBanner
              key={entry.subscriptionId}
              subscriptionId={entry.subscriptionId}
              artistId={entry.artistId}
              daysLeft={entry.daysLeft}
              onDismiss={dismissExpiry}
            />
          ))}
        </div>
      )}

      {/* ── Error state ── */}
      {error && (
        <div className="card px-4 py-3 text-sm text-red-500 border border-red-200">
          {error}
        </div>
      )}
      {cancelError && (
        <div className="card px-4 py-3 text-sm text-red-500 border border-red-200">
          {cancelError}
        </div>
      )}
      {resubscribeError && (
        <div className="card px-4 py-3 text-sm text-red-500 border border-red-200">
          {resubscribeError}
        </div>
      )}

      {/* ── Section 2: Active subscriptions ── */}
      <section>
        <h2 className="text-lg font-semibold text-text-primary mb-3">
          {t("patronage.supporter.subscriptions.title")}
        </h2>

        {loading ? (
          <div className="space-y-3">
            {[1, 2].map((i) => (
              <div key={i} className="card h-24 animate-pulse" />
            ))}
          </div>
        ) : activeSubscriptions.length === 0 ? (
          <div className="card px-6 py-10 text-center space-y-3">
            <p className="text-text-muted text-sm">
              {t("patronage.supporter.subscriptions.empty")}
            </p>
            <Link
              href="/explore"
              className="inline-block text-primary text-sm font-medium hover:underline"
            >
              {t("patronage.supporter.empty.exploreCta")} →
            </Link>
          </div>
        ) : (
          <div className="space-y-3">
            {activeSubscriptions.map((sub) => (
              <SubscriptionCard
                key={sub.id}
                subscription={sub}
                cancelling={cancellingId === sub.id}
                onCancelConfirm={(reason, immediate, feedback) =>
                  cancelSubscriptionById(sub.id, reason, immediate, feedback)
                }
              />
            ))}
          </div>
        )}

        {/* Past subscriptions (collapsed) — B-5: shows resubscribe button */}
        {!loading && inactiveSubscriptions.length > 0 && (
          <details className="mt-3">
            <summary className="cursor-pointer text-xs text-text-muted hover:text-text-primary transition-colors py-2 select-none">
              + {inactiveSubscriptions.length} {t("patronage.supporter.subscriptions.pastLabel")}
            </summary>
            <div className="space-y-3 mt-3">
              {inactiveSubscriptions.map((sub) => (
                <SubscriptionCard
                  key={sub.id}
                  subscription={sub}
                  cancelling={cancellingId === sub.id}
                  onCancelConfirm={(reason, immediate, feedback) =>
                    cancelSubscriptionById(sub.id, reason, immediate, feedback)
                  }
                  onResubscribe={handleResubscribe}
                  resubscribing={resubscribing}
                />
              ))}
            </div>
          </details>
        )}
      </section>

      {/* ── Section 3: One-time history ── */}
      <section>
        <h2 className="text-lg font-semibold text-text-primary mb-3">
          {t("patronage.supporter.history.title")}
        </h2>
        <SponsorshipHistory sponsorships={sponsorships} loading={loading} />
      </section>

      {/* ── Section 4: Tier benefits educational panel ── */}
      <TierBenefitsPanel collapsible />

      {/* ── Support landing link ── */}
      <div className="text-center py-2">
        <Link
          href="/support"
          className="text-xs text-text-muted hover:text-primary transition-colors"
        >
          {t("patronage.support.landing.intro")} →
        </Link>
      </div>
    </main>
  );
}
