"use client";

/**
 * /me/interviews — C-1 ai-artist-interview-generation
 *
 * Artist-facing: view AI-generated interviews, provide GDPR consent, or reject.
 */

import { useState } from "react";
import Link from "next/link";
import { useI18n } from "@/i18n";
import { useMyInterviews } from "@/lib/hooks/useMyInterviews";
import { formatRelativeTime } from "@/lib/formatRelativeTime";

const STATUS_BADGE: Record<string, string> = {
  draft: "bg-surface-hover text-text-muted",
  admin_review: "bg-warning/15 text-warning",
  approved: "bg-success/15 text-success",
  published: "bg-primary/15 text-primary",
  rejected: "bg-danger/15 text-danger",
  archived: "bg-surface-hover text-text-muted",
};

export default function MyInterviewsPage() {
  const { t } = useI18n();
  const { interviews, loading, error, consenting, rejecting, consent, reject } =
    useMyInterviews();
  const [expandedId, setExpandedId] = useState<string | null>(null);

  if (loading) {
    return (
      <main className="flex-1 min-w-0 max-w-2xl mx-auto px-4 py-8">
        <div className="space-y-3">
          {[1, 2].map((i) => (
            <div key={i} className="h-24 card animate-pulse" />
          ))}
        </div>
      </main>
    );
  }

  return (
    <main className="flex-1 min-w-0 max-w-2xl mx-auto px-4 py-8">
      <header className="mb-6">
        <h1 className="text-2xl font-bold text-text-primary">
          {t("interview.me.pageTitle")}
        </h1>
        <p className="text-sm text-text-muted mt-1">
          {t("interview.me.pageSubtitle")}
        </p>
      </header>

      {error && (
        <div className="mb-4 text-sm text-danger">{error}</div>
      )}

      {interviews.length === 0 ? (
        <div className="card p-6 text-center">
          <p className="text-text-muted text-sm">{t("interview.me.noInterviews")}</p>
        </div>
      ) : (
        <div className="space-y-4">
          {interviews.map((interview) => (
            <article key={interview.id} className="card p-5">
              {/* Header row */}
              <div className="flex items-start justify-between gap-3 mb-3">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap mb-1">
                    <span
                      className={`text-xs px-1.5 py-0.5 rounded font-medium ${STATUS_BADGE[interview.status] ?? "bg-surface-hover text-text-muted"}`}
                    >
                      {t(`interview.status.${interview.status}` as `interview.status.${string}`)}
                    </span>
                    <span className="text-xs px-1.5 py-0.5 rounded bg-surface-hover text-text-muted">
                      {interview.locale.toUpperCase()}
                    </span>
                  </div>
                  <h2 className="text-sm font-semibold text-text-primary line-clamp-2">
                    {interview.title}
                  </h2>
                  <p className="text-xs text-text-muted mt-0.5">
                    {formatRelativeTime(interview.created_at)}
                  </p>
                </div>

                <button
                  type="button"
                  className="text-xs text-primary hover:underline flex-shrink-0"
                  onClick={() =>
                    setExpandedId(expandedId === interview.id ? null : interview.id)
                  }
                >
                  {expandedId === interview.id
                    ? t("common.close")
                    : t("interview.me.previewLabel")}
                </button>
              </div>

              {/* Markdown preview */}
              {expandedId === interview.id && (
                <div className="mb-4 p-3 rounded-lg bg-surface-hover">
                  <pre className="whitespace-pre-wrap text-xs text-text-secondary overflow-x-auto max-h-48">
                    {interview.body_markdown}
                  </pre>
                </div>
              )}

              {/* Action buttons — only for approved status */}
              {interview.status === "approved" && (
                <div className="flex gap-2 mt-2">
                  {interview.artist_consent_at ? (
                    <p className="text-xs text-success self-center">
                      {t("interview.admin.consentDone")}
                    </p>
                  ) : (
                    <>
                      <button
                        type="button"
                        className="btn-primary text-xs px-3 py-1.5"
                        disabled={consenting === interview.id}
                        onClick={() => {
                          if (
                            window.confirm(t("interview.me.consentConfirm"))
                          ) {
                            void consent(interview.id);
                          }
                        }}
                      >
                        {consenting === interview.id
                          ? t("common.loading")
                          : t("interview.me.consentBtn")}
                      </button>
                      <button
                        type="button"
                        className="btn-secondary text-xs px-3 py-1.5 text-danger"
                        disabled={rejecting === interview.id}
                        onClick={() => {
                          if (
                            window.confirm(t("interview.me.rejectConfirm"))
                          ) {
                            void reject(interview.id);
                          }
                        }}
                      >
                        {rejecting === interview.id
                          ? t("common.loading")
                          : t("interview.me.rejectBtn")}
                      </button>
                    </>
                  )}
                </div>
              )}

              {/* Link to published interview */}
              {interview.status === "published" && (
                <Link
                  href={`/users/${interview.artist_id}/interviews/${interview.locale}`}
                  className="text-xs text-primary hover:underline mt-2 inline-block"
                >
                  {t("interview.public.readMore")} →
                </Link>
              )}
            </article>
          ))}
        </div>
      )}
    </main>
  );
}
