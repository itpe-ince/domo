"use client";

/**
 * /me/press-kit — C-2 press-kit-auto-export
 *
 * Artist self-service: view own press kit and download PDF.
 * Admin-generated; artist can see download URL if kit exists and is_public=true.
 */

import { useEffect, useState } from "react";
import { useI18n } from "@/i18n";
import { fetchMe, fetchUserPressKit } from "@/lib/api";
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

export default function MyPressKitPage() {
  const { t } = useI18n();
  const [userId, setUserId] = useState<string | null>(null);
  const [locale, setLocale] = useState("ko");
  const [kit, setKit] = useState<PressKitOut | null>(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);

  // Load own user ID on mount
  useEffect(() => {
    fetchMe()
      .then((user) => setUserId(user.id))
      .catch(() => setUserId(null))
      .finally(() => setLoading(false));
  }, []);

  // Fetch press kit when userId or locale changes
  useEffect(() => {
    if (!userId) return;
    setLoading(true);
    setNotFound(false);
    fetchUserPressKit(userId, locale)
      .then((data) => setKit(data))
      .catch(() => {
        setKit(null);
        setNotFound(true);
      })
      .finally(() => setLoading(false));
  }, [userId, locale]);

  return (
    <main className="flex-1 min-w-0 max-w-2xl mx-auto px-4 py-8">
      <header className="mb-6">
        <h1 className="text-2xl font-bold text-stone-900">
          {t("pressKit.me.pageTitle")}
        </h1>
        <p className="text-sm text-stone-500 mt-1">
          {t("pressKit.me.pageSubtitle")}
        </p>
      </header>

      {/* Locale selector */}
      <div className="mb-4 flex items-center gap-3">
        <label className="text-sm font-medium text-stone-600">
          {t("pressKit.locale")}
        </label>
        <select
          className="border border-stone-200 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-amber-400"
          value={locale}
          onChange={(e) => setLocale(e.target.value)}
          disabled={!userId}
        >
          {LOCALES.map((l) => (
            <option key={l.value} value={l.value}>
              {l.label}
            </option>
          ))}
        </select>
      </div>

      {loading && (
        <div className="h-32 bg-stone-100 rounded-xl animate-pulse" />
      )}

      {!loading && notFound && (
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-6 text-sm text-amber-700">
          {t("pressKit.me.noKit")}
        </div>
      )}

      {!loading && kit && (
        <div className="bg-white border border-amber-200 rounded-xl p-6 space-y-4">
          <div className="flex items-center justify-between">
            <span className="font-semibold text-stone-800 uppercase text-xs tracking-wide">
              {kit.locale}
            </span>
            {kit.is_public && (
              <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full font-medium">
                {t("pressKit.isPublic")}
              </span>
            )}
          </div>
          <div className="text-sm text-stone-500 space-y-1">
            <p>
              {t("pressKit.pages")}: <strong>{kit.page_count}</strong>
            </p>
            <p>
              {t("pressKit.fileSize")}:{" "}
              <strong>{formatBytes(kit.file_size_bytes)}</strong>
            </p>
            <p>
              {t("pressKit.expiresAt")}:{" "}
              <strong>
                {new Date(kit.expires_at).toLocaleDateString()}
              </strong>
            </p>
            {kit.interview_id && (
              <p className="text-indigo-600 text-xs">Interview included</p>
            )}
          </div>
          <a
            href={kit.download_url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 px-5 py-2.5 bg-amber-500 text-white rounded-lg font-semibold text-sm hover:bg-amber-600 transition"
          >
            {t("pressKit.me.download")}
          </a>
          <p className="text-xs text-stone-400 mt-1">
            {t("pressKit.me.publicToggleNote")}
          </p>
        </div>
      )}
    </main>
  );
}
