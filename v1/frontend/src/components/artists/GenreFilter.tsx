"use client";

import { useI18n } from "@/i18n";

const GENRES = [
  { value: "watercolor", label: "🎨 Watercolor" },
  { value: "oil", label: "🖼️ Oil" },
  { value: "digital", label: "💻 Digital" },
  { value: "sculpture", label: "🗿 Sculpture" },
  { value: "mixed_media", label: "🎭 Mixed Media" },
  { value: "photography", label: "📷 Photography" },
  { value: "illustration", label: "✏️ Illustration" },
  { value: "printmaking", label: "🖨️ Printmaking" },
];

interface GenreFilterProps {
  value: string;
  onChange: (genre: string) => void;
}

export function GenreFilter({ value, onChange }: GenreFilterProps) {
  const { t } = useI18n();

  return (
    <div className="flex flex-col gap-1">
      <label className="text-sm font-medium text-text-secondary">
        {t("artist.index.filter.genre")}
      </label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="rounded-lg border border-border bg-background px-3 py-2 text-sm text-text-primary focus:outline-none focus:ring-2 focus:ring-primary/50"
        aria-label={t("artist.index.filter.genre")}
      >
        <option value="">{t("artist.index.filter.genreAll")}</option>
        {GENRES.map((g) => (
          <option key={g.value} value={g.value}>
            {g.label}
          </option>
        ))}
      </select>
    </div>
  );
}
