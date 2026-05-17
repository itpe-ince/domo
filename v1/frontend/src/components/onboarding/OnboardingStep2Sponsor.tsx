/**
 * OnboardingStep2Sponsor — Step 2 of the growth-funnel wizard.
 *
 * Explains the Blue Bird sponsorship value proposition and opens
 * BluebirdModal pre-loaded with the most-followed recommended artist.
 *
 * Analytics:
 *   - captureEvent onboarding_step { step: 2 } on mount
 *   - captureEvent first_action { action: "sponsor" } on sponsor_success callback
 *   - captureEvent onboarding_skip { step: 2 } on skip
 */

"use client";

import { useCallback, useEffect, useState } from "react";
import { useI18n } from "@/i18n";
import { captureEvent } from "@/lib/analytics/capture";
import { fetchRecommendedArtists, RecommendedArtist } from "@/lib/api";
import { BluebirdModal } from "@/components/BluebirdModal";

interface OnboardingStep2SponsorProps {
  onNext: (sponsored: boolean) => void;
  onSkip: () => void;
}

export function OnboardingStep2Sponsor({
  onNext,
  onSkip,
}: OnboardingStep2SponsorProps) {
  const { t } = useI18n();
  const [artist, setArtist] = useState<RecommendedArtist | null>(null);
  const [artistLoadFailed, setArtistLoadFailed] = useState(false);
  const [loadingArtist, setLoadingArtist] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [sponsored, setSponsored] = useState(false);

  // Fire step event on mount and load the first recommended artist
  useEffect(() => {
    captureEvent({ type: "onboarding_step", step: 2 });
    void loadArtist();
  }, []);

  async function loadArtist() {
    setLoadingArtist(true);
    setArtistLoadFailed(false);
    try {
      const data = await fetchRecommendedArtists(1);
      if (data.length > 0) {
        setArtist(data[0]);
      } else {
        setArtistLoadFailed(true);
      }
    } catch {
      // Non-fatal: surface as a load-failed state so the CTA button never
      // appears in an unresponsive form (B-2 bugfix: previously the button
      // rendered but click was silently dropped because the modal render
      // gate required a non-null `artist`).
      setArtistLoadFailed(true);
    } finally {
      setLoadingArtist(false);
    }
  }

  const handleSponsorSuccess = useCallback(() => {
    setShowModal(false);
    setSponsored(true);
    captureEvent({ type: "first_action", action: "sponsor" });
  }, []);

  const handleNext = useCallback(() => {
    onNext(sponsored);
  }, [sponsored, onNext]);

  const handleSkip = useCallback(() => {
    captureEvent({ type: "onboarding_skip", step: 2 });
    onSkip();
  }, [onSkip]);

  const bulletKeys = [
    "onboarding.step2.bullet1",
    "onboarding.step2.bullet2",
    "onboarding.step2.bullet3",
  ] as const;

  return (
    <>
      <div className="space-y-5">
        <div className="text-center space-y-1">
          <p className="text-3xl" aria-hidden="true">🐦</p>
          <h2 className="text-xl font-bold text-text-primary">
            {t("onboarding.step2.title")}
          </h2>
          <p className="text-sm text-text-secondary">
            {t("onboarding.step2.subtitle")}
          </p>
        </div>

        {/* Value proposition bullets */}
        <ul className="space-y-3" aria-label={t("onboarding.step2.bulletsAriaLabel")}>
          {bulletKeys.map((key) => (
            <li key={key} className="flex items-start gap-3">
              <span
                className="mt-0.5 w-5 h-5 rounded-full bg-primary/15 text-primary flex items-center justify-center flex-shrink-0 text-xs font-bold"
                aria-hidden="true"
              >
                ✓
              </span>
              <span className="text-sm text-text-secondary">{t(key)}</span>
            </li>
          ))}
        </ul>

        {/* Sponsored success state */}
        {sponsored && (
          <div className="card border-primary/30 bg-primary/5 p-4 text-center space-y-1">
            <p className="text-primary font-semibold text-sm">
              {t("onboarding.step2.sponsoredSuccess")}
            </p>
            <p className="text-xs text-text-muted">
              {artist ? `@${artist.username}` : ""}
            </p>
          </div>
        )}

        {/* CTA area */}
        <div className="flex flex-col gap-2 pt-1">
          {!sponsored && artist && (
            <button
              type="button"
              onClick={() => setShowModal(true)}
              className="btn-primary w-full"
            >
              {t("onboarding.step2.ctaWithArtist").replace(
                "{{artistName}}",
                artist.username
              )}
            </button>
          )}

          {!sponsored && !artist && loadingArtist && (
            <button
              type="button"
              disabled
              className="btn-primary w-full opacity-60 cursor-wait"
            >
              {t("onboarding.step2.cta")}
            </button>
          )}

          {!sponsored && !artist && artistLoadFailed && (
            <p
              role="status"
              className="text-xs text-text-muted text-center py-2"
            >
              {t("onboarding.step1.noArtists")}
            </p>
          )}

          <button
            type="button"
            onClick={handleNext}
            className={sponsored ? "btn-primary w-full" : "btn-secondary w-full"}
          >
            {sponsored
              ? t("onboarding.step2.continueAfterSponsor")
              : t("common.next") + " →"}
          </button>

          {!sponsored && (
            <button
              type="button"
              onClick={handleSkip}
              className="text-sm text-text-muted hover:text-text-primary transition-colors py-1"
            >
              {t("onboarding.common.laterLink")}
            </button>
          )}
        </div>
      </div>

      {/* BluebirdModal integration — B-1 regression 0 */}
      {showModal && artist && (
        <BluebirdModal
          artistId={artist.user_id}
          artistName={artist.username}
          onClose={() => setShowModal(false)}
          onSuccess={handleSponsorSuccess}
        />
      )}
    </>
  );
}
