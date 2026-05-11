"use client";

/**
 * /me/settings/display — 표시 설정 (통화, 인터페이스 언어)
 * (이전 경로: /me/settings/preferences)
 *
 * 통화/언어 선택을 라디오 버튼 목록으로 제공.
 * 사이드바 컴팩트 popover와 분리 (PreferencesCard는 Sidebar 전용).
 */

import { useEffect, useState } from "react";
import Link from "next/link";
import { useI18n, LOCALE_LABELS, Locale } from "@/i18n";
import { useMe } from "@/lib/useMe";
import {
  SUPPORTED_CURRENCIES,
  SupportedCurrency,
  CURRENCY_SYMBOLS,
  CURRENCY_CHANGED_EVENT,
  getStoredCurrency,
  setStoredCurrency,
} from "@/components/CurrencySwitcher";

export default function DisplaySettingsPage() {
  const { t, locale, setLocale } = useI18n();
  const { me } = useMe();
  const isAuthenticated = !!me;

  const [currency, setCurrency] = useState<SupportedCurrency>("USD");

  /* localStorage sync */
  useEffect(() => {
    setCurrency(getStoredCurrency());

    function onCurrencyChange(e: Event) {
      const evt = e as CustomEvent<SupportedCurrency>;
      setCurrency(evt.detail);
    }
    window.addEventListener(CURRENCY_CHANGED_EVENT, onCurrencyChange);
    return () =>
      window.removeEventListener(CURRENCY_CHANGED_EVENT, onCurrencyChange);
  }, []);

  async function handleCurrencySelect(c: SupportedCurrency) {
    setStoredCurrency(c);
    setCurrency(c);

    if (isAuthenticated) {
      try {
        const token =
          typeof window !== "undefined"
            ? localStorage.getItem("domo_access_token")
            : null;
        if (token) {
          await fetch(
            `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:3710/v1"}/me/preferences/currency`,
            {
              method: "PATCH",
              headers: {
                "Content-Type": "application/json",
                Authorization: `Bearer ${token}`,
              },
              body: JSON.stringify({ currency: c }),
            }
          );
        }
      } catch {
        // Non-fatal — localStorage is source of truth
      }
    }
  }

  function handleLocaleSelect(l: Locale) {
    setLocale(l);
  }

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
      <p className="text-text-muted text-sm mb-8">
        {t("preferences.pageSubtitle")}
      </p>

      {/* ─── 통화 ─── */}
      <section className="mb-8" aria-labelledby="currency-heading">
        <h2
          id="currency-heading"
          className="text-sm font-semibold text-text-secondary uppercase tracking-wider mb-3"
        >
          {t("preferences.currency.label")}
        </h2>
        <ul
          role="radiogroup"
          aria-labelledby="currency-heading"
          className="bg-surface border border-border rounded-xl divide-y divide-border/50 overflow-hidden"
        >
          {SUPPORTED_CURRENCIES.map((c) => {
            const selected = c === currency;
            return (
              <li key={c}>
                <button
                  type="button"
                  role="radio"
                  aria-checked={selected}
                  onClick={() => handleCurrencySelect(c)}
                  className={`w-full flex items-center gap-3 px-4 py-3 text-left transition-colors ${
                    selected ? "bg-primary/5" : "hover:bg-surface-hover"
                  }`}
                >
                  <RadioIndicator selected={selected} />
                  <span className="font-mono w-5 text-center text-base font-semibold text-primary">
                    {CURRENCY_SYMBOLS[c]}
                  </span>
                  <span className="font-medium text-text-primary">{c}</span>
                  <span className="ml-auto text-sm text-text-muted">
                    {t(`currency.label.${c}`)}
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
      </section>

      {/* ─── 언어 ─── */}
      <section aria-labelledby="locale-heading">
        <h2
          id="locale-heading"
          className="text-sm font-semibold text-text-secondary uppercase tracking-wider mb-3"
        >
          {t("preferences.locale.label")}
        </h2>
        <ul
          role="radiogroup"
          aria-labelledby="locale-heading"
          className="bg-surface border border-border rounded-xl divide-y divide-border/50 overflow-hidden"
        >
          {(
            Object.entries(LOCALE_LABELS) as [
              Locale,
              { flag: string; name: string },
            ][]
          ).map(([code, { flag, name }]) => {
            const selected = code === locale;
            return (
              <li key={code}>
                <button
                  type="button"
                  role="radio"
                  aria-checked={selected}
                  onClick={() => handleLocaleSelect(code)}
                  className={`w-full flex items-center gap-3 px-4 py-3 text-left transition-colors ${
                    selected ? "bg-primary/5" : "hover:bg-surface-hover"
                  }`}
                >
                  <RadioIndicator selected={selected} />
                  <span className="text-lg leading-none" aria-hidden="true">
                    {flag}
                  </span>
                  <span className="font-medium text-text-primary">{name}</span>
                </button>
              </li>
            );
          })}
        </ul>
      </section>
    </main>
  );
}

function RadioIndicator({ selected }: { selected: boolean }) {
  return (
    <span
      aria-hidden="true"
      className={`flex-shrink-0 w-4 h-4 rounded-full border-2 flex items-center justify-center transition-colors ${
        selected ? "border-primary" : "border-border"
      }`}
    >
      {selected && <span className="w-2 h-2 rounded-full bg-primary" />}
    </span>
  );
}
