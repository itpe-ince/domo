"use client";

/**
 * /me/settings/profile — 자기소개 다국어 편집
 * (이전 경로: /me/bio)
 *
 * Artist bio editor for all 5 supported locales.
 *  - Locale tabs: ko / en / ja / zh / es
 *  - "Auto Translate (AI)" button: calls POST /me/bio/translate (5/day limit)
 *  - Per-locale textarea + Save button: PATCH /me/bio/{locale}
 *  - Shows is_machine_translated badge ("AI Translated" vs "Manually Edited")
 */

import Link from "next/link";
import { useState } from "react";
import { useI18n } from "@/i18n";
import { useMyBio } from "@/lib/hooks/useMyBio";

const LOCALES = ["ko", "en", "ja", "zh", "es"] as const;
type Locale = (typeof LOCALES)[number];

export default function ProfileSettingsPage() {
  const { t } = useI18n();
  const { loading, translating, saving, error, getBio, isMachineTranslated, triggerTranslate, saveLocale } =
    useMyBio();

  const [activeLocale, setActiveLocale] = useState<Locale>("ko");
  const [draftBio, setDraftBio] = useState<Record<Locale, string>>({
    ko: "",
    en: "",
    ja: "",
    zh: "",
    es: "",
  });
  const [translateMsg, setTranslateMsg] = useState<string | null>(null);
  const [saveMsg, setSaveMsg] = useState<Record<Locale, string | null>>({
    ko: null,
    en: null,
    ja: null,
    zh: null,
    es: null,
  });

  function getDisplayBio(locale: Locale): string {
    if (draftBio[locale]) return draftBio[locale];
    return getBio(locale);
  }

  async function handleTranslate() {
    setTranslateMsg(null);
    const ok = await triggerTranslate("ko");
    setTranslateMsg(ok ? t("bio.translateSuccess") : t("bio.translateError"));
    setDraftBio({ ko: "", en: "", ja: "", zh: "", es: "" });
  }

  async function handleSave(locale: Locale) {
    const text = getDisplayBio(locale);
    const ok = await saveLocale(locale, text);
    setSaveMsg((prev) => ({
      ...prev,
      [locale]: ok ? t("bio.saved") : t("bio.translateError"),
    }));
    setTimeout(() => {
      setSaveMsg((prev) => ({ ...prev, [locale]: null }));
    }, 2000);
  }

  return (
    <main className="flex-1 min-w-0 max-w-2xl mx-auto px-4 py-8" aria-label={t("bio.pageTitle")}>
      {/* Breadcrumb */}
      <nav aria-label="breadcrumb" className="mb-6">
        <Link
          href="/me/settings"
          className="text-text-muted text-sm hover:text-primary"
        >
          ← {t("settings.hub.title")}
        </Link>
      </nav>

      {/* Header */}
      <header className="mb-8">
        <h1 className="text-2xl font-bold text-text-primary">{t("bio.pageTitle")}</h1>
        <p className="text-text-muted mt-1">{t("bio.pageSubtitle")}</p>
      </header>

      {/* Auto-translate button */}
      <div className="mb-6">
        <button
          type="button"
          onClick={handleTranslate}
          disabled={translating || loading}
          className="px-4 py-2 rounded-lg bg-primary text-white font-medium text-sm disabled:opacity-50 transition-opacity"
        >
          {translating ? t("bio.translating") : t("bio.translateBtn")}
        </button>
        {translateMsg && (
          <p className="mt-2 text-sm text-text-muted">{translateMsg}</p>
        )}
      </div>

      {/* Locale tabs */}
      <div className="border-b border-border mb-6">
        <nav className="flex gap-1" role="tablist" aria-label={t("bio.pageTitle")}>
          {LOCALES.map((locale) => (
            <button
              key={locale}
              role="tab"
              aria-selected={activeLocale === locale}
              onClick={() => setActiveLocale(locale)}
              className={`px-4 py-2 text-sm font-medium rounded-t-md border-b-2 transition-colors ${
                activeLocale === locale
                  ? "border-primary text-primary"
                  : "border-transparent text-text-muted hover:text-text-primary"
              }`}
            >
              {t(`bio.localeTab.${locale}` as Parameters<typeof t>[0])}
            </button>
          ))}
        </nav>
      </div>

      {/* Editor for active locale */}
      {loading ? (
        <p className="text-text-muted text-sm">{t("common.loading")}</p>
      ) : (
        <div className="space-y-4">
          {/* Machine-translated badge */}
          <div className="flex items-center gap-2">
            <span
              className={`inline-flex items-center text-xs px-2 py-0.5 rounded-full font-medium ${
                isMachineTranslated(activeLocale)
                  ? "bg-accent/10 text-accent"
                  : "bg-success/10 text-success"
              }`}
            >
              {isMachineTranslated(activeLocale) ? t("bio.machineTranslated") : t("bio.humanEdited")}
            </span>
          </div>

          {/* Textarea */}
          <label htmlFor="bio-textarea" className="sr-only">
            {t("bio.bioPlaceholder")}
          </label>
          <textarea
            id="bio-textarea"
            className="w-full h-48 px-3 py-2 border border-border rounded-lg bg-surface text-text-primary text-sm resize-none focus:outline-none focus:ring-2 focus:ring-primary/50"
            placeholder={t("bio.bioPlaceholder")}
            aria-label={`${t("bio.pageTitle")} — ${activeLocale.toUpperCase()}`}
            value={getDisplayBio(activeLocale)}
            onChange={(e) =>
              setDraftBio((prev) => ({ ...prev, [activeLocale]: e.target.value }))
            }
          />

          {/* Save button + message */}
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => handleSave(activeLocale)}
              disabled={saving === activeLocale}
              className="px-4 py-2 rounded-lg bg-surface border border-border text-sm font-medium text-text-primary hover:bg-surface-hover disabled:opacity-50 transition"
            >
              {saving === activeLocale ? t("bio.saving") : t("bio.saveBtn")}
            </button>
            {saveMsg[activeLocale] && (
              <span className="text-sm text-text-muted">{saveMsg[activeLocale]}</span>
            )}
          </div>

          {/* Global error */}
          {error && (
            <p className="text-sm text-red-500">{error}</p>
          )}
        </div>
      )}
    </main>
  );
}
