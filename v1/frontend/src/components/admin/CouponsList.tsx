"use client";

/**
 * CouponsList — D'-3 admin coupon table
 *
 * Displays issued coupons with delete action per row.
 */

import { useI18n } from "@/i18n";
import type { CouponView } from "@/lib/api";

type Props = {
  coupons: CouponView[];
  deletingId: string | null;
  onDelete: (id: string) => void;
};

function formatDiscount(coupon: CouponView): string {
  if (coupon.discount_type === "percent") {
    return `${coupon.discount_value}%`;
  }
  return `$${(coupon.discount_value / 100).toFixed(2)}`;
}

function formatDuration(coupon: CouponView): string {
  if (coupon.duration === "once") return "Once";
  if (coupon.duration === "forever") return "Forever";
  return `${coupon.duration_in_months}mo`;
}

export function CouponsList({ coupons, deletingId, onDelete }: Props) {
  const { t } = useI18n();

  if (coupons.length === 0) {
    return (
      <div className="text-center py-8 text-text-muted">
        {t("coupon.user.empty")}
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border text-left text-text-muted text-xs uppercase tracking-wide">
            <th className="py-2 pr-4">{t("coupon.admin.table.code")}</th>
            <th className="py-2 pr-4">{t("coupon.admin.table.discount")}</th>
            <th className="py-2 pr-4">{t("coupon.admin.table.duration")}</th>
            <th className="py-2 pr-4">{t("coupon.admin.table.redemptions")}</th>
            <th className="py-2 pr-4">{t("coupon.admin.table.status")}</th>
            <th className="py-2" />
          </tr>
        </thead>
        <tbody>
          {coupons.map((coupon) => (
            <tr key={coupon.id} className="border-b border-border hover:bg-surface/50">
              <td className="py-3 pr-4">
                <span className="font-mono font-semibold">{coupon.code ?? coupon.id}</span>
              </td>
              <td className="py-3 pr-4 text-primary font-medium">
                {formatDiscount(coupon)}
              </td>
              <td className="py-3 pr-4 text-text-secondary">
                {formatDuration(coupon)}
              </td>
              <td className="py-3 pr-4 text-text-secondary">
                {coupon.times_redeemed}
                {coupon.max_redemptions ? ` / ${coupon.max_redemptions}` : ""}
              </td>
              <td className="py-3 pr-4">
                <span
                  className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                    coupon.active
                      ? "bg-green-100 text-green-700"
                      : "bg-surface text-text-muted"
                  }`}
                >
                  {coupon.active ? "Active" : "Inactive"}
                </span>
              </td>
              <td className="py-3 text-right">
                <button
                  onClick={() => onDelete(coupon.id)}
                  disabled={deletingId === coupon.id}
                  className="text-xs text-red-500 hover:underline disabled:opacity-50"
                  aria-busy={deletingId === coupon.id}
                >
                  {deletingId === coupon.id
                    ? t("common.loading")
                    : t("coupon.admin.table.delete")}
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
