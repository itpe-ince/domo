"use client";

/**
 * /admin/media-coverage — C-4 media-coverage-cms
 *
 * Admin-only: media coverage CMS.
 * Create/edit/delete external media coverage entries (articles, YouTube, radio, etc.)
 */

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useI18n } from "@/i18n";
import { fetchMe } from "@/lib/api";
import type {
  AdminCreateMediaCoverageBody,
  MediaCoverageOut,
} from "@/lib/api";
import { useAdminMediaCoverage } from "@/lib/hooks/useAdminMediaCoverage";
import { MediaCoverageForm } from "@/components/admin/MediaCoverageForm";
import { MediaCoverageList } from "@/components/admin/MediaCoverageList";

export default function AdminMediaCoveragePage() {
  const { t } = useI18n();
  const router = useRouter();
  const [authChecking, setAuthChecking] = useState(true);
  const [isAdmin, setIsAdmin] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [editTarget, setEditTarget] = useState<MediaCoverageOut | null>(null);

  const {
    entries,
    loading,
    error,
    saving,
    saveError,
    hasMore,
    create,
    patch,
    remove,
    togglePublish,
    loadMore,
    reload,
  } = useAdminMediaCoverage({ limit: 20 });

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

  async function handleCreate(body: AdminCreateMediaCoverageBody) {
    const ok = await create(body);
    if (ok) {
      setShowForm(false);
      setEditTarget(null);
    }
    return ok;
  }

  async function handleEdit(body: AdminCreateMediaCoverageBody) {
    if (!editTarget) return false;
    const ok = await patch(editTarget.id, body);
    if (ok) {
      setEditTarget(null);
      setShowForm(false);
    }
    return ok;
  }

  function handleOpenEdit(entry: MediaCoverageOut) {
    setEditTarget(entry);
    setShowForm(true);
    // Scroll to top
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function handleCancelForm() {
    setShowForm(false);
    setEditTarget(null);
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
    <main className="flex-1 max-w-4xl mx-auto px-4 py-8 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-text-primary">
            {t("mediaCoverage.pageTitle")}
          </h1>
          <p className="text-sm text-text-muted mt-1">
            {t("mediaCoverage.pageSubtitle")}
          </p>
        </div>
        {!showForm && (
          <button
            type="button"
            className="btn-primary text-sm"
            onClick={() => {
              setEditTarget(null);
              setShowForm(true);
            }}
          >
            {t("mediaCoverage.addBtn")}
          </button>
        )}
      </div>

      {/* Form panel */}
      {showForm && (
        <div className="card p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-base font-semibold text-text-primary">
              {editTarget ? t("common.edit") : t("mediaCoverage.addBtn")}
            </h2>
            <button
              type="button"
              className="text-text-muted hover:text-text-primary text-sm"
              onClick={handleCancelForm}
            >
              {t("common.cancel")}
            </button>
          </div>
          <MediaCoverageForm
            key={editTarget?.id ?? "new"}
            initial={editTarget ?? undefined}
            onSubmit={editTarget ? handleEdit : handleCreate}
            submitting={saving}
            error={saveError}
          />
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="text-sm text-danger bg-danger/5 border border-danger/20 rounded-lg px-4 py-3">
          {error}
        </div>
      )}

      {/* List */}
      <MediaCoverageList
        entries={entries}
        loading={loading}
        hasMore={hasMore}
        onEdit={handleOpenEdit}
        onTogglePublish={togglePublish}
        onDelete={remove}
        onLoadMore={loadMore}
      />
    </main>
  );
}
