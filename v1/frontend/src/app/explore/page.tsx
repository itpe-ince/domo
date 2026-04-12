"use client";

import { useEffect, useState } from "react";
import { PostCard } from "@/components/PostCard";
import { fetchExplore, PostView } from "@/lib/api";

const GENRES = [
  null,
  "painting",
  "drawing",
  "photography",
  "sculpture",
  "mixed_media",
];

export default function ExplorePage() {
  const [posts, setPosts] = useState<PostView[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [genre, setGenre] = useState<string | null>(null);
  const [type, setType] = useState<"general" | "product" | null>(null);

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [genre, type]);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const items = await fetchExplore({
        genre: genre ?? undefined,
        type: type ?? undefined,
        limit: 40,
      });
      setPosts(items);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="flex-1 min-w-0 xl:max-w-[900px] mx-auto">
      <div className="sticky top-0 z-20 bg-background/80 backdrop-blur-md border-b border-border px-4 py-3">
        <h1 className="text-xl font-bold mb-3">탐색</h1>
        <div className="space-y-2">
          <div className="flex gap-2 overflow-x-auto pb-1">
            {GENRES.map((g) => (
              <button
                key={g ?? "all-g"}
                onClick={() => setGenre(g)}
                className={`px-3 py-1 rounded-full text-xs whitespace-nowrap ${
                  (genre ?? null) === g
                    ? "bg-primary text-background font-semibold"
                    : "bg-surface text-text-secondary hover:bg-surface-hover"
                }`}
              >
                {g ?? "전체"}
              </button>
            ))}
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => setType(null)}
              className={`px-3 py-1 rounded-full text-xs ${
                type === null
                  ? "bg-primary text-background font-semibold"
                  : "bg-surface text-text-secondary"
              }`}
            >
              모든 포스트
            </button>
            <button
              onClick={() => setType("product")}
              className={`px-3 py-1 rounded-full text-xs ${
                type === "product"
                  ? "bg-primary text-background font-semibold"
                  : "bg-surface text-text-secondary"
              }`}
            >
              판매/경매 작품
            </button>
            <button
              onClick={() => setType("general")}
              className={`px-3 py-1 rounded-full text-xs ${
                type === "general"
                  ? "bg-primary text-background font-semibold"
                  : "bg-surface text-text-secondary"
              }`}
            >
              일반 게시물
            </button>
          </div>
        </div>
      </div>

      <div className="p-4">
        {error && (
          <div className="card border-danger p-4 mb-4 text-danger text-sm">
            {error}
          </div>
        )}
        {loading ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {Array.from({ length: 9 }).map((_, i) => (
              <div
                key={i}
                className="card overflow-hidden animate-pulse"
              >
                <div className="aspect-[4/5] bg-surface-hover" />
                <div className="p-4 space-y-2">
                  <div className="h-3 w-1/2 bg-surface-hover rounded" />
                  <div className="h-4 w-3/4 bg-surface-hover rounded" />
                </div>
              </div>
            ))}
          </div>
        ) : posts.length === 0 ? (
          <div className="card p-12 text-center text-text-muted">
            표시할 포스트가 없습니다.
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {posts.map((post) => (
              <PostCard key={post.id} post={post} />
            ))}
          </div>
        )}
      </div>
    </main>
  );
}
