"use client";

/**
 * MediaCoverageList — C-4 media-coverage-cms
 *
 * Admin table list for media coverage entries.
 * Supports: publish/draft toggle, delete, edit (via onEdit callback).
 */

import { useI18n } from "@/i18n";
import type { MediaCoverageOut } from "@/lib/api";

const TYPE_BADGE_COLORS: Record<string, string> = {
  article: "bg-slate-100 text-slate-700",
  youtube: "bg-red-100 text-red-700",
  radio: "bg-purple-100 text-purple-700",
  podcast: "bg-orange-100 text-orange-700",
  tv: "bg-blue-100 text-blue-700",
};

type Props = {
  entries: MediaCoverageOut[];
  loading: boolean;
  hasMore: boolean;
  onEdit: (entry: MediaCoverageOut) => void;
  onTogglePublish: (id: string, current: boolean) => Promise<boolean>;
  onDelete: (id: string) => Promise<boolean>;
  onLoadMore: () => void;
};

export function MediaCoverageList({
  entries,
  loading,
  hasMore,
  onEdit,
  onTogglePublish,
  onDelete,
  onLoadMore,
}: Props) {
  const { t } = useI18n();

  if (loading && entries.length === 0) {
    return (
      <div className="text-center text-text-muted py-12">{t("common.loading")}</div>
    );
  }

  if (entries.length === 0) {
    return (
      <div className="card p-6 text-center text-text-muted text-sm">
        {t("mediaCoverage.emptyList")}
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {entries.map((entry) => (
        <div
          key={entry.id}
          className="card p-4 flex items-start gap-4"
        >
          {/* Thumbnail */}
          {entry.thumbnail_url ? (
            <img
              src={entry.thumbnail_url}
              alt={entry.title}
              className="w-16 h-12 rounded object-cover flex-shrink-0"
            />
          ) : (
            <div className="w-16 h-12 rounded bg-surface-hover flex-shrink-0 flex items-center justify-center text-xl">
              {entry.coverage_type === "youtube" ? "▶" : entry.coverage_type === "radio" ? "📻" : "📰"}
            </div>
          )}

          {/* Info */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap mb-1">
              <span
                className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                  TYPE_BADGE_COLORS[entry.coverage_type] ?? "bg-gray-100 text-gray-700"
                }`}
              >
                {t(`mediaCoverage.types.${entry.coverage_type}`)}
              </span>
              <span className="text-xs text-text-muted">{entry.locale.toUpperCase()}</span>
              <span
                className={`text-xs px-2 py-0.5 rounded-full ${
                  entry.is_published
                    ? "bg-success/10 text-success"
                    : "bg-warning/10 text-warning"
                }`}
              >
                {entry.is_published
                  ? t("mediaCoverage.publishedLabel")
                  : t("mediaCoverage.draftLabel")}
              </span>
              {entry.is_featured && (
                <span className="text-xs px-2 py-0.5 rounded-full bg-primary/10 text-primary">
                  {t("mediaCoverage.featuredLabel")}
                </span>
              )}
            </div>

            <p className="text-sm font-semibold text-text-primary line-clamp-1">
              {entry.title}
            </p>
            <p className="text-xs text-text-muted mt-0.5">
              {entry.source_name} · {entry.published_at}
            </p>
          </div>

          {/* Actions */}
          <div className="flex items-center gap-2 flex-shrink-0">
            <a
              href={entry.external_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs text-primary hover:underline"
            >
              링크
            </a>
            <button
              type="button"
              className="btn-secondary text-xs px-2 py-1"
              onClick={() => onEdit(entry)}
            >
              {t("common.edit")}
            </button>
            <button
              type="button"
              className="btn-secondary text-xs px-2 py-1"
              onClick={() => void onTogglePublish(entry.id, entry.is_published)}
            >
              {entry.is_published ? t("mediaCoverage.draftLabel") : t("mediaCoverage.publishedLabel")}
            </button>
            <button
              type="button"
              className="btn-danger text-xs px-2 py-1"
              onClick={() => {
                if (window.confirm(t("mediaCoverage.deleteConfirm"))) {
                  void onDelete(entry.id);
                }
              }}
            >
              {t("common.delete")}
            </button>
          </div>
        </div>
      ))}

      {hasMore && (
        <div className="text-center pt-2">
          <button
            type="button"
            className="btn-secondary text-sm"
            onClick={onLoadMore}
            disabled={loading}
          >
            {loading ? t("common.loading") : t("mediaCoverage.loadMore")}
          </button>
        </div>
      )}
    </div>
  );
}
