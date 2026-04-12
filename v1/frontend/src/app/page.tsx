"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { PostCard } from "@/components/PostCard";
import { fetchExplore, fetchHomeFeed, PostView } from "@/lib/api";
import { useMe } from "@/lib/useMe";

export default function HomePage() {
  const { me, loading: meLoading } = useMe();
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
        // 로그인: 팔로우 70% + 트렌딩 30% 혼합 (설계 §6.7)
        const feed = await fetchHomeFeed(20);
        setPosts(feed);
      } else {
        // 비로그인: 공개 피드 (인기순, 트렌딩 스코어 반영)
        const rec = await fetchExplore({ limit: 20, sort: "popular" });
        setPosts(rec);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load feed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen">
      <main className="flex-1 min-w-0 border-r border-border xl:max-w-[680px]">
        <div className="sticky top-0 z-20 bg-background/80 backdrop-blur-md border-b border-border px-4 py-3">
          <h1 className="text-xl font-bold">추천</h1>
          <p className="text-xs text-text-muted mt-0.5">
            {me
              ? "팔로우한 작가와 인기 작품을 섞어 보여드려요."
              : "지금 인기 있는 신진 작가들의 작품이에요."}
          </p>
        </div>

        <div className="p-4">
          {error && (
            <div className="card border-danger p-4 mb-4 text-danger text-sm">
              <div className="font-semibold mb-1">
                피드를 불러오지 못했습니다
              </div>
              <div>{error}</div>
            </div>
          )}

          {loading ? (
            <FeedSkeleton />
          ) : posts.length === 0 ? (
            <div className="card p-12 text-center text-text-muted">
              표시할 포스트가 없습니다.
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {posts.map((post) => (
                <PostCard key={post.id} post={post} />
              ))}
            </div>
          )}
        </div>
      </main>

      <RightRail />
    </div>
  );
}

function FeedSkeleton() {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
      {Array.from({ length: 6 }).map((_, i) => (
        <div key={i} className="card overflow-hidden animate-pulse">
          <div className="aspect-[4/5] bg-surface-hover" />
          <div className="p-4 space-y-3">
            <div className="h-3 w-24 bg-surface-hover rounded" />
            <div className="h-4 w-3/4 bg-surface-hover rounded" />
            <div className="h-3 w-16 bg-surface-hover rounded" />
          </div>
        </div>
      ))}
    </div>
  );
}

function RightRail() {
  const [trending, setTrending] = useState<PostView[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const posts = await fetchExplore({ type: "product", limit: 8 });
        if (!cancelled) setTrending(posts);
      } catch {
        /* ignore */
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  const artists = Array.from(
    new Map(
      trending
        .filter((p) => p.author.role === "artist")
        .map((p) => [p.author.id, p.author])
    ).values()
  ).slice(0, 5);

  const topPosts = trending
    .filter((p) => (p.bluebird_count ?? 0) + (p.like_count ?? 0) > 0)
    .sort(
      (a, b) =>
        b.bluebird_count + b.like_count - (a.bluebird_count + a.like_count)
    )
    .slice(0, 4);

  return (
    <aside className="hidden xl:block w-[340px] flex-shrink-0 py-4 px-6 space-y-4">
      <div className="sticky top-4">
        <div className="card p-4 mb-4">
          <h3 className="text-lg font-bold mb-3">트렌딩 작품</h3>
          {loading ? (
            <div className="space-y-3">
              {Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="flex gap-3 animate-pulse">
                  <div className="w-12 h-12 bg-surface-hover rounded" />
                  <div className="flex-1 space-y-2">
                    <div className="h-3 bg-surface-hover rounded w-3/4" />
                    <div className="h-3 bg-surface-hover rounded w-1/2" />
                  </div>
                </div>
              ))}
            </div>
          ) : topPosts.length === 0 ? (
            <p className="text-text-muted text-sm">아직 트렌딩이 없습니다.</p>
          ) : (
            <ul className="space-y-3">
              {topPosts.map((p) => (
                <li key={p.id}>
                  <Link
                    href={`/posts/${p.id}`}
                    className="flex gap-3 hover:bg-surface-hover -mx-2 px-2 py-2 rounded-lg transition-colors"
                  >
                    {p.media[0] ? (
                      <img
                        src={p.media[0].thumbnail_url ?? p.media[0].url}
                        alt=""
                        className="w-12 h-12 rounded-md object-cover flex-shrink-0"
                      />
                    ) : (
                      <div className="w-12 h-12 rounded-md bg-surface-hover flex-shrink-0" />
                    )}
                    <div className="flex-1 min-w-0">
                      <div className="text-xs text-text-muted">
                        @{p.author.display_name}
                      </div>
                      <div className="text-sm font-medium text-text-primary truncate">
                        {p.title ?? "무제"}
                      </div>
                      <div className="text-xs text-text-muted">
                        ♥ {p.like_count} · 🕊 {p.bluebird_count}
                      </div>
                    </div>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="card p-4 mb-4">
          <h3 className="text-lg font-bold mb-3">추천 작가</h3>
          {loading ? (
            <div className="space-y-3">
              {Array.from({ length: 3 }).map((_, i) => (
                <div key={i} className="flex items-center gap-3 animate-pulse">
                  <div className="w-10 h-10 bg-surface-hover rounded-full" />
                  <div className="flex-1 space-y-2">
                    <div className="h-3 bg-surface-hover rounded w-1/2" />
                    <div className="h-3 bg-surface-hover rounded w-1/3" />
                  </div>
                </div>
              ))}
            </div>
          ) : artists.length === 0 ? (
            <p className="text-text-muted text-sm">추천 작가 없음</p>
          ) : (
            <ul className="space-y-3">
              {artists.map((a) => (
                <li
                  key={a.id}
                  className="flex items-center justify-between gap-3"
                >
                  <Link
                    href={`/users/${a.id}`}
                    className="flex items-center gap-3 flex-1 min-w-0"
                  >
                    <div className="w-10 h-10 rounded-full bg-surface-hover flex items-center justify-center text-primary font-bold flex-shrink-0">
                      {a.avatar_url ? (
                        <img
                          src={a.avatar_url}
                          alt=""
                          className="w-full h-full rounded-full object-cover"
                        />
                      ) : (
                        a.display_name.charAt(0).toUpperCase()
                      )}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-semibold truncate">
                        @{a.display_name}
                      </div>
                      <div className="text-xs text-primary">✓ Artist</div>
                    </div>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="text-xs text-text-muted px-2 space-y-1">
          <div className="flex flex-wrap gap-x-3 gap-y-1">
            <Link href="/legal/privacy" className="hover:text-primary">
              개인정보 처리방침
            </Link>
            <Link href="/legal/terms" className="hover:text-primary">
              이용약관
            </Link>
            <Link href="/legal/cookies" className="hover:text-primary">
              쿠키
            </Link>
          </div>
          <div>© 2026 Domo</div>
        </div>
      </div>
    </aside>
  );
}
