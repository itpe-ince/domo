"use client";

/**
 * FeaturedArtistsList — G'-7 admin-featured-artists
 *
 * Renders the 12-month history grid of featured artist entries.
 * Each row shows month, artist_id, curation_note, active status,
 * and a deactivate button for active entries.
 */

import { useI18n } from "@/i18n";
import type { FeaturedArtistOut } from "@/lib/api";

type Props = {
  entries: FeaturedArtistOut[];
  onDeactivate: (id: string) => void;
};

function formatMonth(dateStr: string): string {
  // dateStr is "YYYY-MM-DD"
  const parts = dateStr.split("-");
  if (parts.length >= 2) return `${parts[0]}-${parts[1]}`;
  return dateStr;
}

export function FeaturedArtistsList({ entries, onDeactivate }: Props) {
  const { t } = useI18n();

  if (entries.length === 0) {
    return (
      <div className="text-center py-8 text-text-muted text-sm">
        {t("admin.featuredArtists.list.empty")}
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border text-left text-text-muted text-xs uppercase tracking-wide">
            <th className="py-2 pr-4">{t("admin.featuredArtists.list.monthCol")}</th>
            <th className="py-2 pr-4">{t("admin.featuredArtists.list.artistCol")}</th>
            <th className="py-2 pr-4">{t("admin.featuredArtists.list.noteCol")}</th>
            <th className="py-2 pr-4">{t("admin.featuredArtists.list.statusCol")}</th>
            <th className="py-2">{t("admin.featuredArtists.list.actionsCol")}</th>
          </tr>
        </thead>
        <tbody>
          {entries.map((entry) => (
            <tr key={entry.id} className="border-b border-border last:border-0">
              <td className="py-3 pr-4 font-mono text-text-primary whitespace-nowrap">
                {formatMonth(entry.month)}
              </td>
              <td className="py-3 pr-4 text-text-secondary font-mono text-xs truncate max-w-[160px]">
                {entry.artist_id}
              </td>
              <td className="py-3 pr-4 text-text-muted max-w-[200px] truncate">
                {entry.curation_note ?? (
                  <span className="italic opacity-50">
                    {t("admin.featuredArtists.list.noNote")}
                  </span>
                )}
              </td>
              <td className="py-3 pr-4">
                {entry.is_active ? (
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-success/10 text-success">
                    {t("admin.featuredArtists.list.active")}
                  </span>
                ) : (
                  <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-surface-hover text-text-muted">
                    {t("admin.featuredArtists.list.inactive")}
                  </span>
                )}
              </td>
              <td className="py-3">
                {entry.is_active && (
                  <button
                    type="button"
                    className="text-xs text-danger hover:underline"
                    onClick={() => onDeactivate(entry.id)}
                  >
                    {t("admin.featuredArtists.list.deactivateBtn")}
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
