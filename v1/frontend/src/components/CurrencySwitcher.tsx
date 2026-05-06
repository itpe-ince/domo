"use client";

/**
 * CurrencySwitcher — B'-1 multi-currency-foundation
 *
 * Mirrors LocaleSwitcher pattern:
 *  - Reads current currency from localStorage (key: "domo-currency")
 *  - Saves selection back to localStorage on change
 *  - Fires a custom "domo-currency-changed" event so consumers can react
 *  - Optionally PATCHes /v1/me/preferences/currency when user is authenticated
 *
 * Supported: USD / KRW / EUR / JPY
 */

import { useState, useEffect } from "react";
import { useI18n } from "@/i18n";

export const CURRENCY_CHANGED_EVENT = "domo-currency-changed";
export const CURRENCY_STORAGE_KEY = "domo-currency";

export const SUPPORTED_CURRENCIES = ["USD", "KRW", "EUR", "JPY"] as const;
export type SupportedCurrency = (typeof SUPPORTED_CURRENCIES)[number];

export const CURRENCY_SYMBOLS: Record<SupportedCurrency, string> = {
  USD: "$",
  KRW: "₩",
  EUR: "€",
  JPY: "¥",
};

export function getStoredCurrency(): SupportedCurrency {
  if (typeof window === "undefined") return "USD";
  const stored = localStorage.getItem(CURRENCY_STORAGE_KEY);
  if (stored && SUPPORTED_CURRENCIES.includes(stored as SupportedCurrency)) {
    return stored as SupportedCurrency;
  }
  return "USD";
}

export function setStoredCurrency(currency: SupportedCurrency) {
  if (typeof window === "undefined") return;
  localStorage.setItem(CURRENCY_STORAGE_KEY, currency);
  window.dispatchEvent(
    new CustomEvent(CURRENCY_CHANGED_EVENT, { detail: currency })
  );
}

interface CurrencySwitcherProps {
  compact?: boolean;
  className?: string;
  /** When true, also PATCHes /v1/me/preferences/currency (requires auth). */
  syncToServer?: boolean;
}

export function CurrencySwitcher({
  compact = false,
  className = "",
  syncToServer = false,
}: CurrencySwitcherProps) {
  const { t } = useI18n();
  const [current, setCurrent] = useState<SupportedCurrency>("USD");
  const [open, setOpen] = useState(false);

  useEffect(() => {
    setCurrent(getStoredCurrency());

    function onCurrencyChange(e: Event) {
      const evt = e as CustomEvent<SupportedCurrency>;
      setCurrent(evt.detail);
    }
    window.addEventListener(CURRENCY_CHANGED_EVENT, onCurrencyChange);
    return () => window.removeEventListener(CURRENCY_CHANGED_EVENT, onCurrencyChange);
  }, []);

  async function handleSelect(currency: SupportedCurrency) {
    setStoredCurrency(currency);
    setCurrent(currency);
    setOpen(false);

    if (syncToServer) {
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
              body: JSON.stringify({ currency }),
            }
          );
        }
      } catch {
        // Non-fatal — localStorage is source of truth
      }
    }
  }

  return (
    <div className={`relative inline-block ${className}`}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-1.5 px-2 py-1 rounded-md border border-border bg-surface text-sm text-text-primary hover:bg-surface-hover transition-colors"
        aria-label={t("currency.switcher.label")}
        aria-expanded={open}
        aria-haspopup="listbox"
      >
        <span className="font-mono font-semibold text-xs text-primary">
          {CURRENCY_SYMBOLS[current]}
        </span>
        {!compact && (
          <span className="hidden sm:inline text-xs">{current}</span>
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
          <div
            className="fixed inset-0 z-10"
            onClick={() => setOpen(false)}
            aria-hidden="true"
          />
          <ul
            role="listbox"
            aria-label={t("currency.switcher.label")}
            className="absolute right-0 mt-1 z-20 min-w-[100px] bg-surface border border-border rounded-lg shadow-lg overflow-hidden"
          >
            {SUPPORTED_CURRENCIES.map((currency) => (
              <li key={currency} role="option" aria-selected={currency === current}>
                <button
                  type="button"
                  onClick={() => handleSelect(currency)}
                  className={`w-full flex items-center gap-2 px-3 py-2 text-sm text-left transition-colors ${
                    currency === current
                      ? "bg-primary/10 text-primary font-medium"
                      : "text-text-primary hover:bg-surface-hover"
                  }`}
                >
                  <span className="font-mono w-4 text-center">
                    {CURRENCY_SYMBOLS[currency]}
                  </span>
                  <span>{currency}</span>
                  <span className="text-xs text-text-muted">
                    {t(`currency.label.${currency}`)}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}
