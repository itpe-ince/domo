/**
 * /me/sponsorships/[id]/layout.tsx — G'-6 Metadata wrapper + H'-3 Multi-language SEO
 *
 * Server component: exports generateMetadata for the sponsor success/share page.
 * The opengraph-image.tsx in this segment is auto-inferred by Next.js.
 *
 * Privacy note: this layout returns a generic title/description to avoid leaking
 * sponsorship details — the OG image route itself applies privacy guards.
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

interface SponsorshipMeta {
  artist_id?: string;
  bluebird_count?: number;
  is_anonymous?: boolean;
}

interface ArtistMeta {
  display_name?: string;
}

async function fetchSponsorshipMeta(id: string): Promise<SponsorshipMeta | null> {
  try {
    const res = await fetch(`${API_BASE}/sponsorships/${id}`, {
      next: { revalidate: 300 },
    });
    if (!res.ok) return null;
    const json = await res.json() as { data?: SponsorshipMeta };
    return json.data ?? null;
  } catch {
    return null;
  }
}

async function fetchArtistMeta(artistId: string): Promise<ArtistMeta | null> {
  try {
    const res = await fetch(`${API_BASE}/users/${artistId}`, {
      next: { revalidate: 300 },
    });
    if (!res.ok) return null;
    const json = await res.json() as { data?: ArtistMeta };
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
  const sponsorship = await fetchSponsorshipMeta(id);

  let title = "Blue Bird 후원 | Domo Lounge";
  let description = "Domo Lounge — 글로벌 신진작가 후원 플랫폼";

  // Only enrich if non-anonymous + sponsorship data available
  if (sponsorship && !sponsorship.is_anonymous && sponsorship.artist_id) {
    const artist = await fetchArtistMeta(sponsorship.artist_id);
    const artistName = artist?.display_name;
    const count = sponsorship.bluebird_count ?? 0;
    if (artistName) {
      title = `@${artistName}에게 🕊 ${count} Blue Bird 후원 | Domo Lounge`;
      description = `Domo에서 @${artistName}을(를) 후원했습니다. 글로벌 신진작가를 함께 응원해보세요.`;
    }
  }

  const pathname = `/me/sponsorships/${id}`;
  const ogLocale = OG_LOCALE[DEFAULT_LOCALE];
  const ogLocaleAlternates = buildOgLocaleAlternates(DEFAULT_LOCALE);

  return {
    title,
    description,
    // Sponsorship share pages: no canonical (user-specific, auth-gated)
    alternates: {
      canonical: buildCanonical(pathname),
      languages: buildAlternateLanguages(pathname),
    },
    openGraph: {
      title,
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

export default function SponsorshipShareLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <>{children}</>;
}
