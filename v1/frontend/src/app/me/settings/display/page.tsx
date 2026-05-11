"use client";

/**
 * /me/settings/display — 표시 설정 (locale, currency)
 * (이전 경로: /me/settings/preferences)
 */

import Link from "next/link";
import { useI18n } from "@/i18n";
import { useMe } from "@/lib/useMe";
import { PreferencesCard } from "@/components/PreferencesCard";

export default function DisplaySettingsPage() {
  const { t } = useI18n();
  const { me } = useMe();

  return (
    <main className="flex-1 min-w-0 max-w-2xl mx-auto px-6 py-8">
      {/* Breadcrumb */}
      <nav aria-label="breadcrumb" className="mb-6">
        <Link
          href="/me/settings"
          className="text-text-muted text-sm hover:text-primary"
        >
          ← {t("settings.hub.title")}
        </Link>
      </nav>

      <h1 className="text-2xl font-bold mb-2">{t("preferences.pageTitle")}</h1>
      <p className="text-text-muted text-sm mb-8">{t("preferences.pageSubtitle")}</p>

      <PreferencesCard isAuthenticated={!!me} className="max-w-md" />
    </main>
  );
}
