"use client";

/**
 * /me/newsletter — C-5 newsletter-digest
 *
 * User newsletter preference settings:
 * opt-in/out, frequency, locale.
 */

import { useI18n } from "@/i18n";
import { useMyNewsletterPreferences } from "@/lib/hooks/useMyNewsletterPreferences";

const LOCALES = [
  { value: "ko", label: "한국어" },
  { value: "en", label: "English" },
  { value: "ja", label: "日本語" },
  { value: "zh", label: "中文" },
  { value: "es", label: "Español" },
] as const;

const FREQUENCIES = [
  { value: "weekly", labelKey: "newsletter.preferences.frequency.weekly" },
  { value: "biweekly", labelKey: "newsletter.preferences.frequency.biweekly" },
  { value: "monthly", labelKey: "newsletter.preferences.frequency.monthly" },
  { value: "never", labelKey: "newsletter.preferences.frequency.never" },
] as const;

export default function MyNewsletterPage() {
  const { t } = useI18n();
  const {
    preferences,
    loading,
    error,
    saving,
    saveError,
    setSubscribed,
    setFrequency,
    setLocale,
  } = useMyNewsletterPreferences();

  if (loading) {
    return (
      <div className="p-8 text-center text-gray-500">{t("common.loading")}</div>
    );
  }

  if (error) {
    return (
      <div className="p-8 text-center text-red-500">{error}</div>
    );
  }

  if (!preferences) return null;

  return (
    <main className="max-w-xl mx-auto px-4 py-8" aria-label={t("newsletter.preferences.title")}>
      <h1 className="text-2xl font-bold mb-6">
        {t("newsletter.preferences.title")}
      </h1>

      {/* Opt-in toggle */}
      <div className="mb-6 p-4 bg-white rounded-lg border border-gray-200">
        <div className="flex items-center justify-between">
          <div>
            <p className="font-medium">{t("newsletter.preferences.subscribe.label")}</p>
            <p className="text-sm text-gray-500">
              {t("newsletter.preferences.subscribe.hint")}
            </p>
          </div>
          <button
            onClick={() => setSubscribed(!preferences.is_subscribed)}
            disabled={saving}
            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none ${
              preferences.is_subscribed ? "bg-blue-600" : "bg-gray-300"
            } disabled:opacity-50`}
            role="switch"
            aria-checked={preferences.is_subscribed}
            aria-label={t("newsletter.preferences.subscribe.label")}
          >
            <span
              className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                preferences.is_subscribed ? "translate-x-6" : "translate-x-1"
              }`}
            />
          </button>
        </div>
      </div>

      {/* Frequency */}
      <div className="mb-6 p-4 bg-white rounded-lg border border-gray-200">
        <label className="block font-medium mb-2">
          {t("newsletter.preferences.frequency.label")}
        </label>
        <select
          value={preferences.frequency}
          onChange={(e) =>
            setFrequency(
              e.target.value as "weekly" | "biweekly" | "monthly" | "never"
            )
          }
          disabled={saving}
          className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
        >
          {FREQUENCIES.map(({ value, labelKey }) => (
            <option key={value} value={value}>
              {t(labelKey)}
            </option>
          ))}
        </select>
      </div>

      {/* Preferred locale */}
      <div className="mb-6 p-4 bg-white rounded-lg border border-gray-200">
        <label className="block font-medium mb-2">
          {t("newsletter.preferences.locale.label")}
        </label>
        <select
          value={preferences.preferred_locale}
          onChange={(e) => setLocale(e.target.value)}
          disabled={saving}
          className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
        >
          {LOCALES.map(({ value, label }) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
      </div>

      {/* Last sent */}
      {preferences.last_sent_at && (
        <p className="text-sm text-gray-500 mb-4">
          {t("newsletter.preferences.lastSent", {
            date: new Date(preferences.last_sent_at).toLocaleDateString(),
          })}
        </p>
      )}

      {/* Saving state */}
      {saving && (
        <p className="text-sm text-blue-500">{t("common.loading")}</p>
      )}
      {saveError && (
        <p className="text-sm text-red-500">{saveError}</p>
      )}

      {/* Unsubscribe note */}
      <p className="text-xs text-gray-400 mt-6">
        {t("newsletter.preferences.unsubscribeNote")}
      </p>
    </main>
  );
}
