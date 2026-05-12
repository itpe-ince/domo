"use client";

/**
 * InterviewGenerateModal — C-1 ai-artist-interview-generation
 *
 * Modal for admin to trigger LLM interview generation.
 * Artist search + locale selection + Generate button.
 */

import { useState } from "react";
import { useI18n } from "@/i18n";
import { searchUsers } from "@/lib/api";
import type { UserSearchResult } from "@/lib/api";

const LOCALES = [
  { value: "ko", label: "한국어" },
  { value: "en", label: "English" },
  { value: "ja", label: "日本語" },
  { value: "zh", label: "中文" },
  { value: "es", label: "Español" },
];

type Props = {
  onGenerate: (params: { artist_id: string; locale: string }) => Promise<boolean>;
  generating: boolean;
  error: string | null;
  onClose: () => void;
};

export function InterviewGenerateModal({
  onGenerate,
  generating,
  error,
  onClose,
}: Props) {
  const { t } = useI18n();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<UserSearchResult[]>([]);
  const [searching, setSearching] = useState(false);
  const [selected, setSelected] = useState<UserSearchResult | null>(null);
  const [locale, setLocale] = useState("ko");

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
    const ok = await onGenerate({ artist_id: selected.id, locale });
    if (ok) onClose();
  }

  return (
    <div
      className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-label={t("interview.admin.generateTitle")}
    >
      <div className="card w-full max-w-md p-6">
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-lg font-semibold text-text-primary">
            {t("interview.admin.generateTitle")}
          </h2>
          <button
            type="button"
            className="text-text-muted hover:text-text-primary"
            onClick={onClose}
            aria-label={t("common.close")}
          >
            ✕
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Artist search */}
          <div>
            <label className="block text-sm font-medium text-text-secondary mb-1">
              {t("interview.admin.artistIdLabel")}
            </label>
            <div className="flex gap-2">
              <input
                type="text"
                className="input flex-1"
                placeholder="작가 이름 검색..."
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
                {searching ? t("common.loading") : t("common.search")}
              </button>
            </div>

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
                    </button>
                  </li>
                ))}
              </ul>
            )}

            {selected && (
              <p className="mt-1 text-xs text-success">
                선택됨: <strong>{selected.display_name}</strong>
              </p>
            )}
          </div>

          {/* Locale select */}
          <div>
            <label className="block text-sm font-medium text-text-secondary mb-1">
              {t("interview.admin.localeLabel")}
            </label>
            <select
              className="input w-full"
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

          {error && <p className="text-sm text-danger">{error}</p>}

          <div className="flex gap-2 pt-2">
            <button
              type="button"
              className="btn-secondary flex-1"
              onClick={onClose}
            >
              {t("common.cancel")}
            </button>
            <button
              type="submit"
              className="btn-primary flex-1"
              disabled={generating || !selected}
            >
              {generating
                ? t("interview.admin.generating")
                : t("interview.admin.generateCta")}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
