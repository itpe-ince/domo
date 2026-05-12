"use client";

/**
 * SeriesCard — publish-controls PDCA #8, Task 4.1.
 *
 * Display card for a Series. Links to /series/[id].
 * OQ-4=C: cover_url manual + first-post thumbnail fallback.
 */

import Link from "next/link";
import type { Series } from "@/lib/api";
import { useI18n } from "@/i18n";

export interface SeriesCardProps {
  series: Series;
  /** First-post thumbnail fallback when cover_url is null (OQ-4=C). */
  firstPostThumbnailUrl?: string | null;
}

export function SeriesCard({ series, firstPostThumbnailUrl }: SeriesCardProps) {
  const { t } = useI18n();
  const cover = series.cover_url ?? firstPostThumbnailUrl ?? null;

  return (
    <Link
      href={`/series/${series.id}`}
      className="block rounded-lg overflow-hidden border border-border bg-surface hover:bg-surface-hover transition-colors"
    >
      {/* Cover area — aspect-square, fallback to initial letter */}
      <div className="relative aspect-square bg-surface-hover overflow-hidden">
        {cover ? (
          <img src={cover} alt="" className="w-full h-full object-cover" />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-4xl text-text-muted font-bold">
            {series.title.charAt(0).toUpperCase()}
          </div>
        )}
      </div>
      {/* Title + post count */}
      <div className="p-3">
        <h3 className="text-sm font-semibold truncate">{series.title}</h3>
        <p className="text-xs text-text-muted">
          {t("post.series.postCount", { count: String(series.post_count ?? 0) })}
        </p>
      </div>
    </Link>
  );
}
