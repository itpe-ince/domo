"use client";

/**
 * ProductFields — editor-responsive-redesign PDCA (#3, Step 2).
 *
 * Reusable product-specific form section: genre, dimensions, medium, year,
 * auction/buy-now toggles, buy-now price. Extracted from posts/new/page.tsx
 * verbatim — Tailwind classes and copy are unchanged so visual diff is zero.
 *
 * Used in two places:
 *   - desktop EditorWorkspace (Step 3): rendered when type === "product"
 *   - mobile EditorStepProductMeta (Step 4): wizard step that wraps this
 *
 * #7 editor-product-meta PDCA will eventually replace the inputs inside
 * with structured controls — leaving this component's prop surface stable
 * keeps that future migration cost low.
 *
 * Pattern source: design §4.1 (ProductFields).
 */

import { useI18n } from "@/i18n";

const GENRES = [
  "painting",
  "drawing",
  "photography",
  "sculpture",
  "mixed_media",
] as const;

export interface ProductFieldsProps {
  genre: string;
  onGenreChange: (v: string) => void;
  dimensions: string;
  onDimensionsChange: (v: string) => void;
  medium: string;
  onMediumChange: (v: string) => void;
  year: number | "";
  onYearChange: (v: number | "") => void;
  isAuction: boolean;
  onIsAuctionChange: (v: boolean) => void;
  isBuyNow: boolean;
  onIsBuyNowChange: (v: boolean) => void;
  buyNowPrice: number | "";
  onBuyNowPriceChange: (v: number | "") => void;
}

export function ProductFields({
  genre,
  onGenreChange,
  dimensions,
  onDimensionsChange,
  medium,
  onMediumChange,
  year,
  onYearChange,
  isAuction,
  onIsAuctionChange,
  isBuyNow,
  onIsBuyNowChange,
  buyNowPrice,
  onBuyNowPriceChange,
}: ProductFieldsProps) {
  const { t } = useI18n();
  return (
    <div className="card p-4 space-y-4">
      <h3 className="font-semibold text-sm">{t("post.productInfo")}</h3>

      <div>
        <label className="block text-xs text-text-secondary mb-1">{t("post.genre")}</label>
        <select
          value={genre}
          onChange={(e) => onGenreChange(e.target.value)}
          className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm focus:border-primary outline-none"
        >
          {GENRES.map((g) => (
            <option key={g} value={g}>
              {g}
            </option>
          ))}
        </select>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-xs text-text-secondary mb-1">{t("post.dimensions")}</label>
          <input
            type="text"
            placeholder="50x70cm"
            value={dimensions}
            onChange={(e) => onDimensionsChange(e.target.value)}
            className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm focus:border-primary outline-none"
          />
        </div>
        <div>
          <label className="block text-xs text-text-secondary mb-1">{t("post.medium")}</label>
          <input
            type="text"
            placeholder="Oil on canvas"
            value={medium}
            onChange={(e) => onMediumChange(e.target.value)}
            className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm focus:border-primary outline-none"
          />
        </div>
        <div>
          <label className="block text-xs text-text-secondary mb-1">{t("post.year")}</label>
          <input
            type="number"
            value={year}
            onChange={(e) => onYearChange(e.target.value ? Number(e.target.value) : "")}
            className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm focus:border-primary outline-none"
          />
        </div>
      </div>

      <div className="space-y-2 text-sm">
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={isAuction}
            onChange={(e) => onIsAuctionChange(e.target.checked)}
            className="accent-primary"
          />
          {t("post.auctionSell")}
        </label>
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={isBuyNow}
            onChange={(e) => onIsBuyNowChange(e.target.checked)}
            className="accent-primary"
          />
          {t("post.buyNow")}
        </label>
        {isBuyNow && (
          <div>
            <label className="block text-xs text-text-secondary mb-1">
              {t("post.buyNowPrice")}
            </label>
            <input
              type="number"
              value={buyNowPrice}
              onChange={(e) =>
                onBuyNowPriceChange(e.target.value ? Number(e.target.value) : "")
              }
              className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm focus:border-primary outline-none"
            />
          </div>
        )}
      </div>
    </div>
  );
}
