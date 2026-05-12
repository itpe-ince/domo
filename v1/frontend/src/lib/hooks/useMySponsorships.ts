"use client";

/**
 * useMySponsorships — B-3 supporter-dashboard
 *
 * Fetches the current user's one-time sponsorships and active subscriptions,
 * computes summary statistics from the raw data, and exposes a cancel mutation.
 *
 * Intentionally keeps backend calls minimal: reuses the two existing endpoints
 * GET /v1/sponsorships/mine and GET /v1/subscriptions/mine.
 * Summary stats (lifetime amount, top artists) are computed client-side to
 * avoid a new backend endpoint — acceptable for MVP supporter volume.
 */

import { useState, useEffect, useCallback } from "react";
import {
  fetchMySponsorships,
  fetchMySubscriptions,
  cancelSubscription,
  SponsorshipView,
  SubscriptionView,
  ApiClientError,
} from "@/lib/api";

// B-5: optional feedback string passed alongside cancel reason
export type CancelFeedback = string | undefined;

export type SupporterSummary = {
  artistsCount: number;
  lifetimeAmountCents: number;
  activeSubscriptionsCount: number;
  topArtists: { artist_id: string; amount_cents: number }[];
};

function computeSummary(
  sponsorships: SponsorshipView[],
  subscriptions: SubscriptionView[]
): SupporterSummary {
  // Lifetime = all succeeded one-time + monthly amounts already charged
  const lifetimeAmountCents = sponsorships
    .filter((s) => s.status === "succeeded" || s.status === "completed")
    .reduce((acc, s) => acc + Math.round(parseFloat(s.amount) * 100), 0);

  const activeSubscriptions = subscriptions.filter(
    (s) => s.status === "active" || s.status === "past_due"
  );

  // Unique artists from either source
  const artistIds = new Set([
    ...sponsorships.map((s) => s.artist_id),
    ...subscriptions.map((s) => s.artist_id),
  ]);

  // Top artists by one-time sponsorship amount
  const artistTotals: Record<string, number> = {};
  for (const s of sponsorships) {
    if (!artistTotals[s.artist_id]) artistTotals[s.artist_id] = 0;
    artistTotals[s.artist_id] += Math.round(parseFloat(s.amount) * 100);
  }
  const topArtists = Object.entries(artistTotals)
    .map(([artist_id, amount_cents]) => ({ artist_id, amount_cents }))
    .sort((a, b) => b.amount_cents - a.amount_cents)
    .slice(0, 5);

  return {
    artistsCount: artistIds.size,
    lifetimeAmountCents,
    activeSubscriptionsCount: activeSubscriptions.length,
    topArtists,
  };
}

export type CancelReason =
  | "too_expensive"
  | "changed_mind"
  | "not_satisfied"
  | "other";

export type UseMySponsorshipsReturn = {
  sponsorships: SponsorshipView[];
  subscriptions: SubscriptionView[];
  summary: SupporterSummary;
  loading: boolean;
  error: string | null;
  cancellingId: string | null;
  cancelError: string | null;
  cancelSubscriptionById: (
    id: string,
    reason: CancelReason,
    immediate: boolean,
    feedback?: CancelFeedback
  ) => Promise<boolean>;
  refresh: () => void;
};

export function useMySponsorships(): UseMySponsorshipsReturn {
  const [sponsorships, setSponsorships] = useState<SponsorshipView[]>([]);
  const [subscriptions, setSubscriptions] = useState<SubscriptionView[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [cancellingId, setCancellingId] = useState<string | null>(null);
  const [cancelError, setCancelError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [sp, sub] = await Promise.all([
        fetchMySponsorships(),
        fetchMySubscriptions(),
      ]);
      setSponsorships(sp);
      setSubscriptions(sub);
    } catch (e) {
      if (e instanceof ApiClientError) {
        setError(e.message);
      } else {
        setError("Failed to load sponsorship data");
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const cancelSubscriptionById = useCallback(
    async (
      id: string,
      reason: CancelReason,
      immediate: boolean,
      feedback?: CancelFeedback
    ): Promise<boolean> => {
      setCancellingId(id);
      setCancelError(null);
      try {
        // B-5: pass reason + feedback to backend; backward-compat body is optional
        const updated = await cancelSubscription(id, {
          reason,
          feedback: feedback?.trim() || undefined,
          immediate,
        });
        setSubscriptions((prev) =>
          prev.map((s) => (s.id === id ? updated : s))
        );
        return true;
      } catch (e) {
        if (e instanceof ApiClientError) {
          setCancelError(e.message);
        } else {
          setCancelError("Failed to cancel subscription");
        }
        return false;
      } finally {
        setCancellingId(null);
      }
    },
    []
  );

  const summary = computeSummary(sponsorships, subscriptions);

  return {
    sponsorships,
    subscriptions,
    summary,
    loading,
    error,
    cancellingId,
    cancelError,
    cancelSubscriptionById,
    refresh: load,
  };
}
