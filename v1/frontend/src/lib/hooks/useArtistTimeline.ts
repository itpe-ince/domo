"use client";

/**
 * useArtistTimeline — A-7 Storytelling Hub
 *
 * Fetches and composes milestone events for an artist's timeline.
 * Client-side synthesis from existing endpoints:
 *   - fetchUserProfile (join date)
 *   - fetchExplore (posts by artist — first post milestone)
 *   - fetchReceivedSponsorships (first Blue Bird milestone)
 *   - fetchArtistRanking (rank milestones)
 *
 * No new backend endpoint needed for MVP.
 */

import { useCallback, useEffect, useState } from "react";
import {
  fetchUserProfile,
  fetchExplore,
  fetchReceivedSponsorships,
  fetchArtistRanking,
  UserProfileView,
  PostView,
  ReceivedSponsorshipView,
  ArtistRankingResponse,
} from "@/lib/api";

export type MilestoneKind =
  | "joined"
  | "first_post"
  | "first_bluebird"
  | "rank_top_1000"
  | "rank_top_100"
  | "rank_top_10"
  | "highlight_post";

export type TimelineMilestone = {
  id: string;
  kind: MilestoneKind;
  date: string; // ISO8601
  /** i18n key suffix: timeline.<kind> */
  labelKey: string;
  /** Optional extra data */
  meta?: {
    postTitle?: string | null;
    sponsorName?: string | null;
    rank?: number;
    postId?: string;
    likeCount?: number;
  };
};

export type ArtistTimelineResult = {
  milestones: TimelineMilestone[];
  profile: UserProfileView | null;
  posts: PostView[];
  ranking: ArtistRankingResponse | null;
  loading: boolean;
  error: string | null;
};

/**
 * Derive milestones from raw data, sorted chronologically (oldest first).
 * We use created_at/dates from the data itself — no backend milestones endpoint needed.
 */
function composeMilestones(
  profile: UserProfileView,
  posts: PostView[],
  sponsorships: ReceivedSponsorshipView[],
  ranking: ArtistRankingResponse | null
): TimelineMilestone[] {
  const events: TimelineMilestone[] = [];

  // 1. Joined Domo — use profile creation proxy via earliest post or a hardcoded placeholder
  // UserProfileView does not expose created_at; we use the earliest post date if available,
  // otherwise fall back to current year start as a safe placeholder.
  const sortedPosts = [...posts].sort(
    (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
  );
  const joinProxy =
    sortedPosts.length > 0 ? sortedPosts[0].created_at : new Date().toISOString();

  events.push({
    id: "joined",
    kind: "joined",
    date: joinProxy,
    labelKey: "timeline.joined",
    meta: {},
  });

  // 2. First post
  if (sortedPosts.length > 0) {
    const first = sortedPosts[0];
    events.push({
      id: `post-first-${first.id}`,
      kind: "first_post",
      date: first.created_at,
      labelKey: "timeline.firstPost",
      meta: { postTitle: first.title, postId: first.id },
    });
  }

  // 3. First Blue Bird received (public sponsorships only — anonymous fallback shows "익명")
  const sortedSponsorships = [...sponsorships].sort(
    (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
  );
  if (sortedSponsorships.length > 0) {
    const first = sortedSponsorships[0];
    events.push({
      id: `bluebird-first-${first.id}`,
      kind: "first_bluebird",
      date: first.created_at,
      labelKey: "timeline.firstBluebird",
      meta: {
        sponsorName: first.is_anonymous
          ? null
          : first.sponsor_id
          ? `@${first.sponsor_id.slice(0, 8)}`
          : null,
      },
    });
  }

  // 4. Rank milestones — infer from current tier (best effort)
  if (ranking) {
    const rankDate = ranking.last_calculated_at ?? new Date().toISOString();
    if (ranking.tier_badge === "top_10") {
      events.push({
        id: "rank-top10",
        kind: "rank_top_10",
        date: rankDate,
        labelKey: "timeline.rankTop10",
        meta: { rank: ranking.rank },
      });
    } else if (ranking.tier_badge === "top_100") {
      events.push({
        id: "rank-top100",
        kind: "rank_top_100",
        date: rankDate,
        labelKey: "timeline.rankTop100",
        meta: { rank: ranking.rank },
      });
    } else if (ranking.tier_badge === "top_1000") {
      events.push({
        id: "rank-top1000",
        kind: "rank_top_1000",
        date: rankDate,
        labelKey: "timeline.rankTop1000",
        meta: { rank: ranking.rank },
      });
    }
  }

  // 5. Top highlight posts (by likes + bluebird_count, top 3 excluding the first post)
  const highlights = [...posts]
    .sort((a, b) => b.like_count + b.bluebird_count - (a.like_count + a.bluebird_count))
    .filter((p) => sortedPosts.length === 0 || p.id !== sortedPosts[0].id)
    .slice(0, 3);

  for (const post of highlights) {
    if (post.like_count + post.bluebird_count > 0) {
      events.push({
        id: `highlight-${post.id}`,
        kind: "highlight_post",
        date: post.created_at,
        labelKey: "timeline.highlightPost",
        meta: {
          postTitle: post.title,
          postId: post.id,
          likeCount: post.like_count,
        },
      });
    }
  }

  // Sort all milestones chronologically (oldest first)
  return events.sort(
    (a, b) => new Date(a.date).getTime() - new Date(b.date).getTime()
  );
}

export function useArtistTimeline(userId: string): ArtistTimelineResult {
  const [milestones, setMilestones] = useState<TimelineMilestone[]>([]);
  const [profile, setProfile] = useState<UserProfileView | null>(null);
  const [posts, setPosts] = useState<PostView[]>([]);
  const [ranking, setRanking] = useState<ArtistRankingResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!userId) return;
    setLoading(true);
    setError(null);
    try {
      const p = await fetchUserProfile(userId);
      setProfile(p);

      // Fetch posts (artist's own) and sponsorships in parallel
      const [exploreData, sponsorData] = await Promise.all([
        fetchExplore({ limit: 50 }).then((all) =>
          all.filter((post) => post.author.id === userId)
        ),
        p.role === "artist" ? fetchReceivedSponsorships(userId, 50) : Promise.resolve([]),
      ]);

      setPosts(exploreData);

      // Ranking is non-blocking — badge only
      let rankData: ArtistRankingResponse | null = null;
      try {
        if (p.role === "artist") {
          rankData = await fetchArtistRanking(userId);
        }
      } catch {
        // non-critical
      }
      setRanking(rankData);

      const composed = composeMilestones(p, exploreData, sponsorData, rankData);
      setMilestones(composed);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load timeline");
    } finally {
      setLoading(false);
    }
  }, [userId]);

  useEffect(() => {
    void load();
  }, [load]);

  return { milestones, profile, posts, ranking, loading, error };
}
