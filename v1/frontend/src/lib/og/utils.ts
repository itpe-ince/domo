/**
 * lib/og/utils.ts — G'-6 Dynamic OG card shared helpers
 *
 * Common layout primitives, brand tokens, and fetch utilities used by all
 * opengraph-image.tsx routes. Edge-runtime compatible (no Node.js built-ins).
 */

// ─── Brand Design Tokens ─────────────────────────────────────────────────────

export const OG_BRAND = {
  /** Primary green — Domo brand */
  primary: "#A8D76E",
  primaryDark: "#7CB83A",
  /** Surface colors */
  background: "#0E1A0A",
  surface: "#162110",
  surfaceLight: "#1F3018",
  /** Text */
  textPrimary: "#F0F7E8",
  textSecondary: "#B8CCA0",
  textMuted: "#7A9060",
  /** Accent for badges */
  gold: "#D4A843",
  silver: "#9EA9B4",
  bronze: "#C27C4A",
  /** Tier badge colors */
  tier: {
    top_10: { bg: "#D4A843", text: "#1A1000" },
    top_100: { bg: "#9EA9B4", text: "#0A0E12" },
    top_1000: { bg: "#C27C4A", text: "#1A0800" },
  },
} as const;

export const OG_SIZE = { width: 1200, height: 630 } as const;
export const OG_CONTENT_TYPE = "image/png" as const;

// ─── Tier badge label helper ──────────────────────────────────────────────────

export type TierBadge = "top_10" | "top_100" | "top_1000" | null;

export function tierLabel(tier: TierBadge): string {
  switch (tier) {
    case "top_10":
      return "TOP 10";
    case "top_100":
      return "TOP 100";
    case "top_1000":
      return "TOP 1000";
    default:
      return "";
  }
}

export function tierColors(tier: TierBadge): { bg: string; text: string } {
  if (tier && tier in OG_BRAND.tier) {
    return OG_BRAND.tier[tier];
  }
  return { bg: OG_BRAND.surface, text: OG_BRAND.textMuted };
}

// ─── Country flag helper (regional indicator Unicode) ────────────────────────

/**
 * Convert ISO 3166-1 alpha-2 country code to flag emoji.
 * e.g. "KR" → "🇰🇷", "US" → "🇺🇸"
 * Returns "" for invalid codes (edge-safe).
 */
export function countryFlag(code: string | null | undefined): string {
  if (!code || code.length !== 2) return "";
  const upper = code.toUpperCase();
  const cp1 = 0x1f1e6 + upper.charCodeAt(0) - 65;
  const cp2 = 0x1f1e6 + upper.charCodeAt(1) - 65;
  return String.fromCodePoint(cp1, cp2);
}

// ─── Domo logotype text (used when custom font not loaded) ───────────────────

export const DOMO_TAGLINE = "글로벌 신진작가 인덱스";
export const DOMO_BRAND_NAME = "Domo Lounge";

// ─── Server-side fetch helpers (edge-compatible) ─────────────────────────────

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:3710/v1";

export interface OgUserProfile {
  id: string;
  display_name: string;
  avatar_url: string | null;
  country_code: string | null;
  role: string;
  follower_count: number;
  following_count: number;
  artist_profile: {
    statement: string | null;
  } | null;
}

export interface OgArtistRanking {
  score: number;
  rank: number;
  tier_badge: TierBadge;
}

export interface OgPost {
  id: string;
  title: string | null;
  content: string | null;
  tags: string[] | null;
  author: {
    id: string;
    display_name: string;
    role: string;
  };
  media: Array<{
    id: string;
    url: string;
    thumbnail_url: string | null;
    media_type: string;
  }>;
}

export interface OgSponsorship {
  id: string;
  artist_id: string;
  bluebird_count: number;
  amount: string;
  currency: string;
  is_anonymous: boolean;
  created_at: string;
}

async function ogFetch<T>(path: string): Promise<T | null> {
  try {
    const res = await fetch(`${API_BASE}${path}`, {
      next: { revalidate: 300 }, // 5-minute cache for OG images
    });
    if (!res.ok) return null;
    const json = await res.json() as { data?: T };
    return json.data ?? null;
  } catch {
    return null;
  }
}

export async function fetchOgUserProfile(userId: string): Promise<OgUserProfile | null> {
  return ogFetch<OgUserProfile>(`/users/${userId}`);
}

export async function fetchOgArtistRanking(userId: string): Promise<OgArtistRanking | null> {
  return ogFetch<OgArtistRanking>(`/artists/${encodeURIComponent(userId)}/index`);
}

export async function fetchOgPost(postId: string): Promise<OgPost | null> {
  return ogFetch<OgPost>(`/posts/${postId}`);
}

export async function fetchOgSponsorship(sponsorshipId: string): Promise<OgSponsorship | null> {
  return ogFetch<OgSponsorship>(`/sponsorships/${sponsorshipId}`);
}

// ─── Score bar helper ─────────────────────────────────────────────────────────

/**
 * Return a 0–100 percentage for a score bar.
 * Uses log scale so mid-range artists look decent even with low scores.
 */
export function scorePercent(score: number, maxScore = 1000): number {
  if (score <= 0) return 0;
  const pct = Math.log10(score + 1) / Math.log10(maxScore + 1);
  return Math.min(Math.round(pct * 100), 100);
}
