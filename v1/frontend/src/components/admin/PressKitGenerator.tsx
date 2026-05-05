"use client";

/**
 * PressKitGenerator — C-2 press-kit-auto-export
 *
 * Admin component to search for an artist, select locale, and trigger
 * press kit PDF generation. Shows 30d cache note.
 */

import { useState } from "react";
import { useI18n } from "@/i18n";
import { searchUsers } from "@/lib/api";
import type { PressKitOut, UserSearchResult } from "@/lib/api";

const LOCALES = [
  { value: "ko", label: "한국어" },
  { value: "en", label: "English" },
  { value: "ja", label: "日本語" },
  { value: "zh", label: "中文" },
  { value: "es", label: "Español" },
];

type Props = {
  onGenerate: (params: {
    user_id: string;
    locale: string;
    force?: boolean;
  }) => Promise<PressKitOut | null>;
  generating: boolean;
  error: string | null;
  onArtistSelected?: (artistId: string) => void;
};

export function PressKitGenerator({
  onGenerate,
  generating,
  error,
  onArtistSelected,
}: Props) {
  const { t } = useI18n();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<UserSearchResult[]>([]);
  const [searching, setSearching] = useState(false);
  const [selected, setSelected] = useState<UserSearchResult | null>(null);
  const [locale, setLocale] = useState("ko");
  const [force, setForce] = useState(false);
  const [lastKit, setLastKit] = useState<PressKitOut | null>(null);

  async function handleSearch() {
    if (query.trim().length < 2) return;
    setSearching(true);
    try {
      const res = await searchUsers(query.trim(), { role: "artist", limit: 8 });
      setResults(res);
    } catch {
      setResults([]);
    } finally {
      setSearching(false);
    }
  }

  function handleSelect(user: UserSearchResult) {
    setSelected(user);
    setResults([]);
    setQuery(user.display_name);
    onArtistSelected?.(user.id);
  }

  async function handleGenerate() {
    if (!selected) return;
    const kit = await onGenerate({
      user_id: selected.id,
      locale,
      force,
    });
    if (kit) {
      setLastKit(kit);
    }
  }

  return (
    <div className="bg-white rounded-xl border border-stone-200 p-6 space-y-4">
      <h2 className="text-lg font-bold text-stone-800">
        {t("pressKit.generateBtn")}
      </h2>

      {/* Artist search */}
      <div className="space-y-1">
        <label className="text-sm font-medium text-stone-600">
          {t("pressKit.artistSearch")}
        </label>
        <div className="flex gap-2">
          <input
            className="flex-1 border border-stone-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-amber-400"
            placeholder={t("pressKit.artistSearch")}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSearch()}
          />
          <button
            className="px-4 py-2 bg-stone-100 text-stone-700 rounded-lg text-sm font-medium hover:bg-stone-200 transition"
            onClick={handleSearch}
            disabled={searching}
          >
            {searching ? t("common.loading") : t("common.search")}
          </button>
        </div>
        {results.length > 0 && (
          <ul className="border border-stone-200 rounded-lg overflow-hidden bg-white shadow-sm mt-1">
            {results.map((u) => (
              <li key={u.id}>
                <button
                  className="w-full text-left px-4 py-2 text-sm hover:bg-amber-50 transition"
                  onClick={() => handleSelect(u)}
                >
                  <span className="font-medium">{u.display_name}</span>
                  <span className="ml-2 text-stone-400 text-xs">{u.role}</span>
                </button>
              </li>
            ))}
          </ul>
        )}
        {selected && (
          <p className="text-xs text-amber-600">
            Selected: <strong>{selected.display_name}</strong> ({selected.id})
          </p>
        )}
      </div>

      {/* Locale selector */}
      <div className="space-y-1">
        <label className="text-sm font-medium text-stone-600">
          {t("pressKit.locale")}
        </label>
        <select
          className="w-full border border-stone-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-amber-400"
          value={locale}
          onChange={(e) => setLocale(e.target.value)}
        >
          {LOCALES.map((l) => (
            <option key={l.value} value={l.value}>
              {l.label}
            </option>
          ))}
        </select>
      </div>

      {/* Force regenerate */}
      <label className="flex items-center gap-2 text-sm text-stone-600 cursor-pointer">
        <input
          type="checkbox"
          checked={force}
          onChange={(e) => setForce(e.target.checked)}
          className="rounded border-stone-300 text-amber-500 focus:ring-amber-400"
        />
        {t("pressKit.regenerateBtn")}
      </label>

      <p className="text-xs text-stone-400">{t("pressKit.cacheNote")}</p>

      {error && (
        <p className="text-sm text-red-500">{t("pressKit.generateError")}</p>
      )}

      {/* Generate button */}
      <button
        className="w-full py-2.5 bg-amber-500 text-white rounded-lg font-semibold text-sm hover:bg-amber-600 transition disabled:opacity-50"
        onClick={handleGenerate}
        disabled={!selected || generating}
      >
        {generating ? t("pressKit.generating") : t("pressKit.generateBtn")}
      </button>

      {/* Result */}
      {lastKit && (
        <div className="mt-3 p-3 bg-green-50 rounded-lg text-sm space-y-1">
          <p className="text-green-700 font-medium">
            Generated — {lastKit.page_count} {t("pressKit.pages")} (
            {(lastKit.file_size_bytes / 1024).toFixed(1)} KB)
          </p>
          <a
            href={lastKit.download_url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-amber-600 underline font-medium"
          >
            {t("pressKit.downloadBtn")}
          </a>
        </div>
      )}
    </div>
  );
}
