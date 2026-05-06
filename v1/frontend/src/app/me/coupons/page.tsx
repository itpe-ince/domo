"use client";

/**
 * /me/coupons — D'-3 user coupon management page
 *
 * Allows authenticated users to:
 *   1. Enter and apply a coupon code to their active subscription
 *   2. View their list of applied coupons with status
 */

import { useState } from "react";
import { useI18n } from "@/i18n";
import { useMyCoupons } from "@/lib/hooks/useMyCoupons";
import type { AppliedCouponView } from "@/lib/api";

function formatDiscount(coupon: AppliedCouponView): string {
  if (coupon.discount_type === "percent") {
    return `${coupon.discount_value}%`;
  }
  return `$${(coupon.discount_value / 100).toFixed(2)}`;
}

function formatDuration(coupon: AppliedCouponView): string {
  if (coupon.duration === "once") return "Once";
  if (coupon.duration === "forever") return "Forever";
  return `${coupon.duration_in_months} month(s)`;
}

export default function MyCouponsPage() {
  const { t } = useI18n();
  const {
    coupons,
    loading,
    error,
    applying,
    applyError,
    applySuccess,
    applyCoupon,
  } = useMyCoupons();

  const [codeInput, setCodeInput] = useState("");

  async function handleApply(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = codeInput.trim();
    if (!trimmed) return;
    await applyCoupon(trimmed);
    setCodeInput("");
  }

  return (
    <main className="max-w-2xl mx-auto px-4 py-8" aria-label={t("coupon.user.title")}>
      <h1 className="text-2xl font-bold text-text-primary mb-6">
        {t("coupon.user.title")}
      </h1>

      {/* Apply coupon form */}
      <div className="card p-5 mb-6">
        <form onSubmit={handleApply} className="flex gap-3">
          <input
            type="text"
            value={codeInput}
            onChange={(e) => setCodeInput(e.target.value.toUpperCase())}
            placeholder={t("coupon.user.applyPlaceholder")}
            maxLength={50}
            className="flex-1 input font-mono"
            aria-label={t("coupon.user.applyCta")}
          />
          <button
            type="submit"
            disabled={applying || !codeInput.trim()}
            className="btn-primary px-5 disabled:opacity-50"
            aria-busy={applying}
          >
            {applying ? t("common.loading") : t("coupon.user.applyCta")}
          </button>
        </form>

        {applyError && (
          <p className="mt-2 text-sm text-red-600" role="alert">
            {applyError}
          </p>
        )}

        {applySuccess && (
          <p className="mt-2 text-sm text-green-600" role="status">
            {t("coupon.user.applySuccess")}
          </p>
        )}
      </div>

      {/* Applied coupons list */}
      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
          {error}
        </div>
      )}

      {loading ? (
        <div className="text-center py-8 text-text-muted">{t("common.loading")}</div>
      ) : coupons.length === 0 ? (
        <div className="text-center py-8 text-text-muted">{t("coupon.user.empty")}</div>
      ) : (
        <ul className="space-y-3">
          {coupons.map((coupon) => (
            <li key={coupon.id} className="card p-4">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <p className="font-mono font-semibold text-text-primary">
                    {coupon.coupon_code ?? coupon.stripe_coupon_id}
                  </p>
                  <p className="mt-0.5 text-sm text-primary font-medium">
                    {formatDiscount(coupon)} — {formatDuration(coupon)}
                  </p>
                  {coupon.valid_until && (
                    <p className="mt-0.5 text-xs text-text-muted">
                      {t("coupon.user.active.expiry")}:{" "}
                      {new Date(coupon.valid_until).toLocaleDateString()}
                    </p>
                  )}
                </div>
                <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-700">
                  {t("coupon.user.active.label")}
                </span>
              </div>
              <p className="mt-1.5 text-xs text-text-muted">
                Applied: {new Date(coupon.applied_at).toLocaleDateString()}
              </p>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
