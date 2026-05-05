"use client";

/**
 * useMyInterviews — C-1 ai-artist-interview-generation
 *
 * Hook for the current artist to view and consent/reject their interviews.
 */

import { useCallback, useEffect, useState } from "react";
import {
  ArtistInterviewOut,
  consentInterview,
  fetchMyInterviews,
  rejectInterviewPublication,
} from "@/lib/api";

export type MyInterviewsState = {
  interviews: ArtistInterviewOut[];
  loading: boolean;
  error: string | null;
  consenting: string | null; // id of interview being consented
  rejecting: string | null;  // id of interview being rejected
  consent: (id: string) => Promise<boolean>;
  reject: (id: string) => Promise<boolean>;
  reload: () => void;
};

export function useMyInterviews(): MyInterviewsState {
  const [interviews, setInterviews] = useState<ArtistInterviewOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [consenting, setConsenting] = useState<string | null>(null);
  const [rejecting, setRejecting] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchMyInterviews();
      setInterviews(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load interviews");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const consent = useCallback(async (id: string): Promise<boolean> => {
    setConsenting(id);
    try {
      const updated = await consentInterview(id);
      setInterviews((prev) => prev.map((i) => (i.id === id ? updated : i)));
      return true;
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to consent");
      return false;
    } finally {
      setConsenting(null);
    }
  }, []);

  const reject = useCallback(async (id: string): Promise<boolean> => {
    setRejecting(id);
    try {
      const updated = await rejectInterviewPublication(id);
      setInterviews((prev) => prev.map((i) => (i.id === id ? updated : i)));
      return true;
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to reject");
      return false;
    } finally {
      setRejecting(null);
    }
  }, []);

  return {
    interviews,
    loading,
    error,
    consenting,
    rejecting,
    consent,
    reject,
    reload: load,
  };
}
