"use client";

/**
 * UserMediaCoverage — C-4 media-coverage-cms
 *
 * Shows external media coverage items for a specific artist.
 * Used in the artist profile page (/users/[id]).
 * Fetches from GET /media-coverage?artist_id=&locale=&limit=5
 */

import { useEffect, useState } from "react";
import { useI18n } from "@/i18n";
import { fetchMediaCoverage } from "@/lib/api";
import type { MediaCoverageOut } from "@/lib/api";

const TYPE_ICONS: Record<string, string> = {
  article: "📰",
  youtube: "▶",
  radio: "📻",
  podcast: "🎙",
  tv: "📺",
  other: "🔗",
};

const TYPE_COLORS: Record<string, string> = {
  article: "bg-slate-100 border-slate-200 text-slate-700",
  youtube: "bg-red-50 border-red-200 text-red-700",
  radio: "bg-purple-50 border-purple-200 text-purple-700",
  podcast: "bg-orange-50 border-orange-200 text-orange-700",
  tv: "bg-blue-50 border-blue-200 text-blue-700",
  other: "bg-gray-100 border-gray-200 text-gray-700",
};

type Props = {
  artistId: string;
  locale?: string;
  limit?: number;
};

export function UserMediaCoverage({ artistId, locale = "ko", limit = 5 }: Props) {
  const { t } = useI18n();
  const [items, setItems] = useState<MediaCoverageOut[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      try {
        const res = await fetchMediaCoverage({
          artist_id: artistId,
          locale,
          limit,
        });
        if (!cancelled) {
          setItems(res.data ?? []);
        }
      } catch {
        // non-critical — silently fail
        if (!cancelled) setItems([]);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, [artistId, locale, limit]);

  if (loading) return null; // Avoid layout shift — section appears after load
  if (items.length === 0) return null; // Graceful degrade — section hidden when no data

  return (
    <section aria-labelledby="media-coverage-heading" className="space-y-3">
      <h3
        id="media-coverage-heading"
        className="text-sm font-semibold text-text-secondary uppercase tracking-wide"
      >
        {t("mediaCoverage.artist.sectionTitle")}
      </h3>
      <div className="space-y-2">
        {items.map((item) => (
          <a
            key={item.id}
            href={item.external_url}
            target="_blank"
            rel="noopener noreferrer"
            className={`flex items-start gap-3 rounded-xl border p-3 hover:shadow-sm transition-shadow ${
              TYPE_COLORS[item.coverage_type] ?? TYPE_COLORS.other
            }`}
            aria-label={`${item.title} — ${item.source_name}`}
          >
            <span className="text-lg flex-shrink-0 mt-0.5" aria-hidden>
              {TYPE_ICONS[item.coverage_type] ?? TYPE_ICONS.other}
            </span>
            <div className="min-w-0">
              <p className="text-sm font-medium leading-snug line-clamp-2">
                {item.title}
              </p>
              <p className="mt-0.5 text-xs opacity-70">
                {item.source_name}
                {item.published_at ? ` · ${item.published_at.substring(0, 7)}` : ""}
              </p>
            </div>
          </a>
        ))}
      </div>
    </section>
  );
}
