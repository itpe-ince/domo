"use client";

/**
 * NewsletterIssueEditor — C-5 newsletter-digest
 *
 * Inline editor for newsletter issue body_markdown + subject.
 * Supports simple preview (rendered HTML in iframe-safe div).
 */

import { useState } from "react";
import { useI18n } from "@/i18n";
import type { NewsletterIssueOut } from "@/lib/api";

interface Props {
  issue: NewsletterIssueOut;
  onSave: (
    id: string,
    body: { subject?: string; body_markdown?: string }
  ) => Promise<void>;
  onSend: (id: string) => Promise<void>;
  onClose: () => void;
  isSending: boolean;
}

export function NewsletterIssueEditor({
  issue,
  onSave,
  onSend,
  onClose,
  isSending,
}: Props) {
  const { t } = useI18n();
  const [subject, setSubject] = useState(issue.subject);
  const [body, setBody] = useState(issue.body_markdown);
  const [saving, setSaving] = useState(false);
  const [showPreview, setShowPreview] = useState(false);

  const isDraft = issue.status === "draft";
  const isEditable = isDraft;

  const handleSave = async () => {
    setSaving(true);
    try {
      await onSave(issue.id, {
        subject: subject !== issue.subject ? subject : undefined,
        body_markdown: body !== issue.body_markdown ? body : undefined,
      });
    } finally {
      setSaving(false);
    }
  };

  const handleSend = async () => {
    if (!isDraft) return;
    const confirmed = window.confirm(t("newsletter.admin.editor.sendConfirm"));
    if (!confirmed) return;
    await onSend(issue.id);
  };

  return (
    <div className="mb-6 p-5 bg-white rounded-lg border border-blue-200 shadow-sm">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold">
          {t("newsletter.admin.editor.title")}
          <span className="ml-2 text-sm font-normal text-gray-500">
            [{issue.locale.toUpperCase()}] {issue.issue_date}
          </span>
        </h2>
        <button
          onClick={onClose}
          className="text-gray-400 hover:text-gray-600 text-xl leading-none"
          aria-label={t("common.close")}
        >
          &times;
        </button>
      </div>

      {/* Status badge */}
      <div className="mb-4">
        <span
          className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${
            issue.status === "draft"
              ? "bg-yellow-100 text-yellow-700"
              : issue.status === "sending"
              ? "bg-blue-100 text-blue-700"
              : issue.status === "sent"
              ? "bg-green-100 text-green-700"
              : "bg-red-100 text-red-700"
          }`}
        >
          {t(`newsletter.admin.status.${issue.status}`)}
        </span>
        {issue.sent_count > 0 && (
          <span className="ml-2 text-xs text-gray-500">
            {t("newsletter.admin.editor.sentCount", {
              sent: issue.sent_count,
              failed: issue.failed_count,
            })}
          </span>
        )}
      </div>

      {/* Subject */}
      <div className="mb-3">
        <label className="block text-sm font-medium text-gray-700 mb-1">
          {t("newsletter.admin.editor.subject")}
        </label>
        <input
          type="text"
          value={subject}
          onChange={(e) => setSubject(e.target.value)}
          disabled={!isEditable}
          maxLength={200}
          className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-50 disabled:text-gray-500"
        />
      </div>

      {/* Body */}
      <div className="mb-3">
        <div className="flex items-center justify-between mb-1">
          <label className="text-sm font-medium text-gray-700">
            {t("newsletter.admin.editor.body")}
          </label>
          <button
            onClick={() => setShowPreview(!showPreview)}
            className="text-xs text-blue-600 hover:underline"
          >
            {showPreview
              ? t("newsletter.admin.editor.hidePreview")
              : t("newsletter.admin.editor.showPreview")}
          </button>
        </div>
        {showPreview ? (
          <div
            className="w-full min-h-48 rounded-md border border-gray-200 px-3 py-2 text-sm bg-gray-50 prose prose-sm max-w-none overflow-auto"
            dangerouslySetInnerHTML={{ __html: issue.body_html }}
          />
        ) : (
          <textarea
            value={body}
            onChange={(e) => setBody(e.target.value)}
            disabled={!isEditable}
            rows={12}
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-50 disabled:text-gray-500"
          />
        )}
      </div>

      {/* Actions */}
      <div className="flex gap-2 flex-wrap">
        {isEditable && (
          <button
            onClick={handleSave}
            disabled={saving}
            className="px-4 py-2 bg-gray-800 text-white rounded-md text-sm font-medium disabled:opacity-50 hover:bg-gray-900 transition-colors"
          >
            {saving ? t("common.loading") : t("common.save")}
          </button>
        )}
        {isDraft && (
          <button
            onClick={handleSend}
            disabled={isSending || saving}
            className="px-4 py-2 bg-blue-600 text-white rounded-md text-sm font-medium disabled:opacity-50 hover:bg-blue-700 transition-colors"
          >
            {isSending
              ? t("newsletter.admin.editor.sending")
              : t("newsletter.admin.editor.send")}
          </button>
        )}
      </div>
    </div>
  );
}
