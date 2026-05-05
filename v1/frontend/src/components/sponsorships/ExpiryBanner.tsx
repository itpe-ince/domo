"use client";

/**
 * ExpiryBanner — A-8 retention-loop-enhancement
 *
 * Shown on the /me/sponsorships dashboard when a subscription is expiring
 * within 7 days. The banner displays per-subscription with a "갱신하기" CTA
 * and a dismissable "잊기" link (7-day cooldown via useExpiryBanner).
 *
 * PostHog events: expiry_banner_view, expiry_banner_renew_click, expiry_banner_dismiss
 */

import { useEffect } from "react";
import Link from "next/link";
import { useI18n } from "@/i18n";
import { captureEvent } from "@/lib/analytics/capture";

type Props = {
  subscriptionId: string;
  artistId: string;
  artistName?: string;
  daysLeft: number;
  onDismiss: (subscriptionId: string) => void;
};

export function ExpiryBanner({
  subscriptionId,
  artistId,
  artistName,
  daysLeft,
  onDismiss,
}: Props) {
  const { t } = useI18n();

  // Fire PostHog view event on mount
  useEffect(() => {
    captureEvent({
      type: "expiry_banner_view",
      subscription_id: subscriptionId,
      days_until_expiry: daysLeft,
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [subscriptionId]);

  function handleRenewClick() {
    captureEvent({
      type: "expiry_banner_renew_click",
      subscription_id: subscriptionId,
    });
    // Navigate to artist page — renew flow handled there (placeholder for Stripe deep integration)
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

        <div className="flex items-center gap-3 flex-wrap">
          <Link
            href={`/users/${artistId}`}
            onClick={handleRenewClick}
            className="px-4 py-1.5 bg-amber-600 text-white rounded-full text-xs font-semibold hover:bg-amber-700 transition-colors"
          >
            {t("retention.expiry.banner.renewCta")}
          </Link>

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
