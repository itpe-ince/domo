"use client";

/**
 * PostCard — feed card for a single post.
 *
 * B-5: Added hover BluebirdButton mini-button (desktop only).
 * - Shows on hover at top-right for artist posts
 * - Mobile: omitted (cluttering prevention per spec)
 * - Clicking opens BluebirdModal without navigating to post
 */

import { useState } from "react";
import Link from "next/link";
import type { PostView } from "@/lib/api";
import { VisibilityBadge } from "@/components/VisibilityBadge";
import { TierBadge } from "@/components/TierBadge";
import { AuctionCountdown } from "@/components/AuctionCountdown";
import dynamic from "next/dynamic";

const BluebirdModal = dynamic(
  () => import("@/components/BluebirdModal").then((m) => ({ default: m.BluebirdModal })),
  { ssr: false, loading: () => null }
);
import { useI18n } from "@/i18n";
import { captureEvent } from "@/lib/analytics/capture";
import { convertAndFormat } from "@/lib/format";
import { useExchangeRates } from "@/lib/hooks/useExchangeRates";

export function PostCard({
  post,
  source = "feed",
}: {
  post: PostView;
  source?: "feed" | "explore" | "search" | "profile";
}) {
  const { t } = useI18n();
  const { rates, currency: preferredCurrency } = useExchangeRates();
  const cover = post.media[0];
  const isProduct = post.type === "product";
  const isArtist = post.author.role === "artist";

  // B-5: sponsorOpen controls BluebirdModal; hover is now CSS group-hover/group-focus-within
  const [sponsorOpen, setSponsorOpen] = useState(false);

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
    <>
      <div
        className="card overflow-hidden relative group"
      >
        {/* B-5: mini BluebirdButton — desktop only, artist posts only.
            Visible on hover OR when the card has keyboard focus (focus-within).
            This ensures keyboard users can reach the button (a11y: B-6). */}
        {isArtist && (
          <button
            onClick={(e) => {
              e.preventDefault();
              e.stopPropagation();
              setSponsorOpen(true);
            }}
            aria-label={t("post_card.bluebirdAriaLabel")}
            className="hidden md:flex absolute top-2 left-2 z-20 items-center gap-1 bg-primary text-background rounded-full px-2.5 py-1 text-xs font-semibold shadow-md hover:opacity-90 transition-opacity focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 opacity-0 group-hover:opacity-100 group-focus-within:opacity-100"
            tabIndex={0}
          >
            <span aria-hidden="true">🕊</span>
            <span>{t("post_card.bluebirdLabel")}</span>
          </button>
        )}

        <Link
          href={`/posts/${post.id}`}
          className="block"
          onClick={() => captureEvent({ type: "post_click", post_id: post.id, source })}
        >
          <div className="absolute top-2 right-2 z-10 flex items-center gap-1">
            <VisibilityBadge visibility={post.visibility} />
            <TierBadge post={post} />
          </div>
          {cover && (
            <div className="relative aspect-[4/5] bg-background overflow-hidden">
              <img
                src={cover.thumbnail_url ?? cover.url}
                alt={post.effective_caption || post.title || ""}
                className="w-full h-full object-cover transition-transform duration-300 group-hover:scale-[1.02]"
                loading="lazy"
              />
              {isProduct && post.product && (
                <div className="absolute top-3 right-3 flex flex-col gap-1 items-end">
                  {post.product.is_auction && (
                    <span className="badge-primary">{t("common_ui.auctionBadge")}</span>
                  )}
                  {post.product.is_buy_now && (
                    <span className="badge-primary">{t("common_ui.buyNowBadge")}</span>
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

            {post.product?.buy_now_price != null && post.product.buy_now_price > 0 && (
              <div className="text-primary font-medium text-sm">
                {convertAndFormat(
                  post.product.buy_now_price,
                  post.product.buy_now_currency || post.product.currency || "USD",
                  preferredCurrency,
                  rates
                )}
              </div>
            )}

            {/* D'-1 carry-over: is_tier_locked lock badge + inline hint */}
            {post.is_tier_locked && (
              <div className="flex items-center gap-1.5 text-xs text-amber-600 bg-amber-50 dark:bg-amber-900/20 rounded px-2 py-1">
                <span aria-hidden="true">🔒</span>
                <span className="font-medium">{t("post.tierLocked.badge")}</span>
                <span className="text-text-muted">·</span>
                <button
                  onClick={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    setSponsorOpen(true);
                  }}
                  className="underline hover:text-primary"
                >
                  {t("post.tierLocked.hint")}
                </button>
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
      </div>

      {/* B-5: BluebirdModal for mini-button */}
      {sponsorOpen && (
        <BluebirdModal
          artistId={post.author.id}
          artistName={post.author.display_name}
          postId={post.id}
          onClose={() => setSponsorOpen(false)}
          onSuccess={() => setSponsorOpen(false)}
        />
      )}
    </>
  );
}
