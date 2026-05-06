"use client";

/**
 * /explore/collections — AI 큐레이션 컬렉션 목록 (Editor's Pick)
 *
 * Phase 10 K-7: LLM이 매주 자동 생성한 주제별 컬렉션을 탐색한다.
 * README 비전 "스토리텔링 hub" 구현:
 *   - AI가 큐레이션한 Editor's Pick 컬렉션 카드 그리드
 *   - 5 locale 자동 매칭 (현재 locale 기준)
 *   - 페이지네이션
 */

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import Image from "next/image";
import { useI18n } from "@/i18n";
import { fetchCollections, type AiCollectionItem } from "@/lib/api";

const LIMIT = 10;

export default function CollectionsPage() {
  const { t, locale } = useI18n();
  const [collections, setCollections] = useState<AiCollectionItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (p: number) => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchCollections({ page: p, limit: LIMIT, locale });
      setCollections(data.items);
      setTotal(data.total);
      setPage(p);
    } catch (err) {
      setError(t("common.error"));
    } finally {
      setLoading(false);
    }
  }, [locale, t]);

  useEffect(() => {
    load(1);
  }, [load]);

  const totalPages = Math.ceil(total / LIMIT);

  return (
    <main className="max-w-5xl mx-auto px-4 py-8">
      {/* 페이지 헤더 */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
          {t("collections.editors_pick")}
        </h1>
        <p className="mt-2 text-gray-500 dark:text-gray-400">
          {t("collections.subtitle")}
        </p>
      </div>

      {/* 로딩 / 에러 */}
      {loading && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {Array.from({ length: 6 }).map((_, i) => (
            <div
              key={i}
              className="rounded-xl bg-gray-100 dark:bg-gray-800 animate-pulse h-64"
            />
          ))}
        </div>
      )}

      {error && (
        <div className="text-center py-12 text-gray-500">{error}</div>
      )}

      {/* 빈 상태 */}
      {!loading && !error && collections.length === 0 && (
        <div className="text-center py-20 text-gray-500">
          <p className="text-lg">{t("collections.no_collections")}</p>
        </div>
      )}

      {/* 컬렉션 카드 그리드 */}
      {!loading && collections.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {collections.map((c) => (
            <CollectionCard key={c.id} collection={c} t={t} locale={locale} />
          ))}
        </div>
      )}

      {/* 페이지네이션 */}
      {totalPages > 1 && (
        <div className="mt-10 flex items-center justify-center gap-3">
          <button
            onClick={() => load(page - 1)}
            disabled={page <= 1 || loading}
            className="px-4 py-2 rounded-lg border border-gray-300 text-sm disabled:opacity-40 hover:bg-gray-50 dark:hover:bg-gray-800"
          >
            {t("common.prev")}
          </button>
          <span className="text-sm text-gray-500">
            {page} / {totalPages}
          </span>
          <button
            onClick={() => load(page + 1)}
            disabled={page >= totalPages || loading}
            className="px-4 py-2 rounded-lg border border-gray-300 text-sm disabled:opacity-40 hover:bg-gray-50 dark:hover:bg-gray-800"
          >
            {t("common.next")}
          </button>
        </div>
      )}
    </main>
  );
}

function CollectionCard({
  collection: c,
  t,
  locale,
}: {
  collection: AiCollectionItem;
  t: (key: string, params?: Record<string, string | number>) => string;
  locale: string;
}) {
  // 날짜 포맷
  const weekLabel = c.week_start
    ? t("collections.week_label", { date: new Date(c.week_start).toLocaleDateString(locale, { month: "long", day: "numeric", year: "numeric" }) })
    : null;

  return (
    <Link
      href={`/explore/collections/${c.id}`}
      className="group block rounded-xl overflow-hidden border border-gray-200 dark:border-gray-700 hover:shadow-lg transition-shadow"
    >
      {/* 썸네일 */}
      <div className="relative aspect-[4/3] bg-gray-100 dark:bg-gray-800">
        {c.cover_image_url ? (
          <Image
            src={c.cover_image_url}
            alt={c.title || t("collections.editors_pick")}
            fill
            className="object-cover group-hover:scale-105 transition-transform duration-300"
            sizes="(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 33vw"
          />
        ) : (
          <div className="absolute inset-0 flex items-center justify-center">
            <span className="text-4xl text-gray-300">?</span>
          </div>
        )}
        {/* AI 큐레이션 배지 */}
        <div className="absolute top-3 left-3">
          <span className="text-xs px-2 py-1 rounded-full bg-black/60 text-white">
            {t("collections.generated_by_ai")}
          </span>
        </div>
      </div>

      {/* 카드 내용 */}
      <div className="p-4">
        <h2 className="font-semibold text-gray-900 dark:text-white line-clamp-2 text-base leading-tight mb-1">
          {c.title || t("collections.editors_pick")}
        </h2>
        {c.description && (
          <p className="text-sm text-gray-500 dark:text-gray-400 line-clamp-2 mb-3">
            {c.description}
          </p>
        )}
        <div className="flex items-center justify-between text-xs text-gray-400">
          <span>{t("collections.works_count", { count: c.post_count })}</span>
          {weekLabel && <span>{weekLabel}</span>}
        </div>
      </div>
    </Link>
  );
}
