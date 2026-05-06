/**
 * /explore/collections/[id] — AI 큐레이션 컬렉션 상세
 *
 * Phase 10 K-7: 컬렉션 헤더 + 작품 그리드 (position 순)
 * OG 메타 태그 (generateMetadata) for SEO + SNS 공유
 *
 * README 비전 "스토리텔링 hub":
 *   - 컬렉션 제목/설명 + 작품 그리드로 "발견 스토리" 노출
 *   - 공유 버튼 → Twitter/X, 링크 복사
 */

import type { Metadata } from "next";
import CollectionDetailClient from "./CollectionDetailClient";

interface Props {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ locale?: string }>;
}

async function fetchCollectionSSR(
  id: string,
  locale: string
): Promise<{
  id: string;
  title: string | null;
  description: string | null;
  cover_image_url: string | null;
  week_start: string | null;
  theme: string;
  published_at: string | null;
  posts: Array<{
    position: number;
    post_id: string;
    title: string | null;
    thumbnail_url: string | null;
    author: { id: string; name: string | null; avatar_url: string | null };
  }>;
} | null> {
  try {
    const apiBase =
      process.env.NEXT_PUBLIC_API_URL || "http://localhost:3710/v1";
    const res = await fetch(
      `${apiBase}/ai-collections/${encodeURIComponent(id)}?locale=${encodeURIComponent(locale)}`,
      { next: { revalidate: 300 } } // 5분 캐시
    );
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

export async function generateMetadata({ params, searchParams }: Props): Promise<Metadata> {
  const { id } = await params;
  const { locale = "ko" } = await searchParams;
  const collection = await fetchCollectionSSR(id, locale);

  if (!collection) {
    return { title: "Editor's Pick — Domo" };
  }

  return {
    title: `${collection.title || "Editor's Pick"} — Domo`,
    description: collection.description || undefined,
    openGraph: {
      title: collection.title || "Editor's Pick",
      description: collection.description || undefined,
      images: collection.cover_image_url
        ? [{ url: collection.cover_image_url }]
        : [],
      type: "article",
    },
    twitter: {
      card: "summary_large_image",
      title: collection.title || "Editor's Pick",
      description: collection.description || undefined,
      images: collection.cover_image_url ? [collection.cover_image_url] : [],
    },
  };
}

export default async function CollectionDetailPage({ params }: Props) {
  const { id } = await params;
  return <CollectionDetailClient collectionId={id} />;
}
