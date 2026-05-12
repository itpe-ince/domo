"use client";

// auction-promotion-suite PDCA #11 — F-1 AuctionCountdown widget
// OQ-7=C: D-1h 이전 60s interval / D-1h 이내 1s interval (adaptive)
// R-FE-2: useEffect cleanup prevents setInterval leak
// R-FE-7: isUnder1h boundary crossing triggers effect re-run via deps array
// SSR-safe: interval only runs client-side inside useEffect

import { useEffect, useRef, useState } from "react";
import { useI18n } from "@/i18n";

interface Remaining {
  totalSeconds: number;
  days: number;
  hours: number;
  minutes: number;
  seconds: number;
}

function calcRemaining(endAt: string): Remaining | null {
  const ms = new Date(endAt).getTime() - Date.now();
  if (ms <= 0) return null;
  const totalSeconds = Math.floor(ms / 1000);
  return {
    totalSeconds,
    days: Math.floor(totalSeconds / 86400),
    hours: Math.floor((totalSeconds % 86400) / 3600),
    minutes: Math.floor((totalSeconds % 3600) / 60),
    seconds: totalSeconds % 60,
  };
}

function pad(n: number) {
  return String(n).padStart(2, "0");
}

interface AuctionCountdownProps {
  /** ISO8601 UTC end time from server */
  endAt: string;
  /** Compact mode for feed cards */
  compact?: boolean;
  /** Called once when the countdown reaches zero */
  onEnded?: () => void;
}

export function AuctionCountdown({
  endAt,
  compact = false,
  onEnded,
}: AuctionCountdownProps) {
  const { t } = useI18n();

  // Initial state computed synchronously from endAt (SSR-safe — no Date.now()
  // on server). On the server this yields a number; hydration will match
  // because the same endAt is used. Small drift (<60s) is acceptable (R-FE-1).
  const [remaining, setRemaining] = useState<Remaining | null>(() =>
    calcRemaining(endAt)
  );
  const [ended, setEnded] = useState(false);

  // Stable ref for onEnded to avoid restarting the interval on every render
  const onEndedRef = useRef(onEnded);
  useEffect(() => {
    onEndedRef.current = onEnded;
  }, [onEnded]);

  const isUnder1h = remaining !== null && remaining.totalSeconds <= 3600;

  // prefers-reduced-motion: downgrade 1s to 60s (a11y)
  const prefersReducedMotion =
    typeof window !== "undefined"
      ? window.matchMedia("(prefers-reduced-motion: reduce)").matches
      : false;

  useEffect(() => {
    // OQ-7=C adaptive interval
    const intervalMs =
      isUnder1h && !prefersReducedMotion ? 1_000 : 60_000;

    const id = setInterval(() => {
      const r = calcRemaining(endAt);
      if (!r) {
        clearInterval(id);
        setEnded(true);
        setRemaining(null);
        onEndedRef.current?.();
        return;
      }
      setRemaining(r);
    }, intervalMs);

    return () => clearInterval(id); // R-FE-2 cleanup
  }, [endAt, isUnder1h, prefersReducedMotion]);

  if (ended || !remaining) {
    return (
      <span
        role="timer"
        aria-live="polite"
        aria-label={t("auction.ended")}
        className="text-xs font-mono text-text-muted"
      >
        {t("auction.ended")}
      </span>
    );
  }

  // Format the display string
  let display: string;
  if (isUnder1h) {
    // Last hour: HH:MM:SS
    display = `${pad(remaining.hours)}:${pad(remaining.minutes)}:${pad(remaining.seconds)}`;
  } else if (compact) {
    // Compact (PostCard): D-Xd Yh or Xh Ym
    if (remaining.days > 0) {
      display = t("auction.countdown.compact.day", {
        days: remaining.days,
        hours: remaining.hours,
      });
    } else {
      display = t("auction.countdown.compact.hour", {
        hours: remaining.hours,
        minutes: remaining.minutes,
      });
    }
  } else {
    // Full (post detail): X일 Y시간 or X시간 Y분
    if (remaining.days > 0) {
      display = t("auction.countdown.full.day_hour", {
        days: remaining.days,
        hours: remaining.hours,
      });
    } else {
      display = t("auction.countdown.full.hour_minute", {
        hours: remaining.hours,
        minutes: remaining.minutes,
      });
    }
  }

  if (compact) {
    return (
      <span
        role="timer"
        aria-live="polite"
        aria-label={`${t("auction.countdown.label")}: ${display}`}
        className="text-xs font-mono text-amber-400 font-semibold"
      >
        {display}
      </span>
    );
  }

  return (
    <div
      role="timer"
      aria-live="polite"
      aria-label={`${t("auction.countdown.label")}: ${display}`}
      className="flex items-center gap-2"
    >
      <span className="text-xs text-text-muted">{t("auction.countdown.label")}</span>
      <span className="font-mono text-sm font-semibold text-amber-400">
        {display}
      </span>
    </div>
  );
}
