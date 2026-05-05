"use client";

/**
 * MediaCoverageForm — C-4 media-coverage-cms
 *
 * Form for admin to create or edit a media coverage entry.
 * Supports: title, type, source, URL, thumbnail, published_at,
 *           artist (optional search), locale, is_published, is_featured.
 */

import { useState } from "react";
import { useI18n } from "@/i18n";
import type {
  AdminCreateMediaCoverageBody,
  CoverageType,
  MediaCoverageOut,
} from "@/lib/api";

const COVERAGE_TYPES: CoverageType[] = [
  "article",
  "youtube",
  "radio",
  "podcast",
  "tv",
];
const SUPPORTED_LOCALES = ["ko", "en", "ja", "zh", "es"] as const;

type Props = {
  initial?: Partial<MediaCoverageOut>;
  onSubmit: (body: AdminCreateMediaCoverageBody) => Promise<boolean>;
  submitting: boolean;
  error: string | null;
};

function todayISO(): string {
  return new Date().toISOString().split("T")[0];
}

export function MediaCoverageForm({ initial, onSubmit, submitting, error }: Props) {
  const { t } = useI18n();

  const [title, setTitle] = useState(initial?.title ?? "");
  const [coverageType, setCoverageType] = useState<CoverageType>(
    (initial?.coverage_type as CoverageType) ?? "article"
  );
  const [sourceName, setSourceName] = useState(initial?.source_name ?? "");
  const [externalUrl, setExternalUrl] = useState(initial?.external_url ?? "");
  const [thumbnailUrl, setThumbnailUrl] = useState(initial?.thumbnail_url ?? "");
  const [publishedAt, setPublishedAt] = useState(
    initial?.published_at ?? todayISO()
  );
  const [description, setDescription] = useState(initial?.description ?? "");
  const [locale, setLocale] = useState(initial?.locale ?? "ko");
  const [isPublished, setIsPublished] = useState(initial?.is_published ?? false);
  const [isFeatured, setIsFeatured] = useState(initial?.is_featured ?? false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const body: AdminCreateMediaCoverageBody = {
      title: title.trim(),
      coverage_type: coverageType,
      source_name: sourceName.trim(),
      external_url: externalUrl.trim(),
      thumbnail_url: thumbnailUrl.trim() || null,
      published_at: publishedAt,
      description: description.trim() || null,
      locale,
      is_published: isPublished,
      is_featured: isFeatured,
    };
    await onSubmit(body);
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {/* Title */}
      <div>
        <label className="block text-sm font-medium text-text-secondary mb-1">
          {t("mediaCoverage.typeLabel")} / 제목
        </label>
        <input
          type="text"
          className="input w-full"
          placeholder="기사 제목"
          value={title}
          maxLength={200}
          onChange={(e) => setTitle(e.target.value)}
          required
        />
      </div>

      {/* Type + Locale row */}
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-sm font-medium text-text-secondary mb-1">
            {t("mediaCoverage.typeLabel")}
          </label>
          <select
            className="input w-full"
            value={coverageType}
            onChange={(e) => setCoverageType(e.target.value as CoverageType)}
          >
            {COVERAGE_TYPES.map((ct) => (
              <option key={ct} value={ct}>
                {t(`mediaCoverage.types.${ct}`)}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-text-secondary mb-1">
            {t("mediaCoverage.localeLabel")}
          </label>
          <select
            className="input w-full"
            value={locale}
            onChange={(e) => setLocale(e.target.value)}
          >
            {SUPPORTED_LOCALES.map((l) => (
              <option key={l} value={l}>
                {l.toUpperCase()}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Source + published_at row */}
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-sm font-medium text-text-secondary mb-1">
            {t("mediaCoverage.sourceLabel")}
          </label>
          <input
            type="text"
            className="input w-full"
            placeholder="한겨레, TBS…"
            value={sourceName}
            maxLength={100}
            onChange={(e) => setSourceName(e.target.value)}
            required
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-text-secondary mb-1">
            {t("mediaCoverage.publishedAtLabel")}
          </label>
          <input
            type="date"
            className="input w-full"
            value={publishedAt}
            onChange={(e) => setPublishedAt(e.target.value)}
            required
          />
        </div>
      </div>

      {/* External URL */}
      <div>
        <label className="block text-sm font-medium text-text-secondary mb-1">
          외부 링크 URL
        </label>
        <input
          type="url"
          className="input w-full"
          placeholder="https://..."
          value={externalUrl}
          onChange={(e) => setExternalUrl(e.target.value)}
          required
        />
      </div>

      {/* Thumbnail URL */}
      <div>
        <label className="block text-sm font-medium text-text-secondary mb-1">
          썸네일 URL (선택)
        </label>
        <input
          type="url"
          className="input w-full"
          placeholder="https://... (OG image 또는 직접 업로드 URL)"
          value={thumbnailUrl}
          onChange={(e) => setThumbnailUrl(e.target.value)}
        />
      </div>

      {/* Description */}
      <div>
        <label className="block text-sm font-medium text-text-secondary mb-1">
          짧은 설명 (선택)
        </label>
        <textarea
          className="input w-full h-20 resize-none"
          placeholder="이 기사에 대한 짧은 설명"
          value={description}
          maxLength={500}
          onChange={(e) => setDescription(e.target.value)}
        />
        <p className="text-xs text-text-muted text-right">{description.length}/500</p>
      </div>

      {/* Toggles */}
      <div className="flex gap-6">
        <label className="flex items-center gap-2 text-sm cursor-pointer">
          <input
            type="checkbox"
            className="rounded"
            checked={isPublished}
            onChange={(e) => setIsPublished(e.target.checked)}
          />
          {t("mediaCoverage.publishedLabel")}
        </label>
        <label className="flex items-center gap-2 text-sm cursor-pointer">
          <input
            type="checkbox"
            className="rounded"
            checked={isFeatured}
            onChange={(e) => setIsFeatured(e.target.checked)}
          />
          {t("mediaCoverage.featuredLabel")}
        </label>
      </div>

      {error && <p className="text-sm text-danger">{error}</p>}

      <button
        type="submit"
        className="btn-primary w-full"
        disabled={submitting || !title.trim() || !sourceName.trim() || !externalUrl.trim()}
      >
        {submitting ? t("common.loading") : t("common.save")}
      </button>
    </form>
  );
}
