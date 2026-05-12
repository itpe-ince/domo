/**
 * OnboardingProgress — progress dot indicator for the 3-step wizard.
 * Matches the StepDots pattern from BluebirdModal for visual consistency.
 */

interface OnboardingProgressProps {
  currentStep: 1 | 2 | 3;
  totalSteps?: number;
}

export function OnboardingProgress({
  currentStep,
  totalSteps = 3,
}: OnboardingProgressProps) {
  return (
    <div
      className="flex items-center justify-center gap-2"
      aria-label={`${currentStep} / ${totalSteps} 단계`}
      role="progressbar"
      aria-valuenow={currentStep}
      aria-valuemin={1}
      aria-valuemax={totalSteps}
    >
      {Array.from({ length: totalSteps }).map((_, i) => {
        const step = i + 1;
        const isActive = step === currentStep;
        const isDone = step < currentStep;
        return (
          <span
            key={i}
            className={`block rounded-full transition-all duration-300 ${
              isActive
                ? "w-5 h-2.5 bg-primary"
                : isDone
                ? "w-2.5 h-2.5 bg-primary/50"
                : "w-2.5 h-2.5 bg-border"
            }`}
            aria-hidden="true"
          />
        );
      })}
    </div>
  );
}
