"use client";

/**
 * KeyboardShortcutsHelp — Phase 12 C-3
 *
 * 전역 ? 키로 열리는 단축키 도움말 모달.
 * Phase 11 D-1: 3개 카테고리 (feed/editor/general)
 * Phase 12 C-3: 4개 카테고리로 확장 (navigation/feed/editor/general)
 * - Navigation 섹션 신규 추가 (g-시퀀스 6개)
 * - Feed 섹션에 b (북마크 토글) 추가
 * - Editor 섹션에 n (새 포스트) 추가
 * - General 섹션에 / (검색 포커스) 추가
 * - g-시퀀스는 두 <Kbd> 요소를 나란히 표시
 * - 5 locale i18n (keyboardShortcuts.* 네임스페이스)
 * - aria-modal 접근성 유지
 */

import { useEffect, useRef } from "react";
import { useI18n } from "@/i18n";

interface KeyboardShortcutsHelpProps {
  open: boolean;
  onClose: () => void;
}

/** 키보드 키 시각적 표기 컴포넌트 */
function Kbd({ children }: { children: React.ReactNode }) {
  return (
    <kbd
      className="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-mono
                 bg-surface-hover text-text-secondary border border-border"
    >
      {children}
    </kbd>
  );
}

interface ShortcutRowProps {
  keys: React.ReactNode[];
  description: string;
}

function ShortcutRow({ keys, description }: ShortcutRowProps) {
  return (
    <tr className="border-b border-border/40 last:border-b-0">
      <td className="py-2 pr-6 text-right align-middle whitespace-nowrap">
        <span className="inline-flex items-center gap-1">
          {keys.map((k, i) => (
            <span key={i} className="inline-flex items-center gap-1">
              {i > 0 && (
                <span className="text-text-muted text-xs px-0.5">/</span>
              )}
              {k}
            </span>
          ))}
        </span>
      </td>
      <td className="py-2 pl-2 text-sm text-text-primary align-middle">
        {description}
      </td>
    </tr>
  );
}

/** g-시퀀스 키 표기: 두 Kbd를 나란히 표시 */
function SequenceKeys({ first, second }: { first: string; second: string }) {
  return (
    <span className="inline-flex items-center gap-0.5">
      <Kbd>{first}</Kbd>
      <Kbd>{second}</Kbd>
    </span>
  );
}

