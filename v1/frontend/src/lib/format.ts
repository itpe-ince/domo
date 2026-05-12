/**
 * format.ts — G'-10 price-unit-consistency helpers + B'-1 multi-currency helpers.
 *
 * All monetary values in the Domo API are stored and transmitted as cents
 * (integer). Use these helpers to convert between cents and display values.
 *
 * B'-1 additions:
 *   - convertAndFormat(cents, native, target, rates) — convert then display
 *   - getStoredCurrency() — read user's preferred currency from localStorage
 *
 * Do NOT use Number().toLocaleString() on raw API price fields — those are
 * cents, not dollars.
 */

import type { SupportedCurrency } from "@/components/CurrencySwitcher";

/**
 * Format a cents integer as a locale-aware currency string.
 *
 * @example
 * formatPriceCents(5000)           // "$50.00" (en-US)
 * formatPriceCents(5000, "KRW")    // "₩5,000"
 * formatPriceCents(130000, "KRW")  // "₩1,300"   (130000 KRW-cents = 1300 won)
 * formatPriceCents(null)           // "—"
 */
export function formatPriceCents(
  cents: number | null | undefined,
  currency = "USD",
  locale?: string
): string {
  if (cents == null) return "—"; // em-dash
  return new Intl.NumberFormat(locale ?? "en-US", {
    style: "currency",
    currency,
    minimumFractionDigits: currency === "KRW" || currency === "JPY" ? 0 : 2,
    maximumFractionDigits: currency === "KRW" || currency === "JPY" ? 0 : 2,
  }).format(cents / 100);
}

/**
 * Parse a user-entered dollar string into cents.
 * Strips non-numeric characters except decimal point.
 *
 * Returns null if the input is empty or non-numeric.
 *
 * @example
 * parsePriceToCents("50")      // 5000
 * parsePriceToCents("50.00")   // 5000
 * parsePriceToCents("$50.99")  // 5099
 * parsePriceToCents("")        // null
 */
export function parsePriceToCents(input: string): number | null {
  const cleaned = input.replace(/[^0-9.]/g, "");
  if (cleaned === "" || cleaned === ".") return null;
  const num = Number(cleaned);
  if (isNaN(num)) return null;
  return Math.round(num * 100);
}

/**
 * Format cents as a simple dollar string without currency symbol.
 * Useful for input placeholder / aria-labels.
 *
 * @example
 * centsToDollarsString(5000)  // "50.00"
 * centsToDollarsString(null)  // ""
 */
export function centsToDollarsString(cents: number | null | undefined): string {
  if (cents == null) return "";
  return (cents / 100).toFixed(2);
}

// ─── B'-1 multi-currency helpers ─────────────────────────────────────────────

/** Rates map returned by GET /v1/exchange-rates (base=USD). */
export type ExchangeRates = Record<string, number>;

/**
 * Convert cents from native currency to target currency using provided rates.
 *
 * All amounts are stored as cents (×100 of the major unit).
 * Conversion: native_cents → USD_cents (÷ from_rate) → target_cents (× to_rate).
 *
 * @param cents        - Amount in native currency cents
 * @param nativeCurrency - Currency the amount is stored in (e.g. "KRW")
 * @param targetCurrency - Currency to display in (e.g. "USD")
 * @param rates        - USD-based exchange rates from GET /v1/exchange-rates
 * @returns            - Converted amount in target currency cents
 *
 * @example
 * // 1300 KRW-cents (= 13 won) → USD at rate 1300 → 0.01 USD-cents = 1 cent
 * convertCents(1300, "KRW", "USD", { KRW: 1300, USD: 1 }) // 1
 */
export function convertCents(
  cents: number,
  nativeCurrency: string,
  targetCurrency: string,
  rates: ExchangeRates
): number {
  if (nativeCurrency === targetCurrency) return cents;
  const fromRate = rates[nativeCurrency] ?? 1;
  const toRate = rates[targetCurrency] ?? 1;
  // Convert via USD
  const usdCents = cents / fromRate;
  return Math.round(usdCents * toRate);
}

/**
 * Convert cents from native currency to target currency, then format for display.
 *
 * Used by PostCard / FeedItem / posts/[id] to show prices in user's preferred currency.
 * DB native currency is preserved; only the display changes.
 *
 * @example
 * convertAndFormat(130000, "KRW", "USD", { KRW: 1300, USD: 1 })
 * // → "$1.00"
 *
 * convertAndFormat(100, "USD", "KRW", { KRW: 1300, USD: 1 })
 * // → "₩13"
 */
export function convertAndFormat(
  cents: number | null | undefined,
  nativeCurrency: string,
  targetCurrency: string,
  rates: ExchangeRates | null | undefined
): string {
  if (cents == null) return "—";
  if (!rates || nativeCurrency === targetCurrency) {
    return formatPriceCents(cents, nativeCurrency);
  }
  const converted = convertCents(cents, nativeCurrency, targetCurrency, rates);
  return formatPriceCents(converted, targetCurrency);
}

/**
 * Read the user's preferred currency from localStorage.
 * Returns "USD" if not set or SSR context.
 */
export function getPreferredCurrency(): SupportedCurrency {
  if (typeof window === "undefined") return "USD";
  const stored = localStorage.getItem("domo-currency");
  const supported = ["USD", "KRW", "EUR", "JPY"] as const;
  if (stored && supported.includes(stored as SupportedCurrency)) {
    return stored as SupportedCurrency;
  }
  return "USD";
}
