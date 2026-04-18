"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useI18n } from "@/i18n";
import { fetchFollowingFeed, PostView } from "@/lib/api";
import { useMe } from "@/lib/useMe";
import { FeedItem, FeedSkeleton } from "../feed/page";

export default function FollowingPage() {
  const { me, loading: meLoading } = useMe();
  const { t } = useI18n();
  const [posts, setPosts] = useState<PostView[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (meLoading) return;
    if (!me) {
      setLoading(false);
      return;
    }
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [me?.id, meLoading]);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      setPosts(await fetchFollowingFeed(20));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="flex-1 min-w-0 max-w-3xl mx-auto">
      <div className="sticky top-0 z-20 bg-background/80 backdrop-blur-md border-b border-border px-4 py-3">
        <h1 className="text-xl font-bold">{t("followingPage.title")}</h1>
        <p className="text-xs text-text-muted mt-0.5">{t("followingPage.subtitle")}</p>
      </div>

      {!me && !meLoading ? (
        <div className="card p-12 m-4 text-center text-text-muted">
          <p>{t("followingPage.loginRequired")}</p>
          <p className="text-xs mt-2">{t("followingPage.loginHint")}</p>
        </div>
      ) : error ? (
        <div className="mx-4 mt-4 card border-danger p-4 text-danger text-sm">
          {error}
        </div>
      ) : loading ? (
        <FeedSkeleton />
      ) : posts.length === 0 ? (
        <div className="card p-8 m-4 text-center">
          <div className="text-4xl mb-3">🕊</div>
          <h2 className="text-lg font-bold mb-2">{t("followingPage.emptyTitle")}</h2>
          <p className="text-sm text-text-muted mb-4">{t("followingPage.emptyHint")}</p>
          <Link
            href="/explore"
            className="inline-block bg-primary text-background hover:bg-primary-hover rounded-full font-bold px-6 py-2.5 transition-colors"
          >
            {t("followingPage.exploreCta")}
          </Link>
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
