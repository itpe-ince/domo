/**
 * /stories/layout.tsx — H'-3 Multi-language SEO meta
 *
 * Server component: exports generateMetadata for the A-7 Storytelling Hub.
 * Static metadata (no API fetch needed — hub page content is list-based).
 *
 * H'-3: og:locale + og:locale:alternate + hreflang alternates + canonical.
 *
 * Non-visual — passes children through unchanged.
 */

import type { Metadata } from "next";
import {
  buildAlternateLanguages,
  buildCanonical,
  buildOgLocaleAlternates,
  OG_LOCALE,
  DEFAULT_LOCALE,
} from "@/lib/seo/locales";

const pathname = "/stories";

export const metadata: Metadata = {
  title: "작가 스토리 | Domo Lounge",
  description:
    "글로벌 신진작가들의 성장 스토리와 주요 마일스톤을 확인하세요 — Domo 글로벌 아티스트 인덱스",
  alternates: {
    canonical: buildCanonical(pathname),
    languages: buildAlternateLanguages(pathname),
  },
  openGraph: {
    title: "작가 스토리 | Domo Lounge",
    description:
      "글로벌 신진작가들의 성장 스토리와 주요 마일스톤을 확인하세요",
    locale: OG_LOCALE[DEFAULT_LOCALE],
    alternateLocale: buildOgLocaleAlternates(DEFAULT_LOCALE),
  },
  twitter: {
    card: "summary_large_image",
    title: "작가 스토리 | Domo Lounge",
    description:
      "글로벌 신진작가들의 성장 스토리와 주요 마일스톤을 확인하세요",
  },
};

export default function StoriesLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <>{children}</>;
}
