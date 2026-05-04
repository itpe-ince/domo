"use client";

/**
 * TierBadge — artist-tier-release PDCA #10, Step 5.
 *
 * Renders an amber lock icon badge for posts in their early-access tier window.
 * Returns null when:
 *   - early_access_until is absent/null
 *   - the window has already expired (client-side clock; actual gate is server-side)
 *   - early_access_tier is absent/null
 *
 * Pattern mirrors VisibilityBadge.tsx (publish-controls PDCA #8).
 */

import type { PostView } from "@/lib/api";
import { LockClosedIcon } from "@/components/icons";
import { useI18n } from "@/i18n";

export function TierBadge({
  post,
  className = "",
}: {
  post: PostView;
  className?: string;
}) {
  const { t } = useI18n();

  if (!post.early_access_until || !post.early_access_tier) return null;

  const expired = new Date(post.early_access_until) <= new Date();
  if (expired) return null;

  const label = t(`post.feed.indicator.tier.${post.early_access_tier}`);

  return (
    <span
      className={`inline-flex items-center gap-1 text-xs text-amber-600 ${className}`}
      title={label}
      aria-label={label}
    >
      <LockClosedIcon className="w-3.5 h-3.5" />
    </span>
  );
}
