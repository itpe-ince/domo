"use client";

/**
 * FocusManager — Phase 9 L-E
 *
 * 모달 열릴 때 포커스 트랩 (Tab / Shift+Tab 순환, Esc 닫기).
 * BluebirdModal, ReportModal, 경매 입찰 확인 모달에 적용.
 * 모달 닫힐 때 트리거 요소로 포커스 복원.
 */
import { useEffect, useRef } from "react";

const FOCUSABLE_SELECTORS = [
  "a[href]",
  "button:not([disabled])",
  "textarea:not([disabled])",
  "input:not([disabled])",
  "select:not([disabled])",
  "[tabindex]:not([tabindex='-1'])",
].join(", ");

interface FocusManagerProps {
  active: boolean;
  onClose: () => void;
  children: React.ReactNode;
  initialFocusRef?: React.RefObject<HTMLElement | null>;
  returnFocusRef?: React.RefObject<HTMLElement | null>;
}

export function FocusManager({
  active,
  onClose,
  children,
  initialFocusRef,
  returnFocusRef,
}: FocusManagerProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!active) return;

    // 모달 열릴 때 초기 포커스 설정
    const frame = requestAnimationFrame(() => {
      if (initialFocusRef?.current) {
        initialFocusRef.current.focus();
      } else if (containerRef.current) {
        const first = containerRef.current.querySelector<HTMLElement>(FOCUSABLE_SELECTORS);
        first?.focus();
      }
    });

    return () => cancelAnimationFrame(frame);
  }, [active, initialFocusRef]);

  useEffect(() => {
    if (!active) return;

    function handleKeyDown(e: KeyboardEvent) {
      if (!containerRef.current) return;

      if (e.key === "Escape") {
        e.preventDefault();
        onClose();
        return;
      }

      if (e.key !== "Tab") return;

      const focusable = Array.from(
        containerRef.current.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTORS)
      ).filter((el) => !el.closest("[aria-hidden='true']"));

      if (focusable.length === 0) return;

      const first = focusable[0];
      const last = focusable[focusable.length - 1];

      if (e.shiftKey) {
        if (document.activeElement === first) {
          e.preventDefault();
          last.focus();
        }
      } else {
        if (document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    }

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [active, onClose]);

  // 모달 닫힐 때 포커스 복원
  useEffect(() => {
    if (active) return;
    if (returnFocusRef?.current) {
      returnFocusRef.current.focus();
    }
  }, [active, returnFocusRef]);

  return <div ref={containerRef}>{children}</div>;
}
