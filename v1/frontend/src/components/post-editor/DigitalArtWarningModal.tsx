"use client";

/**
 * DigitalArtWarningModal — 미디어 첨부 시 등록 버튼 클릭하면 표시되는 경고 모달.
 *
 * 요구사항 ②: 기존 artCheckNote 상시 표시를 제거하고, 등록 직전 한 번만 표시.
 * 사용자가 "확인 후 등록" 누르면 onConfirm 호출 → 실제 등록 진행.
 * "취소" 누르면 모달 닫힘.
 *
 * LoginModal 의 fixed inset-0 / z-50 / role="dialog" 패턴을 따름.
 */

import { useEffect, useRef } from "react";
import { useI18n } from "@/i18n";

export interface DigitalArtWarningModalProps {
  open: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export function DigitalArtWarningModal({
  open,
  onConfirm,
  onCancel,
}: DigitalArtWarningModalProps) {
  const { t } = useI18n();
  const confirmRef = useRef<HTMLButtonElement>(null);

  // 모달 열릴 때 확인 버튼에 포커스
  useEffect(() => {
    if (open) {
      requestAnimationFrame(() => confirmRef.current?.focus());
    }
  }, [open]);

  // Esc 키로 닫기
  useEffect(() => {
    if (!open) return;
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") onCancel();
    }
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [open, onCancel]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm px-4"
      role="presentation"
      onClick={(e) => {
        if (e.target === e.currentTarget) onCancel();
      }}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="digital-art-warning-title"
        className="bg-background border border-border rounded-2xl shadow-xl w-full max-w-sm p-6 space-y-4"
      >
        <div className="space-y-2">
          <h2
            id="digital-art-warning-title"
            className="text-base font-bold text-text-primary"
          >
            {t("post.digitalArtWarning.title")}
          </h2>
          <p className="text-sm text-text-secondary leading-relaxed">
            {t("post.digitalArtWarning.body")}
          </p>
        </div>

        <div className="flex gap-2 justify-end">
          <button
            type="button"
            onClick={onCancel}
            className="px-4 py-2 rounded-full border border-border text-sm text-text-secondary hover:bg-surface-hover transition-colors"
          >
            {t("post.digitalArtWarning.cancel")}
          </button>
          <button
            ref={confirmRef}
            type="button"
            onClick={onConfirm}
            className="btn-primary text-sm px-4 py-2"
          >
            {t("post.digitalArtWarning.confirm")}
          </button>
        </div>
      </div>
    </div>
  );
}
