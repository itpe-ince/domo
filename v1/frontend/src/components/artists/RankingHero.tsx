"use client";

import Link from "next/link";
import { ArtistIndexEntry } from "@/lib/api";
import { TierBadge } from "./TierBadge";
import { useI18n } from "@/i18n";

interface RankingHeroProps {
  top3: ArtistIndexEntry[];
}

const MEDAL_STYLES = [
  // Rank 1 — gold
  "border-yellow-400 shadow-yellow-400/30 shadow-lg",
  // Rank 2 — silver
  "border-zinc-400 shadow-zinc-400/20 shadow-md",
  // Rank 3 — bronze
  "border-amber-700 shadow-amber-700/20 shadow-md",
];

const RANK_ICONS = ["🥇", "🥈", "🥉"];

export function RankingHero({ top3 }: RankingHeroProps) {
  const { t } = useI18n();

  if (top3.length === 0) return null;

  return (
    <section className="mb-10" aria-label={t("artist.index.topHeroTitle")}>
      <h2 className="text-xl font-bold mb-4 text-text-primary">
        {t("artist.index.topHeroTitle")}
      </h2>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {top3.map((artist, i) => (
          <Link
            key={artist.user_id}
            href={`/users/${artist.user_id}`}
            className={`card p-5 flex flex-col items-center text-center border-2 transition-transform hover:scale-[1.02] ${MEDAL_STYLES[i]}`}
          >
            {/* Medal + Rank */}
            <div className="text-3xl mb-2">{RANK_ICONS[i]}</div>
            <div className="text-xs font-bold text-text-muted mb-1">
              #{artist.rank}
            </div>

            {/* Avatar */}
            <div className="w-16 h-16 rounded-full bg-surface-hover flex items-center justify-center text-2xl mb-3 overflow-hidden">
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

            {/* Name + country */}
            <h3 className="font-bold text-text-primary text-base">
              @{artist.username}
            </h3>
            {artist.country && (
              <span className="text-xs text-text-muted mt-0.5">
                {artist.country}
              </span>
            )}

            {/* Tier badge */}
            <div className="mt-2">
              <TierBadge tier={artist.tier_badge} />
            </div>

            {/* Genre */}
            {artist.primary_genre && (
              <span className="mt-1 text-xs text-text-muted italic">
                {artist.primary_genre}
              </span>
            )}

            {/* Score progress bar */}
            <div className="mt-3 w-full">
              <div className="flex justify-between text-xs text-text-muted mb-1">
                <span>{t("artist.index.score")}</span>
                <span>{artist.score.toFixed(1)}</span>
              </div>
              <div className="h-1.5 w-full rounded-full bg-surface-hover overflow-hidden">
                <div
                  className="h-full bg-primary rounded-full transition-all"
                  style={{ width: `${Math.min(100, artist.score)}%` }}
                />
              </div>
            </div>
          </Link>
        ))}
      </div>
    </section>
  );
}
