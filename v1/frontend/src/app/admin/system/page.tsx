"use client";

/**
 * /admin/system — Phase 13 C-1 cron monitor page
 *
 * Admin-only: guarded by role check.
 * Displays 26 cron worker statuses with 30s auto-refresh.
 * overdue → red row, failed → yellow row.
 */

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { fetchMe } from "@/lib/api";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:3710/v1";

// ─── Types ─────────────────────────────────────────────────────────────────

interface WorkerStatus {
  name: string;
  status: "running" | "success" | "failed" | null;
  last_run_at: string | null;
  error_message: string | null;
  run_count: number;
  is_overdue: boolean;
  interval_label: string;
}

interface CronSummary {
  total: number;
  success: number;
  failed: number;
  running: number;
  overdue: number;
}

interface CronResponse {
  workers: WorkerStatus[];
  summary: CronSummary;
}

// ─── Helpers ────────────────────────────────────────────────────────────────

function relativeTime(isoString: string | null): string {
  if (!isoString) return "-";
  const diff = Math.floor((Date.now() - new Date(isoString).getTime()) / 1000);
  if (diff < 60) return `${diff}초 전`;
  if (diff < 3600) return `${Math.floor(diff / 60)}분 전`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}시간 전`;
  return `${Math.floor(diff / 86400)}일 전`;
}

function statusBadge(worker: WorkerStatus): {
  label: string;
  className: string;
} {
  if (worker.is_overdue && worker.status !== "running") {
    return { label: "overdue", className: "bg-red-100 text-red-800" };
  }
  switch (worker.status) {
    case "running":
      return { label: "running", className: "bg-blue-100 text-blue-800" };
    case "success":
      return { label: "success", className: "bg-green-100 text-green-800" };
    case "failed":
      return { label: "failed", className: "bg-yellow-100 text-yellow-800" };
    default:
      return { label: "unknown", className: "bg-gray-100 text-gray-600" };
  }
}

function rowClassName(worker: WorkerStatus): string {
  if (worker.is_overdue && worker.status !== "running") {
    return "bg-red-50 border-red-100";
  }
  if (worker.status === "failed") {
    return "bg-yellow-50 border-yellow-100";
  }
  return "border-gray-100";
}

// ─── Fetch ──────────────────────────────────────────────────────────────────

async function fetchCronStatus(): Promise<CronResponse> {
  const token =
    typeof window !== "undefined" ? localStorage.getItem("domo_access_token") : null;
  const res = await fetch(`${API_BASE}/admin/system/crons`, {
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

// ─── Page Component ─────────────────────────────────────────────────────────

export default function AdminSystemPage() {
  const router = useRouter();
  const [authChecking, setAuthChecking] = useState(true);
  const [isAdmin, setIsAdmin] = useState(false);

  const [data, setData] = useState<CronResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastFetched, setLastFetched] = useState<Date | null>(null);

  // Auth gate
  useEffect(() => {
    fetchMe()
      .then((user) => {
        if (user.role !== "admin") {
          router.replace("/");
        } else {
          setIsAdmin(true);
        }
      })
      .catch(() => {
        router.replace("/");
      })
      .finally(() => {
        setAuthChecking(false);
      });
  }, [router]);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await fetchCronStatus();
      setData(result);
      setLastFetched(new Date());
    } catch (err) {
      setError(err instanceof Error ? err.message : "데이터 로드 실패");
    } finally {
      setLoading(false);
    }
  }, []);

  // Initial fetch + 30s auto-refresh
  useEffect(() => {
    if (!isAdmin) return;
    refresh();
    const interval = setInterval(refresh, 30_000);
    return () => clearInterval(interval);
  }, [isAdmin, refresh]);

  if (authChecking) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <p className="text-text-muted text-sm">인증 확인 중...</p>
      </div>
    );
  }
  if (!isAdmin) return null;

  const summary = data?.summary;
  const workers = data?.workers ?? [];

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-text-primary">
            Cron Worker 모니터
          </h1>
          <p className="text-sm text-text-muted mt-1">
            Phase 13 C-1 — 30초마다 자동 갱신
            {lastFetched && (
              <span className="ml-2 text-text-muted">
                (마지막: {lastFetched.toLocaleTimeString("ko-KR")})
              </span>
            )}
          </p>
        </div>
        <button
          onClick={refresh}
          disabled={loading}
          className="btn-secondary text-sm disabled:opacity-50"
        >
          {loading ? "갱신 중..." : "수동 갱신"}
        </button>
      </div>

      {/* Error */}
      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Summary Cards */}
      {summary && (
        <div className="grid grid-cols-5 gap-3 mb-6">
          {[
            { label: "전체", value: summary.total, color: "text-text-primary" },
            {
              label: "성공",
              value: summary.success,
              color: "text-green-600",
            },
            {
              label: "실행중",
              value: summary.running,
              color: "text-blue-600",
            },
            {
              label: "실패",
              value: summary.failed,
              color: "text-yellow-600",
            },
            {
              label: "지연",
              value: summary.overdue,
              color: "text-red-600",
            },
          ].map(({ label, value, color }) => (
            <div
              key={label}
              className="card p-4 text-center"
            >
              <p className={`text-2xl font-bold ${color}`}>{value}</p>
              <p className="text-xs text-text-muted mt-1">{label}</p>
            </div>
          ))}
        </div>
      )}

      {/* Workers Table */}
      <div className="card p-0 overflow-hidden">
        {loading && !data ? (
          <div className="text-center py-12 text-text-muted text-sm">
            로딩 중...
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 bg-gray-50">
                <th className="text-left px-4 py-3 font-medium text-text-secondary">
                  Worker
                </th>
                <th className="text-left px-4 py-3 font-medium text-text-secondary">
                  상태
                </th>
                <th className="text-left px-4 py-3 font-medium text-text-secondary">
                  마지막 실행
                </th>
                <th className="text-right px-4 py-3 font-medium text-text-secondary">
                  실행 횟수
                </th>
                <th className="text-left px-4 py-3 font-medium text-text-secondary">
                  간격
                </th>
                <th className="text-left px-4 py-3 font-medium text-text-secondary">
                  에러
                </th>
              </tr>
            </thead>
            <tbody>
              {workers.map((worker) => {
                const badge = statusBadge(worker);
                const rowCls = rowClassName(worker);
                return (
                  <tr
                    key={worker.name}
                    className={`border-b ${rowCls} hover:bg-opacity-80 transition-colors`}
                  >
                    <td className="px-4 py-3 font-mono text-xs font-medium text-text-primary">
                      {worker.name}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${badge.className}`}
                      >
                        {badge.label}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-text-secondary">
                      {relativeTime(worker.last_run_at)}
                    </td>
                    <td className="px-4 py-3 text-right text-text-secondary tabular-nums">
                      {worker.run_count.toLocaleString()}
                    </td>
                    <td className="px-4 py-3 text-text-secondary text-xs">
                      {worker.interval_label}
                    </td>
                    <td className="px-4 py-3 text-xs text-red-600 max-w-xs truncate">
                      {worker.error_message || "-"}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      {/* Legend */}
      <div className="mt-4 flex gap-4 text-xs text-text-muted">
        <span className="flex items-center gap-1">
          <span className="w-3 h-3 rounded bg-red-100 inline-block" />
          overdue (5분+ 미실행)
        </span>
        <span className="flex items-center gap-1">
          <span className="w-3 h-3 rounded bg-yellow-100 inline-block" />
          failed (에러 발생)
        </span>
        <span className="flex items-center gap-1">
          <span className="w-3 h-3 rounded bg-blue-100 inline-block" />
          running (실행 중)
        </span>
        <span className="flex items-center gap-1">
          <span className="w-3 h-3 rounded bg-green-100 inline-block" />
          success (정상 완료)
        </span>
      </div>
    </div>
  );
}
