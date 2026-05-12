"use client";

/**
 * ExploreTabs — A-4 Explore Revamp
 *
 * 5 tabs: Trending | New | Region | Genre | Pricing
 * Renders as a sticky horizontally-scrollable pill bar.
 */

import { useI18n } from "@/i18n";
import type { ExploreTab } from "@/lib/hooks/useExploreState";

interface ExploreTabsProps {
  active: ExploreTab;
  onChange: (tab: ExploreTab) => void;
}

const TABS: { key: ExploreTab; labelKey: string }[] = [
  { key: "trending", labelKey: "explore.tabs.trending" },
  { key: "new", labelKey: "explore.tabs.new" },
  { key: "region", labelKey: "explore.tabs.region" },
  { key: "genre", labelKey: "explore.tabs.genre" },
  { key: "pricing", labelKey: "explore.tabs.pricing" },
];

export function ExploreTabs({ active, onChange }: ExploreTabsProps) {
  const { t } = useI18n();

  return (
    <nav
      role="tablist"
      aria-label={t("explore.tabs.ariaLabel")}
      className="flex gap-2 overflow-x-auto pb-1 scrollbar-hide"
    >
      {TABS.map(({ key, labelKey }) => {
        const isActive = active === key;
        return (
          <button
            key={key}
            role="tab"
            aria-selected={isActive}
            onClick={() => onChange(key)}
            className={`px-4 py-1.5 rounded-full text-sm whitespace-nowrap font-medium transition-colors flex-shrink-0 ${
              isActive
                ? "bg-primary text-background"
                : "bg-surface text-text-secondary hover:bg-surface-hover"
            }`}
          >
            {t(labelKey)}
          </button>
        );
      })}
    </nav>
  );
}
