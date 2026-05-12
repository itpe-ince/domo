/**
 * featureFlags.test.ts — A-1 Analytics Foundation
 *
 * Tests for lib/analytics/featureFlags.ts
 * Mock mode (NEXT_PUBLIC_POSTHOG_KEY unset) — all flags return defaults.
 */

delete (process.env as Record<string, string | undefined>).NEXT_PUBLIC_POSTHOG_KEY;

describe("isFeatureEnabled (mock mode)", () => {
  afterEach(() => {
    jest.resetModules();
  });

  it("returns defaultValue=false when PostHog is inactive", async () => {
    const { isFeatureEnabled } = await import("@/lib/analytics/featureFlags");
    expect(isFeatureEnabled("new-feed-algorithm")).toBe(false);
  });

  it("returns provided defaultValue when PostHog is inactive", async () => {
    const { isFeatureEnabled } = await import("@/lib/analytics/featureFlags");
    expect(isFeatureEnabled("some-flag", true)).toBe(true);
  });
});

describe("getFeatureFlag (mock mode)", () => {
  afterEach(() => {
    jest.resetModules();
  });

  it("returns undefined when PostHog is inactive", async () => {
    const { getFeatureFlag } = await import("@/lib/analytics/featureFlags");
    expect(getFeatureFlag("feed-variant")).toBeUndefined();
  });
});
