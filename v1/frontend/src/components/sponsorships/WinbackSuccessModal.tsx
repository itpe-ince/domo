"use client";

/**
 * WinbackSuccessModal — G'-2 winback-coupon-endpoint
 *
 * Shown after a winback coupon is successfully applied via
 * POST /v1/subscriptions/{id}/winback-coupon.
 *
 * Displays:
 *   - Coupon applied confirmation with discount details
 *   - Cancel reverted notice (subscription continues)
 *   - Close button → triggers page refresh to reflect active subscription
 *
 * z-index: [70] (above CancelSubscriptionModal's z-[60]).
 */

import { useEffect } from "react";
import { useI18n } from "@/i18n";
import type { WinbackCouponResponse } from "@/lib/api";

type Props = {
  open: boolean;
  couponResponse: WinbackCouponResponse | null;
  onClose: () => void;
};

export function WinbackSuccessModal({ open, couponResponse, onClose }: Props) {
  const { t } = useI18n();

  // ESC key closes modal (a11y)
  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [open, onClose]);

  if (!open || !couponResponse) return null;

  const { applied_coupon } = couponResponse;
  const discountLabel = `${applied_coupon.discount_value}%`;
  const durationLabel =
    applied_coupon.duration === "once"
      ? t("retention.winback.success.durationOnce")
      : applied_coupon.duration_in_months
        ? t("retention.winback.success.durationMonths", {
            months: String(applied_coupon.duration_in_months),
          })
        : "";

  return (
    <div
      className="fixed inset-0 z-[70] flex items-center justify-center"
      role="dialog"
      aria-modal="true"
      aria-label={t("retention.winback.success.title")}
    >
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/70"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Panel */}
      <div className="relative z-10 card w-full max-w-sm mx-4 p-6 space-y-5 text-center">
        {/* Icon */}
        <div className="text-4xl" aria-hidden="true">
          🎉
        </div>

        {/* Title */}
        <h2 className="text-lg font-bold text-text-primary">
          {t("retention.winback.success.title")}
        </h2>

        {/* Coupon details */}
        <div className="rounded-xl bg-primary/10 border border-primary/30 px-4 py-3 space-y-1">
          <p className="text-base font-semibold text-primary">
            {t("retention.winback.success.discountApplied", {
              discount: discountLabel,
            })}
          </p>
          {durationLabel ? (
            <p className="text-sm text-text-secondary">{durationLabel}</p>
          ) : null}
        </div>

        {/* Cancel reverted notice */}
        <p className="text-sm text-text-secondary">
          {t("retention.winback.success.cancelReverted")}
        </p>

        {/* Close CTA */}
        <button
          onClick={onClose}
          className="w-full btn-primary"
          autoFocus
        >
          {t("retention.winback.success.cta")}
        </button>
      </div>
    </div>
  );
}
