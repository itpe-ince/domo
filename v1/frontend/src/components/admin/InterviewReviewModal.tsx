"use client";

/**
 * InterviewReviewModal — C-1 ai-artist-interview-generation
 *
 * Admin review modal: view markdown preview, edit title/body,
 * add review note, approve or reject. Shows consent status.
 */

import { useState } from "react";
import { useI18n } from "@/i18n";
import type { ArtistInterviewOut } from "@/lib/api";

type Props = {
  interview: ArtistInterviewOut;
  onApprove: (id: string, note?: string) => Promise<boolean>;
  onReject: (id: string, note?: string) => Promise<boolean>;
  onPatch: (
    id: string,
    body: { title?: string; body_markdown?: string; review_note?: string }
  ) => Promise<boolean>;
  onPublish: (id: string) => Promise<boolean>;
  onClose: () => void;
};

export function InterviewReviewModal({
  interview,
  onApprove,
  onReject,
  onPatch,
  onPublish,
  onClose,
}: Props) {
  const { t } = useI18n();
  const [title, setTitle] = useState(interview.title);
  const [body, setBody] = useState(interview.body_markdown);
  const [reviewNote, setReviewNote] = useState(interview.review_note ?? "");
  const [saving, setSaving] = useState(false);
  const [tab, setTab] = useState<"edit" | "preview">("preview");

  const canPublish =
    interview.status === "approved" && interview.artist_consent_at !== null;

  async function handleApprove() {
    setSaving(true);
    // save edits first, then approve
    if (title !== interview.title || body !== interview.body_markdown) {
      await onPatch(interview.id, { title, body_markdown: body });
    }
    await onApprove(interview.id, reviewNote || undefined);
    setSaving(false);
    onClose();
  }

  async function handleReject() {
    setSaving(true);
    await onReject(interview.id, reviewNote || undefined);
    setSaving(false);
    onClose();
  }

  async function handlePublish() {
    setSaving(true);
    await onPublish(interview.id);
    setSaving(false);
    onClose();
  }

  async function handleSaveDraft() {
    setSaving(true);
    await onPatch(interview.id, { title, body_markdown: body, review_note: reviewNote });
    setSaving(false);
  }

  const statusColor: Record<string, string> = {
    draft: "text-text-muted",
    admin_review: "text-warning",
    approved: "text-success",
    published: "text-primary",
    rejected: "text-danger",
    archived: "text-text-muted",
  };

  return (
    <div
      className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-label={t("interview.admin.reviewTitle")}
    >
      <div className="card w-full max-w-2xl p-6 max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-start justify-between mb-4 gap-3">
          <div className="flex-1 min-w-0">
            <span
              className={`text-xs font-medium uppercase ${statusColor[interview.status] ?? "text-text-muted"}`}
            >
              {t(`interview.status.${interview.status}` as `interview.status.${string}`)}
            </span>
            <span className="ml-2 text-xs text-text-muted">
              [{interview.locale.toUpperCase()}]
            </span>
            {interview.artist_consent_at ? (
              <span className="ml-2 text-xs text-success">
                {t("interview.admin.consentDone")}
              </span>
            ) : interview.status === "approved" ? (
              <span className="ml-2 text-xs text-warning">
                {t("interview.admin.consentPending")}
              </span>
            ) : null}
          </div>
          <button
            type="button"
            className="text-text-muted hover:text-text-primary flex-shrink-0"
            onClick={onClose}
            aria-label={t("common.close")}
          >
            ✕
          </button>
        </div>

        {/* Tab switcher */}
        <div className="flex gap-2 mb-4 border-b border-border">
          {(["preview", "edit"] as const).map((tab_) => (
            <button
              key={tab_}
              type="button"
              className={`text-sm px-3 py-1.5 border-b-2 -mb-px transition-colors ${
                tab === tab_
                  ? "border-primary text-primary"
                  : "border-transparent text-text-muted hover:text-text-primary"
              }`}
              onClick={() => setTab(tab_)}
            >
              {tab_ === "edit" ? t("common.edit") : t("interview.me.previewLabel")}
            </button>
          ))}
        </div>

        {tab === "edit" ? (
          <div className="space-y-3">
            <div>
              <label className="block text-xs font-medium text-text-secondary mb-1">
                제목
              </label>
              <input
                type="text"
                className="input w-full text-sm"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                maxLength={200}
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-text-secondary mb-1">
                본문 (Markdown)
              </label>
              <textarea
                className="input w-full h-64 text-xs font-mono resize-none"
                value={body}
                onChange={(e) => setBody(e.target.value)}
              />
            </div>
          </div>
        ) : (
          <div className="prose prose-sm max-w-none text-text-primary">
            <h3 className="text-base font-bold mb-3">{title}</h3>
            <pre className="whitespace-pre-wrap text-xs text-text-secondary bg-surface-hover rounded p-3 overflow-x-auto">
              {body}
            </pre>
          </div>
        )}

        {/* Review note */}
        <div className="mt-4">
          <label className="block text-xs font-medium text-text-secondary mb-1">
            {t("interview.admin.reviewNoteLabel")}
          </label>
          <textarea
            className="input w-full h-16 text-sm resize-none"
            value={reviewNote}
            onChange={(e) => setReviewNote(e.target.value)}
            maxLength={2000}
            placeholder="검수 메모 (선택)"
          />
        </div>

        {/* Actions */}
        <div className="flex flex-wrap gap-2 mt-5">
          {interview.status === "admin_review" && (
            <>
              <button
                type="button"
                className="btn-secondary text-sm px-3"
                disabled={saving}
                onClick={handleSaveDraft}
              >
                {t("common.save")}
              </button>
              <button
                type="button"
                className="btn-primary text-sm px-3"
                disabled={saving}
                onClick={handleApprove}
              >
                {t("interview.admin.approveBtn")}
              </button>
              <button
                type="button"
                className="btn-secondary text-sm px-3 border-danger/50 text-danger hover:bg-danger/10"
                disabled={saving}
                onClick={handleReject}
              >
                {t("interview.admin.rejectBtn")}
              </button>
            </>
          )}
          {interview.status === "approved" && (
            <>
              <button
                type="button"
                className="btn-primary text-sm px-3"
                disabled={saving || !canPublish}
                title={!canPublish ? t("interview.admin.publishDisabled") : undefined}
                onClick={handlePublish}
              >
                {t("interview.admin.publishBtn")}
              </button>
              {!canPublish && (
                <p className="text-xs text-warning self-center">
                  {t("interview.admin.consentPending")}
                </p>
              )}
            </>
          )}
          <button
            type="button"
            className="btn-secondary text-sm px-3 ml-auto"
            onClick={onClose}
          >
            {t("common.close")}
          </button>
        </div>
      </div>
    </div>
  );
}
