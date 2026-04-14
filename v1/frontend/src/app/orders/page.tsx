"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  ApiUser,
  fetchMe,
  fetchMyOrders,
  loginWithMockEmail,
  OrderView,
  payOrder,
  tokenStore,
} from "@/lib/api";

function fmt(n: string | number) {
  const v = typeof n === "string" ? Number(n) : n;
  return `₩ ${Math.round(v).toLocaleString()}`;
}

const STATUS_LABEL: Record<string, string> = {
  pending_payment: "결제 대기",
  paid: "결제 완료",
  cancelled: "취소",
  expired: "만료",
  refunded: "환불",
};

export default function OrdersPage() {
  const [me, setMe] = useState<ApiUser | null>(null);
  const [role, setRole] = useState<"buyer" | "seller">("buyer");
  const [orders, setOrders] = useState<OrderView[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [loginEmail, setLoginEmail] = useState("");
  const [paying, setPaying] = useState<string | null>(null);

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [role]);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      if (!tokenStore.get()) {
        setMe(null);
        setOrders([]);
        return;
      }
      const u = await fetchMe();
      setMe(u);
      const list = await fetchMyOrders(role);
      setOrders(list);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load orders");
    } finally {
      setLoading(false);
    }
  }

  async function handleLogin() {
    try {
      const u = await loginWithMockEmail(loginEmail.trim());
      setMe(u);
      void load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Login failed");
    }
  }

  async function handlePay(id: string) {
    setPaying(id);
    setError(null);
    try {
      const updated = await payOrder(id);
      setOrders((prev) => prev.map((o) => (o.id === id ? updated : o)));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Payment failed");
    } finally {
      setPaying(null);
    }
  }

  return (
    <main className="flex-1 min-w-0 max-w-3xl mx-auto px-6 py-8">
      <header className="flex items-center justify-between mb-8">
        <div>
          <span className="badge-primary">Orders</span>
          <h1 className="text-3xl font-bold mt-3">주문 내역</h1>
        </div>
        <Link href="/" className="btn-ghost text-sm">
          ← 홈
        </Link>
      </header>

      {!me && (
        <div className="card p-6 max-w-md">
          <h2 className="text-lg font-semibold mb-3">로그인 (개발 모드)</h2>
          <input
            type="email"
            placeholder="email@example.com"
            value={loginEmail}
            onChange={(e) => setLoginEmail(e.target.value)}
            className="w-full bg-background border border-border rounded-lg px-4 py-2 text-text-primary mb-4 focus:border-primary outline-none"
          />
          <button onClick={handleLogin} className="btn-primary w-full">
            로그인
          </button>
        </div>
      )}

      {me && (
        <>
          <div className="flex gap-2 mb-6">
            <button
              onClick={() => setRole("buyer")}
              className={`px-4 py-2 rounded-full text-sm transition-colors ${
                role === "buyer"
                  ? "bg-primary text-background"
                  : "bg-surface text-text-secondary"
              }`}
            >
              구매 내역
            </button>
            <button
              onClick={() => setRole("seller")}
              className={`px-4 py-2 rounded-full text-sm transition-colors ${
                role === "seller"
                  ? "bg-primary text-background"
                  : "bg-surface text-text-secondary"
              }`}
            >
              판매 내역
            </button>
          </div>

          {error && (
            <div className="card border-danger p-4 mb-4 text-danger text-sm">
              {error}
            </div>
          )}

          {loading ? (
            <div className="text-text-muted text-center py-8">로딩 중...</div>
          ) : orders.length === 0 ? (
            <div className="card p-12 text-center text-text-muted">
              주문 내역이 없습니다.
            </div>
          ) : (
            <ul className="space-y-3">
              {orders.map((o) => (
                <li key={o.id} className="card p-5">
                  <div className="flex items-start justify-between mb-3">
                    <div>
                      <span className="badge-primary">
                        {o.source === "auction" ? "경매 낙찰" : "즉시 구매"}
                      </span>
                      <span className="ml-2 text-text-muted text-xs">
                        {STATUS_LABEL[o.status] ?? o.status}
                      </span>
                    </div>
                    <div className="text-right">
                      <div className="text-primary font-semibold text-lg">
                        {fmt(o.amount)}
                      </div>
                      <div className="text-text-muted text-xs">
                        수수료 {fmt(o.platform_fee)}
                      </div>
                    </div>
                  </div>

                  <div className="text-text-secondary text-xs space-y-1">
                    <div>주문 ID: {o.id.slice(0, 8)}...</div>
                    <div>생성: {new Date(o.created_at).toLocaleString("ko-KR")}</div>
                    {o.payment_due_at && o.status === "pending_payment" && (
                      <div className="text-warning">
                        결제 기한:{" "}
                        {new Date(o.payment_due_at).toLocaleString("ko-KR")}
                      </div>
                    )}
                    {o.paid_at && (
                      <div>
                        결제: {new Date(o.paid_at).toLocaleString("ko-KR")}
                      </div>
                    )}
                  </div>

                  <div className="flex gap-2 mt-4">
                    <Link
                      href={`/posts/${o.product_post_id}`}
                      className="btn-secondary text-xs"
                    >
                      작품 보기
                    </Link>
                    {role === "buyer" && o.status === "pending_payment" && (
                      <button
                        onClick={() => handlePay(o.id)}
                        disabled={paying === o.id}
                        className="btn-primary text-xs disabled:opacity-50"
                      >
                        {paying === o.id ? "결제 중..." : "💳 결제하기 (Mock)"}
                      </button>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </>
      )}
    </main>
  );
}
