"use client";

import { useState } from "react";
import { useI18n } from "@/i18n";
import { useArtistIndex } from "@/lib/hooks/useArtistIndex";
import { RankingHero } from "@/components/artists/RankingHero";
import { RankingCard } from "@/components/artists/RankingCard";
import { RegionFilter } from "@/components/artists/RegionFilter";
import { GenreFilter } from "@/components/artists/GenreFilter";

export function ArtistIndexClient() {
  const { t } = useI18n();
  const [region, setRegion] = useState("");
  const [genre, setGenre] = useState("");

  const { entries, loading, error, hasMore, loadMore } = useArtistIndex({
    region: region || undefined,
    genre: genre || undefined,
    limit: 50,
  });

  const top3 = entries.slice(0, 3);
  const rest = entries.slice(3);

  return (
    <main className="flex-1 min-w-0 max-w-3xl mx-auto px-4 py-8">
      {/* Page header */}
      <header className="mb-8">
        <h1 className="text-3xl font-bold text-text-primary">
          {t("artist.index.pageTitle")}
        </h1>
        <p className="mt-1 text-text-muted text-sm">
          {t("artist.index.pageSubtitle")}
        </p>
      </header>

      {/* Filters */}
      <div className="flex flex-wrap gap-4 mb-8">
        <RegionFilter
          value={region}
          onChange={(v) => setRegion(v)}
        />
        <GenreFilter
          value={genre}
          onChange={(v) => setGenre(v)}
        />
      </div>

      {/* Loading state */}
      {loading && entries.length === 0 && (
        <div className="text-center py-12 text-text-muted">
          {t("artist.index.loading")}
        </div>
      )}

      {/* Error state */}
      {error && !loading && (
        <div className="text-center py-12 text-danger">
          {t("artist.index.error")}
        </div>
      )}

      {/* Empty state */}
      {!loading && !error && entries.length === 0 && (
        <div className="text-center py-12 text-text-muted">
          {t("artist.index.empty")}
        </div>
      )}

      {/* Top 3 Hero */}
      {top3.length > 0 && <RankingHero top3={top3} />}

      {/* Rank 4~50+ list */}
      {rest.length > 0 && (
        <section aria-label={t("artist.index.listTitle")}>
          <h2 className="text-lg font-semibold text-text-primary mb-3">
            {t("artist.index.listTitle")}
          </h2>
          <div className="card divide-y divide-border">
            {rest.map((artist) => (
              <RankingCard
                key={artist.user_id}
                artist={artist}
                activeRegion={region || undefined}
                activeGenre={genre || undefined}
              />
            ))}
          </div>
        </section>
      )}

      {/* Load more */}
      {hasMore && (
        <div className="flex justify-center mt-8">
          <button
            onClick={loadMore}
            disabled={loading}
            className="btn-secondary px-6 py-2 text-sm disabled:opacity-50"
          >
            {loading ? t("artist.index.loading") : t("artist.index.loadMore")}
          </button>
        </div>
      )}

      {/* Loading spinner for pagination */}
      {loading && entries.length > 0 && (
        <div className="text-center py-4 text-text-muted text-sm">
          {t("artist.index.loading")}
        </div>
      )}
    </main>
  );
}
