"use client";

/**
 * PublishDrawer — B1: 발행 옵션 Drawer slide-out (right).
 *
 * 데스크탑(≥ md) 전용. 오버레이 + 우측 슬라이드 패널로 PublishOptionsPanel 을 감싼다.
 * - ESC 키로 닫기
 * - 외부 클릭(오버레이)으로 닫기
 * - aria-modal / role="dialog" 접근성 대응
 *
 * 모바일(< md): EditorMobileWizard 의 step 분리 구조 그대로 유지 → 이 컴포넌트 미노출.
 */

import { useEffect } from "react";
import { useI18n } from "@/i18n";
import {
  PublishOptionsPanel,
  type PublishOptionsPanelProps,
} from "./PublishOptionsPanel";

export interface PublishDrawerProps extends PublishOptionsPanelProps {
  isOpen: boolean;
  onClose: () => void;
}

export function PublishDrawer({ isOpen, onClose, ...panelProps }: PublishDrawerProps) {
  const { t } = useI18n();

  // ESC 키로 닫기
  useEffect(() => {
    if (!isOpen) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <>
      {/* 오버레이 */}
      <div
        className="fixed inset-0 bg-black/50 z-40 transition-opacity"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Drawer (우측 slide-out) */}
      <aside
        role="dialog"
        aria-modal="true"
        aria-label={t("post.editor.publishOptions.title")}
        className="fixed top-0 right-0 h-full w-full sm:w-[28rem] bg-background border-l border-border z-50 overflow-y-auto shadow-2xl transition-transform duration-200 translate-x-0"
      >
        {/* Drawer 헤더 */}
        <div className="sticky top-0 bg-background border-b border-border px-5 py-4 flex items-center justify-between z-10">
          <h2 className="text-lg font-semibold text-text-primary">
            {t("post.editor.publishOptions.title")}
          </h2>
          <button
            type="button"
            onClick={onClose}
            aria-label={t("common.close")}
            className="text-text-muted hover:text-text-primary text-2xl leading-none px-2 transition-colors"
          >
            &#x2715;
          </button>
        </div>

        {/* Drawer 본문 */}
        <div className="p-5">
          <PublishOptionsPanel {...panelProps} />
        </div>
      </aside>
    </>
  );
}
