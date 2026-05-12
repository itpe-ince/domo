"use client";

import { useEffect, useState } from "react";
import { KYCPendingItem } from "@/lib/api";
import { useKycQueue } from "@/lib/hooks/usePayouts";
import { KYCApproveModal } from "./KYCApproveModal";
import { KYCRejectModal } from "./KYCRejectModal";

function formatDate(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return `${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

function ProviderBadge({ provider }: { provider: string }) {
  const colors: Record<string, string> = {
    mock: "bg-gray-100 text-gray-600",
    toss: "bg-blue-100 text-blue-700",
    stripe: "bg-indigo-100 text-indigo-700",
  };
  return (
    <span
      className={`inline-block px-2 py-0.5 rounded text-[11px] font-medium ${colors[provider] ?? "bg-gray-100 text-gray-600"}`}
    >
      {provider}
    </span>
  );
}

export function KYCQueueTab() {
  const { data, loading, error, load, approve, reject, actionLoading } =
    useKycQueue();

  const [approveTarget, setApproveTarget] = useState<KYCPendingItem | null>(null);
  const [rejectTarget, setRejectTarget] = useState<KYCPendingItem | null>(null);

  useEffect(() => {
    void load();
  }, [load]);

  async function handleApproveConfirm() {
    if (!approveTarget) return;
    await approve(approveTarget);
    setApproveTarget(null);
  }

  async function handleRejectConfirm(reason: string) {
    if (!rejectTarget) return;
    await reject(rejectTarget, reason);
    setRejectTarget(null);
  }

  const items = data?.data ?? [];
  const total = data?.pagination.total ?? 0;

  return (
    <div>
      {/* 모달 */}
      {approveTarget && (
        <KYCApproveModal
          item={approveTarget}
          loading={actionLoading === approveTarget.user_id}
          onConfirm={handleApproveConfirm}
          onCancel={() => setApproveTarget(null)}
        />
      )}
      {rejectTarget && (
        <KYCRejectModal
          item={rejectTarget}
          loading={actionLoading === rejectTarget.user_id}
          onConfirm={handleRejectConfirm}
          onCancel={() => setRejectTarget(null)}
        />
      )}

      {/* 헤더 */}
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-admin-fg font-semibold text-sm">
          KYC 검수 큐{" "}
          <span className="text-admin-muted font-normal">({total}건 대기)</span>
        </h2>
        <button
          onClick={() => void load()}
          disabled={loading}
          className="text-[11px] text-admin-muted border border-admin-border rounded-lg px-3 py-1.5 hover:bg-admin-surface-2 transition-colors disabled:opacity-50"
        >
          {loading ? "로딩 중..." : "새로고침"}
        </button>
      </div>

      {error && (
        <div className="text-admin-danger text-sm bg-admin-danger/10 border border-admin-danger/20 rounded-lg px-4 py-3 mb-4">
          {error}
        </div>
      )}

      {loading && items.length === 0 ? (
        <div className="text-admin-muted text-sm py-8 text-center">로딩 중...</div>
      ) : items.length === 0 ? (
        <div className="text-admin-muted text-sm py-12 text-center border border-admin-border rounded-xl">
          대기 중인 KYC 신청이 없습니다.
        </div>
      ) : (
        <div className="border border-admin-border rounded-xl overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-admin-border bg-admin-surface-2">
                <th className="px-4 py-2.5 text-left text-[11px] font-bold uppercase tracking-wider text-admin-muted">
                  신청일
                </th>
                <th className="px-4 py-2.5 text-left text-[11px] font-bold uppercase tracking-wider text-admin-muted">
                  작가명
                </th>
                <th className="px-4 py-2.5 text-left text-[11px] font-bold uppercase tracking-wider text-admin-muted">
                  이메일
                </th>
                <th className="px-4 py-2.5 text-left text-[11px] font-bold uppercase tracking-wider text-admin-muted">
                  제공자
                </th>
                <th className="px-4 py-2.5 text-right text-[11px] font-bold uppercase tracking-wider text-admin-muted">
                  액션
                </th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr
                  key={item.kyc_session_id}
                  className="border-b border-admin-border last:border-0 hover:bg-admin-surface-2/50 transition-colors"
                >
                  <td className="px-4 py-3 text-admin-muted text-[12px]">
                    {formatDate(item.created_at)}
                  </td>
                  <td className="px-4 py-3 text-admin-fg font-medium">
                    {item.user_display_name}
                  </td>
                  <td className="px-4 py-3 text-admin-muted text-[12px]">
                    {item.user_email}
                  </td>
                  <td className="px-4 py-3">
                    <ProviderBadge provider={item.provider} />
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex gap-2 justify-end">
                      <button
                        onClick={() => setApproveTarget(item)}
                        disabled={actionLoading === item.user_id}
                        className="text-[11px] px-2.5 py-1 rounded-md bg-admin-accent/10 text-admin-accent border border-admin-accent/20 hover:bg-admin-accent/20 transition-colors disabled:opacity-50"
                      >
                        승인
                      </button>
                      <button
                        onClick={() => setRejectTarget(item)}
                        disabled={actionLoading === item.user_id}
                        className="text-[11px] px-2.5 py-1 rounded-md bg-admin-danger/10 text-admin-danger border border-admin-danger/20 hover:bg-admin-danger/20 transition-colors disabled:opacity-50"
                      >
                        거부
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
