"use client";

/**
 * ArtistTierBenefitsView — B-4 tier-benefits-customization.
 *
 * Read-only display of an artist's tier benefits for:
 *   - Artist profile page (app/users/[id]/page.tsx)
 *   - BluebirdModal step 1 preview
 *
 * When artistId is provided, fetches from GET /users/{id}/tier-benefits.
 * Falls back to platform default i18n strings when no override exists.
 */

import { useState } from "react";
import { useI18n } from "@/i18n";
import { useTierBenefits } from "@/lib/hooks/useTierBenefits";

type TierKey = "subscriber" | "sponsor" | "follower";

const TIER_COLORS: Record<TierKey, string> = {
  subscriber: "text-amber-700 bg-amber-50 border-amber-200",
  sponsor: "text-blue-700 bg-blue-50 border-blue-200",
  follower: "text-green-700 bg-green-50 border-green-200",
};

const TIER_ICONS: Record<TierKey, string> = {
  subscriber: "🌟",
  sponsor: "🦋",
  follower: "🕊",
};

type Props = {
  artistId: string;
  /** When true, renders as a collapsible section. */
  collapsible?: boolean;
  /** When set, highlights this tier (e.g. the tier the user is about to choose). */
  highlightTier?: TierKey;
};

export function ArtistTierBenefitsView({
  artistId,
  collapsible = true,
  highlightTier,
}: Props) {
  const { t } = useI18n();
  const { benefits, loading, error } = useTierBenefits(artistId);
  const [open, setOpen] = useState(!collapsible);

  const tiers: TierKey[] = ["subscriber", "sponsor", "follower"];

  if (loading) {
    return (
      <div className="card p-4 animate-pulse">
        <div className="h-4 bg-surface-hover rounded w-1/3 mb-3" />
        <div className="grid sm:grid-cols-3 gap-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-20 bg-surface-hover rounded-xl" />
          ))}
        </div>
      </div>
    );
  }

  if (error || !benefits) return null;

  const renderContent = () => (
    <div className="px-5 pb-5 pt-3 space-y-3">
      <div className="grid gap-3 sm:grid-cols-3">
        {tiers.map((tier) => {
          const item = benefits[tier];
          const isHighlighted = highlightTier === tier;
          const colorClass = TIER_COLORS[tier];

          return (
            <div
              key={tier}
              className={`rounded-xl border p-4 space-y-2 transition-all ${colorClass} ${
                isHighlighted ? "ring-2 ring-current/40 shadow-sm" : ""
              }`}
            >
              <div className="flex items-center gap-2">
                <span className="text-xl">{TIER_ICONS[tier]}</span>
                <span className="font-bold text-sm capitalize">
                  {t(`tierBenefits.tier.${tier}`)}
                </span>
              </div>

              {item.is_platform_default ? (
                <p className="text-xs leading-relaxed opacity-90">
                  {t(item.platform_default_key ?? `patronage.supporter.tier.benefits.${tier}`)}
                </p>
              ) : (
                <ul className="space-y-1">
                  {item.benefits.map((b, i) => (
                    <li key={i} className="text-xs leading-relaxed flex gap-1.5">
                      <span className="mt-0.5 flex-shrink-0">•</span>
                      <span>{b}</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          );
        })}
      </div>

      {/* Per-tier welcome message preview for highlighted tier */}
      {highlightTier && benefits[highlightTier].welcome_message && (
        <div className="rounded-lg bg-surface-hover/40 border border-border px-4 py-3 text-sm text-text-secondary italic">
          {benefits[highlightTier].welcome_message}
        </div>
      )}
    </div>
  );

  return (
    <section className="card overflow-hidden">
      {collapsible ? (
        <button
          onClick={() => setOpen((v) => !v)}
          className="w-full flex items-center justify-between px-5 py-4 hover:bg-surface-hover/40 transition-colors"
          aria-expanded={open}
        >
          <div className="flex items-center gap-2">
            <span className="text-lg">🎖</span>
            <span className="font-semibold text-text-primary">
              {t("tierBenefits.profile.title")}
            </span>
          </div>
          <span className="text-text-muted text-sm">{open ? "−" : "+"}</span>
        </button>
      ) : (
        <div className="flex items-center gap-2 px-5 py-4 border-b border-border">
          <span className="text-lg">🎖</span>
          <span className="font-semibold text-text-primary">
            {t("tierBenefits.profile.title")}
          </span>
        </div>
      )}

      {open && renderContent()}
    </section>
  );
}
