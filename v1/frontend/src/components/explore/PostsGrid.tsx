"use client";

/**
 * PostsGrid — A-4 Explore Revamp
 *
 * Displays a responsive grid of PostCard components.
 * Handles loading skeleton, empty state, and error state.
 */

import { PostCard } from "@/components/PostCard";
import { useI18n } from "@/i18n";
import type { PostView } from "@/lib/api";

interface PostsGridProps {
  posts: PostView[];
  loading: boolean;
  error: string | null;
}

export function PostsGrid({ posts, loading, error }: PostsGridProps) {
  const { t } = useI18n();

  if (error) {
    return (
      <div className="card border-danger p-4 text-danger text-sm">{error}</div>
    );
  }

  if (loading) {
    return (
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {Array.from({ length: 9 }).map((_, i) => (
          <div key={i} className="card overflow-hidden animate-pulse">
            <div className="aspect-[4/5] bg-surface-hover" />
            <div className="p-4 space-y-2">
              <div className="h-3 w-1/2 bg-surface-hover rounded" />
              <div className="h-4 w-3/4 bg-surface-hover rounded" />
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (posts.length === 0) {
    return (
      <div className="card p-12 text-center text-text-muted">
        {t("explore.noPosts")}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
      {posts.map((post) => (
        <PostCard key={post.id} post={post} source="explore" />
      ))}
    </div>
  );
}
