"use client";

/**
 * ArtistIndexPreview — A-4 Explore Revamp
 *
 * Horizontal-scroll strip of top-5 artists from A-6 artist-index.
 * On desktop renders as a grid row, on mobile as a scrollable row.
 * captureEvent: artist_index_preview_click { rank }
 */

import Link from "next/link";
import { useI18n } from "@/i18n";
import { type ArtistIndexEntry } from "@/lib/api";
import { TierBadge } from "@/components/artists/TierBadge";
import { captureEvent } from "@/lib/analytics/capture";

interface ArtistIndexPreviewProps {
  entries: ArtistIndexEntry[];
  loading: boolean;
}

export function ArtistIndexPreview({
  entries,
  loading,
}: ArtistIndexPreviewProps) {
  const { t } = useI18n();

  const preview = entries.slice(0, 5);

  return (
    <section className="mb-6" aria-label={t("explore.rankingPreview.ariaLabel")}>
      {/* Section header */}
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-semibold text-text-primary flex items-center gap-1.5">
          <span>🌍</span>
          <span>{t("explore.rankingPreview.title")}</span>
        </h2>
        <Link
          href="/artists/index"
          className="text-xs text-primary hover:underline font-medium"
        >
          {t("explore.rankingPreview.viewAll")}
        </Link>
      </div>

      {/* Cards */}
      {loading ? (
        <div className="flex gap-3 overflow-x-auto pb-2 scrollbar-hide">
          {[0, 1, 2, 3, 4].map((i) => (
            <div
              key={i}
              className="card p-3 flex-shrink-0 w-28 animate-pulse"
            >
              <div className="w-12 h-12 rounded-full bg-surface-hover mx-auto mb-2" />
              <div className="h-3 w-16 bg-surface-hover rounded mx-auto mb-1" />
              <div className="h-2 w-10 bg-surface-hover rounded mx-auto" />
            </div>
          ))}
        </div>
      ) : preview.length === 0 ? null : (
        <div className="flex gap-3 overflow-x-auto pb-2 scrollbar-hide">
          {preview.map((artist) => (
            <Link
              key={artist.user_id}
              href={`/users/${artist.user_id}`}
              onClick={() =>
                captureEvent({
                  type: "artist_index_preview_click",
                  rank: artist.rank,
                })
              }
              className="card p-3 flex-shrink-0 w-28 flex flex-col items-center text-center hover:bg-surface-hover transition-colors"
              aria-label={`${artist.username} #${artist.rank}`}
            >
              {/* Rank badge */}
              <div className="text-xs font-bold text-text-muted mb-1">
                #{artist.rank}
              </div>

              {/* Avatar */}
              <div className="w-12 h-12 rounded-full bg-surface-hover overflow-hidden mb-2">
                {artist.avatar_url ? (
                  <img
                    src={artist.avatar_url}
                    alt={artist.username}
                    className="w-full h-full object-cover"
                  />
                ) : (
                  <div className="w-full h-full flex items-center justify-center text-lg">
                    👤
                  </div>
                )}
              </div>

              {/* Username */}
              <span className="text-xs font-semibold text-text-primary truncate w-full">
                @{artist.username}
              </span>

              {/* Tier badge */}
              {artist.tier_badge && (
                <div className="mt-1">
                  <TierBadge tier={artist.tier_badge} />
                </div>
              )}
            </Link>
          ))}
        </div>
      )}
    </section>
  );
}
