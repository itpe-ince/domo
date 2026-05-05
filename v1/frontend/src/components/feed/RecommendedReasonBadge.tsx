"use client";

/**
 * RecommendedReasonBadge — A-3 feed-algorithm-v1
 *
 * Small inline badge displayed on PostCard when the API provides a
 * recommendation_reason ("following" | "trending" | "similar_genre").
 *
 * Renders nothing when reason is null/undefined.
 */

import { useI18n } from "@/i18n";

type Props = {
  reason?: "following" | "trending" | "similar_genre" | string | null;
};

const BADGE_STYLES: Record<string, string> = {
  following: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300",
  trending:  "bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300",
  similar_genre: "bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300",
};

export function RecommendedReasonBadge({ reason }: Props) {
  const { t } = useI18n();

  if (!reason) return null;

  const style = BADGE_STYLES[reason] ?? "bg-gray-100 text-gray-600";

  const label: string = (() => {
    switch (reason) {
      case "following":    return t("feed.reasonFollowing");
      case "trending":     return t("feed.reasonTrending");
      case "similar_genre": return t("feed.reasonSimilarGenre");
      default:             return reason;
    }
  })();

  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium ${style}`}
      aria-label={t("feed.reasonLabel", { reason: label })}
    >
      {reason === "following" && (
        <svg className="w-2.5 h-2.5" fill="currentColor" viewBox="0 0 20 20" aria-hidden="true">
          <path d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z" />
        </svg>
      )}
      {reason === "trending" && (
        <svg className="w-2.5 h-2.5" fill="currentColor" viewBox="0 0 20 20" aria-hidden="true">
          <path fillRule="evenodd" d="M12 7a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0V8.414l-4.293 4.293a1 1 0 01-1.414 0L8 10.414l-4.293 4.293a1 1 0 01-1.414-1.414l5-5a1 1 0 011.414 0L11 10.586 14.586 7H12z" clipRule="evenodd" />
        </svg>
      )}
      {label}
    </span>
  );
}
