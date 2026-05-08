"use client";

import { useEffect, useState } from "react";
import { SettlementListItem } from "@/lib/api";
import { useSettlements, SettlementFilters } from "@/lib/hooks/usePayouts";

const STATUS_BADGE: Record<string, { label: string; cls: string }> = {
  pending: { label: "대기", cls: "bg-gray-100 text-gray-500" },
  approved: { label: "승인", cls: "bg-blue-100 text-blue-700" },
  paid: { label: "지급 완료", cls: "bg-green-100 text-green-700" },
  failed: { label: "실패", cls: "bg-red-100 text-red-700" },
};

function StatusBadge({ status }: { status: string }) {
  const cfg = STATUS_BADGE[status] ?? { label: status, cls: "bg-gray-100 text-gray-500" };
  return (
    <span className={`inline-block px-2 py-0.5 rounded text-[11px] font-medium ${cfg.cls}`}>
      {cfg.label}
    </span>
  );
}

function formatAmount(amount: string, currency: string): string {
  const num = parseFloat(amount);
  return `${num.toLocaleString("ko-KR")} ${currency}`;
}

function formatDate(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("ko-KR", {
    month: "2-digit",
    day: "2-digit",
  });
}

function getCurrentMonth(): string {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
}

interface Props {
  onSelectDetail: (settlement: SettlementListItem) => void;
}

export function SettlementHistoryTab({ onSelectDetail }: Props) {
  const { data, loading, error, load } = useSettlements();
  const [filters, setFilters] = useState<SettlementFilters>({
    month: getCurrentMonth(),
    status: "",
    limit: 20,
    offset: 0,
  });

  useEffect(() => {
    void load({
      ...filters,
      status: filters.status || undefined,
    });
  }, [load]); // eslint-disable-line react-hooks/exhaustive-deps

  function handleSearch() {
    void load({
      ...filters,
      status: filters.status || undefined,
    });
  }

  function handleExportCsv() {
    const apiBase =
      process.env.NEXT_PUBLIC_API_URL || "http://localhost:3710/v1";
    const qs = new URLSearchParams({ format: "csv" });
    if (filters.month) qs.set("month", filters.month);
    if (filters.status) qs.set("status", filters.status);
    const url = `${apiBase}/admin/settlements/export?${qs}`;
    window.open(url, "_blank");
  }

  const items = data?.data ?? [];
  const total = data?.pagination.total ?? 0;

  return (
    <div>
      {/* 필터 영역 */}
      <div className="flex items-center gap-3 mb-4 flex-wrap">
        <input
          type="month"
          value={filters.month ?? ""}
          onChange={(e) => setFilters((f) => ({ ...f, month: e.target.value }))}
          className="bg-admin-surface border border-admin-border rounded-lg px-3 py-1.5 text-sm text-admin-fg focus:outline-none focus:border-admin-accent"
        />
        <select
          value={filters.status ?? ""}
          onChange={(e) => setFilters((f) => ({ ...f, status: e.target.value }))}
          className="bg-admin-surface border border-admin-border rounded-lg px-3 py-1.5 text-sm text-admin-fg focus:outline-none focus:border-admin-accent"
        >
          <option value="">전체 상태</option>
          <option value="pending">대기</option>
          <option value="approved">승인</option>
          <option value="paid">지급 완료</option>
          <option value="failed">실패</option>
        </select>
        <button
          onClick={handleSearch}
          disabled={loading}
          className="text-[11px] px-3 py-1.5 bg-admin-accent text-white rounded-lg hover:opacity-90 transition-opacity disabled:opacity-50"
        >
          {loading ? "검색 중..." : "검색"}
        </button>
        <button
          onClick={handleExportCsv}
          className="text-[11px] px-3 py-1.5 border border-admin-border text-admin-muted rounded-lg hover:bg-admin-surface-2 transition-colors ml-auto"
        >
          CSV 내보내기
        </button>
      </div>

      {error && (
        <div className="text-admin-danger text-sm bg-admin-danger/10 border border-admin-danger/20 rounded-lg px-4 py-3 mb-4">
          {error}
        </div>
      )}

      {/* 합계 정보 */}
      <div className="text-[12px] text-admin-muted mb-3">
        총 {total}건
      </div>

      {loading && items.length === 0 ? (
        <div className="text-admin-muted text-sm py-8 text-center">로딩 중...</div>
      ) : items.length === 0 ? (
        <div className="text-admin-muted text-sm py-12 text-center border border-admin-border rounded-xl">
          정산 이력이 없습니다.
        </div>
      ) : (
        <div className="border border-admin-border rounded-xl overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-admin-border bg-admin-surface-2">
                <th className="px-4 py-2.5 text-left text-[11px] font-bold uppercase tracking-wider text-admin-muted">
                  기간
                </th>
                <th className="px-4 py-2.5 text-left text-[11px] font-bold uppercase tracking-wider text-admin-muted">
                  작가
                </th>
                <th className="px-4 py-2.5 text-right text-[11px] font-bold uppercase tracking-wider text-admin-muted">
                  정산액
                </th>
                <th className="px-4 py-2.5 text-left text-[11px] font-bold uppercase tracking-wider text-admin-muted">
                  상태
                </th>
                <th className="px-4 py-2.5 text-left text-[11px] font-bold uppercase tracking-wider text-admin-muted">
                  승인일
                </th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr
                  key={item.id}
                  onClick={() => onSelectDetail(item)}
                  className="border-b border-admin-border last:border-0 hover:bg-admin-surface-2/50 transition-colors cursor-pointer"
                >
                  <td className="px-4 py-3 text-admin-muted text-[12px]">
                    {item.period_start
                      ? `${new Date(item.period_start).getMonth() + 1}월`
                      : "—"}
                  </td>
                  <td className="px-4 py-3">
                    <div className="text-admin-fg font-medium text-[13px]">
                      {item.artist_name}
                    </div>
                    <div className="text-admin-muted text-[11px]">
                      {item.artist_email}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-right font-medium text-admin-fg text-[13px]">
                    {formatAmount(item.net_amount, item.currency)}
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge status={item.status} />
                  </td>
                  <td className="px-4 py-3 text-admin-muted text-[12px]">
                    {formatDate(item.approved_at)}
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
