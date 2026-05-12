"use client";

import { useI18n } from "@/i18n";

type TierBadgeVariant = "top_10" | "top_100" | "top_1000";

interface TierBadgeProps {
  tier: TierBadgeVariant | null | undefined;
  className?: string;
}

const TIER_COLORS: Record<TierBadgeVariant, string> = {
  top_10: "bg-yellow-400 text-yellow-900 ring-1 ring-yellow-500",
  top_100: "bg-zinc-300 text-zinc-800 ring-1 ring-zinc-400",
  top_1000: "bg-amber-700 text-amber-100 ring-1 ring-amber-800",
};

export function TierBadge({ tier, className = "" }: TierBadgeProps) {
  const { t } = useI18n();

  if (!tier) return null;

  const label = t(`artist.index.tierBadge.${tier}` as Parameters<typeof t>[0]);
  const colors = TIER_COLORS[tier];

  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-bold ${colors} ${className}`}
      aria-label={label}
    >
      {tier === "top_10" && "✨ "}
      {label}
    </span>
  );
}
