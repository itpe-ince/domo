"use client";

import Link from "next/link";
import { ArtistIndexEntry } from "@/lib/api";
import { TierBadge } from "./TierBadge";
import { useI18n } from "@/i18n";

interface RankingCardProps {
  artist: ArtistIndexEntry;
  /** When filtering by region, show region rank badge instead of global rank */
  activeRegion?: string;
  /** When filtering by genre, show genre rank badge instead of global rank */
  activeGenre?: string;
}

export function RankingCard({ artist }: RankingCardProps) {
  const { t } = useI18n();

  return (
    <div className="flex items-center gap-4 py-3 px-4 rounded-xl hover:bg-surface-hover transition-colors">
      {/* Rank number */}
      <div className="w-8 text-center font-bold text-text-muted text-sm flex-shrink-0">
        #{artist.rank}
      </div>

      {/* Avatar */}
      <div className="w-10 h-10 rounded-full bg-surface-hover flex items-center justify-center text-lg overflow-hidden flex-shrink-0">
        {artist.avatar_url ? (
          <img
            src={artist.avatar_url}
            alt={artist.username}
            className="w-full h-full object-cover rounded-full"
          />
        ) : (
          "👤"
        )}
      </div>

      {/* Name + meta */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="font-semibold text-text-primary text-sm">
            @{artist.username}
          </span>
          {artist.tier_badge && <TierBadge tier={artist.tier_badge} />}
        </div>
        <div className="flex items-center gap-2 mt-0.5 text-xs text-text-muted">
          {artist.country && <span>{artist.country}</span>}
          {artist.primary_genre && (
            <>
              {artist.country && <span>·</span>}
              <span className="italic">{artist.primary_genre}</span>
            </>
          )}
        </div>
        {/* G'-8: multi-rank badges — show when relevant sub-ranks exist */}
        <div className="flex items-center gap-1.5 mt-1 flex-wrap">
          {/* Global rank badge */}
          <span className="text-[10px] px-1.5 py-0.5 rounded bg-surface-hover text-text-muted">
            {t("artist.index.badge.globalRank", { rank: String(artist.rank) })}
          </span>
          {/* Region rank badge — show when artist has a region rank */}
          {artist.rank_region != null && (
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-blue-50 dark:bg-blue-950 text-blue-600 dark:text-blue-400">
              {t("artist.index.badge.regionRank", { rank: String(artist.rank_region) })}
            </span>
          )}
          {/* Genre rank badge — show when artist has a genre rank */}
          {artist.rank_genre != null && (
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-purple-50 dark:bg-purple-950 text-purple-600 dark:text-purple-400">
              {t("artist.index.badge.genreRank", { rank: String(artist.rank_genre) })}
            </span>
          )}
        </div>
      </div>

      {/* Score progress bar (compact) */}
      <div className="hidden sm:flex flex-col items-end gap-1 w-24 flex-shrink-0">
        <span className="text-xs font-medium text-text-muted">
          {artist.score.toFixed(1)}
        </span>
        <div className="h-1 w-full rounded-full bg-surface-hover overflow-hidden">
          <div
            className="h-full bg-primary rounded-full"
            style={{ width: `${Math.min(100, artist.score)}%` }}
          />
        </div>
      </div>

      {/* View link */}
      <Link
        href={`/users/${artist.user_id}`}
        className="flex-shrink-0 text-xs text-primary hover:underline font-medium"
        aria-label={`${artist.username} ${t("artist.index.viewProfile")}`}
      >
        {t("artist.index.viewProfile")}
      </Link>
    </div>
  );
}
