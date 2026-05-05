/**
 * OnboardingStep3Discover — Step 3 of the growth-funnel wizard.
 *
 * Shows a preview of the Explore page with placeholder thumbnail cards and
 * invites the user to start discovering artwork.
 *
 * Analytics:
 *   - captureEvent onboarding_step { step: 3 } on mount
 *   - captureEvent onboarding_skip { step: 3 } on skip
 *   - captureEvent onboarding_complete on "Start Exploring" CTA
 */

"use client";

import { useCallback, useEffect } from "react";
import Link from "next/link";
import { useI18n } from "@/i18n";
import { captureEvent } from "@/lib/analytics/capture";

/** Metadata for a single explore preview tile (purely decorative). */
interface PreviewTile {
  id: string;
  gradient: string;
  label: string;
}

const PREVIEW_TILES: PreviewTile[] = [
  { id: "a", gradient: "from-violet-400 to-purple-600", label: "Painting" },
  { id: "b", gradient: "from-amber-400 to-orange-500", label: "Illustration" },
  { id: "c", gradient: "from-teal-400 to-cyan-600", label: "Photography" },
  { id: "d", gradient: "from-rose-400 to-pink-600", label: "Digital Art" },
  { id: "e", gradient: "from-blue-400 to-indigo-600", label: "Sculpture" },
  { id: "f", gradient: "from-green-400 to-emerald-600", label: "Mixed Media" },
];

interface OnboardingStep3DiscoverProps {
  onComplete: () => void;
  onSkip: () => void;
  followedCount: number;
  sponsored: boolean;
}

export function OnboardingStep3Discover({
  onComplete,
  onSkip,
  followedCount,
  sponsored,
}: OnboardingStep3DiscoverProps) {
  const { t } = useI18n();

  // Fire step event on mount
  useEffect(() => {
    captureEvent({ type: "onboarding_step", step: 3 });
  }, []);

  const handleComplete = useCallback(() => {
    captureEvent({
      type: "onboarding_complete",
      followed: followedCount,
      sponsored,
    });
    onComplete();
  }, [followedCount, sponsored, onComplete]);

  const handleSkip = useCallback(() => {
    captureEvent({ type: "onboarding_skip", step: 3 });
    onSkip();
  }, [onSkip]);

  return (
    <div className="space-y-5">
      <div className="text-center space-y-1">
        <p className="text-3xl" aria-hidden="true">✨</p>
        <h2 className="text-xl font-bold text-text-primary">
          {t("onboarding.step3.title")}
        </h2>
        <p className="text-sm text-text-secondary">
          {t("onboarding.step3.subtitle")}
        </p>
      </div>

      {/* Explore preview grid */}
      <div
        className="grid grid-cols-3 gap-2"
        aria-label={t("onboarding.step3.previewAriaLabel")}
        aria-hidden="true"
      >
        {PREVIEW_TILES.map((tile) => (
          <div
            key={tile.id}
            className={`aspect-square rounded-xl bg-gradient-to-br ${tile.gradient} flex items-end p-2 overflow-hidden`}
          >
            <span className="text-white/80 text-[10px] font-medium leading-tight truncate">
              {tile.label}
            </span>
          </div>
        ))}
      </div>

      {/* Summary of what was achieved */}
      <div className="card bg-surface-hover/20 p-4 space-y-2 text-sm">
        <p className="font-semibold text-text-primary text-xs uppercase tracking-wide">
          {t("onboarding.step3.summaryTitle")}
        </p>
        <div className="flex items-center gap-2 text-text-secondary">
          <span className="text-primary" aria-hidden="true">✓</span>
          <span>
            {followedCount > 0
              ? t("onboarding.step3.summaryFollowed").replace(
                  "{{count}}",
                  String(followedCount)
                )
              : t("onboarding.step3.summaryFollowedNone")}
          </span>
        </div>
        <div className="flex items-center gap-2 text-text-secondary">
          <span className={sponsored ? "text-primary" : "text-text-muted"} aria-hidden="true">
            {sponsored ? "✓" : "○"}
          </span>
          <span>
            {sponsored
              ? t("onboarding.step3.summarySponsoredDone")
              : t("onboarding.step3.summarySponsoredSkip")}
          </span>
        </div>
      </div>

      {/* Actions */}
      <div className="flex flex-col gap-2 pt-1">
        <Link
          href="/explore"
          className="btn-primary w-full text-center"
          onClick={handleComplete}
        >
          {t("onboarding.step3.cta")}
        </Link>
        <button
          type="button"
          onClick={handleSkip}
          className="text-sm text-text-muted hover:text-text-primary transition-colors py-1"
        >
          {t("onboarding.common.goHome")}
        </button>
      </div>
    </div>
  );
}
