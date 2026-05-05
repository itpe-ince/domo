"use client";

import { useCallback } from "react";
import { MobileTabBar } from "./MobileTabBar";
import { Sidebar } from "./Sidebar";
import { OnboardingWizard } from "./onboarding/OnboardingWizard";
import { useOnboarding } from "@/lib/hooks/useOnboarding";
import { useMe } from "@/lib/useMe";

export function AppShell({ children }: { children: React.ReactNode }) {
  const { me } = useMe();
  const { wizardStep, finish } = useOnboarding();

  // Show the wizard only for authenticated first-session users.
  // wizardStep is "idle" until hydration and "done" once completed.
  const showWizard =
    me !== null && (wizardStep === 1 || wizardStep === 2 || wizardStep === 3);

  const handleWizardClose = useCallback(() => {
    finish();
  }, [finish]);

  return (
    <>
      <div className="flex min-h-screen">
        <Sidebar />
        {/* Main column has bottom padding on mobile so content isn't hidden
            behind the fixed MobileTabBar. */}
        <div className="flex-1 min-w-0 pb-16 md:pb-0">{children}</div>
      </div>
      <MobileTabBar />

      {/* A-2: Growth-funnel onboarding wizard — shown on first session after login */}
      {showWizard && <OnboardingWizard onClose={handleWizardClose} />}
    </>
  );
}
