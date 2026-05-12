import "@testing-library/jest-dom";

// PostHog mock — prevents real SDK initialization during tests.
// capture.ts and featureFlags.ts import posthog-js; this mock satisfies those imports
// while keeping all PostHog calls as silent no-ops.
jest.mock("posthog-js", () => ({
  default: {
    init: jest.fn(),
    capture: jest.fn(),
    identify: jest.fn(),
    reset: jest.fn(),
    isFeatureEnabled: jest.fn(() => false),
    getFeatureFlag: jest.fn(() => undefined),
    opt_in_capturing: jest.fn(),
    opt_out_capturing: jest.fn(),
  },
}));
