"use client";

/**
 * Explore Page — A-4 Explore Revamp
 *
 * Layout:
 *  1. Sticky header with 5 tabs + context filter
 *  2. 오늘의 작가 Hero Card (A-6 artist-index top-3 daily rotation)
 *  3. Ranking Preview strip — top-5 horizontal scroll → /artists/index
 *  4. Posts grid (tab-driven)
 *
 * Tab behavior:
 *  - Trending: popular sort 24h (PostHog flag 'feed-algorithm-v2' → algo=v1)
 *  - New: created_at DESC
 *  - Region: country-group filter + dropdown
 *  - Genre: genre filter + dropdown
 *  - Pricing: product posts (auction active OR buy_now)
 *
 * State: URL query params + localStorage last-tab persistence.
 * Analytics: explore_view {tab}, explore_hero_view {artist_id},
 *            artist_index_preview_click {rank}.
 */

import { Suspense, useEffect, useState } from "react";
import { useI18n } from "@/i18n";
import { fetchExplorePosts } from "@/lib/api";
import { useExploreState } from "@/lib/hooks/useExploreState";
import { useArtistIndex } from "@/lib/hooks/useArtistIndex";
import { isFeatureEnabled } from "@/lib/analytics/featureFlags";
import { ExploreTabs } from "@/components/explore/ExploreTabs";
import { ExploreFilters } from "@/components/explore/ExploreFilters";
import { ExploreHeroCard } from "@/components/explore/ExploreHeroCard";
import { ArtistIndexPreview } from "@/components/explore/ArtistIndexPreview";
import { PostsGrid } from "@/components/explore/PostsGrid";
import type { PostView } from "@/lib/api";

function ExploreContent() {
  const { t } = useI18n();
  const { tab, filters, setTab, setRegion, setGenre } = useExploreState();

  // A-6: artist index (top 5 for preview, top 3 for hero)
  const {
    entries: artistEntries,
    loading: artistLoading,
  } = useArtistIndex({ limit: 5 });

  const top3 = artistEntries.slice(0, 3);

  // Posts state
  const [posts, setPosts] = useState<PostView[]>([]);
  const [postsLoading, setPostsLoading] = useState(true);
  const [postsError, setPostsError] = useState<string | null>(null);

  // Reload posts when tab or filters change
  useEffect(() => {
    let cancelled = false;
    setPostsLoading(true);
    setPostsError(null);

    // PostHog feature flag: trending tab uses algo=v1 when flag active
    // Currently routed through fetchExplorePosts which calls /posts/explore
    // with sort=popular. The v1 personalization is a server-side concern
    // enabled via the feature flag header in a future enhancement.
    const _usePersonalized =
      tab === "trending" && isFeatureEnabled("feed-algorithm-v2");
    void _usePersonalized; // intentional — documents future integration point

    fetchExplorePosts({
      tab,
      region: filters.region || undefined,
      genre: filters.genre || undefined,
      limit: 40,
    })
      .then((items) => {
        if (!cancelled) setPosts(items);
      })
      .catch((e) => {
        if (!cancelled)
          setPostsError(e instanceof Error ? e.message : t("common.error"));
      })
      .finally(() => {
        if (!cancelled) setPostsLoading(false);
      });

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab, filters.region, filters.genre]);

  return (
    <main className="flex-1 min-w-0 xl:max-w-[900px] mx-auto">
      {/* ── Sticky header: title + tabs + context filter ── */}
      <div className="sticky top-0 z-20 bg-background/80 backdrop-blur-md border-b border-border px-4 py-3 space-y-2">
        <h1 className="text-xl font-bold text-text-primary">
          {t("explore.title")}
        </h1>

        <ExploreTabs active={tab} onChange={setTab} />

        {/* Context-sensitive filter row */}
        <ExploreFilters
          tab={tab}
          filters={filters}
          onRegionChange={setRegion}
          onGenreChange={setGenre}
        />
      </div>

      <div className="p-4 space-y-0">
        {/* ── 오늘의 작가 Hero Card ── */}
        <ExploreHeroCard top3={top3} loading={artistLoading} />

        {/* ── Ranking Preview strip ── */}
        <ArtistIndexPreview entries={artistEntries} loading={artistLoading} />

        {/* ── Posts grid ── */}
        <PostsGrid
          posts={posts}
          loading={postsLoading}
          error={postsError}
        />
      </div>
    </main>
  );
}

/**
 * Wrap ExploreContent in a Suspense boundary because useSearchParams()
 * (called inside useExploreState) requires it in Next.js App Router.
 */
export default function ExplorePage() {
  return (
    <Suspense fallback={null}>
      <ExploreContent />
    </Suspense>
  );
}
