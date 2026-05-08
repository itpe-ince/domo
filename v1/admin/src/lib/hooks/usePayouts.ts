"use client";

import { useCallback, useState } from "react";
import {
  KYCPendingItem,
  KYCPendingResponse,
  SettlementDetail,
  SettlementListItem,
  SettlementsResponse,
  StripeConnectStatus,
  adminApproveKyc,
  adminGetKycPending,
  adminGetSettlementDetail,
  adminGetSettlements,
  adminGetStripeConnectStatus,
  adminRejectKyc,
} from "@/lib/api";

// ─── KYC Queue hook ───────────────────────────────────────────────────────────

export function useKycQueue() {
  const [data, setData] = useState<KYCPendingResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<string | null>(null); // user_id

  const load = useCallback(
    async (params?: { limit?: number; offset?: number }) => {
      setLoading(true);
      setError(null);
      try {
        const res = await adminGetKycPending(params);
        setData(res);
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : "KYC 큐를 불러오지 못했습니다.");
      } finally {
        setLoading(false);
      }
    },
    []
  );

  const removeFromQueue = useCallback((userId: string) => {
    setData((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        data: prev.data.filter((item) => item.user_id !== userId),
        pagination: {
          ...prev.pagination,
          total: Math.max(0, prev.pagination.total - 1),
        },
      };
    });
  }, []);

  const approve = useCallback(
    async (item: KYCPendingItem) => {
      setActionLoading(item.user_id);
      setError(null);
      try {
        await adminApproveKyc(item.user_id);
        removeFromQueue(item.user_id);
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : "KYC 승인에 실패했습니다.");
      } finally {
        setActionLoading(null);
      }
    },
    [removeFromQueue]
  );

  const reject = useCallback(
    async (item: KYCPendingItem, reason: string) => {
      setActionLoading(item.user_id);
      setError(null);
      try {
        await adminRejectKyc(item.user_id, reason);
        removeFromQueue(item.user_id);
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : "KYC 거부에 실패했습니다.");
      } finally {
        setActionLoading(null);
      }
    },
    [removeFromQueue]
  );

  return { data, loading, error, load, approve, reject, actionLoading };
}

// ─── Settlements hook ─────────────────────────────────────────────────────────

export interface SettlementFilters {
  month?: string;
  artist_id?: string;
  status?: string;
  limit?: number;
  offset?: number;
}

export function useSettlements() {
  const [data, setData] = useState<SettlementsResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (filters?: SettlementFilters) => {
    setLoading(true);
    setError(null);
    try {
      const res = await adminGetSettlements(filters);
      setData(res);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "정산 이력을 불러오지 못했습니다.");
    } finally {
      setLoading(false);
    }
  }, []);

  return { data, loading, error, load };
}

export function useSettlementDetail(id: string | null) {
  const [data, setData] = useState<SettlementDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      const res = await adminGetSettlementDetail(id);
      setData(res);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "정산 상세를 불러오지 못했습니다.");
    } finally {
      setLoading(false);
    }
  }, [id]);

  return { data, loading, error, load };
}

// ─── Stripe Connect hook ──────────────────────────────────────────────────────

export function useStripeConnectStatus() {
  const [statusMap, setStatusMap] = useState<Record<string, StripeConnectStatus>>({});
  const [loading, setLoading] = useState<string | null>(null); // artistId
  const [error, setError] = useState<string | null>(null);

  const fetchStatus = useCallback(async (artistId: string) => {
    setLoading(artistId);
    setError(null);
    try {
      const res = await adminGetStripeConnectStatus(artistId);
      setStatusMap((prev) => ({ ...prev, [artistId]: res }));
      return res;
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Stripe 상태를 불러오지 못했습니다.");
      return null;
    } finally {
      setLoading(null);
    }
  }, []);

  return { statusMap, loading, error, fetchStatus };
}
