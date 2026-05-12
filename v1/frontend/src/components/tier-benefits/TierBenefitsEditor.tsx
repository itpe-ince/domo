"use client";

/**
 * TierBenefitsEditor — B-4 tier-benefits-customization.
 *
 * Single-tier edit card for the artist settings page.
 * Allows adding/removing benefit strings + optional welcome message.
 */

import { useEffect, useRef, useState } from "react";
import { useI18n } from "@/i18n";
import { TierBenefitsItem, TierBenefitsUpsertInput } from "@/lib/api";

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

const MAX_BENEFITS = 10;
const MAX_BENEFIT_LENGTH = 200;
const MAX_WELCOME_LENGTH = 500;

type Props = {
  tier: TierKey;
  item: TierBenefitsItem;
  saving: boolean;
  onSave: (input: TierBenefitsUpsertInput) => Promise<void>;
  onReset: () => Promise<void>;
};

export function TierBenefitsEditor({ tier, item, saving, onSave, onReset }: Props) {
  const { t } = useI18n();

  const [benefits, setBenefits] = useState<string[]>(item.benefits ?? []);
  const [welcome, setWelcome] = useState(item.welcome_message ?? "");
  const [newBenefit, setNewBenefit] = useState("");
  const [fieldError, setFieldError] = useState<string | null>(null);
  const [isDirty, setIsDirty] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  // Sync when item changes externally (e.g. after reset)
  useEffect(() => {
    setBenefits(item.benefits ?? []);
    setWelcome(item.welcome_message ?? "");
    setIsDirty(false);
  }, [item]);

  function addBenefit() {
    const trimmed = newBenefit.trim();
    if (!trimmed) return;
    if (trimmed.length > MAX_BENEFIT_LENGTH) {
      setFieldError(t("tierBenefits.error.tooLong"));
      return;
    }
    if (benefits.length >= MAX_BENEFITS) {
      setFieldError(t("tierBenefits.error.tooMany"));
      return;
    }
    setFieldError(null);
    setBenefits((prev) => [...prev, trimmed]);
    setNewBenefit("");
    setIsDirty(true);
    inputRef.current?.focus();
  }

  function removeBenefit(idx: number) {
    setBenefits((prev) => prev.filter((_, i) => i !== idx));
    setIsDirty(true);
  }

  async function handleSave() {
    setFieldError(null);
    await onSave({ benefits, welcome_message: welcome || null });
    setIsDirty(false);
  }

  async function handleReset() {
    if (!confirm(t("tierBenefits.action.resetConfirm"))) return;
    await onReset();
  }

  const colorClass = TIER_COLORS[tier];

  return (
    <div className={`rounded-xl border p-5 space-y-4 ${colorClass}`}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-2xl">{TIER_ICONS[tier]}</span>
          <div>
            <h3 className="font-bold text-base capitalize">
              {t(`tierBenefits.tier.${tier}`)}
            </h3>
            {item.is_platform_default && (
              <p className="text-xs opacity-70">
                {t("tierBenefits.empty.platformDefault").replace("{tier}", tier)}
              </p>
            )}
          </div>
        </div>
        {!item.is_platform_default && (
          <button
            onClick={handleReset}
            disabled={saving}
            className="text-xs underline opacity-70 hover:opacity-100 disabled:opacity-40"
          >
            {t("tierBenefits.action.reset")}
          </button>
        )}
      </div>

      {/* Benefit list */}
      <div className="space-y-1.5">
        {benefits.length === 0 ? (
          <p className="text-xs opacity-60">{t("tierBenefits.benefit.emptyHint")}</p>
        ) : (
          benefits.map((b, i) => (
            <div key={i} className="flex items-start gap-2 text-sm">
              <span className="mt-0.5">•</span>
              <span className="flex-1 leading-relaxed">{b}</span>
              <button
                onClick={() => removeBenefit(i)}
                disabled={saving}
                aria-label={t("tierBenefits.benefit.remove")}
                className="text-current opacity-50 hover:opacity-100 text-xs disabled:opacity-30"
              >
                ✕
              </button>
            </div>
          ))
        )}
      </div>

      {/* Add new benefit */}
      {benefits.length < MAX_BENEFITS && (
        <div className="flex gap-2">
          <input
            ref={inputRef}
            type="text"
            value={newBenefit}
            onChange={(e) => {
              setNewBenefit(e.target.value);
              setFieldError(null);
            }}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                addBenefit();
              }
            }}
            maxLength={MAX_BENEFIT_LENGTH}
            placeholder={t("tierBenefits.benefit.placeholder")}
            className="flex-1 bg-white/60 border border-current/20 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:border-current/50"
            aria-label={t("tierBenefits.benefit.add")}
          />
          <button
            onClick={addBenefit}
            disabled={!newBenefit.trim() || saving}
            className="px-3 py-1.5 bg-current/10 hover:bg-current/20 rounded-lg text-sm font-medium disabled:opacity-40 transition-colors"
          >
            {t("tierBenefits.benefit.add")}
          </button>
        </div>
      )}

      {benefits.length >= MAX_BENEFITS && (
        <p className="text-xs opacity-60">
          {t("tierBenefits.benefit.maxCount").replace("{max}", String(MAX_BENEFITS))}
        </p>
      )}

      {fieldError && (
        <p className="text-xs text-red-600 font-medium">{fieldError}</p>
      )}

      {/* Welcome message */}
      <div className="space-y-1">
        <label className="text-xs font-medium opacity-80">
          {t("tierBenefits.welcomeMessage.label")}
        </label>
        <textarea
          value={welcome}
          onChange={(e) => {
            setWelcome(e.target.value);
            setIsDirty(true);
          }}
          maxLength={MAX_WELCOME_LENGTH}
          rows={3}
          placeholder={t("tierBenefits.welcomeMessage.placeholder")}
          className="w-full bg-white/60 border border-current/20 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-current/50 resize-none"
          aria-label={t("tierBenefits.welcomeMessage.label")}
        />
        <p className="text-xs opacity-50 text-right">
          {welcome.length}/{MAX_WELCOME_LENGTH}
        </p>
      </div>

      {/* Save button */}
      <button
        onClick={handleSave}
        disabled={saving || (!isDirty && benefits.length === (item.benefits?.length ?? 0))}
        className="w-full py-2 bg-current/15 hover:bg-current/25 rounded-lg text-sm font-semibold disabled:opacity-40 transition-colors"
        aria-busy={saving}
      >
        {saving
          ? t("tierBenefits.action.saving")
          : t("tierBenefits.action.save")}
      </button>
    </div>
  );
}
