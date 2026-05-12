"use client";

/**
 * /admin/featured-artists — G'-7 admin-featured-artists
 *
 * Admin-only: monthly featured artist curation management.
 * Displays 12-month history grid and registration form.
 */

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useI18n } from "@/i18n";
import { fetchMe } from "@/lib/api";
import { useAdminFeaturedArtists } from "@/lib/hooks/useAdminFeaturedArtists";
import { FeaturedArtistForm } from "@/components/admin/FeaturedArtistForm";
import { FeaturedArtistsList } from "@/components/admin/FeaturedArtistsList";

export default function AdminFeaturedArtistsPage() {
  const { t } = useI18n();
  const router = useRouter();
  const [authChecking, setAuthChecking] = useState(true);
  const [isAdmin, setIsAdmin] = useState(false);
  const [showForm, setShowForm] = useState(false);

  const { entries, loading, error, creating, createError, create, deactivate } =
    useAdminFeaturedArtists({ limit: 12 });

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

  async function handleCreate(params: {
    artist_id: string;
    month: string;
    curation_note?: string;
  }) {
    const ok = await create(params);
    if (ok) setShowForm(false);
    return ok;
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
            {t("admin.featuredArtists.pageTitle")}
          </h1>
          <p className="text-sm text-text-muted mt-1">
            {t("admin.featuredArtists.pageSubtitle")}
          </p>
        </div>
        <button
          type="button"
          className="btn-primary text-sm px-4 py-2 flex-shrink-0"
          onClick={() => setShowForm((v) => !v)}
        >
          {showForm
            ? t("common.cancel")
            : t("admin.featuredArtists.createCta")}
        </button>
      </header>

      {/* Create form */}
      {showForm && (
        <div className="card p-5 mb-6">
          <h2 className="text-base font-semibold text-text-primary mb-4">
            {t("admin.featuredArtists.form.title")}
          </h2>
          <FeaturedArtistForm
            onSubmit={handleCreate}
            submitting={creating}
            error={createError}
          />
        </div>
      )}

      {/* History grid */}
      <div className="card p-5">
        <h2 className="text-base font-semibold text-text-primary mb-4">
          {t("admin.featuredArtists.list.title")}
        </h2>

        {error && (
          <div className="mb-4 text-sm text-danger">{error}</div>
        )}

        {loading ? (
          <div className="space-y-2">
            {[1, 2, 3].map((i) => (
              <div
                key={i}
                className="h-10 bg-surface-hover rounded animate-pulse"
              />
            ))}
          </div>
        ) : (
          <FeaturedArtistsList entries={entries} onDeactivate={deactivate} />
        )}
      </div>
    </main>
  );
}
