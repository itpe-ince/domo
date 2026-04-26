"use client";

import Link from "next/link";
import { useI18n } from "@/i18n";
import { PostView } from "@/lib/api";
import { usePostTranslation } from "@/lib/useTranslation";

export function FeedItem({ post }: { post: PostView }) {
  const { t } = useI18n();
  const heroMedia = post.media[0];
  const { title: translatedTitle, content: translatedContent, isTranslated } = usePostTranslation(
    post.id, post.language, post.title, post.content
  );

  return (
    <article className="px-4 py-4 hover:bg-surface-hover/30 transition-colors">
      {/* Author header */}
      <Link
        href={`/users/${post.author.id}`}
        className="flex items-center gap-3 mb-3"
      >
        <div className="w-10 h-10 rounded-full bg-surface-hover flex items-center justify-center text-primary font-bold flex-shrink-0 overflow-hidden">
          {post.author.avatar_url ? (
            <img
              src={post.author.avatar_url}
              alt=""
              className="w-full h-full object-cover"
            />
          ) : (
            post.author.display_name.charAt(0).toUpperCase()
          )}
        </div>
        <div className="flex-1 min-w-0">
          <span className="text-sm font-semibold">
            @{post.author.display_name}
          </span>
          {post.author.role === "artist" && (
            <span className="text-xs text-primary ml-1.5">✓</span>
          )}
          <div className="text-xs text-text-muted">
            {timeAgo(post.created_at)}
          </div>
        </div>
        <div className="flex gap-1.5">
          {(post as any).recommendation_reason === "following" && (
            <span className="text-[10px] bg-surface text-text-muted px-2 py-0.5 rounded-full">
              {t("recommendation.following")}
            </span>
          )}
          {(post as any).recommendation_reason === "trending" && (
            <span className="text-[10px] bg-surface text-text-muted px-2 py-0.5 rounded-full">
              {t("recommendation.trending")}
            </span>
          )}
          {post.type === "product" && (
            <span className="text-[10px] bg-primary/20 text-primary px-2 py-0.5 rounded-full font-semibold">
              {t("post.artwork")}
            </span>
          )}
        </div>
      </Link>

      {/* Title */}
      {(translatedTitle || post.title) && (
        <Link href={`/posts/${post.id}`}>
          <h2 className="text-base font-bold mb-2 hover:text-primary transition-colors">
            {translatedTitle || post.title}
            {isTranslated && <span className="text-xs text-text-muted font-normal ml-1.5">🌐</span>}
          </h2>
        </Link>
      )}

      {/* Content preview */}
      {(translatedContent || post.content) && (
        <p className="text-sm text-text-secondary mb-3 line-clamp-3">
          {translatedContent || post.content}
        </p>
      )}

      {/* Media — full width, single image */}
      {heroMedia && (
        <Link href={`/posts/${post.id}`} className="block mb-3">
          {heroMedia.type === "video" ? (
            <div className="relative rounded-xl overflow-hidden bg-surface-hover aspect-video">
              <video
                src={heroMedia.url}
                className="w-full h-full object-cover"
                muted
                loop
                playsInline
                onMouseEnter={(e) => (e.target as HTMLVideoElement).play()}
                onMouseLeave={(e) => {
                  const v = e.target as HTMLVideoElement;
                  v.pause();
                  v.currentTime = 0;
                }}
              />
              <span className="absolute inset-0 flex items-center justify-center text-4xl text-white/60">
                ▶
              </span>
            </div>
          ) : (
            <img
              src={heroMedia.thumbnail_url ?? heroMedia.url}
              alt={post.title ?? ""}
              className="w-full rounded-xl object-cover max-h-[500px]"
            />
          )}
        </Link>
      )}

      {/* Location */}
      {post.location_name && (
        <div className="text-xs text-text-muted mb-2">
          📍 {post.location_name}
        </div>
      )}

      {/* Engagement bar */}
      <div className="flex items-center gap-6 text-text-muted text-sm">
        <span className="flex items-center gap-1.5 hover:text-primary cursor-pointer transition-colors">
          ♥ {post.like_count}
        </span>
        <span className="flex items-center gap-1.5">
          💬 {post.comment_count}
        </span>
        <span className="flex items-center gap-1.5 hover:text-primary cursor-pointer transition-colors">
          🕊 {post.bluebird_count}
        </span>
        {post.product && post.product.buy_now_price && (
          <span className="ml-auto text-primary font-semibold text-xs">
            ${Number(post.product.buy_now_price).toLocaleString()}
          </span>
        )}
      </div>

      {/* Tags */}
      {post.tags && post.tags.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mt-2">
          {post.tags.map((tag) => (
            <Link
              key={tag}
              href={`/search?q=${encodeURIComponent(tag)}&tab=artworks`}
              className="text-xs text-primary hover:underline"
            >
              #{tag}
            </Link>
          ))}
        </div>
      )}
    </article>
  );
}

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const sec = Math.floor(diff / 1000);
  if (sec < 60) return `${sec}초 전`;
  const min = Math.floor(sec / 60);
  if (min < 60) return `${min}분 전`;
  const hr = Math.floor(min / 60);
  if (hr < 24) return `${hr}시간 전`;
  return `${Math.floor(hr / 24)}일 전`;
}

export function FeedSkeleton() {
  return (
    <div className="divide-y divide-border">
      {Array.from({ length: 5 }).map((_, i) => (
        <div key={i} className="px-4 py-4 animate-pulse space-y-3">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-surface-hover" />
            <div className="space-y-1.5">
              <div className="h-3 w-24 bg-surface-hover rounded" />
              <div className="h-2 w-16 bg-surface-hover rounded" />
            </div>
          </div>
          <div className="h-4 w-2/3 bg-surface-hover rounded" />
          <div className="w-full aspect-video bg-surface-hover rounded-xl" />
          <div className="flex gap-6">
            <div className="h-3 w-12 bg-surface-hover rounded" />
            <div className="h-3 w-12 bg-surface-hover rounded" />
            <div className="h-3 w-12 bg-surface-hover rounded" />
          </div>
        </div>
      ))}
    </div>
  );
}
