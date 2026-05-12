"use client";

import type { Visibility } from "@/lib/api";
import { LockClosedIcon, LinkIcon } from "@/components/icons";
import { useI18n } from "@/i18n";

export interface VisibilityBadgeProps {
  visibility?: Visibility;
  className?: string;
}

/**
 * VisibilityBadge — publish-controls PDCA #8, Step 5 (Task 5.2).
 *
 * Renders a small icon badge for non-public posts only.
 * Public posts render nothing (avoid noise in feed).
 *
 * - followers_only → LockClosedIcon + aria-label
 * - unlisted       → LinkIcon + aria-label
 * - public / undef → null
 */
export function VisibilityBadge({
  visibility,
  className = "",
}: VisibilityBadgeProps) {
  const { t } = useI18n();

  if (!visibility || visibility === "public") return null;

  const isFollowers = visibility === "followers_only";
  const label = isFollowers
    ? t("post.feed.indicator.followersOnly")
    : t("post.feed.indicator.unlisted");
  const Icon = isFollowers ? LockClosedIcon : LinkIcon;

  return (
    <span
      className={`inline-flex items-center gap-1 text-xs text-text-muted ${className}`}
      title={label}
      aria-label={label}
    >
      <Icon className="w-3.5 h-3.5" />
    </span>
  );
}
