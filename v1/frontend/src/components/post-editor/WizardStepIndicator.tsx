"use client";

/**
 * WizardStepIndicator — editor-responsive-redesign PDCA (#3, Step 4).
 *
 * Mobile wizard top-bar showing progress: dot + line + label per step.
 * Reads steps array + currentStep from useEditorWizardStep.
 *
 * Pattern source: design §4.1 (WizardStepIndicator).
 */

import { useI18n } from "@/i18n";
import type { WizardStep } from "@/lib/hooks/useEditorWizardStep";

const STEP_LABEL_KEYS: Record<WizardStep, string> = {
  type: "post.editor.wizard.steps.type",
  content: "post.editor.wizard.steps.content",
  product_meta: "post.editor.wizard.steps.productMeta",
  "publish-options": "post.editor.wizard.steps.publishOptions",
  publish: "post.editor.wizard.steps.publish",
};

export interface WizardStepIndicatorProps {
  steps: readonly WizardStep[];
  currentStep: WizardStep;
}

export function WizardStepIndicator({
  steps,
  currentStep,
}: WizardStepIndicatorProps) {
  const { t } = useI18n();
  const currentIndex = steps.indexOf(currentStep);
  return (
    <ol
      className="flex items-center justify-between gap-1 px-4 py-3 text-xs"
      aria-label={t("post.editor.wizard.indicator")}
    >
      {steps.map((s, i) => {
        const isActive = i === currentIndex;
        const isDone = i < currentIndex;
        return (
          <li
            key={s}
            className="flex items-center gap-1 flex-1"
            aria-current={isActive ? "step" : undefined}
          >
            <span
              className={
                isActive
                  ? "w-6 h-6 rounded-full bg-primary text-background flex items-center justify-center font-medium text-[11px]"
                  : isDone
                    ? "w-6 h-6 rounded-full bg-primary/30 text-primary flex items-center justify-center text-[11px]"
                    : "w-6 h-6 rounded-full bg-surface-hover text-text-muted flex items-center justify-center text-[11px]"
              }
              aria-hidden
            >
              {isDone ? "✓" : i + 1}
            </span>
            <span
              className={
                isActive
                  ? "text-text-primary font-medium truncate"
                  : "text-text-muted truncate"
              }
            >
              {t(STEP_LABEL_KEYS[s])}
            </span>
            {i < steps.length - 1 && (
              <span
                className={
                  isDone
                    ? "flex-1 h-px bg-primary/40"
                    : "flex-1 h-px bg-border"
                }
                aria-hidden
              />
            )}
          </li>
        );
      })}
    </ol>
  );
}
