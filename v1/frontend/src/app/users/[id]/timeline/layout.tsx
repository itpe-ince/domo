/**
 * /users/[id]/timeline/layout.tsx — G'-6 Metadata wrapper + H'-3 Multi-language SEO
 *
 * Server component: exports generateMetadata for the artist timeline page.
 * The opengraph-image.tsx in this segment is auto-inferred by Next.js.
 *
 * H'-3 additions:
 *  - og:locale (ko_KR) + og:locale:alternate (en_US, ja_JP, zh_CN, es_ES)
 *  - hreflang alternates via metadata.alternates.languages
 *  - canonical URL
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

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:3710/v1";

interface UserMeta {
  display_name?: string;
  country_code?: string | null;
}

interface RankingMeta {
  rank?: number;
  tier_badge?: string | null;
}

async function fetchUserMeta(id: string): Promise<UserMeta | null> {
  try {
    const res = await fetch(`${API_BASE}/users/${id}`, {
      next: { revalidate: 300 },
    });
    if (!res.ok) return null;
    const json = await res.json() as { data?: UserMeta };
    return json.data ?? null;
  } catch {
    return null;
  }
}

async function fetchRankingMeta(id: string): Promise<RankingMeta | null> {
  try {
    const res = await fetch(`${API_BASE}/artists/${encodeURIComponent(id)}/index`, {
      next: { revalidate: 300 },
    });
    if (!res.ok) return null;
    const json = await res.json() as { data?: RankingMeta };
    return json.data ?? null;
  } catch {
    return null;
  }
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ id: string }>;
}): Promise<Metadata> {
  const { id } = await params;
  const [user, ranking] = await Promise.all([
    fetchUserMeta(id),
    fetchRankingMeta(id),
  ]);

  const name = user?.display_name ?? "작가";
  const country = user?.country_code ? ` · ${user.country_code}` : "";
  const rankText =
    ranking?.rank != null ? ` · 글로벌 #${ranking.rank}` : "";

  const title = `${name}의 작가 히스토리 | Domo Lounge`;
  const description = `${name}${country}${rankText} — 성장 스토리와 주요 마일스톤을 확인하세요.`;

  const pathname = `/users/${id}/timeline`;
  const ogLocale = OG_LOCALE[DEFAULT_LOCALE];
  const ogLocaleAlternates = buildOgLocaleAlternates(DEFAULT_LOCALE);

  return {
    title,
    description,
    alternates: {
      canonical: buildCanonical(pathname),
      languages: buildAlternateLanguages(pathname),
    },
    openGraph: {
      title: `${name}의 작가 히스토리`,
      description,
      locale: ogLocale,
      alternateLocale: ogLocaleAlternates,
      // images: auto-inferred from opengraph-image.tsx in this segment
    },
    twitter: {
      card: "summary_large_image",
      title,
      description,
      // images: auto-inferred from opengraph-image.tsx in this segment
    },
  };
}

export default function TimelineLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <>{children}</>;
}
