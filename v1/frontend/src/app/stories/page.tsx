"use client";

/**
 * /stories — A-7 Storytelling Hub
 *
 * Main hub layout:
 *  1. Featured Artist hero (artist_index rank 1)
 *  2. Artist history grid (timeline cards — artists with milestones)
 *  3. External media coverage grid
 */

import { useEffect, useState } from "react";
import Link from "next/link";
import { useI18n } from "@/i18n";
import { fetchArtistIndex, fetchFeaturedArtist, ArtistIndexEntry, ArtistFeaturedView } from "@/lib/api";
import { FeaturedArtistHero } from "@/components/stories/FeaturedArtistHero";
import { MediaCoverageGrid } from "@/components/stories/MediaCoverageGrid";
import { TierBadge } from "@/components/artists/TierBadge";
import { LocaleSwitcher } from "@/components/LocaleSwitcher";
import { captureEvent } from "@/lib/analytics/capture";

export default function StoriesPage() {
  const { t } = useI18n();
  const [topArtists, setTopArtists] = useState<ArtistIndexEntry[]>([]);
  const [featuredArtist, setFeaturedArtist] = useState<ArtistFeaturedView | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void loadData();
    // Fire PostHog story_view event
    captureEvent({ type: "story_view" } as Parameters<typeof captureEvent>[0]);
  }, []);

  async function loadData() {
    setLoading(true);
    setError(null);
    try {
      // Load curated featured artist + artist index in parallel
      const [featured, indexRes] = await Promise.all([
        fetchFeaturedArtist().catch(() => null), // graceful degrade
        fetchArtistIndex({ limit: 12 }),
      ]);
      setFeaturedArtist(featured);
      setTopArtists(indexRes.data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }

  // Use curated featured artist if available, otherwise fall back to rank 1 from index
  const featured: ArtistFeaturedView | null = featuredArtist ?? (
    topArtists[0]
      ? {
          user_id: topArtists[0].user_id,
          username: topArtists[0].username,
          avatar_url: topArtists[0].avatar_url,
          bio: null,
          country: topArtists[0].country,
          primary_genre: topArtists[0].primary_genre,
          tier_badge: topArtists[0].tier_badge,
          rank: topArtists[0].rank,
          score: topArtists[0].score,
          curation_note: null,
          month: new Date().toISOString().slice(0, 7),
          is_curated: false,
        }
      : null
  );
  // Show artists 1-12 (index 0-11) in the timeline grid section
  const gridArtists = topArtists.slice(1, 12);

  return (
    <main className="flex-1 min-w-0 max-w-3xl mx-auto px-4 py-8">
      {/* Page header */}
      <header className="mb-8 flex items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-text-primary">
            {t("stories.pageTitle")}
          </h1>
          <p className="mt-1 text-text-muted text-sm">
            {t("stories.pageSubtitle")}
          </p>
        </div>
        {/* C-3: Locale switcher — lets visitors choose their preferred language */}
        <LocaleSwitcher compact={false} className="shrink-0 mt-1" />
      </header>

      {/* ─── Section 1: Featured Artist ─────────────────────────────── */}
      <section className="mb-10" aria-labelledby="featured-heading">
        <h2
          id="featured-heading"
          className="text-lg font-semibold text-text-primary mb-4 flex items-center gap-2"
        >
          <span aria-hidden>🌟</span>
          {t("stories.featured.sectionTitle")}
        </h2>

        {error && (
          <div className="card p-6 text-center text-danger text-sm">{error}</div>
        )}

        {!error && (loading || featured) && (
          <FeaturedArtistHero
            artist={featured!}
            loading={loading && !featured}
          />
        )}

        {!loading && !error && !featured && (
          <div className="card p-6 text-center text-text-muted text-sm">
            {t("stories.featured.empty")}
          </div>
        )}
      </section>

      {/* ─── Section 2: Artist History Grid ─────────────────────────── */}
      <section className="mb-10" aria-labelledby="history-heading">
        <h2
          id="history-heading"
          className="text-lg font-semibold text-text-primary mb-4 flex items-center gap-2"
        >
          <span aria-hidden>📖</span>
          {t("stories.history.sectionTitle")}
        </h2>
        <p className="text-sm text-text-muted mb-5">
          {t("stories.history.sectionSubtitle")}
        </p>

        {loading && (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {[1, 2, 3, 4].map((i) => (
              <div
                key={i}
                className="h-28 card animate-pulse bg-surface-hover"
              />
            ))}
          </div>
        )}

        {!loading && gridArtists.length > 0 && (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {gridArtists.map((artist) => (
              <ArtistHistoryCard key={artist.user_id} artist={artist} />
            ))}
          </div>
        )}

        {!loading && gridArtists.length === 0 && !error && (
          <div className="card p-6 text-center text-text-muted text-sm">
            {t("stories.history.empty")}
          </div>
        )}

        {/* Link to full ranking */}
        <div className="mt-5 text-center">
          <Link href="/artists/index" className="btn-secondary text-sm px-5 py-2">
            {t("stories.history.viewFullIndex")}
          </Link>
        </div>
      </section>

      {/* ─── Section 3: External Media Coverage ─────────────────────── */}
      <section aria-labelledby="media-heading">
        <h2
          id="media-heading"
          className="text-lg font-semibold text-text-primary mb-4 flex items-center gap-2"
        >
          <span aria-hidden>📰</span>
          {t("stories.media.sectionTitle")}
        </h2>
        <MediaCoverageGrid />
      </section>
    </main>
  );
}

/** Compact artist card for the history grid section */
function ArtistHistoryCard({ artist }: { artist: ArtistIndexEntry }) {
  const { t } = useI18n();

  return (
    <Link
      href={`/users/${artist.user_id}/timeline`}
      className="card p-4 flex items-center gap-4 hover:shadow-md transition-shadow"
      aria-label={`${artist.username} ${t("stories.history.viewTimeline")}`}
    >
      {/* Avatar */}
      {artist.avatar_url ? (
        <img
          src={artist.avatar_url}
          alt={artist.username}
          className="w-14 h-14 rounded-full object-cover flex-shrink-0"
        />
      ) : (
        <div className="w-14 h-14 rounded-full bg-surface-hover flex items-center justify-center text-2xl flex-shrink-0">
          🎨
        </div>
      )}

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <p className="font-semibold text-text-primary truncate">
            @{artist.username}
          </p>
          <TierBadge tier={artist.tier_badge} />
        </div>
        <p className="text-xs text-text-muted mt-0.5">
          {[
            artist.country ? `📍 ${artist.country}` : null,
            artist.primary_genre ?? null,
          ]
            .filter(Boolean)
            .join(" · ")}
        </p>
        <p className="text-xs text-primary mt-1">
          {t("artist.index.badge.globalRank", { rank: String(artist.rank) })}
        </p>
      </div>

      <span className="text-text-muted text-lg flex-shrink-0" aria-hidden>
        →
      </span>
    </Link>
  );
}
