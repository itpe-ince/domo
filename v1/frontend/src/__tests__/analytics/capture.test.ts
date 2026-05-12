/**
 * capture.test.ts — A-1 Analytics Foundation
 *
 * Tests for lib/analytics/capture.ts
 *
 * Runner: Jest (not yet configured — requires jest + ts-jest + jest-environment-jsdom)
 * To run: npm install -D jest ts-jest jest-environment-jsdom @types/jest
 *         then: npx jest src/__tests__/analytics/capture.test.ts
 *
 * Note: These tests use the mock mode path (NEXT_PUBLIC_POSTHOG_KEY unset).
 * PostHog itself is not imported here — tested via spy on console.log in dev mode.
 */

// Ensure mock mode (no PostHog key)
delete (process.env as Record<string, string | undefined>).NEXT_PUBLIC_POSTHOG_KEY;

// jsdom provides window
const originalWindow = global.window;

describe("captureEvent (mock mode)", () => {
  let consoleSpy: jest.SpyInstance;

  beforeEach(() => {
    // Set development environment for console.log fallback
    process.env.NODE_ENV = "development";
    consoleSpy = jest.spyOn(console, "log").mockImplementation(() => {});
    // Ensure window is defined (jsdom)
    Object.defineProperty(global, "window", {
      value: originalWindow,
      writable: true,
    });
  });

  afterEach(() => {
    consoleSpy.mockRestore();
    jest.resetModules();
  });

  it("logs event to console in development mock mode", async () => {
    // Re-import after env setup
    const { captureEvent } = await import("@/lib/analytics/capture");
    captureEvent({ type: "login", method: "google" });
    expect(consoleSpy).toHaveBeenCalledWith(
      "[Analytics]",
      "login",
      expect.objectContaining({ type: "login", method: "google" })
    );
  });

  it("does not throw when window is undefined (SSR)", async () => {
    // Simulate SSR — no window
    Object.defineProperty(global, "window", {
      value: undefined,
      writable: true,
    });
    const { captureEvent } = await import("@/lib/analytics/capture");
    expect(() => captureEvent({ type: "logout" })).not.toThrow();
  });

  it("does not log in production mock mode", async () => {
    process.env.NODE_ENV = "production";
    const { captureEvent } = await import("@/lib/analytics/capture");
    captureEvent({ type: "explore_view", tab: "all" });
    expect(consoleSpy).not.toHaveBeenCalled();
  });
});

describe("identifyUser (mock mode)", () => {
  let consoleSpy: jest.SpyInstance;

  beforeEach(() => {
    process.env.NODE_ENV = "development";
    delete (process.env as Record<string, string | undefined>).NEXT_PUBLIC_POSTHOG_KEY;
    consoleSpy = jest.spyOn(console, "log").mockImplementation(() => {});
    Object.defineProperty(global, "window", {
      value: originalWindow,
      writable: true,
    });
  });

  afterEach(() => {
    consoleSpy.mockRestore();
    jest.resetModules();
  });

  it("logs identify call in development mock mode", async () => {
    const { identifyUser } = await import("@/lib/analytics/capture");
    identifyUser("user-123", { role: "artist" });
    expect(consoleSpy).toHaveBeenCalledWith(
      "[Analytics] identify",
      "user-123",
      expect.objectContaining({ role: "artist" })
    );
  });

  it("logs reset call in development mock mode", async () => {
    const { resetIdentity } = await import("@/lib/analytics/capture");
    resetIdentity();
    expect(consoleSpy).toHaveBeenCalledWith("[Analytics] reset");
  });
});
