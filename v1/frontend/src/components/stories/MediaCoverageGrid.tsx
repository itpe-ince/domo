"use client";

/**
 * MediaCoverageGrid — A-7 Storytelling Hub (C-4 booster)
 *
 * External media exposure grid (articles, YouTube, radio links).
 * C-4: fetches real data from /v1/media-coverage/featured?locale=&limit=3
 * Graceful degrade: shows nothing (no placeholder) when DB has 0 featured entries.
 * Signature is backward-compatible — `items` prop override still works.
 */

import { useEffect, useState } from "react";
import { useI18n } from "@/i18n";
import { captureEvent } from "@/lib/analytics/capture";
import { fetchFeaturedMediaCoverage } from "@/lib/api";
import type { MediaCoverageOut } from "@/lib/api";
import { getStoredLocale, LOCALE_CHANGED_EVENT, type SupportedLocale } from "@/components/LocaleSwitcher";

// Re-exported for backward compatibility with any callers
export type MediaCoverageItem = {
  id: string;
  type: "article" | "youtube" | "radio" | "podcast" | "tv" | "other";
  title: string;
  source: string;
  url: string;
  date?: string;
  imageUrl?: string;
};

const TYPE_ICONS: Record<string, string> = {
  article: "📰",
  youtube: "▶",
  radio: "📻",
  podcast: "🎙",
  tv: "📺",
  other: "🔗",
};

const TYPE_COLORS: Record<string, string> = {
  article: "bg-slate-100 border-slate-200",
  youtube: "bg-red-50 border-red-200",
  radio: "bg-purple-50 border-purple-200",
  podcast: "bg-orange-50 border-orange-200",
  tv: "bg-blue-50 border-blue-200",
  other: "bg-gray-100 border-gray-200",
};

/** Convert a DB MediaCoverageOut to the local MediaCoverageItem shape. */
function dbToItem(row: MediaCoverageOut): MediaCoverageItem {
  return {
    id: row.id,
    type: (row.coverage_type as MediaCoverageItem["type"]) ?? "other",
    title: row.title,
    source: row.source_name,
    url: row.external_url,
    date: row.published_at ? row.published_at.substring(0, 7) : undefined,
    imageUrl: row.thumbnail_url ?? undefined,
  };
}

interface MediaCoverageGridProps {
  /** Override: pass items directly instead of fetching from DB. */
  items?: MediaCoverageItem[];
  limit?: number;
}

export function MediaCoverageGrid({ items, limit = 3 }: MediaCoverageGridProps) {
  const { t } = useI18n();
  const [fetchedItems, setFetchedItems] = useState<MediaCoverageItem[]>([]);
  const [loadError, setLoadError] = useState(false);

  useEffect(() => {
    // If items are passed directly (e.g. Storybook/test), skip fetch
    if (items !== undefined) return;

    const locale = getStoredLocale() as SupportedLocale;

    async function load(loc: string) {
      try {
        const rows = await fetchFeaturedMediaCoverage(loc, limit);
        setFetchedItems(rows.map(dbToItem));
        setLoadError(false);
      } catch {
        setLoadError(true);
      }
    }

    void load(locale);

    // React to locale switcher changes
    function onLocaleChanged(e: Event) {
      const newLocale = (e as CustomEvent<SupportedLocale>).detail;
      void load(newLocale);
    }
    window.addEventListener(LOCALE_CHANGED_EVENT, onLocaleChanged);
    return () => window.removeEventListener(LOCALE_CHANGED_EVENT, onLocaleChanged);
  }, [items, limit]);

  const coverageItems = items !== undefined ? items : fetchedItems;

  function handleClick(item: MediaCoverageItem) {
    captureEvent({
      type: "media_coverage_click",
      coverage_id: item.id,
      coverage_type: item.type,
    } as Parameters<typeof captureEvent>[0]);
  }

  // Graceful degrade: nothing to show — render empty (no hardcoded placeholders)
  if (coverageItems.length === 0) {
    if (loadError) {
      // silent fail — don't disrupt the hub page
      return null;
    }
    return null;
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
      {coverageItems.map((item) => (
        <a
          key={item.id}
          href={item.url}
          target="_blank"
          rel="noopener noreferrer"
          onClick={() => handleClick(item)}
          className={`block rounded-xl border p-4 hover:shadow-md transition-shadow ${
            TYPE_COLORS[item.type] ?? TYPE_COLORS.other
          }`}
          aria-label={`${item.title} — ${item.source}`}
        >
          <div className="flex items-start gap-3">
            {item.imageUrl ? (
              <img
                src={item.imageUrl}
                alt={item.title}
                className="w-12 h-10 rounded object-cover flex-shrink-0"
              />
            ) : (
              <span className="text-2xl flex-shrink-0" aria-hidden>
                {TYPE_ICONS[item.type] ?? TYPE_ICONS.other}
              </span>
            )}
            <div className="min-w-0">
              <p className="font-semibold text-sm text-text-primary leading-snug line-clamp-2">
                {item.title}
              </p>
              <p className="mt-1 text-xs text-text-muted">
                {item.source}
                {item.date ? ` · ${item.date}` : ""}
              </p>
            </div>
          </div>
        </a>
      ))}
    </div>
  );
}
