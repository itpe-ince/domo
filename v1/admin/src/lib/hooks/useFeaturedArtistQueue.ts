import { useState, useCallback } from "react";
import {
  fetchFeaturedArtistCandidates,
  approveCandidate,
  publishCandidate,
  rejectCandidate,
  FeaturedArtistCandidate,
  FeaturedArtistCandidatesResponse,
} from "@/lib/api";

type ActionLoading = { id: string; action: "approve" | "publish" | "reject" } | null;

export function useFeaturedArtistQueue(weekStart: string) {
  const [data, setData] = useState<FeaturedArtistCandidatesResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<ActionLoading>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchFeaturedArtistCandidates(weekStart);
      setData(res);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "데이터를 불러오지 못했습니다.";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, [weekStart]);

  const updateCandidateStatus = useCallback(
    (id: string, updates: Partial<FeaturedArtistCandidate>) => {
      setData((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          candidates: prev.candidates.map((c) =>
            c.id === id ? { ...c, ...updates } : c
          ),
        };
      });
    },
    []
  );

  const approve = useCallback(
    async (id: string) => {
      setActionLoading({ id, action: "approve" });
      try {
        const res = await approveCandidate(id);
        updateCandidateStatus(id, {
          status: res.status,
          reviewed_at: res.reviewed_at,
        });
      } catch (e: unknown) {
        const msg = e instanceof Error ? e.message : "승인에 실패했습니다.";
        setError(msg);
      } finally {
        setActionLoading(null);
      }
    },
    [updateCandidateStatus]
  );

  const publish = useCallback(
    async (id: string, notes?: string) => {
      setActionLoading({ id, action: "publish" });
      try {
        const res = await publishCandidate(id, notes);
        updateCandidateStatus(id, {
          status: res.status,
          published_at: res.published_at,
        });
      } catch (e: unknown) {
        const msg = e instanceof Error ? e.message : "발행에 실패했습니다.";
        setError(msg);
      } finally {
        setActionLoading(null);
      }
    },
    [updateCandidateStatus]
  );

  const reject = useCallback(
    async (id: string, reason: string) => {
      setActionLoading({ id, action: "reject" });
      try {
        const res = await rejectCandidate(id, reason);
        setData((prev) => {
          if (!prev) return prev;
          return {
            ...prev,
            candidates: prev.candidates.map((c) => {
              if (c.id !== id) return c;
              return {
                ...c,
                status: res.status,
                reviewed_at: res.reviewed_at,
                reasoning: {
                  ...c.reasoning,
                  reject_reason: reason,
                },
              };
            }),
          };
        });
      } catch (e: unknown) {
        const msg = e instanceof Error ? e.message : "거부에 실패했습니다.";
        setError(msg);
      } finally {
        setActionLoading(null);
      }
    },
    []
  );

  return { data, loading, error, load, approve, publish, reject, actionLoading };
}
