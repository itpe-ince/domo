"use client";

/**
 * FeaturedArtistHero — A-7 Storytelling Hub
 *
 * Hero card for the monthly featured artist section.
 * Displays the top-ranked artist from artist_index (rank 1)
 * with their recent works gallery, tier badge, and profile link.
 *
 * Featured artist is: artist_index rank 1 (no separate system_settings
 * endpoint needed for MVP — A-7 OQ-6 = C approach).
 */

import Link from "next/link";
import { useI18n } from "@/i18n";
import { ArtistFeaturedView } from "@/lib/api";
import { TierBadge } from "@/components/artists/TierBadge";
import { captureEvent } from "@/lib/analytics/capture";

interface FeaturedArtistHeroProps {
  artist: ArtistFeaturedView;
  loading?: boolean;
}

function FeaturedArtistSkeleton() {
  return (
    <div className="card overflow-hidden animate-pulse">
      <div className="h-40 bg-surface-hover" />
      <div className="p-6 space-y-3">
        <div className="h-6 w-1/3 bg-surface-hover rounded" />
        <div className="h-4 w-2/3 bg-surface-hover rounded" />
        <div className="h-4 w-1/2 bg-surface-hover rounded" />
      </div>
    </div>
  );
}

export function FeaturedArtistHero({ artist, loading = false }: FeaturedArtistHeroProps) {
  const { t } = useI18n();

  if (loading) return <FeaturedArtistSkeleton />;

  function handleClick() {
    captureEvent({
      type: "featured_artist_click",
      artist_id: artist.user_id,
    } as Parameters<typeof captureEvent>[0]);
  }

  return (
    <div className="card overflow-hidden">
      {/* Hero gradient banner */}
      <div className="relative h-36 bg-gradient-to-br from-primary/20 via-primary/5 to-transparent flex items-center justify-center">
        {artist.avatar_url ? (
          <img
            src={artist.avatar_url}
            alt={artist.username}
            className="w-24 h-24 rounded-full object-cover ring-4 ring-background shadow-lg"
          />
        ) : (
          <div className="w-24 h-24 rounded-full bg-surface-hover ring-4 ring-background flex items-center justify-center text-4xl">
            🎨
          </div>
        )}
        {/* Month label overlay */}
        <span className="absolute top-3 left-4 text-xs font-semibold text-primary bg-background/80 px-2 py-1 rounded-full">
          {t("stories.featured.monthLabel")}
        </span>
        {/* Curated badge — shown when admin has handpicked this artist */}
        {artist.is_curated && (
          <span className="absolute top-3 right-4 text-xs font-semibold text-text-muted bg-background/80 px-2 py-1 rounded-full">
            {t("stories.featured.curatedBadge")}
          </span>
        )}
      </div>

      <div className="p-5">
        {/* Artist name + badges */}
        <div className="flex items-center gap-2 flex-wrap mb-1">
          <h2 className="text-xl font-bold text-text-primary">
            @{artist.username}
          </h2>
          <TierBadge tier={artist.tier_badge} />
        </div>

        {/* Country + genre */}
        <p className="text-sm text-text-muted">
          {[
            artist.country ? `📍 ${artist.country}` : null,
            artist.primary_genre ? `🎭 ${artist.primary_genre}` : null,
          ]
            .filter(Boolean)
            .join("  ")}
        </p>

        {/* Global rank */}
        {artist.rank != null && (
          <p className="mt-2 text-sm text-text-secondary">
            {t("artist.index.badge.globalRank", { rank: String(artist.rank) })}
            {artist.score != null && (
              <>
                {" · "}
                <span className="text-text-muted">
                  {t("stories.featured.scoreLabel", {
                    score: String(Math.round(artist.score)),
                  })}
                </span>
              </>
            )}
          </p>
        )}

        {/* Curation note — shown when admin has provided one */}
        {artist.curation_note && (
          <blockquote className="mt-3 pl-3 border-l-2 border-primary/40 text-sm text-text-secondary italic">
            {artist.curation_note}
          </blockquote>
        )}

        {/* CTA */}
        <div className="mt-4 flex gap-3">
          <Link
            href={`/users/${artist.user_id}`}
            onClick={handleClick}
            className="btn-primary text-sm px-4 py-2"
          >
            {t("stories.featured.viewProfile")}
          </Link>
          <Link
            href={`/users/${artist.user_id}/timeline`}
            className="btn-secondary text-sm px-4 py-2"
          >
            {t("stories.featured.viewTimeline")}
          </Link>
        </div>
      </div>
    </div>
  );
}
