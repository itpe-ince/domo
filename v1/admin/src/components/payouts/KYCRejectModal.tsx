"use client";

import { useState } from "react";
import { KYCPendingItem } from "@/lib/api";

interface KYCRejectModalProps {
  item: KYCPendingItem;
  loading: boolean;
  onConfirm: (reason: string) => void;
  onCancel: () => void;
}

export function KYCRejectModal({
  item,
  loading,
  onConfirm,
  onCancel,
}: KYCRejectModalProps) {
  const [reason, setReason] = useState("");
  const isValid = reason.trim().length >= 10;

  function handleSubmit() {
    if (!isValid) return;
    onConfirm(reason.trim());
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-admin-surface border border-admin-border rounded-xl shadow-xl w-full max-w-md mx-4 p-6">
        <h2 className="text-admin-fg text-base font-semibold mb-2">KYC 거부</h2>
        <p className="text-admin-muted text-sm mb-4">
          <span className="font-medium text-admin-fg">{item.user_display_name}</span>의 KYC를
          거부합니다. 거부 사유를 입력하세요.
        </p>

        <div className="mb-4">
          <label className="block text-[11px] font-semibold text-admin-muted uppercase tracking-wider mb-1.5">
            거부 사유 <span className="text-admin-danger">*</span>
          </label>
          <textarea
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="예: 신분증 사진 불명확 — 재촬영 후 재신청 바랍니다"
            maxLength={500}
            rows={4}
            className="w-full bg-admin-surface-2 border border-admin-border rounded-lg px-3 py-2 text-sm text-admin-fg placeholder-admin-muted focus:outline-none focus:border-admin-accent resize-none"
          />
          <div className="flex justify-between mt-1">
            {!isValid && reason.length > 0 && (
              <span className="text-[11px] text-admin-danger">최소 10자 이상 입력해 주세요.</span>
            )}
            {isValid && <span className="text-[11px] text-admin-accent">입력 완료</span>}
            <span className="text-[11px] text-admin-muted ml-auto">{reason.length}/500</span>
          </div>
        </div>

        <div className="flex gap-3 justify-end">
          <button
            onClick={onCancel}
            disabled={loading}
            className="px-4 py-2 text-sm text-admin-muted border border-admin-border rounded-lg hover:bg-admin-surface-2 transition-colors disabled:opacity-50"
          >
            취소
          </button>
          <button
            onClick={handleSubmit}
            disabled={loading || !isValid}
            className="px-4 py-2 text-sm bg-admin-danger text-white rounded-lg hover:opacity-90 transition-opacity disabled:opacity-50 flex items-center gap-2"
          >
            {loading && (
              <span className="inline-block h-3.5 w-3.5 border-2 border-white/40 border-t-white rounded-full animate-spin" />
            )}
            거부
          </button>
        </div>
      </div>
    </div>
  );
}
