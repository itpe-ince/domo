"use client";

/**
 * SubscriptionCard — B-3 supporter-dashboard
 *
 * Displays a single active/past_due/cancelled subscription with:
 *   - Artist avatar + display name link
 *   - Monthly amount + tier badge
 *   - Subscription status badge
 *   - Expandable "tier benefits" section
 *   - Cancel subscription action (opens CancelSubscriptionModal)
 *   - Placeholder "change amount" CTA (B-5 scope)
 *   - D'-3: active coupon inline badge
 *   - B'-4: auto_renew toggle + expiry 7d warning + "지금 갱신" button
 */

import { useState } from "react";
import Link from "next/link";
import { useI18n } from "@/i18n";
import type { SubscriptionView, AppliedCouponView } from "@/lib/api";
import type { CancelReason } from "@/lib/hooks/useMySponsorships";
import { CancelSubscriptionModal } from "./CancelSubscriptionModal";

const STATUS_COLORS: Record<string, string> = {
  active: "bg-green-100 text-green-700",
  past_due: "bg-amber-100 text-amber-700",
  cancelled: "bg-surface text-text-muted",
  incomplete: "bg-surface text-text-muted",
};

const TIER_LABEL_COLORS: Record<string, string> = {
  subscriber: "bg-amber-100 text-amber-700 border-amber-200",
  sponsor: "bg-blue-100 text-blue-700 border-blue-200",
  follower: "bg-green-100 text-green-700 border-green-200",
};

function getTierFromBluebirds(monthly_bluebird: number): string {
  // Platform default tiers based on monthly bluebird count (OQ-5=C placeholder)
  if (monthly_bluebird >= 10) return "sponsor";
  if (monthly_bluebird >= 3) return "subscriber";
  return "follower";
}

