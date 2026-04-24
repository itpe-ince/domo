"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import {
  ApiUser,
  DashboardRevenue,
  DashboardStats,
  fetchDashboardRevenue,
  fetchDashboardStats,
  fetchMe,
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
    <div className="admin-card p-5">
      <div className="text-admin-muted text-[11px] uppercase tracking-wider font-medium">
        {label}
      </div>
      <div
        className={`text-2xl font-semibold mt-2 tabular-nums ${
          accent ? "text-admin-accent" : "text-admin-fg"
        }`}
      >
        {value}
      </div>
      {hint && <div className="text-admin-muted text-xs mt-1">{hint}</div>}
    </div>
  );
}

export default function DashboardPage() {
  const router = useRouter();
  const [me, setMe] = useState<ApiUser | null>(null);
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [revenue, setRevenue] = useState<DashboardRevenue | null>(null);
  const [days, setDays] = useState(30);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [days]);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      if (!tokenStore.get()) {
        router.replace("/login");
        return;
      }
      const u = await fetchMe();
      setMe(u);
      if (u.role !== "admin") {
        return;
      }
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

  return (
    <main className="px-8 py-8">
      <header className="flex items-center justify-between mb-8">
        <div>
          <span className="admin-badge">Admin</span>
          <h1 className="text-2xl font-semibold mt-3 text-admin-fg tracking-tight">
            대시보드
          </h1>
          <p className="text-admin-muted text-sm mt-1">
            매출 / 지표 / 통계
          </p>
        </div>
      </header>

      {me && me.role !== "admin" && (
        <div className="admin-card p-6">
          <p className="text-admin-fg-soft">
            관리자 권한이 필요합니다. 현재 역할:{" "}
            <code className="px-1.5 py-0.5 rounded bg-admin-surface-2 text-admin-accent text-xs">
              {me.role}
            </code>
          </p>
        </div>
      )}

      {error && (
        <div className="rounded-md border border-admin-danger/30 bg-admin-danger/10 px-4 py-3 mb-6 text-admin-danger text-sm">
          {error}
        </div>
      )}

      {me && me.role === "admin" && (
        <>
          <div className="flex items-center gap-2 mb-6">
            <span className="text-admin-muted text-xs mr-2 uppercase tracking-wider">
              기간
            </span>
            {WINDOWS.map((d) => (
              <button
                key={d}
                onClick={() => setDays(d)}
                className={`px-3 py-1 rounded-md text-xs font-medium transition-colors ${
                  days === d
                    ? "bg-admin-accent text-white"
                    : "bg-admin-surface text-admin-fg-soft hover:bg-admin-surface-2 border border-admin-border"
                }`}
              >
                {d}일
              </button>
            ))}
          </div>

          {loading || !stats || !revenue ? (
            <div className="text-admin-muted text-center py-12 text-sm">
              로딩 중...
            </div>
          ) : (
            <>
              {/* Revenue */}
              <section className="mb-10">
                <h2 className="text-sm font-semibold mb-4 text-admin-fg uppercase tracking-wider">
                  매출 (GMV)
                </h2>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-3">
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
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                  <StatCard
                    label="후원"
                    value={fmt(revenue.by_source.sponsorship.amount)}
                    hint={`${revenue.by_source.sponsorship.count}건`}
                  />
                  <StatCard
                    label="경매"
                    value={fmt(revenue.by_source.auction.amount)}
                    hint={`수수료 ${fmt(revenue.by_source.auction.platform_fee)}`}
                  />
                  <StatCard
                    label="즉시구매"
                    value={fmt(revenue.by_source.buy_now.amount)}
                    hint={`수수료 ${fmt(revenue.by_source.buy_now.platform_fee)}`}
                  />
                </div>
              </section>

              {/* Users */}
              <section className="mb-10">
                <h2 className="text-sm font-semibold mb-4 text-admin-fg uppercase tracking-wider">
                  사용자
                </h2>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  <StatCard
                    label="전체"
                    value={stats.users.total}
                    hint={`+${stats.users.new_in_window} ${days}일`}
                  />
                  <StatCard label="작가" value={stats.users.artists} accent />
                  <StatCard label="정지 계정" value={stats.users.suspended} />
                  <StatCard
                    label="활성 구독자"
                    value={stats.sponsorship.active_subscriptions}
                  />
                </div>
              </section>

              {/* Content */}
              <section className="mb-10">
                <h2 className="text-sm font-semibold mb-4 text-admin-fg uppercase tracking-wider">
                  콘텐츠
                </h2>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
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
                  <StatCard
                    label="신고 대기"
                    value={stats.moderation.pending_reports}
                  />
                </div>
              </section>

              {/* Auctions */}
              <section>
                <h2 className="text-sm font-semibold mb-4 text-admin-fg uppercase tracking-wider">
                  경매
                </h2>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  <StatCard label="진행 중" value={stats.auctions.active} accent />
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
