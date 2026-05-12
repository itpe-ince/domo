"use client";

/**
 * ArtistTimeline — A-7 Storytelling Hub
 * Vertical timeline showing auto-generated milestones for an artist.
 */

import { useI18n } from "@/i18n";
import { TimelineMilestone } from "@/lib/hooks/useArtistTimeline";
import { MilestoneCard } from "./MilestoneCard";

interface ArtistTimelineProps {
  milestones: TimelineMilestone[];
  artistId: string;
  loading?: boolean;
  error?: string | null;
}

export function ArtistTimeline({
  milestones,
  artistId,
  loading = false,
  error = null,
}: ArtistTimelineProps) {
  const { t } = useI18n();

  if (loading) {
    return (
      <div className="space-y-3">
        {[1, 2, 3].map((i) => (
          <div
            key={i}
            className="h-16 rounded-xl border border-border bg-surface-hover animate-pulse"
          />
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="card p-6 text-center text-danger text-sm">{error}</div>
    );
  }

  if (milestones.length === 0) {
    return (
      <div className="card p-6 text-center text-text-muted text-sm">
        {t("timeline.empty")}
      </div>
    );
  }

  return (
    <div className="relative">
      {/* Vertical line */}
      <div
        className="absolute left-5 top-4 bottom-4 w-0.5 bg-border"
        aria-hidden
      />
      <ol className="space-y-4 pl-2" aria-label={t("timeline.title")}>
        {milestones.map((milestone) => (
          <li key={milestone.id} className="relative flex gap-2">
            {/* Dot on the vertical line */}
            <div
              className="mt-3 w-3 h-3 rounded-full border-2 border-primary bg-background flex-shrink-0 z-10"
              aria-hidden
            />
            <div className="flex-1 min-w-0">
              <MilestoneCard
                milestone={milestone}
                artistId={artistId}
              />
            </div>
          </li>
        ))}
      </ol>
    </div>
  );
}
