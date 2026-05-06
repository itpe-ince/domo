"use client";

/**
 * CollectionDetailClient — AI 큐레이션 컬렉션 상세 (클라이언트 컴포넌트)
 *
 * 컬렉션 헤더 + 작품 그리드 (position 순) + 공유 버튼
 */

import { useEffect, useState } from "react";
import Link from "next/link";
import Image from "next/image";
import { useI18n } from "@/i18n";
import { fetchCollectionDetail, type AiCollectionDetail } from "@/lib/api";

interface Props {
  collectionId: string;
}

export default function CollectionDetailClient({ collectionId }: Props) {
  const { t, locale } = useI18n();
  const [collection, setCollection] = useState<AiCollectionDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [linkCopied, setLinkCopied] = useState(false);

  useEffect(() => {
    setLoading(true);
    setError(false);
    fetchCollectionDetail(collectionId, locale)
      .then(setCollection)
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  }, [collectionId, locale]);

  const handleShare = async () => {
    const url = typeof window !== "undefined" ? window.location.href : "";
    try {
      await navigator.clipboard.writeText(url);
      setLinkCopied(true);
      setTimeout(() => setLinkCopied(false), 2000);
    } catch {
      // clipboard 접근 불가 시 무시
    }
  };

  const handleShareTwitter = () => {
    if (!collection) return;
    const text = encodeURIComponent(collection.title || "Editor's Pick");
    const url = encodeURIComponent(
      typeof window !== "undefined" ? window.location.href : ""
    );
    window.open(
      `https://twitter.com/intent/tweet?text=${text}&url=${url}`,
      "_blank"
    );
  };

  if (loading) {
    return (
      <main className="max-w-4xl mx-auto px-4 py-8 animate-pulse">
        <div className="h-8 bg-gray-200 dark:bg-gray-700 rounded w-1/2 mb-4" />
        <div className="aspect-video bg-gray-200 dark:bg-gray-700 rounded-xl mb-6" />
        <div className="grid grid-cols-3 gap-4">
          {Array.from({ length: 9 }).map((_, i) => (
            <div key={i} className="aspect-square bg-gray-200 dark:bg-gray-700 rounded-lg" />
          ))}
        </div>
      </main>
    );
  }

  if (error || !collection) {
    return (
      <main className="max-w-4xl mx-auto px-4 py-8 text-center">
        <p className="text-gray-500">{t("common.error")}</p>
        <Link
          href="/explore/collections"
          className="mt-4 inline-block text-blue-600 hover:underline"
        >
          {t("collections.back")}
        </Link>
      </main>
    );
  }

  const weekLabel = collection.week_start
    ? t("collections.week_label", {
        date: new Date(collection.week_start).toLocaleDateString(locale, {
          month: "long",
          day: "numeric",
          year: "numeric",
        }),
      })
    : null;

  return (
    <main className="max-w-4xl mx-auto px-4 py-8">
      {/* 뒤로가기 */}
      <Link
        href="/explore/collections"
        className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-900 dark:hover:text-white mb-6"
      >
        ← {t("collections.back")}
      </Link>

      {/* 컬렉션 헤더 */}
      <div className="mb-8">
        {/* 대표 이미지 */}
        {collection.cover_image_url && (
          <div className="relative w-full aspect-video rounded-xl overflow-hidden mb-6">
            <Image
              src={collection.cover_image_url}
              alt={collection.title || "Collection cover"}
              fill
              className="object-cover"
              priority
              sizes="(max-width: 896px) 100vw, 896px"
            />
          </div>
        )}

        {/* AI 큐레이션 배지 + 날짜 */}
        <div className="flex items-center gap-3 mb-3">
          <span className="text-xs px-2 py-1 rounded-full bg-gray-100 dark:bg-gray-800 text-gray-500">
            {t("collections.generated_by_ai")}
          </span>
          {weekLabel && (
            <span className="text-xs text-gray-400">{weekLabel}</span>
          )}
        </div>

        {/* 제목 */}
        <h1 className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-white mb-3">
          {collection.title || t("collections.editors_pick")}
        </h1>

        {/* 설명 */}
        {collection.description && (
          <p className="text-gray-600 dark:text-gray-300 leading-relaxed mb-4">
            {collection.description}
          </p>
        )}

        {/* 공유 버튼 */}
        <div className="flex items-center gap-3">
          <button
            onClick={handleShareTwitter}
            className="flex items-center gap-2 px-4 py-2 rounded-lg border border-gray-300 text-sm hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
          >
            <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
              <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-4.714-6.231-5.401 6.231H2.744l7.73-8.835L1.254 2.25H8.08l4.26 5.632zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
            </svg>
            X
          </button>
          <button
            onClick={handleShare}
            className="flex items-center gap-2 px-4 py-2 rounded-lg border border-gray-300 text-sm hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
          >
            {linkCopied
              ? t("collections.share_link_copied")
              : t("collections.share")}
          </button>
        </div>
      </div>

      {/* 작품 그리드 (position 순) */}
      <div>
        <p className="text-sm text-gray-500 mb-4">
          {t("collections.works_count", { count: collection.posts.length })}
        </p>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
          {collection.posts.map((post) => (
            <Link
              key={post.post_id}
              href={`/posts/${post.post_id}`}
              className="group block rounded-lg overflow-hidden border border-gray-200 dark:border-gray-700 hover:shadow-md transition-shadow"
            >
              {/* 작품 썸네일 */}
              <div className="relative aspect-square bg-gray-100 dark:bg-gray-800">
                {post.thumbnail_url ? (
                  <Image
                    src={post.thumbnail_url}
                    alt={post.title || "Artwork"}
                    fill
                    className="object-cover group-hover:scale-105 transition-transform duration-200"
                    sizes="(max-width: 640px) 50vw, (max-width: 896px) 33vw, 280px"
                  />
                ) : (
                  <div className="absolute inset-0 flex items-center justify-center text-gray-300">
                    <span className="text-3xl">?</span>
                  </div>
                )}
                {/* position 배지 */}
                <span className="absolute top-2 right-2 w-6 h-6 rounded-full bg-black/60 text-white text-xs flex items-center justify-center">
                  {post.position}
                </span>
              </div>
              {/* 작품 정보 */}
              <div className="p-2">
                <p className="text-sm font-medium text-gray-900 dark:text-white line-clamp-1">
                  {post.title || "Untitled"}
                </p>
                <p className="text-xs text-gray-400 line-clamp-1">
                  {post.author.name || "Unknown"}
                </p>
              </div>
            </Link>
          ))}
        </div>
      </div>
    </main>
  );
}
