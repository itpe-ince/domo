"use client";

/**
 * FeedAlgorithmToggle — A-3 feed-algorithm-v1
 *
 * Radio toggle for switching between chronological (default) and
 * personalized (v1) feed algorithms.
 *
 * Only shown when the user is authenticated and the PostHog feature flag
 * 'feed-algorithm-v2' is enabled (or when showAlways=true for dev/testing).
 *
 * Emits a feed_algorithm_view PostHog event whenever the selected algo changes.
 */

import { useI18n } from "@/i18n";
import { captureEvent } from "@/lib/analytics/capture";
import type { FeedAlgo } from "@/lib/api";

type Props = {
  value: FeedAlgo;
  onChange: (algo: FeedAlgo) => void;
};

export function FeedAlgorithmToggle({ value, onChange }: Props) {
  const { t } = useI18n();

  function handleChange(algo: FeedAlgo) {
    if (algo === value) return;
    onChange(algo);
    captureEvent({ type: "feed_algorithm_view", algo });
  }

  return (
    <div
      role="radiogroup"
      aria-label={t("feed.algoToggleLabel")}
      className="flex gap-1 text-xs"
    >
      <button
        role="radio"
        aria-checked={value === "default"}
        onClick={() => handleChange("default")}
        className={`px-3 py-1 rounded-full border transition-colors ${
          value === "default"
            ? "bg-primary text-white border-primary"
            : "border-border text-text-muted hover:border-primary hover:text-primary"
        }`}
      >
        {t("feed.algoDefault")}
      </button>
      <button
        role="radio"
        aria-checked={value === "v1"}
        onClick={() => handleChange("v1")}
        className={`px-3 py-1 rounded-full border transition-colors ${
          value === "v1"
            ? "bg-primary text-white border-primary"
            : "border-border text-text-muted hover:border-primary hover:text-primary"
        }`}
      >
        {t("feed.algoPersonalized")}
      </button>
    </div>
  );
}
