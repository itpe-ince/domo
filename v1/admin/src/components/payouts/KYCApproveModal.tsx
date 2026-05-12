"use client";

import { KYCPendingItem } from "@/lib/api";

interface KYCApproveModalProps {
  item: KYCPendingItem;
  loading: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export function KYCApproveModal({
  item,
  loading,
  onConfirm,
  onCancel,
}: KYCApproveModalProps) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-admin-surface border border-admin-border rounded-xl shadow-xl w-full max-w-md mx-4 p-6">
        <h2 className="text-admin-fg text-base font-semibold mb-2">KYC 승인 확인</h2>
        <p className="text-admin-muted text-sm mb-4">
          다음 작가의 KYC를 승인하시겠습니까?
        </p>
        <div className="bg-admin-surface-2 rounded-lg p-3 mb-6 space-y-1">
          <div className="text-sm">
            <span className="text-admin-muted">작가명: </span>
            <span className="text-admin-fg font-medium">{item.user_display_name}</span>
          </div>
          <div className="text-sm">
            <span className="text-admin-muted">이메일: </span>
            <span className="text-admin-fg">{item.user_email}</span>
          </div>
          <div className="text-sm">
            <span className="text-admin-muted">제공자: </span>
            <span className="text-admin-fg">{item.provider}</span>
          </div>
        </div>
        <p className="text-[11px] text-admin-muted mb-5">
          승인 시 Stripe Connect onboarding이 트리거됩니다. (미설정 환경에서는 mock 처리)
        </p>
        <div className="flex gap-3 justify-end">
          <button
            onClick={onCancel}
            disabled={loading}
            className="px-4 py-2 text-sm text-admin-muted border border-admin-border rounded-lg hover:bg-admin-surface-2 transition-colors disabled:opacity-50"
          >
            취소
          </button>
          <button
            onClick={onConfirm}
            disabled={loading}
            className="px-4 py-2 text-sm bg-admin-accent text-white rounded-lg hover:opacity-90 transition-opacity disabled:opacity-50 flex items-center gap-2"
          >
            {loading && (
              <span className="inline-block h-3.5 w-3.5 border-2 border-white/40 border-t-white rounded-full animate-spin" />
            )}
            승인
          </button>
        </div>
      </div>
    </div>
  );
}
