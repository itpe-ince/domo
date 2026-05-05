"use client";

/**
 * Feed page — A-2 onboarding wizard + A-3 feed-algorithm-v1
 *
 * A-3 additions:
 *  - PostHog feature flag 'feed-algorithm-v2' for gradual rollout
 *  - FeedAlgorithmToggle: user-facing radio (latest / personalized)
 *  - cursor-based pagination for algo=v1
 *  - captureEvent('feed_algorithm_view') on algo selection
 */

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useI18n } from "@/i18n";
import { captureEvent } from "@/lib/analytics/capture";
import { isFeatureEnabled } from "@/lib/analytics/featureFlags";
import { FeedAlgorithmToggle } from "@/components/feed/FeedAlgorithmToggle";
import { FeedItem, FeedSkeleton } from "@/components/FeedItem";
import { fetchExplore, fetchHomeFeed, type FeedAlgo, type PostView } from "@/lib/api";
import { useMe } from "@/lib/useMe";
import { useOnboarding } from "@/lib/hooks/useOnboarding";

export default function FeedPage() {
  const { me, loading: meLoading } = useMe();
  const { t } = useI18n();
  const [posts, setPosts] = useState<PostView[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { reopenWizard } = useOnboarding();

  // ── A-3: algo state & pagination ─────────────────────────────────────────
  const flagEnabled = isFeatureEnabled("feed-algorithm-v2");
  const defaultAlgo: FeedAlgo = flagEnabled ? "v1" : "default";
  const [algo, setAlgo] = useState<FeedAlgo>(defaultAlgo);
  const [cursor, setCursor] = useState<string | undefined>(undefined);
  const [hasMore, setHasMore] = useState(false);
  // Prevents duplicate initial analytics event
  const algoEventFiredRef = useRef(false);

  // A-2: Open wizard via AppShell (dispatches domo-onboarding-reopen event)
  const handleOpenWizard = useCallback(() => {
    reopenWizard();
  }, [reopenWizard]);

  // ── Load feed (first page or append) ────────────────────────────────────
  const loadFeed = useCallback(
    async (append = false, appendCursor?: string) => {
      if (meLoading) return;
      if (!append) {
        setLoading(true);
        setError(null);
      }
      try {
        if (me) {
          const res = await fetchHomeFeed(
            20,
            algo,
            append ? appendCursor : undefined,
          );
          if (append) {
            setPosts((prev) => [...prev, ...res.data]);
          } else {
            setPosts(res.data);
          }
          setCursor(res.pagination.next_cursor ?? undefined);
          setHasMore(res.pagination.has_more);
        } else {
          const data = await fetchExplore({ limit: 20, sort: "popular" });
          setPosts(data);
          setCursor(undefined);
          setHasMore(false);
        }
      } catch (e) {
        setError(e instanceof Error ? e.message : t("feed.loadError"));
      } finally {
        setLoading(false);
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [me, meLoading, algo]
  );

  // Reload on user or algo change
  useEffect(() => {
    setCursor(undefined);
    setHasMore(false);
    void loadFeed(false);

    // Fire analytics on first load and on subsequent algo changes
    if (!algoEventFiredRef.current) {
      algoEventFiredRef.current = true;
      captureEvent({ type: "feed_algorithm_view", algo });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [me?.id, meLoading, algo]);

  function handleAlgoChange(next: FeedAlgo) {
    if (next === algo) return;
    captureEvent({ type: "feed_algorithm_view", algo: next });
    setAlgo(next);
    algoEventFiredRef.current = true;
  }

  function handleLoadMore() {
    if (!hasMore || loading) return;
    void loadFeed(true, cursor);
  }

  // Show toggle when feature flag is active and user is authenticated
  const showToggle = Boolean(me) && flagEnabled;

  return (
    <main className="flex-1 min-w-0 max-w-3xl mx-auto">
      <div className="sticky top-0 z-20 bg-background/80 backdrop-blur-md border-b border-border px-4 py-3">
        <div className="flex items-center justify-between gap-3">
          <div className="min-w-0">
            <h1 className="text-xl font-bold">
              {algo === "v1" && me ? t("feed.titlePersonalized") : t("feed.title")}
            </h1>
            <p className="text-xs text-text-muted mt-0.5">
              {me
                ? algo === "v1"
                  ? t("feed.subtitlePersonalized")
                  : t("feed.subtitleAuth")
                : t("feed.subtitleGuest")}
            </p>
          </div>
          {showToggle && (
            <div className="flex-shrink-0">
              <FeedAlgorithmToggle value={algo} onChange={handleAlgoChange} />
            </div>
          )}
        </div>
      </div>

      {error && (
        <div className="mx-4 mt-4 card border-danger p-4 text-danger text-sm">
          {error}
        </div>
      )}

      {loading && posts.length === 0 ? (
        <FeedSkeleton />
      ) : posts.length === 0 && me ? (
        /* A-2: Empty feed CTA for authenticated users with no following */
        <div className="card p-10 m-4 text-center space-y-5">
          <div className="text-4xl" aria-hidden="true">🎨</div>
          <div className="space-y-1">
            <h2 className="font-bold text-text-primary text-lg">
              {t("feed.emptyTitle")}
            </h2>
            <p className="text-sm text-text-secondary">
              {t("feed.emptySubtitle")}
            </p>
          </div>
          <div className="flex flex-col sm:flex-row gap-2 justify-center">
            <button
              type="button"
              onClick={handleOpenWizard}
              className="btn-primary"
            >
              {t("feed.emptyCtaFollow")}
            </button>
            <Link href="/support" className="btn-secondary">
              {t("feed.emptyCtaSponsor")}
            </Link>
          </div>
        </div>
      ) : posts.length === 0 ? (
        <div className="card p-12 m-4 text-center text-text-muted">
          {t("feed.noPosts")}
        </div>
      ) : (
        <div className="divide-y divide-border">
          {posts.map((post) => (
            <FeedItem key={post.id} post={post} source="feed" />
          ))}
        </div>
      )}

      {/* A-3: Load more button for cursor pagination (algo=v1) */}
      {hasMore && (
        <div className="flex justify-center py-6">
          <button
            onClick={handleLoadMore}
            disabled={loading}
            className="btn btn-secondary text-sm px-6"
          >
            {loading ? t("common.loading") : t("feed.loadMore")}
          </button>
        </div>
      )}

    </main>
  );
}
