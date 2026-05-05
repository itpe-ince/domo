"use client";

/**
 * ExploreHeroCard — A-4 Explore Revamp
 *
 * "오늘의 작가" hero card.
 * - Picks one artist from A-6 top-3 (random on mount, seeded by date)
 * - Shows avatar + username + tier_badge + recent works thumbnails (up to 3)
 * - captureEvent: explore_hero_view { artist_id }
 */

import { useEffect, useMemo } from "react";
import Link from "next/link";
import { useI18n } from "@/i18n";
import { type ArtistIndexEntry } from "@/lib/api";
import { TierBadge } from "@/components/artists/TierBadge";
import { captureEvent } from "@/lib/analytics/capture";

interface ExploreHeroCardProps {
  /** Top 3 artists from A-6 artist-index endpoint */
  top3: ArtistIndexEntry[];
  loading: boolean;
}

function getDailyIndex(max: number): number {
  if (max === 0) return 0;
  const today = new Date();
  const seed =
    today.getFullYear() * 10000 +
    (today.getMonth() + 1) * 100 +
    today.getDate();
  return seed % max;
}

export function ExploreHeroCard({ top3, loading }: ExploreHeroCardProps) {
  const { t } = useI18n();

  // Daily rotation: deterministic pick from top-3
  const artist = useMemo<ArtistIndexEntry | null>(() => {
    if (top3.length === 0) return null;
    return top3[getDailyIndex(top3.length)];
  }, [top3]);

  useEffect(() => {
    if (artist) {
      captureEvent({ type: "explore_hero_view", artist_id: artist.user_id });
    }
  }, [artist]);

  if (loading) {
    return (
      <section
        aria-label={t("explore.hero.ariaLabel")}
        className="card p-5 mb-6 animate-pulse"
      >
        <div className="flex items-center gap-4">
          <div className="w-16 h-16 rounded-full bg-surface-hover flex-shrink-0" />
          <div className="flex-1 space-y-2">
            <div className="h-3 w-24 bg-surface-hover rounded" />
            <div className="h-4 w-36 bg-surface-hover rounded" />
          </div>
        </div>
        <div className="flex gap-2 mt-4">
          {[0, 1, 2].map((i) => (
            <div key={i} className="w-20 h-20 rounded-lg bg-surface-hover" />
          ))}
        </div>
      </section>
    );
  }

  if (!artist) return null;

  return (
    <section
      aria-label={t("explore.hero.ariaLabel")}
      className="card p-5 mb-6 border border-primary/20 bg-gradient-to-br from-surface to-surface/60"
    >
      {/* Header: badge + profile link */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-1.5">
          <span className="text-base">🌟</span>
          <span className="text-xs font-semibold text-primary uppercase tracking-wide">
            {t("explore.hero.badge")}
          </span>
        </div>
        <span className="text-xs text-text-muted">#{artist.rank}</span>
      </div>

      {/* Artist info */}
      <div className="flex items-center gap-4">
        <Link href={`/users/${artist.user_id}`} className="flex-shrink-0">
          <div className="w-16 h-16 rounded-full bg-surface-hover overflow-hidden border-2 border-primary/30">
            {artist.avatar_url ? (
              <img
                src={artist.avatar_url}
                alt={artist.username}
                className="w-full h-full object-cover"
              />
            ) : (
              <div className="w-full h-full flex items-center justify-center text-2xl">
                👤
              </div>
            )}
          </div>
        </Link>

        <div className="flex-1 min-w-0">
          <Link
            href={`/users/${artist.user_id}`}
            className="font-bold text-text-primary text-base hover:underline"
          >
            @{artist.username}
          </Link>
          <div className="flex items-center gap-2 mt-0.5 flex-wrap">
            {artist.tier_badge && <TierBadge tier={artist.tier_badge} />}
            {artist.primary_genre && (
              <span className="text-xs text-text-muted italic">
                {artist.primary_genre}
              </span>
            )}
            {artist.country && (
              <span className="text-xs text-text-muted">{artist.country}</span>
            )}
          </div>
        </div>

        <Link
          href={`/users/${artist.user_id}`}
          className="btn-primary text-xs px-3 py-1.5 flex-shrink-0 hidden sm:block"
        >
          {t("explore.hero.viewProfile")}
        </Link>
      </div>

      {/* Mobile CTA */}
      <Link
        href={`/users/${artist.user_id}`}
        className="btn-primary text-xs px-3 py-1.5 w-full text-center mt-3 sm:hidden block"
      >
        {t("explore.hero.viewProfile")}
      </Link>
    </section>
  );
}
