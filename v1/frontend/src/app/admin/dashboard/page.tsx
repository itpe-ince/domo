"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  ApiUser,
  DashboardRevenue,
  DashboardStats,
  fetchDashboardRevenue,
  fetchDashboardStats,
  fetchMe,
  loginWithMockEmail,
  tokenStore,
} from "@/lib/api";

const WINDOWS = [7, 30, 90];

function fmt(n: string | number) {
  const v = typeof n === "string" ? Number(n) : n;
  return `₩ ${Math.round(v).toLocaleString()}`;
}

function StatCard({
  label,
  value,
  hint,
  accent = false,
}: {
  label: string;
  value: string | number;
  hint?: string;
  accent?: boolean;
}) {
  return (
    <div className="card p-5">
      <div className="text-text-muted text-xs uppercase tracking-wide">
        {label}
      </div>
      <div
        className={`text-3xl font-bold mt-2 ${
          accent ? "text-primary" : "text-text-primary"
        }`}
      >
        {value}
      </div>
      {hint && <div className="text-text-muted text-xs mt-1">{hint}</div>}
    </div>
  );
}

export default function DashboardPage() {
  const [me, setMe] = useState<ApiUser | null>(null);
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [revenue, setRevenue] = useState<DashboardRevenue | null>(null);
  const [days, setDays] = useState(30);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [loginEmail, setLoginEmail] = useState("");

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [days]);

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
      if (u.role !== "admin") return;
      const [s, r] = await Promise.all([
        fetchDashboardStats(days),
        fetchDashboardRevenue(days),
      ]);
      setStats(s);
      setRevenue(r);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load");
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

  return (
    <main className="min-h-screen px-6 py-8 max-w-6xl mx-auto">
      <header className="flex items-center justify-between mb-8">
        <div>
          <span className="badge-primary">Admin</span>
          <h1 className="text-3xl font-bold mt-3">대시보드</h1>
          <p className="text-text-secondary text-sm mt-1">
            매출 / 지표 / 통계
          </p>
        </div>
        <nav className="flex gap-2">
          <Link href="/admin/applications" className="btn-ghost text-sm">
            승인
          </Link>
          <Link href="/admin/moderation" className="btn-ghost text-sm">
            모더레이션
          </Link>
          <Link href="/admin/settings" className="btn-ghost text-sm">
            설정
          </Link>
        </nav>
      </header>

      {!me && (
        <div className="card p-6 max-w-md">
          <h2 className="text-lg font-semibold mb-3">로그인 (개발 모드)</h2>
          <input
            type="email"
            placeholder="admin@domo.example.com"
            value={loginEmail}
            onChange={(e) => setLoginEmail(e.target.value)}
            className="w-full bg-background border border-border rounded-lg px-4 py-2 mb-4 focus:border-primary outline-none"
          />
          <button onClick={handleLogin} className="btn-primary w-full">
            로그인
          </button>
        </div>
      )}

      {me && me.role !== "admin" && (
        <div className="card p-6">
          <p className="text-text-secondary">
            관리자 권한이 필요합니다. 현재 역할: <code>{me.role}</code>
          </p>
        </div>
      )}

      {error && (
        <div className="card border-danger p-4 mb-6 text-danger text-sm">
          {error}
        </div>
      )}

      {me && me.role === "admin" && (
        <>
          <div className="flex items-center gap-2 mb-6">
            <span className="text-text-muted text-sm mr-2">기간</span>
            {WINDOWS.map((d) => (
              <button
                key={d}
                onClick={() => setDays(d)}
                className={`px-3 py-1 rounded-full text-xs transition-colors ${
                  days === d
                    ? "bg-primary text-background"
                    : "bg-surface text-text-secondary"
                }`}
              >
                {d}일
              </button>
            ))}
          </div>

          {loading || !stats || !revenue ? (
            <div className="text-text-muted text-center py-12">로딩 중...</div>
          ) : (
            <>
              {/* Revenue */}
              <section className="mb-10">
                <h2 className="text-lg font-semibold mb-4">매출 (GMV)</h2>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
                  <StatCard
                    label="GMV 합계"
                    value={fmt(revenue.gmv_total)}
                    accent
                    hint={`${days}일 기준`}
                  />
                  <StatCard
                    label="플랫폼 수수료"
                    value={fmt(revenue.platform_fee_total)}
                    hint="auction + buy_now 합계"
                  />
                  <StatCard
                    label="구독 월 환산"
                    value={fmt(
                      revenue.by_source.subscription_monthly_run_rate.amount
                    )}
                    hint={`활성 ${revenue.by_source.subscription_monthly_run_rate.active_count}건`}
                  />
                </div>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <StatCard
                    label="🕊 후원"
                    value={fmt(revenue.by_source.sponsorship.amount)}
                    hint={`${revenue.by_source.sponsorship.count}건`}
                  />
                  <StatCard
                    label="🔨 경매"
                    value={fmt(revenue.by_source.auction.amount)}
                    hint={`수수료 ${fmt(revenue.by_source.auction.platform_fee)}`}
                  />
                  <StatCard
                    label="💳 즉시구매"
                    value={fmt(revenue.by_source.buy_now.amount)}
                    hint={`수수료 ${fmt(revenue.by_source.buy_now.platform_fee)}`}
                  />
                </div>
              </section>

              {/* Users */}
              <section className="mb-10">
                <h2 className="text-lg font-semibold mb-4">사용자</h2>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <StatCard
                    label="전체"
                    value={stats.users.total}
                    hint={`+${stats.users.new_in_window} ${days}일`}
                  />
                  <StatCard label="작가" value={stats.users.artists} accent />
                  <StatCard
                    label="정지 계정"
                    value={stats.users.suspended}
                  />
                  <StatCard
                    label="활성 구독자"
                    value={stats.sponsorship.active_subscriptions}
                  />
                </div>
              </section>

              {/* Content */}
              <section className="mb-10">
                <h2 className="text-lg font-semibold mb-4">콘텐츠</h2>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <StatCard
                    label="전체 포스트"
                    value={stats.content.total_posts}
                    hint={`+${stats.content.new_in_window} ${days}일`}
                  />
                  <StatCard
                    label="공개 포스트"
                    value={stats.content.published}
                  />
                  <StatCard
                    label="판독 대기"
                    value={stats.content.pending_review}
                  />
                  <StatCard label="신고 대기" value={stats.moderation.pending_reports} />
                </div>
              </section>

              {/* Auctions */}
              <section>
                <h2 className="text-lg font-semibold mb-4">경매</h2>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <StatCard
                    label="진행 중"
                    value={stats.auctions.active}
                    accent
                  />
                  <StatCard label="종료" value={stats.auctions.ended} />
                  <StatCard
                    label="후원 누적"
                    value={stats.sponsorship.completed_total}
                  />
                  <StatCard
                    label="활성 구독"
                    value={stats.sponsorship.active_subscriptions}
                  />
                </div>
              </section>
            </>
          )}
        </>
      )}
    </main>
  );
}
