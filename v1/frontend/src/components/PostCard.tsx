import Link from "next/link";
import type { PostView } from "@/lib/api";
import { VisibilityBadge } from "@/components/VisibilityBadge";
import { TierBadge } from "@/components/TierBadge";
import { AuctionCountdown } from "@/components/AuctionCountdown";

export function PostCard({ post }: { post: PostView }) {
  const cover = post.media[0];
  const isProduct = post.type === "product";

  // auction-promotion-suite PDCA #11 — F-4: D-1h compact countdown
  // OQ-10=B: only show in feed when end_at is within 1h (R-FE-6: optional field)
  const auctionEndAt = post.active_auction_end_at;
  const showCountdown = isProduct &&
    auctionEndAt != null &&
    (() => {
      const msLeft = new Date(auctionEndAt).getTime() - Date.now();
      return msLeft > 0 && msLeft <= 3_600_000;
    })();

  return (
    <Link
      href={`/posts/${post.id}`}
      className="card overflow-hidden block group relative"
    >
      <div className="absolute top-2 right-2 z-10 flex items-center gap-1">
        <VisibilityBadge visibility={post.visibility} />
        <TierBadge post={post} />
      </div>
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
          {/* D-1h compact countdown badge — bottom-left, opposite corner from badges */}
          {showCountdown && auctionEndAt && (
            <div className="absolute bottom-3 left-3 right-3 pointer-events-none">
              <div className="bg-black/60 backdrop-blur-sm rounded px-2 py-1 inline-flex items-center gap-1">
                <span className="text-xs text-amber-200">⏱</span>
                <AuctionCountdown endAt={auctionEndAt} compact />
              </div>
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
