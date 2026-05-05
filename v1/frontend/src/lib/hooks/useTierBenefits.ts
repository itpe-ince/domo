"use client";

/**
 * useTierBenefits — B-4 tier-benefits-customization.
 *
 * Two modes:
 *   - artistId === undefined: fetch authenticated artist's own benefits (GET /me/tier-benefits)
 *   - artistId === string:    fetch another artist's benefits (GET /users/{id}/tier-benefits)
 */
import { useCallback, useEffect, useState } from "react";
import {
  AllTierBenefits,
  ApiClientError,
  deleteMyTierBenefits,
  fetchMyTierBenefits,
  fetchUserTierBenefits,
  putMyTierBenefits,
  TierBenefitsItem,
  TierBenefitsUpsertInput,
} from "@/lib/api";

type Tier = "subscriber" | "sponsor" | "follower";

type UseTierBenefitsState = {
  benefits: AllTierBenefits | null;
  loading: boolean;
  error: string | null;
  /** Save one tier's benefits (upsert). Returns updated item. */
  saveTier: (
    tier: Tier,
    input: TierBenefitsUpsertInput
  ) => Promise<TierBenefitsItem | null>;
  /** Reset one tier to platform default (delete override). */
  resetTier: (tier: Tier) => Promise<void>;
  /** Manual refresh. */
  reload: () => void;
  saving: Tier | null;
};

/**
 * Hook for fetching/mutating tier benefits.
 *
 * @param artistId  When provided, reads the given artist's public benefits
 *                  (read-only mode). When absent, reads the current user's own
 *                  benefits and exposes mutate helpers.
 */
export function useTierBenefits(artistId?: string): UseTierBenefitsState {
  const [benefits, setBenefits] = useState<AllTierBenefits | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState<Tier | null>(null);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    const fetch = artistId
      ? fetchUserTierBenefits(artistId)
      : fetchMyTierBenefits();

    void fetch
      .then((data) => {
        if (!cancelled) setBenefits(data);
      })
      .catch((e) => {
        if (!cancelled)
          setError(
            e instanceof ApiClientError ? e.message : "Failed to load tier benefits"
          );
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [artistId, tick]);

  const reload = useCallback(() => setTick((n) => n + 1), []);

  const saveTier = useCallback(
    async (tier: Tier, input: TierBenefitsUpsertInput) => {
      setSaving(tier);
      setError(null);
      try {
        const updated = await putMyTierBenefits(tier, input);
        setBenefits((prev) =>
          prev ? { ...prev, [tier]: updated } : null
        );
        return updated;
      } catch (e) {
        setError(
          e instanceof ApiClientError ? e.message : "Failed to save tier benefits"
        );
        return null;
      } finally {
        setSaving(null);
      }
    },
    []
  );

  const resetTier = useCallback(async (tier: Tier) => {
    setSaving(tier);
    setError(null);
    try {
      await deleteMyTierBenefits(tier);
      // Refresh to get platform default item
      reload();
    } catch (e) {
      setError(
        e instanceof ApiClientError ? e.message : "Failed to reset tier benefits"
      );
    } finally {
      setSaving(null);
    }
  }, [reload]);

  return { benefits, loading, error, saveTier, resetTier, reload, saving };
}
