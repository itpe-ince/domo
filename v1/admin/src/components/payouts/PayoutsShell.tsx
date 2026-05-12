"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { SettlementListItem } from "@/lib/api";
import { useSettlementDetail } from "@/lib/hooks/usePayouts";
import { KYCQueueTab } from "./KYCQueueTab";
import { SettlementHistoryTab } from "./SettlementHistoryTab";
import { StripeConnectStatusTab } from "./StripeConnectStatusTab";

type Tab = "kyc-queue" | "settlements" | "connect-status";

const TABS: { id: Tab; label: string }[] = [
  { id: "kyc-queue", label: "KYC 검수 큐" },
  { id: "settlements", label: "정산 이력" },
  { id: "connect-status", label: "Stripe Connect 상태" },
];

export function PayoutsShell() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<Tab>("kyc-queue");
  const [selectedSettlement, setSelectedSettlement] =
    useState<SettlementListItem | null>(null);

  // URL query string으로 탭 동기화
  useEffect(() => {
    const tab = searchParams.get("tab") as Tab | null;
    if (tab && TABS.some((t) => t.id === tab)) {
      setActiveTab(tab);
    }
  }, [searchParams]);

  function handleTabChange(tab: Tab) {
    setActiveTab(tab);
    setSelectedSettlement(null);
    router.replace(`/payouts?tab=${tab}`, { scroll: false });
  }

  // 정산 상세 페이지 (탭 내 하위 뷰)
  if (selectedSettlement) {
    return (
      <SettlementDetailView
        settlement={selectedSettlement}
        onBack={() => setSelectedSettlement(null)}
      />
    );
  }

  return (
    <div className="p-6 max-w-6xl mx-auto">
      {/* 페이지 제목 */}
      <div className="mb-6">
        <h1 className="text-admin-fg text-xl font-bold">정산 관리</h1>
        <p className="text-admin-muted text-sm mt-1">
          KYC 검수, 정산 이력 조회, Stripe Connect 상태 관리
        </p>
      </div>

      {/* 탭 네비게이션 */}
      <div className="flex border-b border-admin-border mb-6">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => handleTabChange(tab.id)}
            className={`px-4 py-2.5 text-sm font-medium transition-colors border-b-2 -mb-px ${
              activeTab === tab.id
                ? "border-admin-accent text-admin-accent"
                : "border-transparent text-admin-muted hover:text-admin-fg"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* 탭 콘텐츠 */}
      {activeTab === "kyc-queue" && <KYCQueueTab />}
      {activeTab === "settlements" && (
        <SettlementHistoryTab onSelectDetail={setSelectedSettlement} />
      )}
      {activeTab === "connect-status" && <StripeConnectStatusTab />}
    </div>
  );
}

// ─── 정산 상세 인라인 뷰 ─────────────────────────────────────────────────────

function SettlementDetailView({
  settlement,
  onBack,
}: {
  settlement: SettlementListItem;
  onBack: () => void;
}) {
  const { data, loading, error, load } = useSettlementDetail(settlement.id);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <button
        onClick={onBack}
        className="text-admin-muted text-[12px] hover:text-admin-fg transition-colors mb-4 flex items-center gap-1"
      >
        ← 목록으로
      </button>
      <h1 className="text-admin-fg text-lg font-bold mb-1">
        정산 상세 — {settlement.artist_name}
      </h1>
      <p className="text-admin-muted text-sm mb-6">
        {settlement.period_start
          ? `${new Date(settlement.period_start).getFullYear()}년 ${new Date(settlement.period_start).getMonth() + 1}월`
          : ""}
      </p>

      {error && (
        <div className="text-admin-danger text-sm bg-admin-danger/10 border border-admin-danger/20 rounded-lg px-4 py-3 mb-4">
          {error}
        </div>
      )}

      {loading ? (
        <div className="text-admin-muted text-sm py-8 text-center">로딩 중...</div>
      ) : data ? (
        <div className="space-y-6">
          {/* 요약 */}
          <div className="grid grid-cols-3 gap-4">
            <StatCard label="총 매출" value={`${parseFloat(data.gross_amount).toLocaleString("ko-KR")}원`} />
            <StatCard label="플랫폼 수수료" value={`${parseFloat(data.platform_fee).toLocaleString("ko-KR")}원`} />
            <StatCard label="정산액" value={`${parseFloat(data.net_amount).toLocaleString("ko-KR")}원`} highlight />
          </div>

          {/* 정산 정보 */}
          <div className="border border-admin-border rounded-xl p-4 space-y-2">
            <InfoRow label="상태" value={data.status} />
            <InfoRow label="지급일" value={data.paid_at ? new Date(data.paid_at).toLocaleDateString("ko-KR") : "—"} />
            <InfoRow label="참조" value={data.payout_reference ?? "—"} mono />
            <InfoRow label="주문 수" value={`${data.order_count}건`} />
          </div>

          {/* 포함 주문 */}
          <div>
            <h3 className="text-admin-fg font-semibold text-sm mb-3">
              포함 주문 ({data.items.length}건)
            </h3>
            {data.items.length === 0 ? (
              <p className="text-admin-muted text-sm">주문이 없습니다.</p>
            ) : (
              <div className="border border-admin-border rounded-xl overflow-hidden">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-admin-border bg-admin-surface-2">
                      <th className="px-4 py-2.5 text-left text-[11px] font-bold uppercase tracking-wider text-admin-muted">
                        주문 ID
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.items.map((item) => (
                      <tr
                        key={item.order_id}
                        className="border-b border-admin-border last:border-0"
                      >
                        <td className="px-4 py-2.5 text-[12px] text-admin-muted font-mono">
                          {item.order_id}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Stripe Transfer 정보 */}
          <div>
            <h3 className="text-admin-fg font-semibold text-sm mb-3">
              Stripe Transfer 정보
            </h3>
            {data.stripe_transfer ? (
              <div className="border border-admin-border rounded-xl p-4 space-y-2">
                <InfoRow label="Transfer ID" value={data.stripe_transfer.transfer_id} mono />
                <InfoRow
                  label="금액"
                  value={`${data.stripe_transfer.amount.toLocaleString("ko-KR")} ${data.stripe_transfer.currency.toUpperCase()}`}
                />
                <InfoRow label="Destination" value={data.stripe_transfer.destination} mono />
              </div>
            ) : (
              <div className="border border-admin-border rounded-xl p-4 text-admin-muted text-sm">
                Stripe 실제 연동 전 mock 상태입니다.
              </div>
            )}
          </div>
        </div>
      ) : null}
    </div>
  );
}

function StatCard({
  label,
  value,
  highlight = false,
}: {
  label: string;
  value: string;
  highlight?: boolean;
}) {
  return (
    <div
      className={`border rounded-xl p-4 ${highlight ? "border-admin-accent/30 bg-admin-accent/5" : "border-admin-border"}`}
    >
      <div className="text-[11px] text-admin-muted uppercase tracking-wider mb-1">
        {label}
      </div>
      <div
        className={`text-lg font-bold ${highlight ? "text-admin-accent" : "text-admin-fg"}`}
      >
        {value}
      </div>
    </div>
  );
}

function InfoRow({
  label,
  value,
  mono = false,
}: {
  label: string;
  value: string;
  mono?: boolean;
}) {
  return (
    <div className="flex items-center gap-4">
      <span className="text-[11px] font-semibold text-admin-muted uppercase tracking-wider w-24 flex-shrink-0">
        {label}
      </span>
      <span className={`text-[13px] text-admin-fg ${mono ? "font-mono" : ""}`}>
        {value}
      </span>
    </div>
  );
}
