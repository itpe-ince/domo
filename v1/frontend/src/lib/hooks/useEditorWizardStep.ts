"use client";

/**
 * useEditorWizardStep — editor-responsive-redesign PDCA (#3, Step 1).
 *
 * Step state machine for the mobile wizard (`< md`). Defaults to a 3-step
 * flow (`type → content → publish`); when `type === "product"` the array
 * grows to 4 steps with `product_meta` inserted between `content` and
 * `publish`. The hook auto-corrects `step` if the post type changes while a
 * now-removed step is current (e.g. switch product → general while on
 * `product_meta` → fall back to `content`).
 *
 * Step validation is intentionally NOT in this hook. Each EditorStepXxx
 * component decides when its "다음" button is enabled, then calls `goNext()`.
 *
 * Created in Step 1 but not wired into page.tsx until Step 5
 * (EditorMobileWizard integration). Pattern source: design §4.2, §4.3.
 */
import { useCallback, useEffect, useMemo, useState } from "react";

export type WizardStep = "type" | "content" | "product_meta" | "publish-options" | "publish";

const GENERAL_STEPS: readonly WizardStep[] = ["type", "content", "publish-options", "publish"];
const PRODUCT_STEPS: readonly WizardStep[] = [
  "type",
  "content",
  "product_meta",
  "publish-options",
  "publish",
];

export interface UseEditorWizardStepOptions {
  type: "general" | "product";
  initialStep?: WizardStep;
}

export interface UseEditorWizardStepReturn {
  step: WizardStep;
  steps: readonly WizardStep[];
  isFirstStep: boolean;
  isLastStep: boolean;
  goNext: () => void;
  goPrev: () => void;
  goTo: (s: WizardStep) => void;
}

export function useEditorWizardStep({
  type,
  initialStep = "type",
}: UseEditorWizardStepOptions): UseEditorWizardStepReturn {
  const steps = type === "product" ? PRODUCT_STEPS : GENERAL_STEPS;
  const [step, setStep] = useState<WizardStep>(initialStep);

  // Auto-correct: if the active step is no longer in the steps array (e.g.,
  // user was on `product_meta` and the post type just switched to general),
  // fall back to "content" — the closest meaningful neighbor.
  useEffect(() => {
    if (!steps.includes(step)) {
      setStep("content");
    }
  }, [step, steps]);

  const currentIndex = Math.max(0, steps.indexOf(step));
  const isFirstStep = currentIndex <= 0;
  const isLastStep = currentIndex >= steps.length - 1;

  const goNext = useCallback(() => {
    setStep((prev) => {
      const idx = steps.indexOf(prev);
      if (idx < 0 || idx >= steps.length - 1) return prev;
      return steps[idx + 1];
    });
  }, [steps]);

  const goPrev = useCallback(() => {
    setStep((prev) => {
      const idx = steps.indexOf(prev);
      if (idx <= 0) return prev;
      return steps[idx - 1];
    });
  }, [steps]);

  const goTo = useCallback((s: WizardStep) => {
    setStep(s);
  }, []);

  return useMemo(
    () => ({
      step,
      steps,
      isFirstStep,
      isLastStep,
      goNext,
      goPrev,
      goTo,
    }),
    [step, steps, isFirstStep, isLastStep, goNext, goPrev, goTo]
  );
}
