"use client";

/**
 * SponsorValiditySettings — D'-1 carry-over.
 * Allows artists to configure how long a completed one-time sponsorship
 * qualifies for tier access.
 *
 * Options: lifetime (null) | 1d | 7d | 30d | 90d | 365d
 * API: PATCH /v1/me/sponsor-settings { sponsor_validity_days: N | null }
 */

import { useState, useEffect } from "react";
import { patchSponsorSettings, fetchSponsorSettings, type SponsorValidityDays } from "@/lib/api";
import { useI18n } from "@/i18n";

const VALIDITY_OPTIONS: Array<{ value: SponsorValidityDays; labelKey: string }> = [
  { value: null, labelKey: "lifetime" },
  { value: 1, labelKey: "days" },
  { value: 7, labelKey: "days" },
  { value: 30, labelKey: "days" },
  { value: 90, labelKey: "days" },
  { value: 365, labelKey: "days" },
];

export function SponsorValiditySettings() {
  const { t } = useI18n();
  const [selected, setSelected] = useState<SponsorValidityDays>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void fetchSponsorSettings()
      .then((data) => setSelected(data.sponsor_validity_days))
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load"))
      .finally(() => setLoading(false));
  }, []);

  async function handleSave() {
    setSaving(true);
    setSaved(false);
    setError(null);
    try {
      const data = await patchSponsorSettings(selected);
      setSelected(data.sponsor_validity_days);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to save");
    } finally {
      setSaving(false);
    }
  }

  const ns = "me.settings.sponsorValidity";

  if (loading) {
    return (
      <div className="text-text-muted text-sm py-4">{t("common.loading")}</div>
    );
  }

  return (
    <div className="card p-6 space-y-4">
      <div>
        <h3 className="font-semibold">{t(`${ns}.title`)}</h3>
        <p className="text-text-muted text-sm mt-1">{t(`${ns}.hint`)}</p>
      </div>

      <div className="flex flex-wrap gap-2">
        {VALIDITY_OPTIONS.map(({ value, labelKey }) => {
          const label =
            value === null
              ? t(`${ns}.lifetime`)
              : t(`${ns}.days`).replace("{{n}}", String(value));
          const isSelected = selected === value;
          return (
            <button
              key={String(value)}
              onClick={() => {
                setSelected(value);
                setSaved(false);
              }}
              className={`px-4 py-2 rounded-full text-sm border transition-colors ${
                isSelected
                  ? "bg-primary text-background border-primary font-semibold"
                  : "border-border text-text-secondary hover:border-primary hover:text-primary"
              }`}
            >
              {label}
            </button>
          );
        })}
      </div>

      {error && <p className="text-danger text-sm">{error}</p>}

      <div className="flex items-center gap-3">
        <button
          onClick={handleSave}
          disabled={saving}
          className="btn-primary text-sm disabled:opacity-50"
        >
          {saving ? t("common.loading") : t(`${ns}.save`)}
        </button>
        {saved && (
          <span className="text-primary text-sm">{t(`${ns}.saved`)}</span>
        )}
      </div>
    </div>
  );
}
