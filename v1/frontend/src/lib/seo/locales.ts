/**
 * lib/seo/locales.ts — H'-3 Multi-language SEO meta shared constants
 *
 * Locale → og:locale mapping and hreflang language tag helpers used by all
 * generateMetadata() exports across the 4 key routes.
 *
 * Locale codes follow BCP 47 (language tag) and og:locale (underscore) conventions.
 */

export const SITE_URL =
  process.env.NEXT_PUBLIC_SITE_URL ?? "https://domo.lounge";

/** og:locale value for each supported locale */
export const OG_LOCALE: Record<string, string> = {
  ko: "ko_KR",
  en: "en_US",
  ja: "ja_JP",
  zh: "zh_CN",
  es: "es_ES",
};

/** All 5 supported locales */
export const SUPPORTED_LOCALES = ["ko", "en", "ja", "zh", "es"] as const;
export type SeoLocale = (typeof SUPPORTED_LOCALES)[number];

/** Default locale for server-rendered content (Korean-primary platform) */
export const DEFAULT_LOCALE: SeoLocale = "ko";

/**
 * Build Next.js `alternates.languages` object for a given pathname.
 * Produces hreflang tags for all 5 supported locales.
 *
 * Next.js metadata `alternates.languages` emits:
 *   <link rel="alternate" hreflang="ko" href="https://domo.lounge/ko/users/123" />
 *
 * @param pathname  e.g. "/users/abc123"
 */
export function buildAlternateLanguages(
  pathname: string
): Record<string, string> {
  return Object.fromEntries(
    SUPPORTED_LOCALES.map((locale) => [
      locale,
      `${SITE_URL}/${locale}${pathname}`,
    ])
  );
}

/**
 * Build the og:locale:alternate list (all locales except the primary).
 */
export function buildOgLocaleAlternates(primary = DEFAULT_LOCALE): string[] {
  return SUPPORTED_LOCALES.filter((l) => l !== primary).map(
    (l) => OG_LOCALE[l]
  );
}

/**
 * Build canonical URL for a pathname.
 */
export function buildCanonical(pathname: string): string {
  return `${SITE_URL}${pathname}`;
}
