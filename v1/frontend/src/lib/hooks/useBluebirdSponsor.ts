/**
 * useBluebirdSponsor — state machine hook for the Blue Bird sponsor flow.
 *
 * Manages the multi-step flow state and API calls for BluebirdModal.
 * Separated from the component to allow testing and reuse.
 *
 * Flow states:
 *   idle → setup_intent → payment_input → confirming → success | error
 *
 * Usage:
 *   const { flow, proceed, reset, error } = useBluebirdSponsor({ artistId, postId });
 */

"use client";

import { useState, useCallback } from "react";
import {
  ApiClientError,
  createSetupIntent,
  createSponsorship,
  confirmSponsorship,
  createSubscription,
  type SetupIntentResponse,
} from "@/lib/api";

export type SponsorMode = "one_time" | "recurring";

export type FlowState =
  | "idle"
  | "fetching_setup_intent"
  | "payment_input"
  | "confirming"
  | "success"
  | "error";

export interface SponsorParams {
  artistId: string;
  postId?: string;
  mode: SponsorMode;
  amountUsd: number;
  message?: string;
  isAnonymous?: boolean;
  visibility?: "public" | "artist_only" | "private";
}

export interface UseBluebirdSponsorReturn {
  flowState: FlowState;
  setupIntent: SetupIntentResponse | null;
  error: string | null;
  fetchSetupIntent: (mode: SponsorMode, amountUsd: number) => Promise<void>;
  confirmPayment: (params: SponsorParams) => Promise<void>;
  reset: () => void;
}

export function useBluebirdSponsor(): UseBluebirdSponsorReturn {
  const [flowState, setFlowState] = useState<FlowState>("idle");
  const [setupIntent, setSetupIntent] = useState<SetupIntentResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fetchSetupIntent = useCallback(
    async (mode: SponsorMode, amountUsd: number) => {
      setFlowState("fetching_setup_intent");
      setError(null);
      try {
        const si = await createSetupIntent({ purpose: mode, amount: String(amountUsd) });
        setSetupIntent(si);
        setFlowState("payment_input");
      } catch (e) {
        const msg =
          e instanceof ApiClientError
            ? e.message
            : "결제 수단 초기화에 실패했습니다.";
        setError(msg);
        setFlowState("error");
      }
    },
    []
  );

  const confirmPayment = useCallback(async (params: SponsorParams) => {
    setFlowState("confirming");
    setError(null);
    try {
      if (params.mode === "one_time") {
        const created = await createSponsorship({
          artist_id: params.artistId,
          post_id: params.postId ?? null,
          bluebird_count: params.amountUsd, // 1 bluebird = $1
          is_anonymous: params.isAnonymous ?? false,
          visibility: params.visibility ?? "public",
          message: params.message?.trim() || undefined,
        });
        await confirmSponsorship(created.sponsorship.id);
      } else {
        await createSubscription({
          artist_id: params.artistId,
          monthly_bluebird: params.amountUsd,
        });
      }
      setFlowState("success");
    } catch (e) {
      const msg =
        e instanceof ApiClientError
          ? `${e.code}: ${e.message}`
          : e instanceof Error
          ? e.message
          : "알 수 없는 오류";
      setError(msg);
      setFlowState("error");
    }
  }, []);

  const reset = useCallback(() => {
    setFlowState("idle");
    setSetupIntent(null);
    setError(null);
  }, []);

  return { flowState, setupIntent, error, fetchSetupIntent, confirmPayment, reset };
}
