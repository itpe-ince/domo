/**
 * /posts/[id]/layout.tsx — G'-6 Metadata wrapper + H'-3 Multi-language SEO
 *
 * Server component: exports generateMetadata for post detail pages.
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

interface PostMeta {
  title?: string | null;
  content?: string | null;
  tags?: string[] | null;
  author?: { display_name?: string };
}

async function fetchPostMeta(id: string): Promise<PostMeta | null> {
  try {
    const res = await fetch(`${API_BASE}/posts/${id}`, {
      next: { revalidate: 300 },
    });
    if (!res.ok) return null;
    const json = await res.json() as { data?: PostMeta };
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
  const post = await fetchPostMeta(id);

  const title = post?.title ?? "작품";
  const authorName = post?.author?.display_name ?? "작가";
  const content = post?.content ?? "";
  const tags = post?.tags?.slice(0, 5) ?? [];
  const tagText = tags.length > 0 ? ` · #${tags.join(" #")}` : "";

  const pageTitle = `${title} — @${authorName} | Domo Lounge`;
  const description =
    content.length > 0
      ? content.slice(0, 150) + tagText
      : `@${authorName}의 작품${tagText} — Domo 글로벌 신진작가 플랫폼`;

  const pathname = `/posts/${id}`;
  const ogLocale = OG_LOCALE[DEFAULT_LOCALE];
  const ogLocaleAlternates = buildOgLocaleAlternates(DEFAULT_LOCALE);

  return {
    title: pageTitle,
    description,
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
      title: pageTitle,
      description,
      // images: auto-inferred from opengraph-image.tsx in this segment
    },
  };
}

export default function PostLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <>{children}</>;
}
