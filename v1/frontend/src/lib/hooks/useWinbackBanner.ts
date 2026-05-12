"use client";

/**
 * useWinbackBanner — B-5 patronage-retention-ux
 *
 * Determines whether to show the win-back banner on an artist profile page.
 * Logic:
 *   - hasPastSponsorship: user previously sponsored or subscribed to this artist
 *   - isCurrentlyActive: user has an active/past_due subscription to this artist
 *   - isDismissed: banner was dismissed within the 7-day cooldown window
 *
 * 7-day cooldown is stored in localStorage per artistId.
 * SSR-safe: all localStorage access is guarded by typeof window check.
 */

import { useState, useEffect, useCallback } from "react";

const COOLDOWN_MS = 7 * 24 * 60 * 60 * 1000; // 7 days
const STORAGE_KEY_PREFIX = "domo_winback_dismiss_";

function getDismissKey(artistId: string): string {
  return `${STORAGE_KEY_PREFIX}${artistId}`;
}

function isDismissedLocally(artistId: string): boolean {
  if (typeof window === "undefined") return false;
  try {
    const raw = localStorage.getItem(getDismissKey(artistId));
    if (!raw) return false;
    const timestamp = parseInt(raw, 10);
    if (isNaN(timestamp)) return false;
    return Date.now() - timestamp < COOLDOWN_MS;
  } catch {
    return false;
  }
}

function setDismissedLocally(artistId: string): void {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(getDismissKey(artistId), String(Date.now()));
  } catch {
    // ignore storage errors
  }
}

export type UseWinbackBannerOptions = {
  artistId: string;
  /** Whether the current user has any past sponsorship or subscription with this artist */
  hasPastSponsorship: boolean;
  /** Whether the user currently has an active subscription to this artist */
  isCurrentlyActive: boolean;
};

export type UseWinbackBannerReturn = {
  /** Whether the banner should be displayed */
  shouldShow: boolean;
  /** Dismiss the banner — stores timestamp in localStorage, 7d cooldown */
  dismiss: () => void;
};

export function useWinbackBanner({
  artistId,
  hasPastSponsorship,
  isCurrentlyActive,
}: UseWinbackBannerOptions): UseWinbackBannerReturn {
  // Initialise dismissed state on client only (SSR returns false)
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    // Hydrate dismissed state from localStorage after mount
    setDismissed(isDismissedLocally(artistId));
  }, [artistId]);

  const dismiss = useCallback(() => {
    setDismissedLocally(artistId);
    setDismissed(true);
  }, [artistId]);

  // Show banner when:
  //   1. User has a past sponsorship/subscription with this artist
  //   2. User does NOT currently have an active subscription
  //   3. Banner has not been dismissed within the 7-day cooldown
  const shouldShow = hasPastSponsorship && !isCurrentlyActive && !dismissed;

  return { shouldShow, dismiss };
}
