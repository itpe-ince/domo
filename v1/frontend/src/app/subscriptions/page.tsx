"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  ApiUser,
  cancelSubscription,
  fetchMe,
  fetchMySubscriptions,
  loginWithMockEmail,
  SubscriptionView,
  tokenStore,
} from "@/lib/api";

function fmt(n: string | number) {
  const v = typeof n === "string" ? Number(n) : n;
  return `₩ ${Math.round(v).toLocaleString()}`;
}

const STATUS_LABEL: Record<string, string> = {
  active: "활성",
  cancelled: "해지됨",
  past_due: "결제 실패",
};

export default function SubscriptionsPage() {
  const [me, setMe] = useState<ApiUser | null>(null);
  const [subs, setSubs] = useState<SubscriptionView[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [acting, setActing] = useState<string | null>(null);
  const [loginEmail, setLoginEmail] = useState("");

  useEffect(() => {
    void load();
  }, []);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      if (!tokenStore.get()) {
        setMe(null);
        return;
      }
      const u = await fetchMe();
      setMe(u);
      setSubs(await fetchMySubscriptions());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }

  async function handleCancel(id: string) {
    if (!confirm("정기 후원을 해지하시겠습니까? 이번 달까지는 유지되고 다음 달부터 결제되지 않습니다.")) {
      return;
    }
    setActing(id);
    setError(null);
    try {
      const updated = await cancelSubscription(id);
      setSubs((prev) => prev.map((s) => (s.id === id ? updated : s)));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Cancel failed");
    } finally {
      setActing(null);
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

  const active = subs.filter(
    (s) => s.status === "active" && !s.cancel_at_period_end
  );
  const cancelling = subs.filter(
    (s) => s.status === "active" && s.cancel_at_period_end
  );
  const cancelled = subs.filter((s) => s.status === "cancelled");

  return (
    <main className="min-h-screen px-6 py-8 max-w-3xl mx-auto">
      <header className="flex items-center justify-between mb-8">
        <div>
          <span className="badge-primary">🕊 My</span>
          <h1 className="text-3xl font-bold mt-3">정기 후원 관리</h1>
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
            className="w-full bg-background border border-border rounded-lg px-4 py-2 mb-4 focus:border-primary outline-none"
          />
          <button onClick={handleLogin} className="btn-primary w-full">
            로그인
          </button>
        </div>
      )}

      {error && (
        <div className="card border-danger p-4 mb-4 text-danger text-sm">
          {error}
        </div>
      )}

      {me && (
        <>
          {loading ? (
            <div className="text-text-muted text-center py-8">로딩 중...</div>
          ) : subs.length === 0 ? (
            <div className="card p-12 text-center text-text-muted">
              정기 후원이 없습니다.
            </div>
          ) : (
            <>
              {active.length > 0 && (
                <Section title={`활성 (${active.length})`}>
                  {active.map((s) => (
                    <SubCard
                      key={s.id}
                      sub={s}
                      onCancel={() => handleCancel(s.id)}
                      acting={acting === s.id}
                    />
                  ))}
                </Section>
              )}
              {cancelling.length > 0 && (
                <Section title={`해지 예정 (${cancelling.length})`}>
                  {cancelling.map((s) => (
                    <SubCard key={s.id} sub={s} />
                  ))}
                </Section>
              )}
              {cancelled.length > 0 && (
                <Section title={`해지됨 (${cancelled.length})`} muted>
                  {cancelled.map((s) => (
                    <SubCard key={s.id} sub={s} />
                  ))}
                </Section>
              )}
            </>
          )}
        </>
      )}
    </main>
  );
}

function Section({
  title,
  children,
  muted = false,
}: {
  title: string;
  children: React.ReactNode;
  muted?: boolean;
}) {
  return (
    <section className={`mb-8 ${muted ? "opacity-60" : ""}`}>
      <h2 className="text-lg font-semibold mb-3">{title}</h2>
      <ul className="space-y-3">{children}</ul>
    </section>
  );
}

function SubCard({
  sub,
  onCancel,
  acting,
}: {
  sub: SubscriptionView;
  onCancel?: () => void;
  acting?: boolean;
}) {
  return (
    <li className="card p-5">
      <div className="flex items-start justify-between mb-3">
        <div>
          <span className="badge-primary">{STATUS_LABEL[sub.status] ?? sub.status}</span>
          {sub.cancel_at_period_end && sub.status === "active" && (
            <span className="ml-2 text-warning text-xs">기간 말 해지 예정</span>
          )}
        </div>
        <div className="text-right">
          <div className="text-primary font-semibold text-lg">
            {fmt(sub.monthly_amount)}
          </div>
          <div className="text-text-muted text-xs">
            매월 {sub.monthly_bluebird} 블루버드
          </div>
        </div>
      </div>

      <div className="text-xs text-text-secondary space-y-1">
        <div>
          작가:{" "}
          <Link
            href={`/users/${sub.artist_id}`}
            className="text-primary hover:underline"
          >
            {sub.artist_id.slice(0, 8)}...
          </Link>
        </div>
        <div>시작: {new Date(sub.created_at).toLocaleString("ko-KR")}</div>
        {sub.current_period_end && (
          <div>
            현 결제 주기 종료:{" "}
            {new Date(sub.current_period_end).toLocaleDateString("ko-KR")}
          </div>
        )}
        {sub.cancelled_at && (
          <div>해지 요청: {new Date(sub.cancelled_at).toLocaleString("ko-KR")}</div>
        )}
      </div>

      {onCancel && sub.status === "active" && !sub.cancel_at_period_end && (
        <button
          onClick={onCancel}
          disabled={acting}
          className="btn-secondary text-xs mt-4 disabled:opacity-50"
        >
          {acting ? "처리 중..." : "정기 후원 해지"}
        </button>
      )}
    </li>
  );
}
