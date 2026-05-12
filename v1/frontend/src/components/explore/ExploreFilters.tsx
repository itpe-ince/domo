"use client";

/**
 * ExploreFilters — A-4 Explore Revamp
 *
 * Renders context-appropriate filter controls:
 * - region tab → Region dropdown
 * - genre tab  → Genre dropdown
 * - pricing tab → no secondary filter (handled by backend)
 */

import { useI18n } from "@/i18n";
import type { ExploreTab, ExploreFilters } from "@/lib/hooks/useExploreState";

interface ExploreFiltersProps {
  tab: ExploreTab;
  filters: ExploreFilters;
  onRegionChange: (v: string) => void;
  onGenreChange: (v: string) => void;
}

const REGIONS = [
  { value: "", labelKey: "explore.filters.regionAll" },
  { value: "SEA", labelKey: "explore.filters.regionSEA" },
  { value: "LATAM", labelKey: "explore.filters.regionLATAM" },
  { value: "EEU", labelKey: "explore.filters.regionEEU" },
  { value: "EAS", labelKey: "explore.filters.regionEAS" },
  { value: "NAM", labelKey: "explore.filters.regionNAM" },
  { value: "WEU", labelKey: "explore.filters.regionWEU" },
];

const GENRES = [
  { value: "", labelKey: "explore.filters.genreAll" },
  { value: "watercolor", labelKey: "explore.filters.genreWatercolor" },
  { value: "oil", labelKey: "explore.filters.genreOil" },
  { value: "digital", labelKey: "explore.filters.genreDigital" },
  { value: "sculpture", labelKey: "explore.filters.genreSculpture" },
  { value: "mixed", labelKey: "explore.filters.genreMixed" },
];

export function ExploreFilters({
  tab,
  filters,
  onRegionChange,
  onGenreChange,
}: ExploreFiltersProps) {
  const { t } = useI18n();

  if (tab === "region") {
    return (
      <div className="flex items-center gap-2">
        <label
          htmlFor="explore-region-select"
          className="text-xs text-text-muted whitespace-nowrap"
        >
          {t("explore.filters.regionLabel")}
        </label>
        <select
          id="explore-region-select"
          value={filters.region}
          onChange={(e) => onRegionChange(e.target.value)}
          className="text-sm bg-surface border border-border rounded-lg px-3 py-1.5 text-text-primary focus:outline-none focus:ring-1 focus:ring-primary"
        >
          {REGIONS.map(({ value, labelKey }) => (
            <option key={value} value={value}>
              {t(labelKey)}
            </option>
          ))}
        </select>
      </div>
    );
  }

  if (tab === "genre") {
    return (
      <div className="flex items-center gap-2">
        <label
          htmlFor="explore-genre-select"
          className="text-xs text-text-muted whitespace-nowrap"
        >
          {t("explore.filters.genreLabel")}
        </label>
        <select
          id="explore-genre-select"
          value={filters.genre}
          onChange={(e) => onGenreChange(e.target.value)}
          className="text-sm bg-surface border border-border rounded-lg px-3 py-1.5 text-text-primary focus:outline-none focus:ring-1 focus:ring-primary"
        >
          {GENRES.map(({ value, labelKey }) => (
            <option key={value} value={value}>
              {t(labelKey)}
            </option>
          ))}
        </select>
      </div>
    );
  }

  if (tab === "pricing") {
    return (
      <p className="text-xs text-text-muted">
        {t("explore.filters.pricingHint")}
      </p>
    );
  }

  return null;
}