export function KeyboardShortcutsHelp({
  open,
  onClose,
}: KeyboardShortcutsHelpProps) {
  const { t } = useI18n();
  const dialogRef = useRef<HTMLDivElement>(null);

  // ESC 닫기 처리 — Dialog 내부 focus trap 과 충돌 방지를 위해
  // 이 모달 자체의 keydown 에서만 처리한다
  useEffect(() => {
    if (!open) return;

    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") {
        e.stopPropagation();
        onClose();
      }
    }

    // capture: true — useGlobalHotkeys보다 먼저 ESC를 잡아야 함
    window.addEventListener("keydown", handleKeyDown, true);
    return () => {
      window.removeEventListener("keydown", handleKeyDown, true);
    };
  }, [open, onClose]);

  // 모달 열릴 때 포커스 이동 (a11y)
  useEffect(() => {
    if (open && dialogRef.current) {
      dialogRef.current.focus();
    }
  }, [open]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm px-4"
      role="presentation"
      onClick={onClose}
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-label={t("keyboardShortcuts.title")}
        tabIndex={-1}
        className="w-full max-w-sm bg-surface border border-border rounded-2xl shadow-2xl
                   overflow-hidden outline-none max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        {/* 헤더 */}
        <header className="flex items-center justify-between px-5 pt-5 pb-3 border-b border-border sticky top-0 bg-surface z-10">
          <h2 className="text-base font-bold text-text-primary">
            {t("keyboardShortcuts.title")}
          </h2>
          <button
            type="button"
            onClick={onClose}
            aria-label={t("keyboardShortcuts.close")}
            className="text-text-muted hover:text-text-primary transition-colors rounded p-1
                       hover:bg-surface-hover focus:outline-none focus:ring-2 focus:ring-primary/50"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </header>

        {/* 단축키 목록 */}
        <div className="px-5 py-4 space-y-5">
          {/* Navigation 카테고리 (Phase 12 C-3 신규) */}
          <section aria-labelledby="shortcut-category-navigation">
            <h3
              id="shortcut-category-navigation"
              className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-2"
            >
              {t("keyboardShortcuts.category.navigation")}
            </h3>
            <table className="w-full">
              <tbody>
                <ShortcutRow
                  keys={[<SequenceKeys key="g-h" first="g" second="h" />]}
                  description={t("keyboardShortcuts.action.gotoHome")}
                />
                <ShortcutRow
                  keys={[<SequenceKeys key="g-f" first="g" second="f" />]}
                  description={t("keyboardShortcuts.action.gotoFeed")}
                />
                <ShortcutRow
                  keys={[<SequenceKeys key="g-e" first="g" second="e" />]}
                  description={t("keyboardShortcuts.action.gotoExplore")}
                />
                <ShortcutRow
                  keys={[<SequenceKeys key="g-m" first="g" second="m" />]}
                  description={t("keyboardShortcuts.action.gotoMessages")}
                />
                <ShortcutRow
                  keys={[<SequenceKeys key="g-n" first="g" second="n" />]}
                  description={t("keyboardShortcuts.action.gotoNotifications")}
                />
                <ShortcutRow
                  keys={[<SequenceKeys key="g-p" first="g" second="p" />]}
                  description={t("keyboardShortcuts.action.gotoProfile")}
                />
              </tbody>
            </table>
          </section>

          {/* 피드 카테고리 */}
          <section aria-labelledby="shortcut-category-feed">
            <h3
              id="shortcut-category-feed"
              className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-2"
            >
              {t("keyboardShortcuts.category.feed")}
            </h3>
            <table className="w-full">
              <tbody>
                <ShortcutRow
                  keys={[<Kbd key="j">j</Kbd>]}
                  description={t("keyboardShortcuts.action.nextPost")}
                />
                <ShortcutRow
                  keys={[<Kbd key="k">k</Kbd>]}
                  description={t("keyboardShortcuts.action.prevPost")}
                />
                <ShortcutRow
                  keys={[<Kbd key="b">b</Kbd>]}
                  description={t("keyboardShortcuts.action.bookmarkToggle")}
                />
              </tbody>
            </table>
          </section>

          {/* 등록(에디터) 카테고리 */}
          <section aria-labelledby="shortcut-category-editor">
            <h3
              id="shortcut-category-editor"
              className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-2"
            >
              {t("keyboardShortcuts.category.editor")}
            </h3>
            <table className="w-full">
              <tbody>
                <ShortcutRow
                  keys={[
                    <span key="cmd-s" className="inline-flex items-center gap-1">
                      <Kbd>⌘</Kbd>
                      <Kbd>S</Kbd>
                    </span>,
                    <span key="ctrl-s" className="inline-flex items-center gap-1">
                      <Kbd>Ctrl</Kbd>
                      <Kbd>S</Kbd>
                    </span>,
                  ]}
                  description={t("keyboardShortcuts.action.saveDraft")}
                />
                <ShortcutRow
                  keys={[<Kbd key="n">n</Kbd>]}
                  description={t("keyboardShortcuts.action.newPost")}
                />
              </tbody>
            </table>
          </section>

          {/* 일반 카테고리 */}
          <section aria-labelledby="shortcut-category-general">
            <h3
              id="shortcut-category-general"
              className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-2"
            >
              {t("keyboardShortcuts.category.general")}
            </h3>
            <table className="w-full">
              <tbody>
                <ShortcutRow
                  keys={[<Kbd key="slash">/</Kbd>]}
                  description={t("keyboardShortcuts.action.searchFocus")}
                />
                <ShortcutRow
                  keys={[<Kbd key="q">?</Kbd>]}
                  description={t("keyboardShortcuts.action.showHelp")}
                />
                <ShortcutRow
                  keys={[<Kbd key="esc">Esc</Kbd>]}
                  description={t("keyboardShortcuts.action.closeModal")}
                />
              </tbody>
            </table>
          </section>
        </div>
      </div>
    </div>
  );
}
