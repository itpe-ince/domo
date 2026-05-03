"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";
import ko from "./ko.json";
import en from "./en.json";
import ja from "./ja.json";
import zh from "./zh.json";
import es from "./es.json";

export type Locale = "ko" | "en" | "ja" | "zh" | "es";

const messages: Record<Locale, Record<string, any>> = { ko, en, ja, zh, es };

export const LOCALE_LABELS: Record<Locale, { flag: string; name: string }> = {
  ko: { flag: "🇰🇷", name: "한국어" },
  en: { flag: "🇺🇸", name: "English" },
  ja: { flag: "🇯🇵", name: "日本語" },
  zh: { flag: "🇹🇼", name: "繁體中文" },
  es: { flag: "🇪🇸", name: "Español" },
};

type I18nContextType = {
  locale: Locale;
  setLocale: (l: Locale) => void;
  /**
   * Translate a key. Optional `params` performs simple `{{varName}}`
   * substitution — added 2026-05-02 (editor-media-ux PDCA #4) so callers
   * can pass `{ remaining: "10" }` etc. Existing single-arg calls are
   * unaffected.
   */
  t: (key: string, params?: Record<string, string | number>) => string;
};

const I18nContext = createContext<I18nContextType>({
  locale: "ko",
  setLocale: () => {},
  t: (key) => key,
});

function getNestedValue(obj: any, path: string): string {
  const result = path.split(".").reduce((o, k) => o?.[k], obj);
  return typeof result === "string" ? result : path;
}

function interpolate(
  template: string,
  params?: Record<string, string | number>
): string {
  if (!params) return template;
  return template.replace(/\{\{\s*(\w+)\s*\}\}/g, (_match, name: string) =>
    params[name] !== undefined ? String(params[name]) : `{{${name}}}`
  );
}

export function I18nProvider({ children }: { children: React.ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>(() => {
    if (typeof window === "undefined") return "ko";
    return (localStorage.getItem("domo-locale") as Locale) || "ko";
  });

  useEffect(() => {
    localStorage.setItem("domo-locale", locale);
    document.documentElement.lang = locale;
  }, [locale]);

  const setLocale = useCallback((l: Locale) => {
    setLocaleState(l);
  }, []);

  const t = useCallback(
    (key: string, params?: Record<string, string | number>) =>
      interpolate(getNestedValue(messages[locale], key), params),
    [locale]
  );

  return (
    <I18nContext.Provider value={{ locale, setLocale, t }}>
      {children}
    </I18nContext.Provider>
  );
}

export function useI18n() {
  return useContext(I18nContext);
}
