"use client";

/**
 * InterviewsList — C-1 ai-artist-interview-generation
 *
 * Admin list of interviews grouped by status.
 * Each row shows title, artist, locale, status, consent badge.
 */

import { useI18n } from "@/i18n";
import type { ArtistInterviewOut } from "@/lib/api";
import { formatRelativeTime } from "@/lib/formatRelativeTime";

type Props = {
  interviews: ArtistInterviewOut[];
  onReview: (interview: ArtistInterviewOut) => void;
};

const STATUS_BADGE: Record<string, string> = {
  draft: "bg-surface-hover text-text-muted",
  admin_review: "bg-warning/15 text-warning",
  approved: "bg-success/15 text-success",
  published: "bg-primary/15 text-primary",
  rejected: "bg-danger/15 text-danger",
  archived: "bg-surface-hover text-text-muted",
};

export function InterviewsList({ interviews, onReview }: Props) {
  const { t } = useI18n();

  if (interviews.length === 0) {
    return (
      <p className="text-sm text-text-muted text-center py-4">
        {t("common.noData")}
      </p>
    );
  }

  return (
    <div className="divide-y divide-border">
      {interviews.map((interview) => (
        <div
          key={interview.id}
          className="flex items-start justify-between gap-3 py-3 first:pt-0 last:pb-0"
        >
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span
                className={`text-xs px-1.5 py-0.5 rounded font-medium ${STATUS_BADGE[interview.status] ?? "bg-surface-hover text-text-muted"}`}
              >
                {t(`interview.status.${interview.status}` as `interview.status.${string}`)}
              </span>
              <span className="text-xs px-1.5 py-0.5 rounded bg-surface-hover text-text-muted">
                {interview.locale.toUpperCase()}
              </span>
              {interview.artist_consent_at && (
                <span className="text-xs text-success">
                  {t("interview.admin.consentDone")}
                </span>
              )}
              {!interview.artist_consent_at && interview.status === "approved" && (
                <span className="text-xs text-warning">
                  {t("interview.admin.consentPending")}
                </span>
              )}
            </div>
            <p className="text-sm font-medium text-text-primary mt-1 line-clamp-1">
              {interview.title}
            </p>
            <p className="text-xs text-text-muted mt-0.5">
              {interview.llm_model ?? "—"} &middot;{" "}
              {formatRelativeTime(interview.created_at)}
            </p>
          </div>

          <button
            type="button"
            className="btn-secondary text-xs px-3 py-1.5 flex-shrink-0"
            onClick={() => onReview(interview)}
          >
            {interview.status === "admin_review"
              ? t("interview.admin.reviewTitle")
              : t("common.edit")}
          </button>
        </div>
      ))}
    </div>
  );
}
