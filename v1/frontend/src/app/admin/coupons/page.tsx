"use client";

/**
 * /admin/coupons — D'-3 admin coupon management page
 *
 * Admin-only: guarded by role check. Displays issued coupons and allows
 * creating + deleting coupons via the admin coupon API.
 */

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useI18n } from "@/i18n";
import { fetchMe } from "@/lib/api";
import { useAdminCoupons } from "@/lib/hooks/useAdminCoupons";
import { CreateCouponModal } from "@/components/admin/CreateCouponModal";
import { CouponsList } from "@/components/admin/CouponsList";
import type { AdminCreateCouponInput } from "@/lib/api";

export default function AdminCouponsPage() {
  const { t } = useI18n();
  const router = useRouter();
  const [authChecking, setAuthChecking] = useState(true);
  const [isAdmin, setIsAdmin] = useState(false);
  const [createModalOpen, setCreateModalOpen] = useState(false);

  const {
    coupons,
    loading,
    error,
    creating,
    createError,
    deletingId,
    deleteError,
    createCoupon,
    deleteCoupon,
    refresh,
  } = useAdminCoupons();

  // Auth gate — redirect non-admins
  useEffect(() => {
    fetchMe()
      .then((user) => {
        if (user.role !== "admin") {
          router.replace("/");
        } else {
          setIsAdmin(true);
        }
      })
      .catch(() => {
        router.replace("/");
      })
      .finally(() => {
        setAuthChecking(false);
      });
  }, [router]);

  async function handleCreate(input: AdminCreateCouponInput) {
    const result = await createCoupon(input);
    if (result) {
      setCreateModalOpen(false);
    }
  }

  async function handleDelete(id: string) {
    if (!window.confirm(`Delete coupon "${id}"?`)) return;
    await deleteCoupon(id);
  }

  if (authChecking) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <p className="text-text-muted">{t("common.loading")}</p>
      </div>
    );
  }

  if (!isAdmin) return null;

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-text-primary">
          {t("coupon.admin.title")}
        </h1>
        <button
          onClick={() => setCreateModalOpen(true)}
          className="btn-primary text-sm"
        >
          + {t("coupon.admin.createCta")}
        </button>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
          {error}
        </div>
      )}

      {deleteError && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
          {deleteError}
        </div>
      )}

      {loading ? (
        <div className="text-center py-8 text-text-muted">{t("common.loading")}</div>
      ) : (
        <div className="card p-0 overflow-hidden">
          <CouponsList
            coupons={coupons}
            deletingId={deletingId}
            onDelete={handleDelete}
          />
        </div>
      )}

      <CreateCouponModal
        open={createModalOpen}
        creating={creating}
        createError={createError}
        onSubmit={handleCreate}
        onClose={() => setCreateModalOpen(false)}
      />
    </div>
  );
}
