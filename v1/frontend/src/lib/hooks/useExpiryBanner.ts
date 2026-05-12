"use client";

/**
 * useExpiryBanner — A-8 retention-loop-enhancement
 *
 * Determines whether to show the subscription expiry banner for a given subscription.
 * 7-day dismiss cooldown stored in localStorage per subscription id.
 * SSR-safe: all localStorage access is guarded by typeof window check.
 *
 * Mirrors useWinbackBanner cooldown pattern (B-5).
 */

import { useState, useEffect, useCallback, useMemo } from "react";

const COOLDOWN_MS = 7 * 24 * 60 * 60 * 1000; // 7 days
const STORAGE_KEY_PREFIX = "domo_expiry_dismiss_";

function getDismissKey(subscriptionId: string): string {
  return `${STORAGE_KEY_PREFIX}${subscriptionId}`;
}

function isDismissedLocally(subscriptionId: string): boolean {
  if (typeof window === "undefined") return false;
  try {
    const raw = localStorage.getItem(getDismissKey(subscriptionId));
    if (!raw) return false;
    const timestamp = parseInt(raw, 10);
    if (isNaN(timestamp)) return false;
    return Date.now() - timestamp < COOLDOWN_MS;
  } catch {
    return false;
  }
}

function setDismissedLocally(subscriptionId: string): void {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(getDismissKey(subscriptionId), String(Date.now()));
  } catch {
    // ignore storage errors
  }
}

export type ExpirySubscription = {
  id: string;
  artist_id: string;
  current_period_end: string | null;
};

export type UseExpiryBannerOptions = {
  subscriptions: ExpirySubscription[];
  /** How many days ahead to consider "expiring soon" (default: 7) */
  windowDays?: number;
};

export type ExpiryBannerEntry = {
  subscriptionId: string;
  artistId: string;
  daysLeft: number;
};

export type UseExpiryBannerReturn = {
  /** Subscriptions that should display an expiry banner (not dismissed, within window) */
  expiring: ExpiryBannerEntry[];
  /** Dismiss the banner for a specific subscription — stores 7d cooldown */
  dismiss: (subscriptionId: string) => void;
};

export function useExpiryBanner({
  subscriptions,
  windowDays = 7,
}: UseExpiryBannerOptions): UseExpiryBannerReturn {
  // dismissed set is hydrated from localStorage after mount (SSR-safe)
  const [dismissedIds, setDismissedIds] = useState<Set<string>>(new Set());

  // Stable dependency key — caller가 매 렌더마다 새 array를 전달해도
  // 실제 subscription id 집합이 같으면 effect 재실행 방지 (무한 루프 차단)
  const idsKey = useMemo(
    () => subscriptions.map((s) => s.id).join("|"),
    [subscriptions],
  );

  useEffect(() => {
    // Hydrate on client
    const dismissed = new Set<string>();
    for (const sub of subscriptions) {
      if (isDismissedLocally(sub.id)) {
        dismissed.add(sub.id);
      }
    }
    setDismissedIds((prev) => {
      // 동등 비교: 같은 set이면 setState skip — 무한 루프 차단
      if (
        prev.size === dismissed.size &&
        [...prev].every((id) => dismissed.has(id))
      ) {
        return prev;
      }
      return dismissed;
    });
    // subscriptions reference 대신 idsKey 사용 (eslint disable는 의도된 것)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [idsKey]);

  const dismiss = useCallback((subscriptionId: string) => {
    setDismissedLocally(subscriptionId);
    setDismissedIds((prev) => {
      const next = new Set(prev);
      next.add(subscriptionId);
      return next;
    });
  }, []);

  const now = Date.now();
  const windowMs = windowDays * 24 * 60 * 60 * 1000;

  const expiring: ExpiryBannerEntry[] = subscriptions
    .filter((sub) => {
      if (!sub.current_period_end) return false;
      if (dismissedIds.has(sub.id)) return false;
      const endMs = new Date(sub.current_period_end).getTime();
      const diff = endMs - now;
      return diff > 0 && diff <= windowMs;
    })
    .map((sub) => {
      const endMs = new Date(sub.current_period_end!).getTime();
      const daysLeft = Math.ceil((endMs - now) / (24 * 60 * 60 * 1000));
      return {
        subscriptionId: sub.id,
        artistId: sub.artist_id,
        daysLeft,
      };
    });

  return { expiring, dismiss };
}
