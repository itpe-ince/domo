"use client";

/**
 * FeaturedArtistForm — G'-7 admin-featured-artists
 *
 * Form for admin to select an artist and set the monthly featured artist.
 * Accepts: artist username/id search, month picker, optional curation note.
 */

import { useState } from "react";
import { useI18n } from "@/i18n";
import { searchUsers } from "@/lib/api";
import type { UserSearchResult } from "@/lib/api";

type Props = {
  onSubmit: (params: {
    artist_id: string;
    month: string;
    curation_note?: string;
  }) => Promise<boolean>;
  submitting: boolean;
  error: string | null;
};

/** Return "YYYY-MM-01" for today's month. */
function defaultMonthValue(): string {
  const d = new Date();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  return `${d.getFullYear()}-${m}-01`;
}

export function FeaturedArtistForm({ onSubmit, submitting, error }: Props) {
  const { t } = useI18n();

  // Artist search state
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<UserSearchResult[]>([]);
  const [searching, setSearching] = useState(false);
  const [selected, setSelected] = useState<UserSearchResult | null>(null);

  // Form fields
  const [month, setMonth] = useState(defaultMonthValue());
  const [note, setNote] = useState("");

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

  function handleSelectArtist(artist: UserSearchResult) {
    setSelected(artist);
    setQuery(artist.display_name);
    setResults([]);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!selected) return;

    await onSubmit({
      artist_id: selected.id,
      month,
      curation_note: note.trim() || undefined,
    });
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {/* Artist search */}
      <div>
        <label className="block text-sm font-medium text-text-secondary mb-1">
          {t("admin.featuredArtists.form.artistLabel")}
        </label>
        <div className="flex gap-2">
          <input
            type="text"
            className="input flex-1"
            placeholder={t("admin.featuredArtists.form.artistPlaceholder")}
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setSelected(null);
            }}
          />
          <button
            type="button"
            className="btn-secondary text-sm px-3"
            disabled={searching || query.trim().length < 2}
            onClick={handleSearch}
          >
            {searching
              ? t("common.loading")
              : t("admin.featuredArtists.form.searchBtn")}
          </button>
        </div>

        {/* Search results dropdown */}
        {results.length > 0 && (
          <ul className="mt-1 border border-border rounded-lg bg-surface shadow-sm divide-y divide-border text-sm">
            {results.map((r) => (
              <li key={r.id}>
                <button
                  type="button"
                  className="w-full text-left px-3 py-2 hover:bg-surface-hover flex items-center gap-2"
                  onClick={() => handleSelectArtist(r)}
                >
                  {r.avatar_url ? (
                    <img
                      src={r.avatar_url}
                      alt={r.display_name}
                      className="w-6 h-6 rounded-full object-cover"
                    />
                  ) : (
                    <span className="w-6 h-6 rounded-full bg-surface-hover flex items-center justify-center text-xs">
                      🎨
                    </span>
                  )}
                  <span className="font-medium">{r.display_name}</span>
                  <span className="text-text-muted text-xs ml-auto">artist</span>
                </button>
              </li>
            ))}
          </ul>
        )}

        {selected && (
          <p className="mt-1 text-xs text-success">
            {t("admin.featuredArtists.form.selectedArtist", {
              name: selected.display_name,
            })}
          </p>
        )}
      </div>

      {/* Month picker */}
      <div>
        <label className="block text-sm font-medium text-text-secondary mb-1">
          {t("admin.featuredArtists.form.monthLabel")}
        </label>
        <input
          type="date"
          className="input"
          value={month}
          onChange={(e) => setMonth(e.target.value)}
          min={(() => {
            const d = new Date();
            return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-01`;
          })()}
        />
        <p className="text-xs text-text-muted mt-1">
          {t("admin.featuredArtists.form.monthHint")}
        </p>
      </div>

      {/* Curation note */}
      <div>
        <label className="block text-sm font-medium text-text-secondary mb-1">
          {t("admin.featuredArtists.form.noteLabel")}
        </label>
        <textarea
          className="input w-full h-24 resize-none"
          placeholder={t("admin.featuredArtists.form.notePlaceholder")}
          value={note}
          maxLength={1000}
          onChange={(e) => setNote(e.target.value)}
        />
        <p className="text-xs text-text-muted text-right">{note.length}/1000</p>
      </div>

      {error && (
        <p className="text-sm text-danger">{error}</p>
      )}

      <button
        type="submit"
        className="btn-primary w-full"
        disabled={submitting || !selected}
      >
        {submitting
          ? t("common.loading")
          : t("admin.featuredArtists.form.submitBtn")}
      </button>
    </form>
  );
}
