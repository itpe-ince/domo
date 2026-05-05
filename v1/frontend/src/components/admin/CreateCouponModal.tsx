"use client";

/**
 * CreateCouponModal — D'-3 admin coupon creation form
 *
 * Renders inside a modal overlay when `open=true`.
 * Validates client-side before submitting to useAdminCoupons.createCoupon.
 */

import { useState } from "react";
import { useI18n } from "@/i18n";
import type { AdminCreateCouponInput, CouponDiscountType, CouponDuration } from "@/lib/api";

type Props = {
  open: boolean;
  creating: boolean;
  createError: string | null;
  onSubmit: (input: AdminCreateCouponInput) => void;
  onClose: () => void;
};

const DURATION_OPTIONS: CouponDuration[] = ["once", "forever", "repeating"];
const DISCOUNT_TYPES: CouponDiscountType[] = ["percent", "amount"];

export function CreateCouponModal({
  open,
  creating,
  createError,
  onSubmit,
  onClose,
}: Props) {
  const { t } = useI18n();

  const [code, setCode] = useState("");
  const [discountType, setDiscountType] = useState<CouponDiscountType>("percent");
  const [discountValue, setDiscountValue] = useState<number>(50);
  const [duration, setDuration] = useState<CouponDuration>("once");
  const [durationInMonths, setDurationInMonths] = useState<number>(1);
  const [validUntil, setValidUntil] = useState<string>("");
  const [maxRedemptions, setMaxRedemptions] = useState<string>("");
  const [validationError, setValidationError] = useState<string | null>(null);

  if (!open) return null;

  function validate(): string | null {
    const sanitized = code.trim().toUpperCase();
    if (!/^[A-Za-z0-9_-]{4,50}$/.test(sanitized)) {
      return "Coupon code must be 4-50 chars: letters, digits, hyphens, underscores.";
    }
    if (discountType === "percent" && (discountValue < 1 || discountValue > 100)) {
      return "Percent discount must be between 1 and 100.";
    }
    if (discountType === "amount" && (discountValue < 1 || discountValue > 10000)) {
      return "Amount discount must be between 1 and 10000 cents.";
    }
    if (duration === "repeating" && (!durationInMonths || durationInMonths < 1)) {
      return "Duration in months is required for repeating coupons.";
    }
    return null;
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const err = validate();
    if (err) {
      setValidationError(err);
      return;
    }
    setValidationError(null);
    const input: AdminCreateCouponInput = {
      code: code.trim().toUpperCase(),
      discount_type: discountType,
      discount_value: discountValue,
      duration,
      duration_in_months: duration === "repeating" ? durationInMonths : null,
      valid_until: validUntil ? new Date(validUntil).toISOString() : null,
      max_redemptions: maxRedemptions ? parseInt(maxRedemptions, 10) : null,
    };
    onSubmit(input);
  }

  const displayError = validationError || createError;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      role="dialog"
      aria-modal="true"
      aria-label={t("coupon.admin.createCta")}
    >
      <div className="bg-white dark:bg-surface rounded-2xl shadow-xl w-full max-w-md mx-4 p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold text-text-primary">
            {t("coupon.admin.createCta")}
          </h2>
          <button
            onClick={onClose}
            className="text-text-muted hover:text-text-primary p-1 rounded-lg"
            aria-label={t("common.close")}
          >
            x
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Code */}
          <div>
            <label className="block text-sm font-medium text-text-secondary mb-1">
              {t("coupon.admin.form.label.code")}
            </label>
            <input
              type="text"
              value={code}
              onChange={(e) => setCode(e.target.value.toUpperCase())}
              placeholder="WINBACK50"
              maxLength={50}
              className="w-full input"
              required
            />
          </div>

          {/* Discount type */}
          <div>
            <label className="block text-sm font-medium text-text-secondary mb-1">
              {t("coupon.admin.form.label.discountType")}
            </label>
            <div className="flex gap-3">
              {DISCOUNT_TYPES.map((dt) => (
                <label key={dt} className="flex items-center gap-1.5 cursor-pointer">
                  <input
                    type="radio"
                    name="discountType"
                    value={dt}
                    checked={discountType === dt}
                    onChange={() => setDiscountType(dt)}
                  />
                  <span className="text-sm">{t(`coupon.admin.form.discountType.${dt}`)}</span>
                </label>
              ))}
            </div>
          </div>

          {/* Discount value */}
          <div>
            <label className="block text-sm font-medium text-text-secondary mb-1">
              {t("coupon.admin.form.label.discountValue")}
              {discountType === "percent" ? " (%)" : " (cents)"}
            </label>
            <input
              type="number"
              value={discountValue}
              onChange={(e) => setDiscountValue(parseInt(e.target.value, 10) || 0)}
              min={1}
              max={discountType === "percent" ? 100 : 10000}
              className="w-full input"
              required
            />
          </div>

          {/* Duration */}
          <div>
            <label className="block text-sm font-medium text-text-secondary mb-1">
              {t("coupon.admin.form.label.duration")}
            </label>
            <div className="flex gap-3">
              {DURATION_OPTIONS.map((d) => (
                <label key={d} className="flex items-center gap-1.5 cursor-pointer">
                  <input
                    type="radio"
                    name="duration"
                    value={d}
                    checked={duration === d}
                    onChange={() => setDuration(d)}
                  />
                  <span className="text-sm">{t(`coupon.admin.form.duration.${d}`)}</span>
                </label>
              ))}
            </div>
          </div>

          {/* Duration in months (only for repeating) */}
          {duration === "repeating" && (
            <div>
              <label className="block text-sm font-medium text-text-secondary mb-1">
                {t("coupon.admin.form.label.durationInMonths")}
              </label>
              <input
                type="number"
                value={durationInMonths}
                onChange={(e) => setDurationInMonths(parseInt(e.target.value, 10) || 1)}
                min={1}
                max={12}
                className="w-full input"
                required
              />
            </div>
          )}

          {/* Valid until (optional) */}
          <div>
            <label className="block text-sm font-medium text-text-secondary mb-1">
              {t("coupon.admin.form.label.validUntil")}
            </label>
            <input
              type="date"
              value={validUntil}
              onChange={(e) => setValidUntil(e.target.value)}
              className="w-full input"
            />
          </div>

          {/* Max redemptions (optional) */}
          <div>
            <label className="block text-sm font-medium text-text-secondary mb-1">
              {t("coupon.admin.form.label.maxRedemptions")}
            </label>
            <input
              type="number"
              value={maxRedemptions}
              onChange={(e) => setMaxRedemptions(e.target.value)}
              min={1}
              className="w-full input"
              placeholder="—"
            />
          </div>

          {displayError && (
            <p className="text-sm text-red-600" role="alert">
              {displayError}
            </p>
          )}

          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 btn-secondary"
              disabled={creating}
            >
              {t("common.cancel")}
            </button>
            <button
              type="submit"
              className="flex-1 btn-primary"
              disabled={creating}
              aria-busy={creating}
            >
              {creating ? t("common.loading") : t("coupon.admin.createCta")}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
