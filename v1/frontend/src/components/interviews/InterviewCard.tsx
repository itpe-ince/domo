"use client";

/**
 * InterviewCard — C-1 ai-artist-interview-generation
 *
 * Public-facing card showing a published artist interview preview.
 * Renders markdown as plain text excerpt with a read-more link.
 */

import Link from "next/link";
import { useI18n } from "@/i18n";
import type { ArtistInterviewPublicOut } from "@/lib/api";
import { formatRelativeTime } from "@/lib/formatRelativeTime";

type Props = {
  interview: ArtistInterviewPublicOut;
  artistHref?: string;
};

function stripMarkdown(md: string): string {
  return md
    .replace(/^#{1,6}\s+/gm, "")
    .replace(/\*\*([^*]+)\*\*/g, "$1")
    .replace(/\*([^*]+)\*/g, "$1")
    .replace(/\[([^\]]+)\]\([^)]+\)/g, "$1")
    .replace(/\n{2,}/g, " ")
    .replace(/\n/g, " ")
    .trim();
}

export function InterviewCard({ interview, artistHref }: Props) {
  const { t } = useI18n();
  const excerpt = stripMarkdown(interview.body_markdown).slice(0, 160);
  const localeBadge = interview.locale.toUpperCase();

  return (
    <article className="card p-4 flex flex-col gap-2">
      {/* Header */}
      <div className="flex items-start justify-between gap-2">
        <h3 className="text-sm font-semibold text-text-primary line-clamp-2 flex-1">
          {interview.title}
        </h3>
        <span className="text-xs px-1.5 py-0.5 rounded bg-surface-hover text-text-muted flex-shrink-0">
          {localeBadge}
        </span>
      </div>

      {/* Excerpt */}
      <p className="text-xs text-text-secondary line-clamp-3">
        {excerpt}
        {excerpt.length >= 160 ? "…" : ""}
      </p>

      {/* Footer */}
      <div className="flex items-center justify-between mt-1">
        <div className="flex items-center gap-1.5">
          <span className="text-xs px-1.5 py-0.5 rounded bg-primary/10 text-primary">
            {t("interview.public.aiGenerated")}
          </span>
          <span className="text-xs text-text-muted">
            {formatRelativeTime(interview.published_at)}
          </span>
        </div>
        {artistHref && (
          <Link
            href={artistHref}
            className="text-xs text-primary hover:underline"
          >
            {t("interview.public.readMore")} →
          </Link>
        )}
      </div>
    </article>
  );
}
