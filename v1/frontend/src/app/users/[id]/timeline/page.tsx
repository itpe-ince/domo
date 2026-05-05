"use client";

/**
 * /users/[id]/timeline — A-7 Storytelling Hub
 *
 * Auto-generated artist timeline page.
 * Milestones are client-side composed from existing endpoints via useArtistTimeline.
 * C-1 booster: shows published AI interview link when available.
 */

import { use, useEffect, useState } from "react";
import Link from "next/link";
import { useI18n } from "@/i18n";
import { useArtistTimeline } from "@/lib/hooks/useArtistTimeline";
import { ArtistTimeline } from "@/components/stories/ArtistTimeline";
import { TierBadge } from "@/components/artists/TierBadge";
import { captureEvent } from "@/lib/analytics/capture";
import { fetchArtistInterviews, type ArtistInterviewPublicOut } from "@/lib/api";

export default function ArtistTimelinePage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const { t } = useI18n();
  const { milestones, profile, posts, ranking, loading, error } =
    useArtistTimeline(id);

  // C-1: load published interviews (non-blocking, graceful on error)
  const [interviews, setInterviews] = useState<ArtistInterviewPublicOut[]>([]);
  useEffect(() => {
    if (id) {
      fetchArtistInterviews(id, "ko")
        .then(setInterviews)
        .catch(() => {
          // Graceful: interview section simply stays empty
        });
    }
  }, [id]);

  useEffect(() => {
    if (id) {
      captureEvent({
        type: "story_view",
        artist_id: id,
      } as Parameters<typeof captureEvent>[0]);
    }
  }, [id]);

  if (loading) {
    return (
      <main className="flex-1 min-w-0 max-w-2xl mx-auto px-4 py-8">
        <div className="h-32 card animate-pulse mb-6" />
        <div className="space-y-3">
          {[1, 2, 3, 4].map((i) => (
            <div
              key={i}
              className="h-16 rounded-xl border border-border bg-surface-hover animate-pulse"
            />
          ))}
        </div>
      </main>
    );
  }

  if (!profile) {
    return (
      <main className="flex-1 min-w-0 max-w-2xl mx-auto px-4 py-8">
        <div className="card p-6 text-center">
          <p className="text-danger text-sm">
            {error ?? t("timeline.notFound")}
          </p>
          <Link href="/stories" className="btn-secondary text-sm mt-4 inline-block">
            {t("stories.backToHub")}
          </Link>
        </div>
      </main>
    );
  }

  return (
    <main className="flex-1 min-w-0 max-w-2xl mx-auto px-4 py-8">
      {/* Back link */}
      <Link
        href="/stories"
        className="text-text-secondary text-sm mb-6 inline-block hover:text-primary"
      >
        ← {t("stories.pageTitle")}
      </Link>

      {/* Artist header card */}
      <header className="card p-5 mb-8">
        <div className="flex items-start gap-4">
          {profile.avatar_url ? (
            <img
              src={profile.avatar_url}
              alt={profile.display_name}
              className="w-16 h-16 rounded-full object-cover flex-shrink-0"
            />
          ) : (
            <div className="w-16 h-16 rounded-full bg-surface-hover flex items-center justify-center text-3xl flex-shrink-0">
              🎨
            </div>
          )}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <h1 className="text-xl font-bold text-text-primary">
                @{profile.display_name}
              </h1>
              {profile.role === "artist" && (
                <span className="badge-primary text-xs">Artist</span>
              )}
              {ranking && <TierBadge tier={ranking.tier_badge} />}
            </div>
            {profile.country_code && (
              <p className="text-sm text-text-muted mt-0.5">
                📍 {profile.country_code}
              </p>
            )}
            {ranking && (
              <p className="text-xs text-primary mt-1">
                {t("artist.index.badge.globalRank", { rank: String(ranking.rank) })}
              </p>
            )}
            {profile.artist_profile?.statement && (
              <p className="text-sm text-text-secondary mt-2 line-clamp-2">
                {profile.artist_profile.statement}
              </p>
            )}
          </div>
        </div>

        {/* Quick stats */}
        <div className="flex gap-5 mt-4 pt-4 border-t border-border text-sm">
          <span>
            <strong>{profile.follower_count}</strong>{" "}
            <span className="text-text-muted">{t("common.followers")}</span>
          </span>
          <span>
            <strong>{posts.length}</strong>{" "}
            <span className="text-text-muted">{t("timeline.postsCount")}</span>
          </span>
        </div>

        {/* Link to profile */}
        <div className="mt-4 flex gap-3">
          <Link href={`/users/${id}`} className="btn-secondary text-sm px-4 py-2">
            {t("timeline.viewProfile")}
          </Link>
        </div>
      </header>

      {/* C-1: AI Interview section (non-blocking; only shown when published) */}
      {interviews.length > 0 && (
        <section aria-labelledby="interview-heading" className="mb-8">
          <h2
            id="interview-heading"
            className="text-base font-semibold text-text-primary mb-3"
          >
            {t("interview.public.sectionTitle")}
          </h2>
          <div className="space-y-2">
            {interviews.map((iv) => (
              <Link
                key={iv.id}
                href={`/users/${id}/interviews/${iv.locale}`}
                className="block card p-4 hover:border-primary/40 transition-colors"
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-1.5 mb-1">
                      <span className="text-xs px-1.5 py-0.5 rounded bg-primary/10 text-primary">
                        {t("interview.public.aiGenerated")}
                      </span>
                      <span className="text-xs text-text-muted">
                        {iv.locale.toUpperCase()}
                      </span>
                    </div>
                    <p className="text-sm font-medium text-text-primary line-clamp-1">
                      {iv.title}
                    </p>
                  </div>
                  <span className="text-xs text-primary flex-shrink-0 self-center">
                    {t("interview.public.readMore")} →
                  </span>
                </div>
              </Link>
            ))}
          </div>
        </section>
      )}

      {/* Timeline */}
      <section aria-labelledby="timeline-heading">
        <h2
          id="timeline-heading"
          className="text-base font-semibold text-text-primary mb-5"
        >
          {t("timeline.title")}
        </h2>
        <ArtistTimeline
          milestones={milestones}
          artistId={id}
          loading={loading}
          error={error}
        />
      </section>
    </main>
  );
}
