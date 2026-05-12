"use client";

/**
 * LocaleSwitcher — C-3 multi-language-story
 *
 * A compact locale selector that:
 *  - Reads the current locale from localStorage (key: "domo_locale")
 *  - Saves the selection back to localStorage on change
 *  - Fires a custom "domo-locale-changed" event so i18n provider can react
 *
 * Decision: cookie/localStorage-based (not URL subpath) for App Router
 * compatibility without needing a full subpath-routing migration.
 * SEO multi-language OG is handled separately (G'-6 booster, out of C-3 scope).
 */

import { useState, useEffect } from "react";
import { useI18n, type Locale } from "@/i18n";

export const LOCALE_CHANGED_EVENT = "domo-locale-changed";
// Must match the key used in I18nProvider (i18n/index.tsx)
export const LOCALE_STORAGE_KEY = "domo-locale";

export const SUPPORTED_LOCALES = ["ko", "en", "ja", "zh", "es"] as const;
export type SupportedLocale = (typeof SUPPORTED_LOCALES)[number];

export function getStoredLocale(): SupportedLocale {
  if (typeof window === "undefined") return "ko";
  const stored = localStorage.getItem(LOCALE_STORAGE_KEY);
  if (stored && SUPPORTED_LOCALES.includes(stored as SupportedLocale)) {
    return stored as SupportedLocale;
  }
  return "ko";
}

export function setStoredLocale(locale: SupportedLocale) {
  if (typeof window === "undefined") return;
  localStorage.setItem(LOCALE_STORAGE_KEY, locale);
  window.dispatchEvent(new CustomEvent(LOCALE_CHANGED_EVENT, { detail: locale }));
}

interface LocaleSwitcherProps {
  compact?: boolean; // true = show flag only, false = show full label
  className?: string;
}

const LOCALE_FLAGS: Record<SupportedLocale, string> = {
  ko: "🇰🇷",
  en: "🇺🇸",
  ja: "🇯🇵",
  zh: "🇨🇳",
  es: "🇪🇸",
};

const LOCALE_LABELS: Record<SupportedLocale, string> = {
  ko: "한국어",
  en: "English",
  ja: "日本語",
  zh: "中文",
  es: "Español",
};

export function LocaleSwitcher({ compact = false, className = "" }: LocaleSwitcherProps) {
  const { t, setLocale } = useI18n();
  const [current, setCurrent] = useState<SupportedLocale>("ko");
  const [open, setOpen] = useState(false);

  useEffect(() => {
    setCurrent(getStoredLocale());
  }, []);

  function handleSelect(locale: SupportedLocale) {
    setStoredLocale(locale);
    setLocale(locale as Locale); // sync i18n provider immediately
    setCurrent(locale);
    setOpen(false);
  }

  return (
    <div className={`relative inline-block ${className}`}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-1.5 px-2 py-1 rounded-md border border-border bg-surface text-sm text-text-primary hover:bg-surface-hover transition-colors"
        aria-label={t("localeSwitcher.label")}
        aria-expanded={open}
        aria-haspopup="listbox"
      >
        <span aria-hidden="true">{LOCALE_FLAGS[current]}</span>
        {!compact && (
          <span className="hidden sm:inline">{LOCALE_LABELS[current]}</span>
        )}
        <svg
          className={`w-3.5 h-3.5 text-text-muted transition-transform ${open ? "rotate-180" : ""}`}
          viewBox="0 0 20 20"
          fill="currentColor"
          aria-hidden="true"
        >
          <path
            fillRule="evenodd"
            d="M5.22 8.22a.75.75 0 0 1 1.06 0L10 11.94l3.72-3.72a.75.75 0 1 1 1.06 1.06l-4.25 4.25a.75.75 0 0 1-1.06 0L5.22 9.28a.75.75 0 0 1 0-1.06Z"
            clipRule="evenodd"
          />
        </svg>
      </button>

      {open && (
        <>
          {/* Backdrop to close dropdown */}
          <div
            className="fixed inset-0 z-10"
            onClick={() => setOpen(false)}
            aria-hidden="true"
          />
          <ul
            role="listbox"
            aria-label={t("localeSwitcher.label")}
            className="absolute right-0 mt-1 z-20 min-w-[130px] bg-surface border border-border rounded-lg shadow-lg overflow-hidden"
          >
            {SUPPORTED_LOCALES.map((locale) => (
              <li key={locale} role="option" aria-selected={locale === current}>
                <button
                  type="button"
                  onClick={() => handleSelect(locale)}
                  className={`w-full flex items-center gap-2 px-3 py-2 text-sm text-left transition-colors ${
                    locale === current
                      ? "bg-primary/10 text-primary font-medium"
                      : "text-text-primary hover:bg-surface-hover"
                  }`}
                >
                  <span aria-hidden="true">{LOCALE_FLAGS[locale]}</span>
                  <span>{LOCALE_LABELS[locale]}</span>
                </button>
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}
