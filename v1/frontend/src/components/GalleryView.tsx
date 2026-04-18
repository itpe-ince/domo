"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useI18n } from "@/i18n";
import { fetchExplore, PostView } from "@/lib/api";

type Section = {
  title: string;
  emoji: string;
  posts: PostView[];
  loading: boolean;
};

const GENRE_SECTIONS = [
  { key: "painting", title: "Painting", emoji: "🎨" },
  { key: "drawing", title: "Drawing", emoji: "✏️" },
  { key: "photography", title: "Photography", emoji: "📸" },
  { key: "sculpture", title: "Sculpture", emoji: "🎭" },
  { key: "mixed_media", title: "Mixed Media", emoji: "🌈" },
];

export function GalleryView() {
  const { t } = useI18n();
  const [trending, setTrending] = useState<PostView[]>([]);
  const [genreSections, setGenreSections] = useState<
    Record<string, PostView[]>
  >({});
  const [makingVideos, setMakingVideos] = useState<PostView[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    void loadAll();
  }, []);

  async function loadAll() {
    setLoading(true);
    try {
      const [trendingRes, ...genreResults] = await Promise.all([
        fetchExplore({ sort: "popular", limit: 10 }),
        ...GENRE_SECTIONS.map((g) =>
          fetchExplore({ genre: g.key, limit: 10 })
        ),
      ]);

      setTrending(trendingRes);

      const genres: Record<string, PostView[]> = {};
      GENRE_SECTIONS.forEach((g, i) => {
        genres[g.key] = genreResults[i];
      });
      setGenreSections(genres);

      // Making videos: filter from trending
      const making = trendingRes.filter((p) =>
        p.media.some((m) => m.is_making_video)
      );
      setMakingVideos(making);
    } catch {
      /* ignore */
    } finally {
      setLoading(false);
    }
  }

  // Top 10 artists from trending
  const topArtists = Array.from(
    new Map(
      trending
        .filter((p) => p.author.role === "artist")
        .map((p) => [p.author.id, p.author])
    ).values()
  ).slice(0, 10);

  if (loading) {
    return (
      <div className="p-4 space-y-8">
        {/* Hero skeleton */}
        <div className="w-full h-64 rounded-2xl bg-surface-hover animate-pulse" />
        {/* Row skeletons */}
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="space-y-3">
            <div className="h-5 w-40 bg-surface-hover rounded animate-pulse" />
            <div className="flex gap-3 overflow-hidden">
              {Array.from({ length: 5 }).map((_, j) => (
                <div
                  key={j}
                  className="w-40 h-52 flex-shrink-0 bg-surface-hover rounded-lg animate-pulse"
                />
              ))}
            </div>
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-6 pb-8">
      {/* Hero banner */}
      {trending[0] && (
        <Link href={`/posts/${trending[0].id}`}>
          <div className="relative mx-4 mt-4 h-64 rounded-2xl overflow-hidden bg-surface-hover">
            {trending[0].media[0] && (
              <img
                src={
                  trending[0].media[0].thumbnail_url ??
                  trending[0].media[0].url
                }
                alt=""
                className="w-full h-full object-cover"
              />
            )}
            <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-transparent" />
            <div className="absolute bottom-4 left-4 right-4">
              <div className="text-xs text-primary font-semibold mb-1">
                {t("home.mostPopular")}
              </div>
              <h2 className="text-xl font-bold text-white">
                {trending[0].title ?? "무제"}
              </h2>
              <div className="text-sm text-white/70 mt-1">
                @{trending[0].author.display_name} · ♥{" "}
                {trending[0].like_count} · 🕊 {trending[0].bluebird_count}
              </div>
            </div>
          </div>
        </Link>
      )}

      {/* Trending */}
      <CardRow
        title={`🔥 ${t("home.trending")}`}
        posts={trending}
      />

      {/* TOP 10 Artists */}
      {topArtists.length > 0 && (
        <div className="px-4">
          <h3 className="text-lg font-bold mb-3">🏆 {t("home.topArtists")}</h3>
          <div className="flex gap-3 overflow-x-auto pb-2 scrollbar-hide">
            {topArtists.map((artist, idx) => (
              <Link
                key={artist.id}
                href={`/users/${artist.id}`}
                className="flex-shrink-0 w-28 text-center"
              >
                <div className="relative">
                  <div className="w-20 h-20 mx-auto rounded-full bg-surface-hover flex items-center justify-center text-primary font-bold text-xl overflow-hidden">
                    {artist.avatar_url ? (
                      <img
                        src={artist.avatar_url}
                        alt=""
                        className="w-full h-full object-cover"
                      />
                    ) : (
                      artist.display_name.charAt(0).toUpperCase()
                    )}
                  </div>
                  <span className="absolute -bottom-1 -left-1 bg-primary text-background text-xs font-bold rounded-full w-6 h-6 flex items-center justify-center">
                    {idx + 1}
                  </span>
                </div>
                <div className="text-xs font-semibold mt-2 truncate">
                  @{artist.display_name}
                </div>
              </Link>
            ))}
          </div>
        </div>
      )}

      {/* Making videos section */}
      {makingVideos.length > 0 && (
        <CardRow
          title={`🎬 ${t("home.makingVideos")}`}
          posts={makingVideos}
        />
      )}

      {/* Genre sections */}
      {GENRE_SECTIONS.map((g) => {
        const posts = genreSections[g.key] ?? [];
        if (posts.length === 0) return null;
        return (
          <CardRow
            key={g.key}
            title={`${g.emoji} ${g.title}`}
            posts={posts}
          />
        );
      })}
    </div>
  );
}

function CardRow({ title, posts }: { title: string; posts: PostView[] }) {
  if (posts.length === 0) return null;

  return (
    <div className="px-4">
      <h3 className="text-lg font-bold mb-3">{title}</h3>
      <div className="flex gap-3 overflow-x-auto pb-2 scrollbar-hide">
        {posts.map((post) => (
          <Link
            key={post.id}
            href={`/posts/${post.id}`}
            className="flex-shrink-0 w-40 group"
          >
            <div className="aspect-[3/4] rounded-lg overflow-hidden bg-surface-hover relative">
              {post.media[0] ? (
                <img
                  src={
                    post.media[0].thumbnail_url ?? post.media[0].url
                  }
                  alt=""
                  className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                />
              ) : (
                <div className="w-full h-full flex items-center justify-center text-text-muted text-sm">
                  🖼
                </div>
              )}
              {post.product && post.product.buy_now_price && (
                <span className="absolute bottom-2 right-2 bg-primary text-background text-[10px] font-bold px-1.5 py-0.5 rounded">
                  ${Number(post.product.buy_now_price).toLocaleString()}
                </span>
              )}
            </div>
            <div className="mt-1.5">
              <div className="text-xs font-medium truncate text-text-primary">
                {post.title ?? "무제"}
              </div>
              <div className="text-[10px] text-text-muted truncate">
                @{post.author.display_name}
              </div>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
