"use client";

import { useCallback, useState } from "react";
import { usePathname } from "next/navigation";
import { MobileTabBar } from "./MobileTabBar";
import { Sidebar } from "./Sidebar";
import { SkipLink } from "./SkipLink";
import { OnboardingWizard } from "./onboarding/OnboardingWizard";
import { CognitiveSimpleModeProvider } from "./CognitiveSimpleModeProvider";
import { KeyboardShortcutsHelp } from "./KeyboardShortcutsHelp";
import { useOnboarding } from "@/lib/hooks/useOnboarding";
import { useGlobalHotkeys } from "@/lib/hooks/useGlobalHotkeys";
import { useMe } from "@/lib/useMe";

/**
 * 화면 중앙에 가장 가까운 피드 카드의 인덱스를 반환한다.
 * data-feed-item 속성을 가진 요소를 기준으로 계산.
 */
function getActiveIndex(cards: HTMLElement[]): number {
  const centerY = window.innerHeight / 2;
  let closest = 0;
  let minDist = Infinity;
  cards.forEach((card, i) => {
    const rect = card.getBoundingClientRect();
    const cardCenterY = rect.top + rect.height / 2;
    const dist = Math.abs(cardCenterY - centerY);
    if (dist < minDist) {
      minDist = dist;
      closest = i;
    }
  });
  return closest;
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const { me } = useMe();
  const { wizardStep, finish } = useOnboarding();
  const pathname = usePathname();
  const [helpOpen, setHelpOpen] = useState(false);

  // 피드 페이지 여부 — j/k 단축키 활성 조건
  const isFeedPage = pathname === "/" || pathname === "/feed";

  // Show the wizard only for authenticated first-session users.
  // wizardStep is "idle" until hydration and "done" once completed.
  const showWizard =
    me !== null && (wizardStep === 1 || wizardStep === 2 || wizardStep === 3);

  const handleWizardClose = useCallback(() => {
    finish();
  }, [finish]);

  // j/k 피드 내비게이션 핸들러
  const navigateFeed = useCallback((direction: "next" | "prev") => {
    const cards = Array.from(
      document.querySelectorAll<HTMLElement>("[data-feed-item]")
    );
    if (cards.length === 0) return;
    const activeIdx = getActiveIndex(cards);
    const targetIdx = direction === "next" ? activeIdx + 1 : activeIdx - 1;
    if (targetIdx < 0 || targetIdx >= cards.length) return;
    cards[targetIdx].scrollIntoView({ behavior: "smooth", block: "center" });
    cards[targetIdx].focus({ preventScroll: true });
  }, []);

  // 전역 단축키 등록
  useGlobalHotkeys([
    {
      key: "j",
      handler: () => navigateFeed("next"),
      enabled: isFeedPage && !helpOpen,
    },
    {
      key: "k",
      handler: () => navigateFeed("prev"),
      enabled: isFeedPage && !helpOpen,
    },
    {
      key: "?",
      handler: () => setHelpOpen(true),
      enabled: !helpOpen,
    },
  ]);

  return (
    <CognitiveSimpleModeProvider>
      {/* H'-1: Skip navigation link — WCAG 2.4.1 Bypass Blocks (Level A) */}
      <SkipLink />

      <div className="flex min-h-screen">
        <Sidebar />
        {/* Main column has bottom padding on mobile so content isn't hidden
            behind the fixed MobileTabBar.
            id="main-content" is the SkipLink anchor target. */}
        <div id="main-content" className="flex-1 min-w-0 pb-16 md:pb-0">
          {children}
        </div>
      </div>
      <MobileTabBar />

      {/* A-2: Growth-funnel onboarding wizard — shown on first session after login */}
      {showWizard && <OnboardingWizard onClose={handleWizardClose} />}

      {/* Phase 11 D-1: 키보드 단축키 도움말 모달 */}
      <KeyboardShortcutsHelp open={helpOpen} onClose={() => setHelpOpen(false)} />
    </CognitiveSimpleModeProvider>
  );
}
