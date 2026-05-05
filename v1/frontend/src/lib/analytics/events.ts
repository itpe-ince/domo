/**
 * analytics/events.ts — A-1 Analytics Foundation
 *
 * Canonical TypeScript event schema for all PostHog events.
 * Each event type is a discriminated union member keyed by `type`.
 * captureEvent() in capture.ts consumes this union.
 *
 * Design: exhaustive union means adding new events without touching
 * capture.ts; TypeScript enforces correct property shapes at call sites.
 */

// ─── User lifecycle ────────────────────────────────────────────────────────

export type SignupEvent = {
  type: "signup";
  method: "email" | "google" | "kakao";
};

export type LoginEvent = {
  type: "login";
  method: "email" | "google" | "kakao" | string;
};

export type LogoutEvent = {
  type: "logout";
};

// ─── First-action funnel ───────────────────────────────────────────────────

export type FirstActionEvent = {
  type: "first_action";
  action: "post" | "follow" | "like" | "comment" | "sponsor";
};

// ─── Sponsorship funnel ───────────────────────────────────────────────────

export type SponsorStartEvent = {
  type: "sponsor_start";
  mode: "one_time" | "recurring";
  amount_cents: number;
  artist_id: string;
};

export type SponsorSuccessEvent = {
  type: "sponsor_success";
  mode: "one_time" | "recurring";
  amount_cents: number;
  artist_id: string;
};

export type SponsorCancelEvent = {
  type: "sponsor_cancel";
  reason: string;
  tier: string;
};

// ─── Discovery ───────────────────────────────────────────────────────────

export type ExploreViewEvent = {
  type: "explore_view";
  tab: string;
};

/** A-4: Fired when the daily-hero artist card is rendered in Explore. */
export type ExploreHeroViewEvent = {
  type: "explore_hero_view";
  artist_id: string;
};

/** A-4: Fired when a user clicks an artist mini-card in the ranking preview strip. */
export type ArtistIndexPreviewClickEvent = {
  type: "artist_index_preview_click";
  rank: number;
};

// ─── Storytelling Hub (A-7) ───────────────────────────────────────────────

/** A-7: Fired when /stories hub or /users/[id]/timeline is viewed. */
export type StoryViewEvent = {
  type: "story_view";
  /** Optional: set when viewing a specific artist timeline. */
  artist_id?: string;
};

/** A-7: Fired when the featured artist hero card is clicked. */
export type FeaturedArtistClickEvent = {
  type: "featured_artist_click";
  artist_id: string;
};

/** A-7: Fired when an external media coverage item is clicked. */
export type MediaCoverageClickEvent = {
  type: "media_coverage_click";
  coverage_id: string;
  coverage_type: "article" | "youtube" | "radio" | "other";
};

export type SearchEvent = {
  type: "search";
  query: string;
  results_count: number;
};

// A-5 search-enhancement — 3 new search interaction events

/** Fired when a filter or sort option is applied on the search page. */
export type SearchFilterAppliedEvent = {
  type: "search_filter_applied";
  /** e.g. "price_range", "region", "tier_only", "active", "sort", "tab" */
  filter_type: string;
};

/** Fired when a user clicks a recent search history entry. */
export type SearchHistoryClickEvent = {
  type: "search_history_click";
};

/** Fired when a user clicks a popular search suggestion. */
export type SearchPopularClickEvent = {
  type: "search_popular_click";
};

export type FeedScrollDepthEvent = {
  type: "feed_scroll_depth";
  depth_pct: number;
};

export type PostClickEvent = {
  type: "post_click";
  post_id: string;
  source: "feed" | "explore" | "search" | "profile";
};

// ─── Engagement ──────────────────────────────────────────────────────────

export type LikeEvent = {
  type: "like";
  post_id: string;
};

export type CommentEvent = {
  type: "comment";
  post_id: string;
};

export type FollowEvent = {
  type: "follow";
  artist_id: string;
};

// ─── Feed algorithm (A-3) ────────────────────────────────────────────────

/**
 * Fired when the user switches the feed algorithm toggle, or when the feed
 * page loads with a specific algorithm (controlled by PostHog feature flag
 * 'feed-algorithm-v2').
 *
 * algo: "default" = legacy chronological mix.
 *       "v1"      = A-3 personalized score-ranked feed.
 */