/** Days until current_period_end. Returns null if no period end. */
function daysUntilExpiry(current_period_end: string | null): number | null {
  if (!current_period_end) return null;
  const end = new Date(current_period_end);
  const now = new Date();
  const diff = Math.floor((end.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
  return diff;
}

type Props = {
  subscription: SubscriptionView;
  cancelling: boolean;
  onCancelConfirm: (reason: CancelReason, immediate: boolean, feedback?: string) => void;
  /** B-5: called when user clicks "다시 구독" on a cancelled card */
  onResubscribe?: (artistId: string) => void;
  resubscribing?: boolean;
  /** D'-3: active coupon applied to this subscription (if any) */
  activeCoupon?: AppliedCouponView | null;
  /** B'-4: manual renew handler */
  onRenew?: (subscriptionId: string) => void;
  renewing?: boolean;
  /** B'-4: auto-renew toggle handler */
  onToggleAutoRenew?: (subscriptionId: string, enabled: boolean) => void;
  togglingAutoRenew?: boolean;
};

export function SubscriptionCard({
  subscription,
  cancelling,
  onCancelConfirm,
  onResubscribe,
  resubscribing = false,
  activeCoupon = null,
  onRenew,
  renewing = false,
  onToggleAutoRenew,
  togglingAutoRenew = false,
}: Props) {
  const { t } = useI18n();
  const [benefitsOpen, setBenefitsOpen] = useState(false);
  const [cancelModalOpen, setCancelModalOpen] = useState(false);

  const tier = getTierFromBluebirds(subscription.monthly_bluebird);
  const isActive = subscription.status === "active" || subscription.status === "past_due";
  const isCancelled =
    subscription.status === "cancelled" || subscription.cancel_at_period_end;

  const daysLeft = daysUntilExpiry(subscription.current_period_end);
  // Show expiry warning when 7 days or fewer remain and subscription is active
  const showExpiryWarning =
    isActive &&
    !isCancelled &&
    daysLeft !== null &&
    daysLeft >= 0 &&
    daysLeft <= 7;

  const tierBenefits: Record<string, string[]> = {
    subscriber: [
      t("patronage.supporter.tier.benefits.subscriber"),
    ],
    sponsor: [
      t("patronage.supporter.tier.benefits.sponsor"),
    ],
    follower: [
      t("patronage.supporter.tier.benefits.follower"),
    ],
  };

  const sinceDate = new Date(subscription.created_at).toLocaleDateString();
  const periodEndDate = subscription.current_period_end
    ? new Date(subscription.current_period_end).toLocaleDateString()
    : null;

  // Artist display — we only have artist_id from the subscription row.
  // Full name hydration would require fetching /v1/users/{id}; for MVP we
  // show the ID abbreviated to avoid N+1 fetches on this page.
  // B-4/B-5 can hydrate artist names via a batch endpoint.
  const artistShortId = subscription.artist_id.slice(0, 8);

  return (
    <>
      <div className="card overflow-hidden">
        {/* Card header */}
        <div className="p-4 flex items-start gap-4">
          {/* Artist avatar placeholder */}
          <Link
            href={`/users/${subscription.artist_id}`}
            className="flex-shrink-0 w-12 h-12 rounded-full bg-surface-hover flex items-center justify-center text-primary font-bold text-lg hover:opacity-80 transition-opacity"
            aria-label={`Artist ${artistShortId}`}
          >
            {artistShortId.charAt(0).toUpperCase()}
          </Link>

          {/* Info */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <Link
                href={`/users/${subscription.artist_id}`}
                className="font-semibold text-text-primary hover:underline truncate"
              >
                @{artistShortId}
              </Link>

              {/* Tier badge */}
              <span
                className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${TIER_LABEL_COLORS[tier] ?? "bg-surface text-text-muted border-border"}`}
              >
                {tier}
              </span>

              {/* Status badge */}
              <span
                className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_COLORS[subscription.status] ?? "bg-surface text-text-muted"}`}
              >
                {subscription.status}
                {subscription.cancel_at_period_end && ` · ${t("patronage.supporter.subscriptions.cancelAtEnd")}`}
              </span>

              {/* B'-4: auto-renew badge */}
              {isActive && !isCancelled && (
                <span
                  className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${
                    subscription.auto_renew_enabled
                      ? "bg-blue-50 text-blue-600 border-blue-200"
                      : "bg-surface text-text-muted border-border"
                  }`}
                >
                  {subscription.auto_renew_enabled
                    ? t("subscription.renewal.autoOn")
                    : t("subscription.renewal.autoOff")}
                </span>
              )}
            </div>

            <div className="mt-1 flex flex-wrap gap-x-4 gap-y-0.5 text-xs text-text-muted">
              <span>
                {t("patronage.supporter.subscriptions.since")}: {sinceDate}
              </span>
              <span className="font-medium text-text-primary">
                ${parseFloat(subscription.monthly_amount).toFixed(2)}/mo
              </span>
              {periodEndDate && (
                <span>
                  {subscription.cancel_at_period_end
                    ? `${t("patronage.supporter.subscriptions.cancelAtEnd")}: ${periodEndDate}`
                    : `Renews: ${periodEndDate}`}
                </span>
              )}
            </div>

            {/* D'-3: Active coupon badge */}
            {activeCoupon && activeCoupon.discount_type === "percent" && (
              <div className="mt-1.5 inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-amber-50 text-amber-700 border border-amber-200">
                <span>🎟</span>
                <span>
                  {t("coupon.subscription.appliedBadge").replace(
                    "{{discount}}",
                    String(activeCoupon.discount_value)
                  )}
                </span>
                {activeCoupon.duration === "repeating" && activeCoupon.duration_in_months && (
                  <span className="text-amber-500">
                    ({activeCoupon.duration_in_months}mo)
                  </span>
                )}
              </div>
            )}
          </div>
        </div>

        {/* G'-1: past_due amber warning banner */}
        {subscription.status === "past_due" && (
          <div className="mx-4 mb-2 px-3 py-2 rounded-md bg-amber-50 border border-amber-200 flex items-start gap-2">
            <span className="text-amber-500 mt-0.5 flex-shrink-0" aria-hidden="true">⚠</span>
            <div className="flex-1 min-w-0">
              <p className="text-xs font-semibold text-amber-800">
                {t("webhook.notification.subscription_payment_failed")}
              </p>
              <a
                href="/me/settings/payment"
                className="text-xs text-amber-700 underline hover:text-amber-900"
              >
                {t("webhook.notification.update_payment_method")}
              </a>
            </div>
          </div>
        )}

        {/* B'-4: 7-day expiry warning inline banner */}
        {showExpiryWarning && (
          <div className="mx-4 mb-2 px-3 py-2 rounded-md bg-amber-50 border border-amber-200 flex items-center justify-between gap-2">
            <div className="flex items-center gap-2 min-w-0">
              <span className="text-amber-500 flex-shrink-0" aria-hidden="true">⏳</span>
              <p className="text-xs font-medium text-amber-800">
                {t("subscription.renewal.expiryWarning").replace("{{days}}", String(daysLeft))}
              </p>
            </div>
            {onRenew && (
              <button
                onClick={() => onRenew(subscription.id)}
                disabled={renewing}
                className="flex-shrink-0 px-3 py-1 text-xs font-semibold bg-amber-600 text-white rounded-full hover:bg-amber-700 transition-colors disabled:opacity-50"
                aria-busy={renewing}
              >
                {renewing
                  ? t("subscription.renewal.renewing")
                  : t("subscription.renewal.renewNow")}
              </button>
            )}
          </div>
        )}

        {/* Tier benefits expand */}
        {benefitsOpen && (
          <div className="border-t border-border px-4 py-3 bg-surface/50">
            <p className="text-xs font-semibold text-text-muted uppercase tracking-wide mb-2">
              {t("patronage.supporter.tier.benefits.title")}
            </p>
            <ul className="text-sm text-text-secondary space-y-1">
              {(tierBenefits[tier] ?? []).map((benefit, i) => (
                <li key={i} className="flex items-start gap-2">
                  <span className="mt-0.5 text-primary">•</span>
                  <span>{benefit}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Actions */}
        <div className="border-t border-border px-4 py-2.5 flex items-center gap-2 flex-wrap">
          <button
            onClick={() => setBenefitsOpen((v) => !v)}
            className="text-xs text-primary hover:underline"
          >
            {benefitsOpen
              ? "− " + t("patronage.supporter.subscriptions.benefits")
              : "+ " + t("patronage.supporter.subscriptions.benefits")}
          </button>

          <span className="text-border text-xs">|</span>

          {/* Change amount — B-5 placeholder */}
          <button
            disabled
            className="text-xs text-text-muted cursor-not-allowed opacity-50"
            title="Coming soon"
          >
            {t("patronage.supporter.subscriptions.changeAmount")}
          </button>

          {/* B'-4: Auto-renew toggle (active subscriptions only) */}
          {isActive && !isCancelled && onToggleAutoRenew && (
            <>
              <span className="text-border text-xs">|</span>
              <button
                onClick={() =>
                  onToggleAutoRenew(subscription.id, !subscription.auto_renew_enabled)
                }
                disabled={togglingAutoRenew}
                className="text-xs text-text-secondary hover:text-text-primary transition-colors disabled:opacity-50"
                aria-busy={togglingAutoRenew}
                title={
                  subscription.auto_renew_enabled
                    ? t("subscription.renewal.disableAutoRenew")
                    : t("subscription.renewal.enableAutoRenew")
                }
              >
                {subscription.auto_renew_enabled
                  ? t("subscription.renewal.disableAutoRenew")
                  : t("subscription.renewal.enableAutoRenew")}
              </button>
            </>
          )}

          {isActive && !isCancelled && (
            <>
              <span className="text-border text-xs">|</span>
              <button
                onClick={() => setCancelModalOpen(true)}
                className="text-xs text-red-500 hover:underline ml-auto"
              >
                {t("patronage.supporter.subscriptions.cancel")}
              </button>
            </>
          )}

          {/* B-5: Resubscribe button for cancelled subscriptions */}
          {!isActive && subscription.status === "cancelled" && onResubscribe && (
            <>
              <span className="text-border text-xs">|</span>
              <button
                onClick={() => onResubscribe(subscription.artist_id)}
                disabled={resubscribing}
                className="text-xs text-primary hover:underline ml-auto disabled:opacity-50"
                aria-busy={resubscribing}
              >
                {resubscribing
                  ? t("retention.resubscribe.confirming")
                  : t("retention.resubscribe.cta")}
              </button>
            </>
          )}

          {/* B'-4: Manual renew for cancel_at_period_end subscriptions */}
          {isActive && subscription.cancel_at_period_end && onRenew && !showExpiryWarning && (
            <>
              <span className="text-border text-xs">|</span>
              <button
                onClick={() => onRenew(subscription.id)}
                disabled={renewing}
                className="text-xs text-primary hover:underline disabled:opacity-50"
                aria-busy={renewing}
              >
                {renewing
                  ? t("subscription.renewal.renewing")
                  : t("subscription.renewal.renewNow")}
              </button>
            </>
          )}
        </div>
      </div>

      {/* Cancel modal */}
      <CancelSubscriptionModal
        open={cancelModalOpen}
        subscriptionId={subscription.id}
        artistName={artistShortId}
        artistId={subscription.artist_id}
        currentPeriodEnd={subscription.current_period_end}
        cancelling={cancelling}
        onConfirm={(reason, immediate, feedback) => {
          onCancelConfirm(reason, immediate, feedback);
          setCancelModalOpen(false);
        }}
        onClose={() => setCancelModalOpen(false)}
      />
    </>
  );
}
