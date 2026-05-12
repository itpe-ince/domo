"use client";

/**
 * NewsletterIssuesList — C-5 newsletter-digest
 *
 * Table-style list of newsletter issues for admin.
 */

import { useI18n } from "@/i18n";
import type { NewsletterIssueOut } from "@/lib/api";

interface Props {
  issues: NewsletterIssueOut[];
  loading: boolean;
  error: string | null;
  onEdit: (issue: NewsletterIssueOut) => void;
  onSend: (id: string) => Promise<void>;
  onRefresh: () => void;
  sendingId: string | null;
}

export function NewsletterIssuesList({
  issues,
  loading,
  error,
  onEdit,
  onSend,
  onRefresh,
  sendingId,
}: Props) {
  const { t } = useI18n();

  if (loading) {
    return (
      <div className="text-center text-gray-500 py-8">{t("common.loading")}</div>
    );
  }

  if (error) {
    return (
      <div className="text-center text-red-500 py-8">
        {error}
        <button
          onClick={onRefresh}
          className="ml-2 text-blue-600 hover:underline text-sm"
        >
          {t("newsletter.admin.list.retry")}
        </button>
      </div>
    );
  }

  if (issues.length === 0) {
    return (
      <div className="text-center text-gray-400 py-12">
        {t("newsletter.admin.list.empty")}
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-lg font-semibold">{t("newsletter.admin.list.title")}</h2>
        <button
          onClick={onRefresh}
          className="text-sm text-gray-500 hover:text-gray-700"
        >
          {t("newsletter.admin.list.refresh")}
        </button>
      </div>
      <div className="overflow-x-auto rounded-lg border border-gray-200">
        <table className="min-w-full divide-y divide-gray-200 text-sm">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left font-medium text-gray-600">
                {t("newsletter.admin.list.col.date")}
              </th>
              <th className="px-4 py-3 text-left font-medium text-gray-600">
                {t("newsletter.admin.list.col.locale")}
              </th>
              <th className="px-4 py-3 text-left font-medium text-gray-600">
                {t("newsletter.admin.list.col.subject")}
              </th>
              <th className="px-4 py-3 text-left font-medium text-gray-600">
                {t("newsletter.admin.list.col.status")}
              </th>
              <th className="px-4 py-3 text-left font-medium text-gray-600">
                {t("newsletter.admin.list.col.sent")}
              </th>
              <th className="px-4 py-3 text-left font-medium text-gray-600">
                {t("newsletter.admin.list.col.actions")}
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 bg-white">
            {issues.map((issue) => (
              <tr key={issue.id} className="hover:bg-gray-50 transition-colors">
                <td className="px-4 py-3 text-gray-700 whitespace-nowrap">
                  {issue.issue_date}
                </td>
                <td className="px-4 py-3 text-gray-700 uppercase">
                  {issue.locale}
                </td>
                <td className="px-4 py-3 text-gray-700 max-w-xs truncate">
                  {issue.subject}
                </td>
                <td className="px-4 py-3">
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
                </td>
                <td className="px-4 py-3 text-gray-700 whitespace-nowrap">
                  {issue.sent_count > 0 ? (
                    <span>
                      {issue.sent_count}
                      {issue.failed_count > 0 && (
                        <span className="text-red-500 ml-1">
                          (-{issue.failed_count})
                        </span>
                      )}
                    </span>
                  ) : (
                    "—"
                  )}
                </td>
                <td className="px-4 py-3">
                  <div className="flex gap-2">
                    <button
                      onClick={() => onEdit(issue)}
                      className="text-blue-600 hover:underline text-sm"
                    >
                      {t("common.edit")}
                    </button>
                    {issue.status === "draft" && (
                      <button
                        onClick={() => onSend(issue.id)}
                        disabled={sendingId === issue.id}
                        className="text-green-600 hover:underline text-sm disabled:opacity-50"
                      >
                        {sendingId === issue.id
                          ? t("common.loading")
                          : t("newsletter.admin.list.sendAction")}
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
