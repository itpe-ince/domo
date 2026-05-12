"use client";

/**
 * ExpiryBanner — A-8 retention-loop-enhancement + B'-4 auto-renewal booster
 *
 * Shown on the /me/sponsorships dashboard when a subscription is expiring
 * within 7 days. The banner displays per-subscription with a "갱신하기" CTA
 * that now calls POST /subscriptions/{id}/renew (B'-4) and a dismissable
 * "잊기" link (7-day cooldown via useExpiryBanner).
 *
 * On successful renewal: shows updated expiry date (+30d refresh indication).
 *
 * PostHog events: expiry_banner_view, expiry_banner_renew_click, expiry_banner_dismiss,
 *                 expiry_banner_renew_success (B'-4)
 */

import { useEffect, useState } from "react";
import { useI18n } from "@/i18n";
import { captureEvent } from "@/lib/analytics/capture";
import { renewSubscription } from "@/lib/api";

type Props = {
  subscriptionId: string;
  artistId: string;
  artistName?: string;
  daysLeft: number;
  onDismiss: (subscriptionId: string) => void;
  /** B'-4: called after successful renewal so parent can refresh subscription list */
  onRenewSuccess?: (subscriptionId: string) => void;
};

export function ExpiryBanner({
  subscriptionId,
  artistId,
  artistName,
  daysLeft,
  onDismiss,
  onRenewSuccess,
}: Props) {
  const { t } = useI18n();
  const [renewing, setRenewing] = useState(false);
  const [renewError, setRenewError] = useState<string | null>(null);
  const [renewedPeriodEnd, setRenewedPeriodEnd] = useState<string | null>(null);

  // Fire PostHog view event on mount
  useEffect(() => {
    captureEvent({
      type: "expiry_banner_view",
      subscription_id: subscriptionId,
      days_until_expiry: daysLeft,
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [subscriptionId]);

  async function handleRenewClick() {
    captureEvent({
      type: "expiry_banner_renew_click",
      subscription_id: subscriptionId,
    });

    setRenewing(true);
    setRenewError(null);
    try {
      const res = await renewSubscription(subscriptionId);
      const updated = (res as { data?: { current_period_end?: string | null }; current_period_end?: string | null }).data ?? res;
      const newPeriodEnd = (updated as { current_period_end?: string | null }).current_period_end;
      if (newPeriodEnd) {
        setRenewedPeriodEnd(new Date(newPeriodEnd).toLocaleDateString());
      }
      captureEvent({
        type: "expiry_banner_renew_click",
        subscription_id: subscriptionId,
      });
      onRenewSuccess?.(subscriptionId);
    } catch (err) {
      const msg = err instanceof Error ? err.message : t("subscription.renewal.renewError");
      setRenewError(msg);
    } finally {
      setRenewing(false);
    }
  }

  function handleDismiss() {
    captureEvent({
      type: "expiry_banner_dismiss",
      subscription_id: subscriptionId,
    });
    onDismiss(subscriptionId);
  }

  const label = t("retention.expiry.banner.title")
    .replace("{{artistName}}", artistName ?? `@${artistId.slice(0, 8)}`)
    .replace("{{days}}", String(daysLeft));

  // Post-renewal success state
  if (renewedPeriodEnd) {
    return (
      <div
        role="alert"
        className="rounded-xl border border-green-300 bg-green-50 px-5 py-4 flex items-center gap-3"
      >
        <span className="text-2xl flex-shrink-0" aria-hidden="true">✅</span>
        <p className="text-sm font-semibold text-green-900">
          {t("subscription.renewal.renewSuccess").replace("{{date}}", renewedPeriodEnd)}
        </p>
      </div>
    );
  }

  return (
    <div
      role="alert"
      aria-label={label}
      className="rounded-xl border border-amber-300 bg-amber-50 px-5 py-4 flex items-start gap-4"
    >
      <span className="text-2xl flex-shrink-0 mt-0.5" aria-hidden="true">⏳</span>

      <div className="flex-1 min-w-0 space-y-2">
        <div>
          <p className="text-sm font-semibold text-amber-900">
            {label}
          </p>
          <p className="text-xs text-amber-700 mt-0.5">
            {t("retention.expiry.banner.subtitle")}
          </p>
        </div>

        {renewError && (
          <p className="text-xs text-red-600">{renewError}</p>
        )}

        <div className="flex items-center gap-3 flex-wrap">
          <button
            onClick={handleRenewClick}
            disabled={renewing}
            className="px-4 py-1.5 bg-amber-600 text-white rounded-full text-xs font-semibold hover:bg-amber-700 transition-colors disabled:opacity-50"
            aria-busy={renewing}
          >
            {renewing
              ? t("subscription.renewal.renewing")
              : t("retention.expiry.banner.renewCta")}
          </button>

          <button
            onClick={handleDismiss}
            className="text-xs text-amber-600 hover:text-amber-800 transition-colors"
            aria-label={t("retention.expiry.banner.dismiss")}
          >
            {t("retention.expiry.banner.dismiss")}
          </button>
        </div>
      </div>
    </div>
  );
}
