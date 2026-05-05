/**
 * useOnboarding — A-2 Onboarding Funnel
 *
 * Manages first-session detection and growth-funnel wizard state.
 *
 * First-session flag:
 *   localStorage key "domo_is_first_session" is written to "false" once the
 *   user dismisses or completes the wizard. Until then `isFirstSession` is true
 *   so that any code path can decide whether to show the wizard.
 *
 * State machine:
 *   idle → step1 → step2 → step3 → done
 *   Any step can transition to `done` via skip.
 *
 * Usage:
 *   const { wizardStep, goNext, skipStep, completedFollows, markSponsored, finish } = useOnboarding();
 */

"use client";

import { useCallback, useEffect, useState } from "react";

export type WizardStep = "idle" | 1 | 2 | 3 | "done";

const FIRST_SESSION_KEY = "domo_is_first_session";
const WIZARD_SEEN_KEY = "domo_onboarding_wizard_seen";

function readFirstSession(): boolean {
  if (typeof window === "undefined") return false;
  // If the "seen" key is already set, wizard was already shown.
  if (localStorage.getItem(WIZARD_SEEN_KEY) === "true") return false;
  // If "first_session" was explicitly set to false, the wizard was completed.
  const raw = localStorage.getItem(FIRST_SESSION_KEY);
  if (raw === "false") return false;
  return true;
}

function markWizardSeen() {
  if (typeof window === "undefined") return;
  localStorage.setItem(FIRST_SESSION_KEY, "false");
  localStorage.setItem(WIZARD_SEEN_KEY, "true");
}

export function useOnboarding() {
  const [isFirstSession, setIsFirstSession] = useState(false);
  const [wizardStep, setWizardStep] = useState<WizardStep>("idle");

  // Count of artists followed during step 1
  const [followedCount, setFollowedCount] = useState(0);
  // Whether a sponsorship was initiated during step 2
  const [sponsored, setSponsored] = useState(false);

  // Hydrate on mount (SSR-safe) and listen for cross-component reopens
  useEffect(() => {
    function sync() {
      const first = readFirstSession();
      setIsFirstSession(first);
      if (first) {
        setWizardStep(1);
        setFollowedCount(0);
        setSponsored(false);
      } else {
        setWizardStep("done");
      }
    }

    sync();

    // Listen for storage changes (same-tab reopen via reopenWizard())
    window.addEventListener("storage", sync);
    window.addEventListener("domo-onboarding-reopen", sync);
    return () => {
      window.removeEventListener("storage", sync);
      window.removeEventListener("domo-onboarding-reopen", sync);
    };
  }, []);

  /** Move from current numbered step to the next, or to done after step 3. */
  const goNext = useCallback(() => {
    setWizardStep((prev) => {
      if (prev === 1) return 2;
      if (prev === 2) return 3;
      return "done";
    });
  }, []);

  /** Skip the current step and advance to done (or next step). */
  const skipStep = useCallback((step: number) => {
    if (step >= 3) {
      setWizardStep("done");
    } else {
      setWizardStep((step + 1) as WizardStep);
    }
  }, []);

  /** Register that an artist was followed in step 1. */
  const incrementFollowed = useCallback(() => {
    setFollowedCount((n) => n + 1);
  }, []);

  /** Mark that the user initiated a sponsorship in step 2. */
  const markSponsored = useCallback(() => {
    setSponsored(true);
  }, []);

  /**
   * Finish the wizard (step 3 complete or any close).
   * Persists seen flag so the wizard is not shown again.
   */
  const finish = useCallback(() => {
    markWizardSeen();
    setWizardStep("done");
    setIsFirstSession(false);
  }, []);

  /**
   * Force-open the wizard (e.g. "restart onboarding" from sidebar indicator).
   * Clears the "seen" flag so AppShell's useOnboarding hook also picks it up
   * via the dispatched custom event.
   */
  const reopenWizard = useCallback(() => {
    if (typeof window !== "undefined") {
      localStorage.removeItem(WIZARD_SEEN_KEY);
      // Notify other useOnboarding instances in the same tab
      window.dispatchEvent(new Event("domo-onboarding-reopen"));
    }
    setWizardStep(1);
    setFollowedCount(0);
    setSponsored(false);
    setIsFirstSession(true);
  }, []);

  return {
    isFirstSession,
    wizardStep,
    followedCount,
    sponsored,
    goNext,
    skipStep,
    incrementFollowed,
    markSponsored,
    finish,
    reopenWizard,
  };
}
