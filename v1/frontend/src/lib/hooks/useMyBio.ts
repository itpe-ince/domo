"use client";

/**
 * useMyBio — C-3 multi-language-story
 *
 * Hook for artist bio multi-locale management.
 * Handles: fetch all locales, trigger LLM translate, patch one locale.
 */

import { useState, useEffect, useCallback } from "react";
import {
  BioTranslationOut,
  fetchMyBioTranslations,
  translateMyBio,
  patchMyBioLocale,
} from "@/lib/api";

export type BioLocaleState = Record<string, string>; // locale → bio text

export function useMyBio() {
  const [rows, setRows] = useState<BioTranslationOut[]>([]);
  const [loading, setLoading] = useState(false);
  const [translating, setTranslating] = useState(false);
  const [saving, setSaving] = useState<string | null>(null); // locale being saved
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchMyBioTranslations();
      setRows(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load bio translations");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function triggerTranslate(sourceLocale: string = "ko"): Promise<boolean> {
    setTranslating(true);
    setError(null);
    try {
      await translateMyBio(sourceLocale);
      await load(); // refresh rows after translation
      return true;
    } catch (e) {
      setError(e instanceof Error ? e.message : "Translation failed");
      return false;
    } finally {
      setTranslating(false);
    }
  }

  async function saveLocale(locale: string, bio: string): Promise<boolean> {
    setSaving(locale);
    setError(null);
    try {
      const updated = await patchMyBioLocale(locale, bio);
      setRows((prev) => {
        const idx = prev.findIndex((r) => r.locale === locale);
        if (idx >= 0) {
          const next = [...prev];
          next[idx] = updated;
          return next;
        }
        return [...prev, updated];
      });
      return true;
    } catch (e) {
      setError(e instanceof Error ? e.message : "Save failed");
      return false;
    } finally {
      setSaving(null);
    }
  }

  /** Get bio text for a specific locale (or empty string if not set). */
  function getBio(locale: string): string {
    return rows.find((r) => r.locale === locale)?.bio ?? "";
  }

  /** Whether a locale was machine-translated (vs manually edited). */
  function isMachineTranslated(locale: string): boolean {
    return rows.find((r) => r.locale === locale)?.is_machine_translated ?? true;
  }

  return {
    rows,
    loading,
    translating,
    saving,
    error,
    getBio,
    isMachineTranslated,
    triggerTranslate,
    saveLocale,
    reload: load,
  };
}
