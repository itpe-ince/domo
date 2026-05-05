/**
 * format.ts — G'-10 price-unit-consistency helpers.
 *
 * All monetary values in the Domo API are stored and transmitted as cents
 * (integer). Use these helpers to convert between cents and display dollars.
 *
 * Do NOT use Number().toLocaleString() on raw API price fields — those are
 * cents, not dollars.
 */

/**
 * Format a cents integer as a locale-aware currency string.
 *
 * @example
 * formatPriceCents(5000)           // "$50.00" (en-US)
 * formatPriceCents(5000, "KRW")    // "₩5,000"
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
