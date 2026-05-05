"use client";

/**
 * useAdminInterviews — C-1 ai-artist-interview-generation
 *
 * Hook for admin to manage artist interview generation, review, and publishing.
 */

import { useCallback, useEffect, useState } from "react";
import {
  ArtistInterviewOut,
  adminGenerateInterview,
  adminListInterviews,
  adminPatchInterview,
  adminPublishInterview,
} from "@/lib/api";

export type AdminInterviewsState = {
  interviews: ArtistInterviewOut[];
  loading: boolean;
  error: string | null;
  generating: boolean;
  generateError: string | null;
  generate: (params: { artist_id: string; locale: string }) => Promise<ArtistInterviewOut | null>;
  approve: (id: string, note?: string) => Promise<boolean>;
  reject: (id: string, note?: string) => Promise<boolean>;
  patch: (
    id: string,
    body: { title?: string; body_markdown?: string; review_note?: string }
  ) => Promise<boolean>;
  publish: (id: string) => Promise<boolean>;
  reload: (params?: { status?: string; artist_id?: string }) => void;
  setStatusFilter: (status: string) => void;
  statusFilter: string;
};

export function useAdminInterviews(
  opts?: { limit?: number; initialStatus?: string }
): AdminInterviewsState {
  const [interviews, setInterviews] = useState<ArtistInterviewOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [generating, setGenerating] = useState(false);
  const [generateError, setGenerateError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState(
    opts?.initialStatus ?? "admin_review"
  );

  const load = useCallback(
    async (params?: { status?: string; artist_id?: string }) => {
      setLoading(true);
      setError(null);
      try {
        const data = await adminListInterviews({
          status: params?.status ?? statusFilter,
          artist_id: params?.artist_id,
          limit: opts?.limit ?? 20,
        });
        setInterviews(data);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to load interviews");
      } finally {
        setLoading(false);
      }
    },
    [statusFilter, opts?.limit]
  );

  useEffect(() => {
    void load();
  }, [load]);

  const generate = useCallback(
    async (params: { artist_id: string; locale: string }): Promise<ArtistInterviewOut | null> => {
      setGenerating(true);
      setGenerateError(null);
      try {
        const interview = await adminGenerateInterview(params);
        setInterviews((prev) => [interview, ...prev]);
        return interview;
      } catch (e) {
        setGenerateError(
          e instanceof Error ? e.message : "Failed to generate interview"
        );
        return null;
      } finally {
        setGenerating(false);
      }
    },
    []
  );

  const approve = useCallback(async (id: string, note?: string): Promise<boolean> => {
    try {
      const updated = await adminPatchInterview(id, {
        status: "approved",
        ...(note ? { review_note: note } : {}),
      });
      setInterviews((prev) =>
        prev.map((i) => (i.id === id ? updated : i))
      );
      return true;
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to approve");
      return false;
    }
  }, []);

  const reject = useCallback(async (id: string, note?: string): Promise<boolean> => {
    try {
      const updated = await adminPatchInterview(id, {
        status: "rejected",
        ...(note ? { review_note: note } : {}),
      });
      setInterviews((prev) =>
        prev.map((i) => (i.id === id ? updated : i))
      );
      return true;
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to reject");
      return false;
    }
  }, []);

  const patch = useCallback(
    async (
      id: string,
      body: { title?: string; body_markdown?: string; review_note?: string }
    ): Promise<boolean> => {
      try {
        const updated = await adminPatchInterview(id, body);
        setInterviews((prev) =>
          prev.map((i) => (i.id === id ? updated : i))
        );
        return true;
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to update");
        return false;
      }
    },
    []
  );

  const publish = useCallback(async (id: string): Promise<boolean> => {
    try {
      const updated = await adminPublishInterview(id);
      setInterviews((prev) =>
        prev.map((i) => (i.id === id ? updated : i))
      );
      return true;
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to publish");
      return false;
    }
  }, []);

  return {
    interviews,
    loading,
    error,
    generating,
    generateError,
    generate,
    approve,
    reject,
    patch,
    publish,
    reload: load,
    setStatusFilter,
    statusFilter,
  };
}
