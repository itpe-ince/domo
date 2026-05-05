"use client";

/**
 * useAdminCoupons — D'-3 admin coupon management hook
 *
 * Manages creation, listing, and deletion of coupons from the admin panel.
 */

import { useState, useEffect, useCallback } from "react";
import {
  adminListCoupons,
  adminCreateCoupon,
  adminDeleteCoupon,
  CouponView,
  AdminCreateCouponInput,
  ApiClientError,
} from "@/lib/api";

export type UseAdminCouponsReturn = {
  coupons: CouponView[];
  loading: boolean;
  error: string | null;
  creating: boolean;
  createError: string | null;
  deletingId: string | null;
  deleteError: string | null;
  createCoupon: (input: AdminCreateCouponInput) => Promise<CouponView | null>;
  deleteCoupon: (id: string) => Promise<boolean>;
  refresh: () => void;
};

export function useAdminCoupons(): UseAdminCouponsReturn {
  const [coupons, setCoupons] = useState<CouponView[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await adminListCoupons({ limit: 50 });
      setCoupons(data);
    } catch (e) {
      if (e instanceof ApiClientError) {
        setError(e.message);
      } else {
        setError("Failed to load coupons");
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const createCoupon = useCallback(
    async (input: AdminCreateCouponInput): Promise<CouponView | null> => {
      setCreating(true);
      setCreateError(null);
      try {
        const coupon = await adminCreateCoupon(input);
        setCoupons((prev) => [coupon, ...prev]);
        return coupon;
      } catch (e) {
        if (e instanceof ApiClientError) {
          setCreateError(e.message);
        } else {
          setCreateError("Failed to create coupon");
        }
        return null;
      } finally {
        setCreating(false);
      }
    },
    []
  );

  const deleteCoupon = useCallback(async (id: string): Promise<boolean> => {
    setDeletingId(id);
    setDeleteError(null);
    try {
      await adminDeleteCoupon(id);
      setCoupons((prev) => prev.filter((c) => c.id !== id));
      return true;
    } catch (e) {
      if (e instanceof ApiClientError) {
        setDeleteError(e.message);
      } else {
        setDeleteError("Failed to delete coupon");
      }
      return false;
    } finally {
      setDeletingId(null);
    }
  }, []);

  return {
    coupons,
    loading,
    error,
    creating,
    createError,
    deletingId,
    deleteError,
    createCoupon,
    deleteCoupon,
    refresh: load,
  };
}
