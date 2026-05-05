"use client";

/**
 * useAdminPressKits — C-2 press-kit-auto-export
 *
 * Hook for admin to trigger press kit generation and view history.
 */

import { useCallback, useEffect, useState } from "react";
import {
  PressKitOut,
  adminGeneratePressKit,
  adminListPressKits,
} from "@/lib/api";

export type AdminPressKitsState = {
  pressKits: PressKitOut[];
  loading: boolean;
  error: string | null;
  generating: boolean;
  generateError: string | null;
  generate: (params: {
    user_id: string;
    locale: string;
    force?: boolean;
  }) => Promise<PressKitOut | null>;
  loadHistory: (user_id: string, limit?: number) => void;
  currentArtistId: string | null;
  setCurrentArtistId: (id: string | null) => void;
};

export function useAdminPressKits(): AdminPressKitsState {
  const [pressKits, setPressKits] = useState<PressKitOut[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [generating, setGenerating] = useState(false);
  const [generateError, setGenerateError] = useState<string | null>(null);
  const [currentArtistId, setCurrentArtistId] = useState<string | null>(null);

  const loadHistory = useCallback(
    async (user_id: string, limit: number = 20) => {
      setLoading(true);
      setError(null);
      try {
        const data = await adminListPressKits({ user_id, limit });
        setPressKits(data);
      } catch (e) {
        setError(
          e instanceof Error ? e.message : "Failed to load press kit history"
        );
      } finally {
        setLoading(false);
      }
    },
    []
  );

  useEffect(() => {
    if (currentArtistId) {
      void loadHistory(currentArtistId);
    }
  }, [currentArtistId, loadHistory]);

  const generate = useCallback(
    async (params: {
      user_id: string;
      locale: string;
      force?: boolean;
    }): Promise<PressKitOut | null> => {
      setGenerating(true);
      setGenerateError(null);
      try {
        const kit = await adminGeneratePressKit(params);
        // Prepend to history list
        setPressKits((prev) => [kit, ...prev.filter((k) => k.id !== kit.id)]);
        return kit;
      } catch (e) {
        setGenerateError(
          e instanceof Error ? e.message : "Failed to generate press kit"
        );
        return null;
      } finally {
        setGenerating(false);
      }
    },
    []
  );

  return {
    pressKits,
    loading,
    error,
    generating,
    generateError,
    generate,
    loadHistory,
    currentArtistId,
    setCurrentArtistId,
  };
}
