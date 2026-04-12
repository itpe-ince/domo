import Link from "next/link";
import type { PostView } from "@/lib/api";

export function PostCard({ post }: { post: PostView }) {
  const cover = post.media[0];
  const isProduct = post.type === "product";

  return (
    <Link
      href={`/posts/${post.id}`}
      className="card overflow-hidden block group"
    >
      {cover && (
        <div className="relative aspect-[4/5] bg-background overflow-hidden">
          <img
            src={cover.thumbnail_url ?? cover.url}
            alt={post.title ?? "post"}
            className="w-full h-full object-cover transition-transform duration-300 group-hover:scale-[1.02]"
            loading="lazy"
          />
          {isProduct && post.product && (
            <div className="absolute top-3 right-3 flex flex-col gap-1 items-end">
              {post.product.is_auction && (
                <span className="badge-primary">경매</span>
              )}
              {post.product.is_buy_now && (
                <span className="badge-primary">즉시구매</span>
              )}
            </div>
          )}
        </div>
      )}

      <div className="p-4 space-y-2">
        <div className="flex items-center justify-between gap-2">
          <span className="text-sm text-text-secondary truncate">
            @{post.author.display_name}
          </span>
          {post.author.role === "artist" && (
            <span className="text-xs text-primary">✓ Artist</span>
          )}
        </div>

        {post.title && (
          <h3 className="font-semibold text-text-primary line-clamp-2">
            {post.title}
          </h3>
        )}

        {post.product?.buy_now_price && (
          <div className="text-primary font-medium text-sm">
            ₩ {Number(post.product.buy_now_price).toLocaleString()}
          </div>
        )}

        <div className="flex items-center gap-4 text-xs text-text-muted pt-1">
          <span>♥ {post.like_count}</span>
          <span>💬 {post.comment_count}</span>
          {post.bluebird_count > 0 && (
            <span className="text-primary">🕊 {post.bluebird_count}</span>
          )}
        </div>
      </div>
    </Link>
  );
}
