/**
 * analytics/capture.ts — A-1 Analytics Foundation
 *
 * Thin wrapper around posthog-js.
 *
 * Mock mode: NEXT_PUBLIC_POSTHOG_KEY 미설정 시 PostHog 비활성.
 *   - NODE_ENV=development → console.log fallback (dev/CI 친화)
 *   - NODE_ENV=production  → silent (no-op)
 *
 * GDPR: posthog.init의 opt_out_capturing_by_default: true 가 기본.
 * CookieConsentBanner에서 opt_in_capturing() / opt_out_capturing() 호출.
 *
 * PII guard: email/phone은 traits로만 허용; event properties에 직접 포함 금지.
 */

import posthog from "posthog-js";
import type { AnalyticsEvent } from "./events";

// ─── Internal: is PostHog active? ─────────────────────────────────────────

function isActive(): boolean {
  if (typeof window === "undefined") return false;
  return Boolean(process.env.NEXT_PUBLIC_POSTHOG_KEY);
}

// ─── Public API ───────────────────────────────────────────────────────────

/**
 * Capture an analytics event.
 * The `event` param provides the discriminated type; additional ad-hoc
 * properties may be passed via `extra` (must not contain PII).
 */
export function captureEvent(
  event: AnalyticsEvent,
  extra?: Record<string, unknown>
): void {
  if (typeof window === "undefined") return;

  if (!isActive()) {
    if (process.env.NODE_ENV === "development") {
      // eslint-disable-next-line no-console
      console.log("[Analytics]", event.type, { ...event, ...extra });
    }
    return;
  }

  const { type, ...props } = event;
  posthog.capture(type, { ...props, ...extra });
}

/**
 * Identify the current user.
 * Call after login / session restore.
 * traits MUST NOT include raw PII beyond email — PostHog stores them server-side.
 */
export function identifyUser(
  userId: string,
  traits?: {
    email?: string;
    language?: string;
    role?: string;
    [key: string]: unknown;
  }
): void {
  if (typeof window === "undefined") return;
  if (!isActive()) {
    if (process.env.NODE_ENV === "development") {
      // eslint-disable-next-line no-console
      console.log("[Analytics] identify", userId, traits);
    }
    return;
  }
  posthog.identify(userId, traits);
}

/**
 * Reset the PostHog identity.
 * Call on logout — dissociates future events from the current user.
 */
export function resetIdentity(): void {
  if (typeof window === "undefined") return;
  if (!isActive()) {
    if (process.env.NODE_ENV === "development") {
      // eslint-disable-next-line no-console
      console.log("[Analytics] reset");
    }
    return;
  }
  posthog.reset();
}
