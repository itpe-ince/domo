"use client";

import { useState } from "react";

interface CollectionRejectModalProps {
  open: boolean;
  collectionId: string | null;
  onClose: () => void;
  onRejected: (id: string, reason: string) => Promise<void>;
}

export function CollectionRejectModal({
  open,
  collectionId,
  onClose,
  onRejected,
}: CollectionRejectModalProps) {
  const [reason, setReason] = useState("");
  const [rejecting, setRejecting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!open || !collectionId) return null;

  function handleClose() {
    setReason("");
    setError(null);
    onClose();
  }

  async function handleConfirm() {
    if (!collectionId || reason.trim().length === 0) return;
    setRejecting(true);
    setError(null);
    try {
      await onRejected(collectionId, reason.trim());
      setReason("");
      onClose();
    } catch {
      setError("거부 처리 중 오류가 발생했습니다.");
    } finally {
      setRejecting(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      onClick={(e) => {
        if (e.target === e.currentTarget) handleClose();
      }}
    >
      <div className="bg-admin-surface border border-admin-border rounded-lg shadow-xl w-full max-w-sm mx-4 flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-admin-border">
          <h2 className="text-sm font-semibold text-admin-fg">컬렉션 거부</h2>
          <button
            onClick={handleClose}
            className="text-admin-muted hover:text-admin-fg transition-colors text-lg leading-none"
            aria-label="닫기"
          >
            ×
          </button>
        </div>

        {/* Body */}
        <div className="px-5 py-4 space-y-3">
          <div className="text-xs text-admin-muted space-y-1">
            <p>이 컬렉션을 완전히 삭제합니다.</p>
            <p className="text-red-500 font-medium">삭제 후 복구할 수 없습니다.</p>
          </div>

          <div>
            <label className="block text-xs font-medium text-admin-fg mb-1">
              거부 사유 (필수)
            </label>
            <textarea
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              rows={3}
              className="w-full border border-admin-border rounded px-3 py-2 text-sm text-admin-fg bg-admin-surface placeholder:text-admin-muted focus:outline-none focus:ring-1 focus:ring-red-400 resize-none"
              placeholder="예: 주제 부적합, 품질 미달, 이전 컬렉션과 중복 등"
            />
          </div>

          {error && <p className="text-xs text-red-500">{error}</p>}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-2 px-5 py-4 border-t border-admin-border">
          <button
            onClick={handleClose}
            disabled={rejecting}
            className="border border-admin-border text-admin-fg px-4 py-1.5 rounded text-xs hover:bg-admin-surface-2 transition-colors disabled:opacity-40"
          >
            취소
          </button>
          <button
            onClick={handleConfirm}
            disabled={rejecting || reason.trim().length === 0}
            className="bg-red-600 text-white px-4 py-1.5 rounded text-xs hover:bg-red-700 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {rejecting ? "처리 중..." : "거부 확정"}
          </button>
        </div>
      </div>
    </div>
  );
}