export type FeedAlgorithmViewEvent = {
  type: "feed_algorithm_view";
  algo: "default" | "v1";
};

// ─── Onboarding funnel (A-2) ─────────────────────────────────────────────

/** Fired when the growth-funnel onboarding wizard is first entered. */
export type OnboardingStartEvent = {
  type: "onboarding_start";
};

/** Fired on each wizard step render. step: 1 = follow, 2 = sponsor, 3 = discover. */
export type OnboardingStepEvent = {
  type: "onboarding_step";
  step: 1 | 2 | 3;
};

/** Fired when user explicitly skips a wizard step. */
export type OnboardingSkipEvent = {
  type: "onboarding_skip";
  step: number;
};

/** Fired when user completes the full wizard (reaches step 3 and continues). */
export type OnboardingCompleteEvent = {
  type: "onboarding_complete";
  /** Number of artists followed during the wizard (step 1). */
  followed: number;
  /** Whether a Blue Bird sponsorship was initiated during step 2. */
  sponsored: boolean;
};

// ─── Retention — subscription expiry (A-8) ───────────────────────────────

/** Fired when the expiry banner renders for an expiring subscription. */
export type ExpiryBannerViewEvent = {
  type: "expiry_banner_view";
  subscription_id: string;
  days_until_expiry: number;
};

/** Fired when the user clicks the "갱신하기" CTA on the expiry banner. */
export type ExpiryBannerRenewClickEvent = {
  type: "expiry_banner_renew_click";
  subscription_id: string;
};

/** Fired when the user dismisses the expiry banner. */
export type ExpiryBannerDismissEvent = {
  type: "expiry_banner_dismiss";
  subscription_id: string;
};

// ─── Retention — winback (A-8 B-5 booster) ───────────────────────────────

/** Fired when the winback banner renders on an artist profile. */
export type WinbackBannerViewEvent = {
  type: "winback_banner_view";
  artist_id: string;
  cancellation_reason?: string;
};

/** Fired when the user clicks the resubscribe CTA on the winback banner. */
export type WinbackBannerResubscribeClickEvent = {
  type: "winback_banner_resubscribe_click";
  artist_id: string;
};

// ─── Retention — winback coupon (G'-2) ───────────────────────────────────

/** Fired when the CancelSubscriptionModal shows a winback offer based on reason. */
export type WinbackCouponOfferedEvent = {
  type: "winback_coupon_offered";
  reason: string;
};

/** Fired when the user accepts the winback coupon offer (clicks the offer CTA). */
export type WinbackCouponAcceptedEvent = {
  type: "winback_coupon_accepted";
  reason: string;
  coupon_id: string;
};

/** Fired when the user declines the winback offer and proceeds with cancellation. */
export type WinbackCouponDeclinedEvent = {
  type: "winback_coupon_declined";
  reason: string;
};

// ─── Union ───────────────────────────────────────────────────────────────

export type AnalyticsEvent =
  | SignupEvent
  | LoginEvent
  | LogoutEvent
  | FirstActionEvent
  | SponsorStartEvent
  | SponsorSuccessEvent
  | SponsorCancelEvent
  | ExploreViewEvent
  | ExploreHeroViewEvent
  | ArtistIndexPreviewClickEvent
  | SearchEvent
  | FeedScrollDepthEvent
  | PostClickEvent
  | LikeEvent
  | CommentEvent
  | FollowEvent
  | FeedAlgorithmViewEvent
  | OnboardingStartEvent
  | OnboardingStepEvent
  | OnboardingSkipEvent
  | OnboardingCompleteEvent
  | FeaturedArtistClickEvent
  | MediaCoverageClickEvent
  | ExpiryBannerViewEvent
  | ExpiryBannerRenewClickEvent
  | ExpiryBannerDismissEvent
  | WinbackBannerViewEvent
  | WinbackBannerResubscribeClickEvent
  | WinbackCouponOfferedEvent
  | WinbackCouponAcceptedEvent
  | WinbackCouponDeclinedEvent
  | SearchFilterAppliedEvent
  | SearchHistoryClickEvent
  | SearchPopularClickEvent
  | StoryViewEvent;
