/**
 * OnboardingWizard — A-2 Growth Funnel Wizard overlay.
 *
 * Renders a centered modal overlay with the 3-step wizard.
 * Manages step transitions and analytics flow coordination.
 *
 * Analytics flow:
 *   onboarding_start  → on wizard open
 *   onboarding_step   → per step (delegated to each step component)
 *   onboarding_skip   → per skip (delegated to each step component)
 *   onboarding_complete → on finish (delegated to Step 3)
 *
 * ESC key closes the wizard (treated as skip from current step).
 *
 * Constraint: BluebirdModal renders above this overlay (z-[60]) so
 * this component uses z-50 to avoid stacking conflicts.
 */

"use client";

import { useCallback, useEffect, useState } from "react";
import { useI18n } from "@/i18n";
import { captureEvent } from "@/lib/analytics/capture";
import { OnboardingProgress } from "./OnboardingProgress";
import { OnboardingStep1Follow } from "./OnboardingStep1Follow";
import { OnboardingStep2Sponsor } from "./OnboardingStep2Sponsor";
import { OnboardingStep3Discover } from "./OnboardingStep3Discover";

type WizardStep = 1 | 2 | 3;

interface OnboardingWizardProps {
  /** Called when the wizard is dismissed (skip or complete). */
  onClose: () => void;
}

export function OnboardingWizard({ onClose }: OnboardingWizardProps) {
  const { t } = useI18n();
  const [step, setStep] = useState<WizardStep>(1);
  const [followedCount, setFollowedCount] = useState(0);
  const [sponsored, setSponsored] = useState(false);

  // Fire onboarding_start once on mount
  useEffect(() => {
    captureEvent({ type: "onboarding_start" });
  }, []);

  // ESC close
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        captureEvent({ type: "onboarding_skip", step });
        onClose();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [step, onClose]);

  // ── Step 1 handlers ──
  const handleStep1Next = useCallback((count: number) => {
    setFollowedCount(count);
    setStep(2);
  }, []);

  const handleStep1Skip = useCallback(() => {
    setStep(2);
  }, []);

  // ── Step 2 handlers ──
  const handleStep2Next = useCallback((didSponsor: boolean) => {
    setSponsored(didSponsor);
    setStep(3);
  }, []);

  const handleStep2Skip = useCallback(() => {
    setStep(3);
  }, []);

  // ── Step 3 handlers ──
  const handleStep3Complete = useCallback(() => {
    onClose();
  }, [onClose]);

  const handleStep3Skip = useCallback(() => {
    captureEvent({
      type: "onboarding_complete",
      followed: followedCount,
      sponsored,
    });
    onClose();
  }, [followedCount, sponsored, onClose]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 px-4"
      role="dialog"
      aria-modal="true"
      aria-label={t("onboarding.wizard.ariaLabel")}
      onClick={(e) => {
        if (e.target === e.currentTarget) {
          captureEvent({ type: "onboarding_skip", step });
          onClose();
        }
      }}
    >
      <div
        className="card w-full max-w-md p-6 space-y-5 max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header with progress and close */}
        <div className="flex items-center justify-between">
          <OnboardingProgress currentStep={step} totalSteps={3} />
          <button
            type="button"
            onClick={() => {
              captureEvent({ type: "onboarding_skip", step });
              onClose();
            }}
            aria-label={t("common.close")}
            className="text-text-muted hover:text-text-primary transition-colors text-lg focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 rounded"
          >
            ✕
          </button>
        </div>

        {/* Step content */}
        {step === 1 && (
          <OnboardingStep1Follow
            onNext={handleStep1Next}
            onSkip={handleStep1Skip}
          />
        )}
        {step === 2 && (
          <OnboardingStep2Sponsor
            onNext={handleStep2Next}
            onSkip={handleStep2Skip}
          />
        )}
        {step === 3 && (
          <OnboardingStep3Discover
            onComplete={handleStep3Complete}
            onSkip={handleStep3Skip}
            followedCount={followedCount}
            sponsored={sponsored}
          />
        )}
      </div>
    </div>
  );
}
