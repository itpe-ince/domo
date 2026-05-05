"use client";

/**
 * MilestoneCard — A-7 Storytelling Hub
 * Single milestone card in an artist's timeline.
 */

import Link from "next/link";
import { useI18n } from "@/i18n";
import { TimelineMilestone, MilestoneKind } from "@/lib/hooks/useArtistTimeline";

const KIND_ICONS: Record<MilestoneKind, string> = {
  joined: "🌱",
  first_post: "🎨",
  first_bluebird: "🕊",
  rank_top_1000: "🏅",
  rank_top_100: "🥈",
  rank_top_10: "✨",
  highlight_post: "🔥",
};

const KIND_COLORS: Record<MilestoneKind, string> = {
  joined: "bg-green-100 border-green-300 text-green-800",
  first_post: "bg-blue-100 border-blue-300 text-blue-800",
  first_bluebird: "bg-sky-100 border-sky-300 text-sky-800",
  rank_top_1000: "bg-amber-100 border-amber-300 text-amber-800",
  rank_top_100: "bg-zinc-100 border-zinc-300 text-zinc-800",
  rank_top_10: "bg-yellow-100 border-yellow-300 text-yellow-800",
  highlight_post: "bg-rose-100 border-rose-300 text-rose-800",
};

interface MilestoneCardProps {
  milestone: TimelineMilestone;
  artistId?: string;
  compact?: boolean;
}

function formatDate(iso: string, locale: string): string {
  try {
    return new Date(iso).toLocaleDateString(locale === "ko" ? "ko-KR" : locale, {
      year: "numeric",
      month: "long",
      day: "numeric",
    });
  } catch {
    return iso.slice(0, 10);
  }
}

export function MilestoneCard({ milestone, artistId, compact = false }: MilestoneCardProps) {
  const { t, locale } = useI18n();
  const icon = KIND_ICONS[milestone.kind];
  const colorClass = KIND_COLORS[milestone.kind];

  function buildLabel(): string {
    const base = t(milestone.labelKey as Parameters<typeof t>[0]);
    switch (milestone.kind) {
      case "first_post":
        return milestone.meta?.postTitle
          ? `${base} — "${milestone.meta.postTitle}"`
          : base;
      case "first_bluebird":
        return milestone.meta?.sponsorName
          ? `${base} (${milestone.meta.sponsorName})`
          : base;
      case "rank_top_10":
      case "rank_top_100":
      case "rank_top_1000":
        return milestone.meta?.rank ? `${base} (#${milestone.meta.rank})` : base;
      case "highlight_post":
        return milestone.meta?.postTitle
          ? `${base} — "${milestone.meta.postTitle}"`
          : base;
      default:
        return base;
    }
  }

  const label = buildLabel();
  const dateStr = formatDate(milestone.date, locale);

  const content = (
    <div
      className={`flex items-start gap-3 px-4 py-3 rounded-xl border ${colorClass} ${
        compact ? "text-sm" : ""
      }`}
    >
      <span className="text-xl flex-shrink-0 leading-tight" aria-hidden>
        {icon}
      </span>
      <div className="flex-1 min-w-0">
        <p className="font-medium leading-snug truncate">{label}</p>
        <p className="text-xs opacity-70 mt-0.5">{dateStr}</p>
      </div>
      {milestone.kind === "highlight_post" && milestone.meta?.likeCount != null && (
        <span className="text-xs opacity-60 flex-shrink-0">
          ❤ {milestone.meta.likeCount}
        </span>
      )}
    </div>
  );

  // Wrap highlight posts in a link
  if (
    (milestone.kind === "first_post" || milestone.kind === "highlight_post") &&
    milestone.meta?.postId
  ) {
    return (
      <Link
        href={`/posts/${milestone.meta.postId}`}
        className="block hover:opacity-80 transition-opacity"
        aria-label={label}
      >
        {content}
      </Link>
    );
  }

  return <div>{content}</div>;
}
