"use client";

/**
 * TierBenefitsPanel — B-3 supporter-dashboard (enhanced in B-4)
 *
 * When `artistId` is provided, fetches artist-specific overrides via
 * GET /v1/users/{id}/tier-benefits (B-4). Otherwise shows platform defaults.
 */

import { useState } from "react";
import { useI18n } from "@/i18n";
import { ArtistTierBenefitsView } from "@/components/tier-benefits/ArtistTierBenefitsView";

type TierKey = "subscriber" | "sponsor" | "follower";

const TIER_COLORS: Record<TierKey, string> = {
  subscriber: "text-amber-600 bg-amber-50 border-amber-200",
  sponsor: "text-blue-600 bg-blue-50 border-blue-200",
  follower: "text-green-600 bg-green-50 border-green-200",
};

const TIER_ICONS: Record<TierKey, string> = {
  subscriber: "🌟",
  sponsor: "🦋",
  follower: "🕊",
};

type Props = {
  /** When true, renders as a collapsible section. When false, always expanded. */
  collapsible?: boolean;
  /**
   * B-4: When provided, fetches artist-specific overrides.
   * When absent, shows platform default text.
   */
  artistId?: string;
};

export function TierBenefitsPanel({ collapsible = true, artistId }: Props) {
  const { t } = useI18n();
  const [open, setOpen] = useState(!collapsible);

  // B-4: delegate to ArtistTierBenefitsView when artistId is provided
  if (artistId) {
    return (
      <ArtistTierBenefitsView
        artistId={artistId}
        collapsible={collapsible}
      />
    );
  }

  // Platform default fallback (original B-3 behaviour)
  const tiers: TierKey[] = ["subscriber", "sponsor", "follower"];

  return (
    <section className="card overflow-hidden">
      {/* Header */}
      {collapsible ? (
        <button
          onClick={() => setOpen((v) => !v)}
          className="w-full flex items-center justify-between px-5 py-4 hover:bg-surface-hover/40 transition-colors"
          aria-expanded={open}
        >
          <div className="flex items-center gap-2">
            <span className="text-lg">🎖</span>
            <span className="font-semibold text-text-primary">
              {t("patronage.supporter.tier.benefits.title")}
            </span>
          </div>
          <span className="text-text-muted text-sm">{open ? "−" : "+"}</span>
        </button>
      ) : (
        <div className="flex items-center gap-2 px-5 py-4 border-b border-border">
          <span className="text-lg">🎖</span>
          <span className="font-semibold text-text-primary">
            {t("patronage.supporter.tier.benefits.title")}
          </span>
        </div>
      )}

      {/* Content */}
      {open && (
        <div className="px-5 pb-5 pt-3 space-y-4">
          <div className="grid gap-3 sm:grid-cols-3">
            {tiers.map((tier) => (
              <div
                key={tier}
                className={`rounded-xl border p-4 space-y-2 ${TIER_COLORS[tier]}`}
              >
                <div className="flex items-center gap-2">
                  <span className="text-xl">{TIER_ICONS[tier]}</span>
                  <span className="font-bold text-sm capitalize">
                    {tier}
                  </span>
                </div>
                <p className="text-xs leading-relaxed opacity-90">
                  {t(`patronage.supporter.tier.benefits.${tier}`)}
                </p>
              </div>
            ))}
          </div>

          <p className="text-xs text-text-muted text-center pt-1">
            {t("patronage.supporter.tier.benefits.detailsLink")}
          </p>
        </div>
      )}
    </section>
  );
}
