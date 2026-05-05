"use client";

/**
 * /me/tier-benefits — 작가 tier benefits 설정 페이지 (B-4).
 *
 * Artist-only. Redirects non-artists to home.
 * Allows defining custom benefits + welcome message for each tier.
 */

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useI18n } from "@/i18n";
import { useMe } from "@/lib/useMe";
import { useTierBenefits } from "@/lib/hooks/useTierBenefits";
import { TierBenefitsEditor } from "@/components/tier-benefits/TierBenefitsEditor";
import { ArtistTierBenefitsView } from "@/components/tier-benefits/ArtistTierBenefitsView";
import { TierBenefitsUpsertInput } from "@/lib/api";

type TierKey = "subscriber" | "sponsor" | "follower";
const TIERS: TierKey[] = ["subscriber", "sponsor", "follower"];

export default function TierBenefitsSettingsPage() {
  const { t } = useI18n();
  const router = useRouter();
  const { me, loading: meLoading } = useMe();
  const { benefits, loading, error, saveTier, resetTier, saving } =
    useTierBenefits(); // no artistId → own benefits

  // Redirect non-artists
  useEffect(() => {
    if (!meLoading && me && me.role !== "artist") {
      router.replace("/");
    }
    if (!meLoading && !me) {
      router.replace("/");
    }
  }, [me, meLoading, router]);

  if (meLoading || loading) {
    return (
      <main className="flex-1 min-w-0 max-w-3xl mx-auto px-6 py-8 space-y-6">
        <div className="h-8 bg-surface-hover/40 rounded w-1/2 animate-pulse" />
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-48 bg-surface-hover/40 rounded-xl animate-pulse" />
        ))}
      </main>
    );
  }

  if (!me || me.role !== "artist") return null;

  const handleSave = async (tier: TierKey, input: TierBenefitsUpsertInput) => {
    await saveTier(tier, input);
  };

  const handleReset = async (tier: TierKey) => {
    await resetTier(tier);
  };

  return (
    <main className="flex-1 min-w-0 max-w-3xl mx-auto px-6 py-8 space-y-8">
      {/* Back */}
      <Link
        href="/me/patronage"
        className="text-text-secondary text-sm inline-block hover:text-primary"
      >
        ← {t("nav.patronageDashboard")}
      </Link>

      {/* Header */}
      <header>
        <h1 className="text-2xl font-bold text-text-primary">
          {t("tierBenefits.editor.title")}
        </h1>
        <p className="text-text-secondary text-sm mt-1">
          {t("tierBenefits.editor.subtitle")}
        </p>
      </header>

      {error && (
        <div className="card border-danger p-4 text-danger text-sm" role="alert">
          {error}
        </div>
      )}

      {/* 3 tier editors */}
      {benefits && (
        <div className="space-y-5">
          {TIERS.map((tier) => (
            <TierBenefitsEditor
              key={tier}
              tier={tier}
              item={benefits[tier]}
              saving={saving === tier}
              onSave={(input) => handleSave(tier, input)}
              onReset={() => handleReset(tier)}
            />
          ))}
        </div>
      )}

      {/* Live preview */}
      {me && benefits && (
        <section className="space-y-3">
          <h2 className="text-base font-semibold text-text-primary">
            {t("tierBenefits.preview.title")}
          </h2>
          <ArtistTierBenefitsView artistId={me.id} collapsible={false} />
        </section>
      )}
    </main>
  );
}
