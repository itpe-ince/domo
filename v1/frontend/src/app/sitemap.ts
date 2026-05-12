/**
 * app/sitemap.ts — H'-3 Multi-language Sitemap
 *
 * Generates /sitemap.xml with hreflang alternates for all 5 supported locales.
 * Static routes only — dynamic artist/post URLs are excluded (too many to enumerate
 * without a crawl budget concern; dynamic OG is handled per-route).
 *
 * Next.js MetadataRoute.Sitemap supports `alternates.languages` per entry, which
 * produces <xhtml:link rel="alternate" hreflang="..."> tags in the sitemap XML.
 *
 * Revalidates every 24h (ISR cache).
 */

import type { MetadataRoute } from "next";
import { SITE_URL, SUPPORTED_LOCALES } from "@/lib/seo/locales";

// 24h ISR revalidation for the sitemap
export const revalidate = 86400;

/** Build language alternates for a given pathname */
function buildAlternates(pathname: string): Record<string, string> {
  return Object.fromEntries(
    SUPPORTED_LOCALES.map((locale) => [
      locale,
      `${SITE_URL}/${locale}${pathname}`,
    ])
  );
}

export default function sitemap(): MetadataRoute.Sitemap {
  const now = new Date();

  /** Static routes with full hreflang coverage */
  const staticRoutes: Array<{
    pathname: string;
    priority: number;
    changeFrequency: MetadataRoute.Sitemap[number]["changeFrequency"];
  }> = [
    { pathname: "/", priority: 1.0, changeFrequency: "daily" },
    { pathname: "/explore", priority: 0.9, changeFrequency: "daily" },
    { pathname: "/stories", priority: 0.8, changeFrequency: "daily" },
    { pathname: "/artists", priority: 0.8, changeFrequency: "daily" },
    { pathname: "/feed", priority: 0.7, changeFrequency: "hourly" },
    { pathname: "/search", priority: 0.6, changeFrequency: "weekly" },
    { pathname: "/communities", priority: 0.6, changeFrequency: "weekly" },
    { pathname: "/auctions", priority: 0.7, changeFrequency: "daily" },
    { pathname: "/legal", priority: 0.3, changeFrequency: "monthly" },
  ];

  return staticRoutes.map(({ pathname, priority, changeFrequency }) => ({
    url: `${SITE_URL}${pathname}`,
    lastModified: now,
    changeFrequency,
    priority,
    alternates: {
      languages: buildAlternates(pathname),
    },
  }));
}
