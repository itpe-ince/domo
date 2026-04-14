"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";

type TabKey = "auctions" | "orders";

export default function AdminTransactionsPage() {
  const [tab, setTab] = useState<TabKey>("auctions");
  const [data, setData] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [offset, setOffset] = useState(0);

  useEffect(() => { void load(); }, [tab, offset]);

  async function load() {
    setLoading(true);
    try {
      const endpoint = tab === "auctions" ? "/admin/auctions/list" : "/admin/orders/list";
      const qs = new URLSearchParams({ limit: "20", offset: String(offset) });
      const res = await apiFetch<any>(`${endpoint}?${qs}`, { raw: true });
      setData(res.data); setTotal(res.pagination.total);
    } catch { /* ignore */ }
    finally { setLoading(false); }
  }

  return (
    <main className="flex-1 min-w-0 max-w-5xl mx-auto px-6 py-8">
      <h1 className="text-2xl font-bold mb-6">거래 관리</h1>

      <div className="flex gap-1 mb-4">
        {(["auctions", "orders"] as TabKey[]).map((t) => (
          <button key={t} onClick={() => { setTab(t); setOffset(0); }}
            className={`px-4 py-2 rounded-full text-sm font-semibold transition-colors ${tab === t ? "bg-primary text-background" : "bg-surface text-text-secondary hover:bg-surface-hover"}`}>
            {t === "auctions" ? "경매" : "주문"}
          </button>
        ))}
      </div>

      {loading ? <div className="animate-pulse card p-8" /> : (
        <div className="card overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-surface text-text-muted text-left">
              {tab === "auctions" ? (
                <tr>
                  <th className="px-4 py-3">판매자</th><th className="px-4 py-3">시작가</th>
                  <th className="px-4 py-3">현재가</th><th className="px-4 py-3">입찰</th>
                  <th className="px-4 py-3">상태</th><th className="px-4 py-3">마감</th>
                </tr>
              ) : (
                <tr>
                  <th className="px-4 py-3">구매자</th><th className="px-4 py-3">판매자</th>
                  <th className="px-4 py-3">금액</th><th className="px-4 py-3">수수료</th>
                  <th className="px-4 py-3">유형</th><th className="px-4 py-3">상태</th>
                </tr>
              )}
            </thead>
            <tbody className="divide-y divide-border">
              {data.map((item, i) => (
                <tr key={i} className="hover:bg-surface-hover/30">
                  {tab === "auctions" ? (
                    <>
                      <td className="px-4 py-3">@{item.seller_name}</td>
                      <td className="px-4 py-3">${item.start_price}</td>
                      <td className="px-4 py-3 font-medium">${item.current_price}</td>
                      <td className="px-4 py-3">{item.bid_count}건</td>
                      <td className="px-4 py-3"><span className="badge-primary text-xs">{item.status}</span></td>
                      <td className="px-4 py-3 text-text-muted text-xs">{new Date(item.end_at).toLocaleDateString("ko-KR")}</td>
                    </>
                  ) : (
                    <>
                      <td className="px-4 py-3">@{item.buyer_name}</td>
                      <td className="px-4 py-3">@{item.seller_name}</td>
                      <td className="px-4 py-3 font-medium">${item.amount}</td>
                      <td className="px-4 py-3 text-text-muted">${item.platform_fee}</td>
                      <td className="px-4 py-3 text-xs">{item.source}</td>
                      <td className="px-4 py-3"><span className="badge-primary text-xs">{item.status}</span></td>
                    </>
                  )}
                </tr>
              ))}
              {data.length === 0 && (
                <tr><td colSpan={6} className="px-4 py-8 text-center text-text-muted">데이터가 없습니다.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {total > 20 && (
        <div className="flex justify-center gap-2 mt-4">
          <button onClick={() => setOffset(Math.max(0, offset - 20))} disabled={offset === 0} className="text-sm px-3 py-1 rounded bg-surface disabled:opacity-30">← 이전</button>
          <span className="text-sm text-text-muted py-1">{Math.floor(offset / 20) + 1} / {Math.ceil(total / 20)}</span>
          <button onClick={() => setOffset(offset + 20)} disabled={offset + 20 >= total} className="text-sm px-3 py-1 rounded bg-surface disabled:opacity-30">다음 →</button>
        </div>
      )}
    </main>
  );
}
