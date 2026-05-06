"use client";

/**
 * /admin/artist-interviews — C-1 ai-artist-interview-generation
 *
 * Admin-only: LLM interview generation, review queue, publish workflow.
 */

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useI18n } from "@/i18n";
import { fetchMe } from "@/lib/api";
import dynamic from "next/dynamic";
import { useAdminInterviews } from "@/lib/hooks/useAdminInterviews";
import { InterviewsList } from "@/components/admin/InterviewsList";
import type { ArtistInterviewOut } from "@/lib/api";

// Heavy admin modals — lazy-load to keep the interviews list chunk small
const InterviewGenerateModal = dynamic(
  () => import("@/components/admin/InterviewGenerateModal").then((m) => ({ default: m.InterviewGenerateModal })),
  { ssr: false, loading: () => null }
);
const InterviewReviewModal = dynamic(
  () => import("@/components/admin/InterviewReviewModal").then((m) => ({ default: m.InterviewReviewModal })),
  { ssr: false, loading: () => null }
);

const STATUS_TABS = [
  "admin_review",
  "approved",
  "published",
  "rejected",
] as const;

export default function AdminArtistInterviewsPage() {
  const { t } = useI18n();
  const router = useRouter();
  const [authChecking, setAuthChecking] = useState(true);
  const [isAdmin, setIsAdmin] = useState(false);
  const [showGenerate, setShowGenerate] = useState(false);
  const [reviewing, setReviewing] = useState<ArtistInterviewOut | null>(null);

  const {
    interviews,
    loading,
    error,
    generating,
    generateError,
    generate,
    approve,
    reject,
    patch,
    publish,
    reload,
    setStatusFilter,
    statusFilter,
  } = useAdminInterviews({ limit: 20, initialStatus: "admin_review" });

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

  function handleTabChange(status: string) {
    setStatusFilter(status);
    reload({ status });
  }

  async function handleGenerate(params: {
    artist_id: string;
    locale: string;
  }): Promise<boolean> {
    const result = await generate(params);
    if (result) {
      setShowGenerate(false);
      return true;
    }
    return false;
  }

  if (authChecking) {
    return (
      <main className="flex-1 flex items-center justify-center">
        <p className="text-text-muted text-sm">{t("common.loading")}</p>
      </main>
    );
  }

  if (!isAdmin) return null;

  return (
    <main className="flex-1 min-w-0 max-w-3xl mx-auto px-4 py-8">
      {/* Header */}
      <header className="mb-6 flex items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-text-primary">
            {t("interview.admin.pageTitle")}
          </h1>
          <p className="text-sm text-text-muted mt-1">
            {t("interview.admin.pageSubtitle")}
          </p>
        </div>
        <button
          type="button"
          className="btn-primary text-sm px-4 py-2 flex-shrink-0"
          onClick={() => setShowGenerate(true)}
        >
          {t("interview.admin.generateCta")}
        </button>
      </header>

      {/* Status tabs */}
      <nav className="flex gap-1 mb-6 border-b border-border" aria-label="Interview status filter">
        {STATUS_TABS.map((s) => (
          <button
            key={s}
            type="button"
            className={`text-sm px-3 py-2 border-b-2 -mb-px transition-colors ${
              statusFilter === s
                ? "border-primary text-primary"
                : "border-transparent text-text-muted hover:text-text-primary"
            }`}
            onClick={() => handleTabChange(s)}
          >
            {t(`interview.status.${s}` as `interview.status.${string}`)}
          </button>
        ))}
      </nav>

      {/* Interview list */}
      <div className="card p-5">
        {error && (
          <div className="mb-4 text-sm text-danger">{error}</div>
        )}

        {loading ? (
          <div className="space-y-2">
            {[1, 2, 3].map((i) => (
              <div
                key={i}
                className="h-14 bg-surface-hover rounded animate-pulse"
              />
            ))}
          </div>
        ) : (
          <InterviewsList
            interviews={interviews}
            onReview={(interview) => setReviewing(interview)}
          />
        )}
      </div>

      {/* Generate modal */}
      {showGenerate && (
        <InterviewGenerateModal
          onGenerate={handleGenerate}
          generating={generating}
          error={generateError}
          onClose={() => setShowGenerate(false)}
        />
      )}

      {/* Review modal */}
      {reviewing && (
        <InterviewReviewModal
          interview={reviewing}
          onApprove={approve}
          onReject={reject}
          onPatch={patch}
          onPublish={publish}
          onClose={() => setReviewing(null)}
        />
      )}
    </main>
  );
}
