/**
 * analytics/featureFlags.ts — A-1 Analytics Foundation
 *
 * PostHog feature flag helpers.
 *
 * Used by A-3 feed-algorithm-v1 A/B test infra and future PostHog flags.
 * Falls back gracefully when PostHog is not active (mock mode / SSR).
 *
 * Usage:
 *   if (isFeatureEnabled("new-feed-algorithm")) { ... }
 *   const variant = getFeatureFlag("feed-variant"); // "control" | "test" | undefined
 */

import posthog from "posthog-js";

function isActive(): boolean {
  if (typeof window === "undefined") return false;
  return Boolean(process.env.NEXT_PUBLIC_POSTHOG_KEY);
}

/**
 * Check if a boolean feature flag is enabled.
 * @param flagKey PostHog flag key
 * @param defaultValue Fallback when PostHog is unavailable (dev/SSR/mock)
 */
export function isFeatureEnabled(flagKey: string, defaultValue = false): boolean {
  if (!isActive()) return defaultValue;
  return posthog.isFeatureEnabled(flagKey) ?? defaultValue;
}

/**
 * Get the value of a multivariate feature flag.
 * Returns `undefined` when PostHog is unavailable or the flag is unset.
 * @param flagKey PostHog flag key
 */
export function getFeatureFlag(flagKey: string): string | boolean | undefined {
  if (!isActive()) return undefined;
  return posthog.getFeatureFlag(flagKey);
}
