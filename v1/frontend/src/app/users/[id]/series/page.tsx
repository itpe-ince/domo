"use client";

/**
 * UserSeriesPage — publish-controls PDCA #8, Task 4.3.
 *
 * /users/[id]/series — author's series gallery (OQ-D-4=A: separate route).
 */

import { use, useEffect, useState } from "react";
import Link from "next/link";
import {
  listSeriesByAuthor,
  fetchUserProfile,
  type Series,
  type UserProfileView,
} from "@/lib/api";
import { SeriesCard } from "@/components/SeriesCard";
import { useI18n } from "@/i18n";

export default function UserSeriesPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const { t } = useI18n();
  const [profile, setProfile] = useState<UserProfileView | null>(null);
  const [series, setSeries] = useState<Series[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const [p, s] = await Promise.all([
        fetchUserProfile(id),
        listSeriesByAuthor(id),
      ]);
      setProfile(p);
      setSeries(s);
    } catch (e) {
      setError(e instanceof Error ? e.message : "load_failed");
    } finally {
      setLoading(false);
    }
  }

  if (loading) {
    return (
      <main className="min-h-screen flex items-center justify-center text-text-muted">
        {t("common.loading")}
      </main>
    );
  }

  if (error) {
    return (
      <main className="p-4 text-danger">{error}</main>
    );
  }

  return (
    <main className="max-w-5xl mx-auto p-4">
      <header className="mb-6">
        <Link
          href={`/users/${id}`}
          className="text-sm text-text-muted hover:underline"
        >
          &larr; {profile?.display_name ?? "User"}
        </Link>
        <h1 className="text-2xl font-bold mt-1">
          {t("post.series.byAuthor", {
            name: profile?.display_name ?? "",
          })}
        </h1>
      </header>

      {series.length === 0 ? (
        <div className="p-8 text-center text-text-muted bg-surface rounded-lg border border-border">
          {t("post.series.empty")}
        </div>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
          {series.map((s) => (
            <SeriesCard key={s.id} series={s} />
          ))}
        </div>
      )}
    </main>
  );
}
