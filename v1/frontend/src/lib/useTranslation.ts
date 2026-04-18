"use client";

import { useEffect, useState } from "react";
import { useI18n } from "@/i18n";
import { fetchPostTranslation } from "./api";

/**
 * Auto-translate post title/content based on current locale.
 * Returns original if post language matches locale.
 * Caches via backend post_translations table.
 */
export function usePostTranslation(
  postId: string,
  originalLang: string,
  originalTitle: string | null,
  originalContent: string | null
) {
  const { locale } = useI18n();
  const [title, setTitle] = useState(originalTitle);
  const [content, setContent] = useState(originalContent);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    // No translation needed if same language
    if (locale === originalLang || !postId) {
      setTitle(originalTitle);
      setContent(originalContent);
      return;
    }

    let cancelled = false;
    setLoading(true);

    fetchPostTranslation(postId, locale)
      .then((t) => {
        if (!cancelled) {
          setTitle(t.title ?? originalTitle);
          setContent(t.content ?? originalContent);
        }
      })
      .catch(() => {
        // Fallback to original
        if (!cancelled) {
          setTitle(originalTitle);
          setContent(originalContent);
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [postId, locale, originalLang, originalTitle, originalContent]);

  return { title, content, loading, isTranslated: locale !== originalLang };
}
