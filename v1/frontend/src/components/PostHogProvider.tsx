"use client";

/**
 * PostHogProvider.tsx — A-1 Analytics Foundation
 *
 * Initialises posthog-js once on client mount and wraps children in the
 * PostHog React context provider.
 *
 * Design decisions:
 * - `opt_out_capturing_by_default: true` — GDPR: no data collected until
 *   user accepts analytics in CookieConsentBanner (posthog.opt_in_capturing()).
 * - `capture_pageview: false` — manual pageview via usePageView hook (not yet
 *   implemented; deferred to A-2). Prevents double-counting in Next.js SPA.
 * - `autocapture: false` — explicit events only (captureEvent calls).
 * - Mock mode: NEXT_PUBLIC_POSTHOG_KEY 미설정 시 PostHog 완전 비활성.
 */

import { useEffect } from "react";
import posthog from "posthog-js";
import { PostHogProvider as PHProvider } from "posthog-js/react";
import { getStoredConsent } from "@/components/CookieConsent";

const POSTHOG_KEY = process.env.NEXT_PUBLIC_POSTHOG_KEY;
const POSTHOG_HOST =
  process.env.NEXT_PUBLIC_POSTHOG_HOST || "https://us.i.posthog.com";

let _initialized = false;

function initPostHog() {
  if (typeof window === "undefined") return;
  if (!POSTHOG_KEY) return;
  if (_initialized) return;

  posthog.init(POSTHOG_KEY, {
    api_host: POSTHOG_HOST,
    // GDPR: no capture until user opts in via CookieConsentBanner
    opt_out_capturing_by_default: true,
    // Manual pageview control (A-2 will add usePageView)
    capture_pageview: false,
    capture_pageleave: true,
    // Explicit events only — no DOM autocapture
    autocapture: false,
    session_recording: {
      recordCrossOriginIframes: false,
    },
    // Do not store PostHog cookie before consent
    persistence: "localStorage",
    loaded: (ph) => {
      // Restore consent from CookieConsent (set in previous session)
      const stored = getStoredConsent();
      if (stored?.level === "all") {
        ph.opt_in_capturing();
      }
    },
  });

  _initialized = true;
}

export function PostHogClientProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  useEffect(() => {
    initPostHog();
  }, []);

  if (!POSTHOG_KEY) {
    // Mock mode: render children without PostHog context
    return <>{children}</>;
  }

  return <PHProvider client={posthog}>{children}</PHProvider>;
}
