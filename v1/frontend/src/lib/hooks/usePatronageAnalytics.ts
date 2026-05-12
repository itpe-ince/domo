"use client";

/**
 * usePatronageAnalytics — data fetching + types for B'-5 analytics dashboard.
 *
 * Fetches GET /v1/me/patronage/analytics (backend B'-5 endpoint).
 * Falls back to mock data when:
 *   - API returns 404 (endpoint not yet deployed)
 *   - NEXT_PUBLIC_POSTHOG_KEY is unset (mock mode indicator)
 *   - Network error in development
 *
 * All data types are plain objects; no PostHog SDK imported here.
 */

import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";

// ─── Data types ───────────────────────────────────────────────────────────────

export type CohortRetentionData = {
  week: string;      // "W1", "W2", …
  d1: number;        // D1 retention %
  d7: number;        // D7 retention %
  d30: number;       // D30 retention %
};

export type CouponRedemptionData = {
  issued: number;
  applied: number;
  cancel_reverted: number;
  expired: number;
};

export type NewsletterIssueStats = {
  issue: string;        // "#1", "#2", …
  sent: number;
  opened: number;
  clicked: number;
  open_rate: number;    // %
  click_rate: number;   // %
};

export type ConversionFunnelData = {
  post_click: number;
  sponsor_start: number;
  sponsor_success: number;
  active_30d: number;
};

export type DmEngagementData = {
  first_message_rate: number;    // %
  avg_response_minutes: number;  // median
  total_threads: number;
};

export type PatronageAnalytics = {
  cohort_retention: CohortRetentionData[];
  coupon_redemption: CouponRedemptionData;
  newsletter: NewsletterIssueStats[];
  conversion_funnel: ConversionFunnelData;
  dm_engagement: DmEngagementData;
  is_mock: boolean;
};

// ─── Mock data (PostHog key unset or endpoint not available) ──────────────────

const MOCK_ANALYTICS: PatronageAnalytics = {
  cohort_retention: [
    { week: "W1", d1: 72, d7: 48, d30: 22 },
    { week: "W2", d1: 68, d7: 44, d30: 20 },
    { week: "W3", d1: 70, d7: 46, d30: 21 },
    { week: "W4", d1: 65, d7: 41, d30: 18 },
    { week: "W5", d1: 71, d7: 47, d30: 23 },
    { week: "W6", d1: 67, d7: 43, d30: 19 },
  ],
  coupon_redemption: {
    issued: 120,
    applied: 72,
    cancel_reverted: 38,
    expired: 48,
  },
  newsletter: [
    { issue: "#1", sent: 800, opened: 440, clicked: 132, open_rate: 55, click_rate: 16.5 },
    { issue: "#2", sent: 820, opened: 476, clicked: 148, open_rate: 58, click_rate: 18.0 },
    { issue: "#3", sent: 810, opened: 437, clicked: 130, open_rate: 54, click_rate: 16.0 },
    { issue: "#4", sent: 850, opened: 510, clicked: 170, open_rate: 60, click_rate: 20.0 },
    { issue: "#5", sent: 870, opened: 522, clicked: 165, open_rate: 60, click_rate: 19.0 },
  ],
  conversion_funnel: {
    post_click: 2400,
    sponsor_start: 480,
    sponsor_success: 320,
    active_30d: 260,
  },
  dm_engagement: {
    first_message_rate: 34.5,
    avg_response_minutes: 42,
    total_threads: 88,
  },
  is_mock: true,
};

// ─── Hook ─────────────────────────────────────────────────────────────────────

export type UsePatronageAnalyticsResult = {
  analytics: PatronageAnalytics | null;
  loading: boolean;
  error: string | null;
  isMock: boolean;
};

/**
 * Fetches patronage analytics from GET /v1/me/patronage/analytics.
 *
 * Falls back to MOCK_ANALYTICS when:
 *   - API returns 404 (endpoint not deployed yet)
 *   - NEXT_PUBLIC_POSTHOG_KEY is not set (dev/test environment)
 *   - Fetch fails in development
 */
export function usePatronageAnalytics(): UsePatronageAnalyticsResult {
  const [analytics, setAnalytics] = useState<PatronageAnalytics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isMock, setIsMock] = useState(false);

  useEffect(() => {
    let cancelled = false;

    const posthogKey = process.env.NEXT_PUBLIC_POSTHOG_KEY;
    const isDev = process.env.NODE_ENV !== "production";

    // If PostHog key is not configured, go straight to mock mode
    if (!posthogKey) {
      if (!cancelled) {
        setAnalytics(MOCK_ANALYTICS);
        setIsMock(true);
        setLoading(false);
      }
      return;
    }

    apiFetch<PatronageAnalytics>("/me/patronage/analytics")
      .then((data) => {
        if (!cancelled) {
          setAnalytics({ ...data, is_mock: false });
          setIsMock(false);
        }
      })
      .catch((err: unknown) => {
        if (cancelled) return;

        const msg =
          err != null && typeof err === "object" && "message" in err
            ? String((err as { message: unknown }).message)
            : "Failed to load analytics";

        // Graceful fallback: use mock data for 404 (not-yet-deployed) or in dev
        const isNotFound =
          err != null &&
          typeof err === "object" &&
          "code" in err &&
          (err as { code: unknown }).code === "NOT_FOUND";

        if (isNotFound || isDev) {
          setAnalytics(MOCK_ANALYTICS);
          setIsMock(true);
          setError(null);
        } else {
          setError(msg);
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  return { analytics, loading, error, isMock };
}
