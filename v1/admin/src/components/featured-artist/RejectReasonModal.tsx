"use client";

import { useEffect, useRef, useState } from "react";

const MIN_LENGTH = 10;
const MAX_LENGTH = 500;

interface RejectReasonModalProps {
  open: boolean;
  onClose: () => void;
  onConfirm: (reason: string) => void;
  loading: boolean;
}

export function RejectReasonModal({
  open,
  onClose,
  onConfirm,
  loading,
}: RejectReasonModalProps) {
  const [reason, setReason] = useState("");
  const [error, setError] = useState<string | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const titleId = "reject-modal-title";

  // 모달 열릴 때 초기화 + focus
  useEffect(() => {
    if (open) {
      setReason("");
      setError(null);
      setTimeout(() => textareaRef.current?.focus(), 50);
    }
  }, [open]);

  // Esc 키로 닫기
  useEffect(() => {
    if (!open) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && !loading) onClose();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [open, loading, onClose]);

  function handleSubmit() {
    const trimmed = reason.trim();
    if (trimmed.length < MIN_LENGTH) {
      setError(`거부 사유는 최소 ${MIN_LENGTH}자 이상 입력해 주세요.`);
      return;
    }
    setError(null);
    onConfirm(trimmed);
  }

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      style={{ backgroundColor: "rgba(11,18,32,0.85)" }}
      onClick={(e) => {
        if (e.target === e.currentTarget && !loading) onClose();
      }}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        className="bg-admin-surface border border-admin-border rounded-xl shadow-xl w-full max-w-md mx-4 p-6"
      >
        {/* 헤더 */}
        <div className="flex items-center justify-between mb-4">
          <h2
            id={titleId}
            className="text-base font-semibold text-admin-fg"
          >
            거부 사유 입력
          </h2>
          <button
            onClick={onClose}
            disabled={loading}
            aria-label="닫기"
            className="text-admin-muted hover:text-admin-fg transition-colors disabled:opacity-40"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* 설명 */}
        <p className="text-sm text-admin-muted mb-3">
          이 후보를 거부하는 사유를 입력해 주세요. 모델 학습에 활용됩니다.
        </p>

        {/* textarea */}
        <textarea
          ref={textareaRef}
          rows={4}
          maxLength={MAX_LENGTH}
          value={reason}
          onChange={(e) => {
            setReason(e.target.value);
            if (error) setError(null);
          }}
          disabled={loading}
          placeholder="거부 사유를 구체적으로 입력해 주세요..."
          className="w-full bg-admin-surface-2 border border-admin-border rounded-lg px-3 py-2 text-sm text-admin-fg placeholder:text-admin-muted resize-none focus:outline-none focus:border-admin-accent disabled:opacity-50"
        />

        {/* 글자 수 + 에러 */}
        <div className="flex items-center justify-between mt-1.5 mb-4">
          <span className="text-[11px] text-admin-muted">
            최소 {MIN_LENGTH}자, 최대 {MAX_LENGTH}자
          </span>
          <span className={`text-[11px] ${reason.trim().length < MIN_LENGTH ? "text-admin-muted" : "text-admin-fg"}`}>
            현재 {reason.length}자
          </span>
        </div>

        {error && (
          <p className="text-xs text-red-400 mb-3">{error}</p>
        )}

        {/* 액션 버튼 */}
        <div className="flex justify-end gap-2">
          <button
            onClick={onClose}
            disabled={loading}
            className="px-4 py-2 text-sm rounded-lg border border-admin-border text-admin-muted hover:text-admin-fg hover:border-admin-fg transition-colors disabled:opacity-40"
          >
            취소
          </button>
          <button
            onClick={handleSubmit}
            disabled={loading || reason.trim().length < MIN_LENGTH}
            className="px-4 py-2 text-sm rounded-lg bg-red-600 text-white font-medium hover:bg-red-700 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {loading ? "처리 중..." : "거부 확정"}
          </button>
        </div>
      </div>
    </div>
  );
}
