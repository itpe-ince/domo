"use client";

import { useEffect, useState } from "react";
import { useI18n } from "@/i18n";
import { FeedItem, FeedSkeleton } from "@/components/FeedItem";
import { fetchExplore, fetchHomeFeed, PostView } from "@/lib/api";
import { useMe } from "@/lib/useMe";

export default function FeedPage() {
  const { me, loading: meLoading } = useMe();
  const { t } = useI18n();
  const [posts, setPosts] = useState<PostView[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (meLoading) return;
    void loadFeed();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [me?.id, meLoading]);

  async function loadFeed() {
    setLoading(true);
    setError(null);
    try {
      if (me) {
        setPosts(await fetchHomeFeed(20));
      } else {
        setPosts(await fetchExplore({ limit: 20, sort: "popular" }));
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="flex-1 min-w-0 max-w-3xl mx-auto">
      <div className="sticky top-0 z-20 bg-background/80 backdrop-blur-md border-b border-border px-4 py-3">
        <h1 className="text-xl font-bold">{t("feed.title")}</h1>
        <p className="text-xs text-text-muted mt-0.5">
          {me ? t("feed.subtitleAuth") : t("feed.subtitleGuest")}
        </p>
      </div>

      {error && (
        <div className="mx-4 mt-4 card border-danger p-4 text-danger text-sm">
          {error}
        </div>
      )}

      {loading ? (
        <FeedSkeleton />
      ) : posts.length === 0 ? (
        <div className="card p-12 m-4 text-center text-text-muted">
          표시할 포스트가 없습니다.
        </div>
      ) : (
        <div className="divide-y divide-border">
          {posts.map((post) => (
            <FeedItem key={post.id} post={post} />
          ))}
        </div>
      )}
    </main>
  );
}
