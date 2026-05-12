"use client";

/**
 * /users/[id]/interviews/[locale] — C-1 ai-artist-interview-generation
 *
 * Public page: renders a published artist interview in the specified locale.
 * If no published interview exists for this locale, shows a graceful empty state.
 */

import { use, useEffect, useState } from "react";
import Link from "next/link";
import { useI18n } from "@/i18n";
import {
  fetchArtistInterviews,
  fetchMe,
  type ArtistInterviewPublicOut,
} from "@/lib/api";
import { formatRelativeTime } from "@/lib/formatRelativeTime";

const VALID_LOCALES = ["ko", "en", "ja", "zh", "es"];

export default function ArtistInterviewPage({
  params,
}: {
  params: Promise<{ id: string; locale: string }>;
}) {
  const { id, locale } = use(params);
  const { t } = useI18n();
  const [interview, setInterview] = useState<ArtistInterviewPublicOut | null>(
    null
  );
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!VALID_LOCALES.includes(locale)) {
      setError("Invalid locale");
      setLoading(false);
      return;
    }

    fetchArtistInterviews(id, locale)
      .then((list) => {
        setInterview(list.length > 0 ? list[0] : null);
      })
      .catch((e) => {
        setError(e instanceof Error ? e.message : "Failed to load interview");
      })
      .finally(() => {
        setLoading(false);
      });
  }, [id, locale]);

  if (loading) {
    return (
      <main className="flex-1 min-w-0 max-w-2xl mx-auto px-4 py-8">
        <div className="h-64 card animate-pulse" />
      </main>
    );
  }

  if (error || !interview) {
    return (
      <main className="flex-1 min-w-0 max-w-2xl mx-auto px-4 py-8">
        <div className="card p-6 text-center">
          <p className="text-text-muted text-sm">
            {error ?? t("interview.public.noPublished")}
          </p>
          <Link
            href={`/users/${id}/timeline`}
            className="btn-secondary text-sm mt-4 inline-block"
          >
            ← {t("timeline.viewProfile")}
          </Link>
        </div>
      </main>
    );
  }

  return (
    <main className="flex-1 min-w-0 max-w-2xl mx-auto px-4 py-8">
      {/* Back link */}
      <Link
        href={`/users/${id}/timeline`}
        className="text-text-secondary text-sm mb-6 inline-block hover:text-primary"
      >
        ← {t("timeline.viewProfile")}
      </Link>

      {/* Interview article */}
      <article className="card p-6">
        {/* Meta */}
        <div className="flex items-center gap-2 mb-4">
          <span className="text-xs px-1.5 py-0.5 rounded bg-primary/10 text-primary">
            {t("interview.public.aiGenerated")}
          </span>
          <span className="text-xs px-1.5 py-0.5 rounded bg-surface-hover text-text-muted">
            {interview.locale.toUpperCase()}
          </span>
          <span className="text-xs text-text-muted">
            {formatRelativeTime(interview.published_at)}
          </span>
        </div>

        {/* Title */}
        <h1 className="text-xl font-bold text-text-primary mb-6">
          {interview.title}
        </h1>

        {/* Body — markdown rendered as pre-wrapped text */}
        <div className="prose prose-sm max-w-none">
          <pre className="whitespace-pre-wrap text-sm text-text-primary leading-relaxed font-sans">
            {interview.body_markdown}
          </pre>
        </div>

        {/* Consent note */}
        <p className="text-xs text-text-muted mt-6 border-t border-border pt-4">
          {t("interview.public.consentNote")}
        </p>
      </article>
    </main>
  );
}
