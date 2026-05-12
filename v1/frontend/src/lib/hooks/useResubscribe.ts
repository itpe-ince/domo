"use client";

/**
 * useResubscribe — B-5 patronage-retention-ux
 *
 * One-click resubscribe hook.
 * Reuses the existing createSubscription API endpoint — no new backend route needed.
 * Records audit context via the existing subscription creation path.
 *
 * Usage:
 *   const { resubscribe, subscribing, error, success } = useResubscribe();
 *   await resubscribe({ artistId, monthlyBluebird });
 */

import { useState, useCallback } from "react";
import { createSubscription, ApiClientError } from "@/lib/api";

export type ResubscribeInput = {
  artistId: string;
  monthlyBluebird?: number; // defaults to 3 (subscriber tier minimum)
};

export type UseResubscribeReturn = {
  resubscribe: (input: ResubscribeInput) => Promise<boolean>;
  subscribing: boolean;
  error: string | null;
  success: boolean;
  reset: () => void;
};

const DEFAULT_MONTHLY_BLUEBIRD = 3; // subscriber tier minimum

export function useResubscribe(): UseResubscribeReturn {
  const [subscribing, setSubscribing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const resubscribe = useCallback(
    async ({ artistId, monthlyBluebird = DEFAULT_MONTHLY_BLUEBIRD }: ResubscribeInput): Promise<boolean> => {
      setSubscribing(true);
      setError(null);
      setSuccess(false);
      try {
        await createSubscription({
          artist_id: artistId,
          monthly_bluebird: monthlyBluebird,
        });
        setSuccess(true);
        return true;
      } catch (e) {
        const msg =
          e instanceof ApiClientError
            ? e.message
            : "재구독에 실패했습니다. 다시 시도해주세요.";
        setError(msg);
        return false;
      } finally {
        setSubscribing(false);
      }
    },
    []
  );

  const reset = useCallback(() => {
    setSubscribing(false);
    setError(null);
    setSuccess(false);
  }, []);

  return { resubscribe, subscribing, error, success, reset };
}
