"use client";

/**
 * useMyCoupons — D'-3 coupon frontend hook
 *
 * Fetches the current user's applied coupons and exposes an apply mutation.
 */

import { useState, useEffect, useCallback } from "react";
import {
  fetchMyCoupons,
  applyMyCoupon,
  AppliedCouponView,
  ApiClientError,
} from "@/lib/api";

export type UseMyCouponsReturn = {
  coupons: AppliedCouponView[];
  loading: boolean;
  error: string | null;
  applying: boolean;
  applyError: string | null;
  applySuccess: string | null;
  applyCoupon: (
    code: string,
    subscriptionId?: string | null
  ) => Promise<AppliedCouponView | null>;
  refresh: () => void;
};

export function useMyCoupons(): UseMyCouponsReturn {
  const [coupons, setCoupons] = useState<AppliedCouponView[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [applying, setApplying] = useState(false);
  const [applyError, setApplyError] = useState<string | null>(null);
  const [applySuccess, setApplySuccess] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchMyCoupons();
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

  const applyCoupon = useCallback(
    async (
      code: string,
      subscriptionId?: string | null
    ): Promise<AppliedCouponView | null> => {
      setApplying(true);
      setApplyError(null);
      setApplySuccess(null);
      try {
        const applied = await applyMyCoupon({
          coupon_code: code.trim().toUpperCase(),
          subscription_id: subscriptionId ?? null,
        });
        setCoupons((prev) => [applied, ...prev]);
        setApplySuccess("coupon.user.applySuccess");
        return applied;
      } catch (e) {
        if (e instanceof ApiClientError) {
          setApplyError(e.message);
        } else {
          setApplyError("Failed to apply coupon");
        }
        return null;
      } finally {
        setApplying(false);
      }
    },
    []
  );

  return {
    coupons,
    loading,
    error,
    applying,
    applyError,
    applySuccess,
    applyCoupon,
    refresh: load,
  };
}
