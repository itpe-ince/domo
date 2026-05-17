"use client";

import { useCallback, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { BuildVersionWatcher } from "./BuildVersionWatcher";
import { MobileTabBar } from "./MobileTabBar";
import { Sidebar } from "./Sidebar";
import { SkipLink } from "./SkipLink";
import { OnboardingWizard } from "./onboarding/OnboardingWizard";
import { KeyboardShortcutsHelp } from "./KeyboardShortcutsHelp";
import { useOnboarding } from "@/lib/hooks/useOnboarding";
import { useGlobalHotkeys } from "@/lib/hooks/useGlobalHotkeys";
import { useSequenceHotkeys } from "@/lib/hooks/useSequenceHotkeys";
import { useMe } from "@/lib/useMe";
import { FollowingProvider } from "@/lib/FollowingContext";

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
  const router = useRouter();
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

  // Phase 12 C-3: / 단축키 — SearchBar 포커스
  const focusSearchBar = useCallback(() => {
    const searchInput = document.querySelector<HTMLElement>("[data-search-input]");
    if (searchInput) {
      searchInput.focus();
    }
  }, []);

  // Phase 12 C-3: b 단축키 — 뷰포트 중앙 활성 포스트 북마크 토글
  // D-1의 getActiveIndex 헬퍼 함수 재사용, data-post-id/data-bookmark-btn 속성 준용
  const toggleActivePostBookmark = useCallback(() => {
    const cards = Array.from(
      document.querySelectorAll<HTMLElement>("[data-feed-item]")
    );
    if (cards.length === 0) return;

    const activeIdx = getActiveIndex(cards);
    const activeCard = cards[activeIdx];

    // 북마크 버튼을 프로그래매틱하게 클릭 (기존 북마크 로직 재활용)
    const bookmarkBtn = activeCard.querySelector<HTMLElement>("[data-bookmark-btn]");
    if (bookmarkBtn) {
      bookmarkBtn.click();
    }
  }, []);

  // Phase 12 C-3: g-시퀀스 navigation 단축키 (useSequenceHotkeys)
  useSequenceHotkeys([
    {
      sequence: ["g", "h"],
      handler: () => router.push("/"),
      enabled: !helpOpen,
    },
    {
      sequence: ["g", "f"],
      handler: () => router.push("/feed"),
      enabled: !helpOpen,
    },
    {
      sequence: ["g", "e"],
      handler: () => router.push("/explore"),
      enabled: !helpOpen,
    },
    {
      sequence: ["g", "m"],
      handler: () => router.push("/me/messages"),
      enabled: !helpOpen,
    },
    {
      sequence: ["g", "n"],
      handler: () => router.push("/notifications"),
      enabled: !helpOpen,
    },
    {
      sequence: ["g", "p"],
      handler: () => {
        if (me?.id) router.push(`/users/${me.id}`);
      },
      enabled: !helpOpen && !!me,
    },
  ]);

  // 전역 단축키 등록 (D-1 기존 + C-3 신규)
  useGlobalHotkeys([
    // D-1 기존 단축키 (변경 없음)
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
    // Phase 12 C-3 신규 단축키
    {
      key: "n",
      handler: () => router.push("/posts/new"),
      enabled: !helpOpen,
      // preventInInputs: true (default) — input 포커스 시 자동 비활성
    },
    {
      key: "/",
      handler: (e) => {
        e.preventDefault();
        focusSearchBar();
      },
      enabled: !helpOpen,
    },
    {
      key: "b",
      handler: () => toggleActivePostBookmark(),
      enabled: !helpOpen,
      // preventInInputs: true (default)
    },
  ]);

  return (
    <FollowingProvider>
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

      {/* Phase 11 D-1 / Phase 12 C-3: 키보드 단축키 도움말 모달 */}
      <KeyboardShortcutsHelp open={helpOpen} onClose={() => setHelpOpen(false)} />

      {/* Deployment-stuck mitigation (plan C2): polls /api/build-id and
          surfaces a reload toast when a new server build is detected. */}
      <BuildVersionWatcher />
    </FollowingProvider>
  );
}
