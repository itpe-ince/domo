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
  t: (key: string) => string;
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
    (key: string) => getNestedValue(messages[locale], key),
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
