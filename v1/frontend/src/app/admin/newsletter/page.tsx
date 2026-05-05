"use client";

/**
 * /admin/newsletter — C-5 newsletter-digest
 *
 * Admin-only: newsletter issue management.
 * Compose, edit, list, and send newsletter issues.
 */

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useI18n } from "@/i18n";
import { fetchMe } from "@/lib/api";
import type { NewsletterIssueOut } from "@/lib/api";
import { useAdminNewsletter } from "@/lib/hooks/useAdminNewsletter";
import { NewsletterIssuesList } from "@/components/admin/NewsletterIssuesList";
import { NewsletterIssueEditor } from "@/components/admin/NewsletterIssueEditor";

export default function AdminNewsletterPage() {
  const { t } = useI18n();
  const router = useRouter();
  const [authChecking, setAuthChecking] = useState(true);
  const [isAdmin, setIsAdmin] = useState(false);
  const [editTarget, setEditTarget] = useState<NewsletterIssueOut | null>(null);

  const {
    issues,
    loading,
    error,
    composing,
    composeError,
    compose,
    loadIssues,
    patchIssue,
    sendIssue,
    sending,
  } = useAdminNewsletter();

  // Auth gate — redirect non-admins
  useEffect(() => {
    fetchMe()
      .then((user) => {
        if (user.role !== "admin") {
          router.replace("/");
        } else {
          setIsAdmin(true);
        }
      })
      .catch(() => {
        router.replace("/");
      })
      .finally(() => {
        setAuthChecking(false);
      });
  }, [router]);

  if (authChecking) {
    return (
      <div className="p-8 text-center text-gray-500">
        {t("common.loading")}
      </div>
    );
  }

  if (!isAdmin) return null;

  const today = new Date().toISOString().split("T")[0];

  const handleCompose = async (locale: string) => {
    const issue = await compose({ issue_date: today, locale });
    if (issue) {
      setEditTarget(issue);
    }
  };

  const handleSend = async (id: string) => {
    await sendIssue(id);
  };

  const handleSave = async (
    id: string,
    body: { subject?: string; body_markdown?: string }
  ) => {
    const updated = await patchIssue(id, body);
    if (updated) setEditTarget(updated);
  };

  return (
    <div className="max-w-5xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold mb-6">
        {t("newsletter.admin.title")}
      </h1>

      {/* Compose controls */}
      <div className="mb-6 p-4 bg-gray-50 rounded-lg border border-gray-200">
        <h2 className="text-lg font-semibold mb-3">
          {t("newsletter.admin.compose.title")}
        </h2>
        <div className="flex gap-2 flex-wrap">
          {(["ko", "en", "ja", "zh", "es"] as const).map((locale) => (
            <button
              key={locale}
              onClick={() => handleCompose(locale)}
              disabled={composing}
              className="px-4 py-2 bg-blue-600 text-white rounded-md text-sm font-medium disabled:opacity-50 hover:bg-blue-700 transition-colors"
            >
              {composing
                ? t("common.loading")
                : t("newsletter.admin.compose.button", { locale })}
            </button>
          ))}
        </div>
        {composeError && (
          <p className="mt-2 text-sm text-red-500">{composeError}</p>
        )}
      </div>

      {/* Issue editor (when editing) */}
      {editTarget && (
        <NewsletterIssueEditor
          issue={editTarget}
          onSave={handleSave}
          onSend={handleSend}
          onClose={() => setEditTarget(null)}
          isSending={sending === editTarget.id}
        />
      )}

      {/* Issues list */}
      <NewsletterIssuesList
        issues={issues}
        loading={loading}
        error={error}
        onEdit={setEditTarget}
        onSend={handleSend}
        onRefresh={() => loadIssues()}
        sendingId={sending}
      />
    </div>
  );
}
