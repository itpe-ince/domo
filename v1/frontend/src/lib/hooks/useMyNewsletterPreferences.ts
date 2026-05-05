"use client";

/**
 * useMyNewsletterPreferences — C-5 newsletter-digest
 *
 * Hook for authenticated users to manage newsletter preferences:
 * opt-in/out, frequency, locale.
 */

import { useCallback, useEffect, useState } from "react";
import {
  NewsletterPreferencesOut,
  fetchMyNewsletterPreferences,
  patchMyNewsletterPreferences,
} from "@/lib/api";

export type MyNewsletterPreferencesState = {
  preferences: NewsletterPreferencesOut | null;
  loading: boolean;
  error: string | null;
  saving: boolean;
  saveError: string | null;
  reload: () => void;
  setSubscribed: (subscribed: boolean) => Promise<void>;
  setFrequency: (frequency: "weekly" | "biweekly" | "monthly" | "never") => Promise<void>;
  setLocale: (locale: string) => Promise<void>;
};

export function useMyNewsletterPreferences(): MyNewsletterPreferencesState {
  const [preferences, setPreferences] = useState<NewsletterPreferencesOut | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  const reload = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchMyNewsletterPreferences();
      setPreferences(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "설정 로드 실패");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  const _patch = useCallback(
    async (body: {
      is_subscribed?: boolean;
      frequency?: "weekly" | "biweekly" | "monthly" | "never";
      preferred_locale?: string;
    }) => {
      setSaving(true);
      setSaveError(null);
      try {
        const updated = await patchMyNewsletterPreferences(body);
        setPreferences(updated);
      } catch (e) {
        setSaveError(e instanceof Error ? e.message : "저장 실패");
      } finally {
        setSaving(false);
      }
    },
    []
  );

  const setSubscribed = useCallback(
    (subscribed: boolean) => _patch({ is_subscribed: subscribed }),
    [_patch]
  );

  const setFrequency = useCallback(
    (frequency: "weekly" | "biweekly" | "monthly" | "never") =>
      _patch({ frequency }),
    [_patch]
  );

  const setLocale = useCallback(
    (preferred_locale: string) => _patch({ preferred_locale }),
    [_patch]
  );

  return {
    preferences,
    loading,
    error,
    saving,
    saveError,
    reload,
    setSubscribed,
    setFrequency,
    setLocale,
  };
}
