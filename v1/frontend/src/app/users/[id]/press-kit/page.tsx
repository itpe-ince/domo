"use client";

/**
 * /users/[id]/press-kit — C-2 press-kit-auto-export
 *
 * Public press kit page for external media.
 * Displays download link if the artist has enabled public download (is_public=true).
 */

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { useI18n } from "@/i18n";
import { fetchUserPressKit } from "@/lib/api";
import type { PressKitOut } from "@/lib/api";

const LOCALES = [
  { value: "ko", label: "한국어" },
  { value: "en", label: "English" },
  { value: "ja", label: "日本語" },
  { value: "zh", label: "中文" },
  { value: "es", label: "Español" },
];

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function UserPressKitPage() {
  const { t } = useI18n();
  const params = useParams<{ id: string }>();
  const artistId = params.id;
  const [locale, setLocale] = useState("ko");
  const [kit, setKit] = useState<PressKitOut | null>(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);

  useEffect(() => {
    if (!artistId) return;
    setLoading(true);
    setNotFound(false);
    fetchUserPressKit(artistId, locale)
      .then((data) => setKit(data))
      .catch(() => {
        setKit(null);
        setNotFound(true);
      })
      .finally(() => setLoading(false));
  }, [artistId, locale]);

  return (
    <main className="max-w-2xl mx-auto px-4 py-10">
      <div className="flex items-center gap-3 mb-6">
        <Link
          href={`/users/${artistId}`}
          className="text-sm text-stone-500 hover:text-stone-700 transition"
        >
          &larr; Profile
        </Link>
        <h1 className="text-xl font-bold text-stone-900">
          {t("pressKit.pageTitle")}
        </h1>
      </div>

      {/* Locale selector */}
      <div className="mb-6 flex items-center gap-3">
        <label className="text-sm font-medium text-stone-600">
          {t("pressKit.locale")}
        </label>
        <select
          className="border border-stone-200 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-amber-400"
          value={locale}
          onChange={(e) => setLocale(e.target.value)}
        >
          {LOCALES.map((l) => (
            <option key={l.value} value={l.value}>
              {l.label}
            </option>
          ))}
        </select>
      </div>

      {loading && (
        <div className="h-36 bg-stone-100 rounded-xl animate-pulse" />
      )}

      {!loading && notFound && (
        <div className="bg-stone-100 rounded-xl p-8 text-center text-stone-500 text-sm">
          {t("pressKit.noHistory")}
        </div>
      )}

      {!loading && kit && (
        <div className="bg-white border border-amber-200 rounded-xl shadow-sm p-8 space-y-5">
          {/* Header */}
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-amber-100 rounded-full flex items-center justify-center">
              <span className="text-amber-600 font-bold text-sm">
                {locale.toUpperCase()}
              </span>
            </div>
            <div>
              <p className="font-semibold text-stone-800">
                {t("pressKit.pageTitle")}
              </p>
              <p className="text-xs text-stone-400">
                {t("pressKit.pages")}: {kit.page_count} &middot;{" "}
                {formatBytes(kit.file_size_bytes)}
              </p>
            </div>
          </div>

          <p className="text-sm text-stone-500">
            {t("pressKit.pageSubtitle")}
          </p>

          {kit.interview_id && (
            <p className="text-xs text-indigo-600">Interview included</p>
          )}

          <div className="pt-2">
            <a
              href={kit.download_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 px-6 py-3 bg-amber-500 text-white rounded-lg font-semibold text-sm hover:bg-amber-600 transition shadow-sm"
            >
              {t("pressKit.downloadBtn")} (PDF)
            </a>
          </div>

          <p className="text-xs text-stone-400">
            {t("pressKit.expiresAt")}:{" "}
            {new Date(kit.expires_at).toLocaleDateString()}
          </p>
        </div>
      )}
    </main>
  );
}
