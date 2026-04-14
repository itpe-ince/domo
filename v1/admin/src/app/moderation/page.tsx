"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  ApiUser,
  adminCancelWarning,
  adminListAppeals,
  adminListReports,
  adminRejectAppeal,
  adminResolveReport,
  fetchMe,
  loginWithMockEmail,
  ReportView,
  tokenStore,
  WarningView,
} from "@/lib/api";

type Tab = "reports" | "appeals";

export default function ModerationPage() {
  const [me, setMe] = useState<ApiUser | null>(null);
  const [tab, setTab] = useState<Tab>("reports");
  const [reports, setReports] = useState<ReportView[]>([]);
  const [appeals, setAppeals] = useState<WarningView[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actingId, setActingId] = useState<string | null>(null);
  const [resolveNote, setResolveNote] = useState<Record<string, string>>({});
  const [loginEmail, setLoginEmail] = useState("");

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab]);

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

      if (tab === "reports") {
        setReports(await adminListReports("pending"));
      } else {
        setAppeals(await adminListAppeals());
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }

  async function handleResolve(
    id: string,
    action: "issue_warning" | "dismiss"
  ) {
    setActingId(id);
    try {
      await adminResolveReport(id, action, resolveNote[id]);
      setReports((prev) => prev.filter((r) => r.id !== id));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Resolve failed");
    } finally {
      setActingId(null);
    }
  }

  async function handleCancelWarning(id: string) {
    setActingId(id);
    try {
      await adminCancelWarning(id);
      setAppeals((prev) => prev.filter((w) => w.id !== id));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Cancel failed");
    } finally {
      setActingId(null);
    }
  }

  async function handleRejectAppeal(id: string) {
    setActingId(id);
    try {
      await adminRejectAppeal(id);
      setAppeals((prev) => prev.filter((w) => w.id !== id));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Reject failed");
    } finally {
      setActingId(null);
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
    <main className="min-h-screen px-6 py-8 max-w-5xl mx-auto">
      <header className="flex items-center justify-between mb-8">
        <div>
          <span className="badge-primary">Admin</span>
          <h1 className="text-3xl font-bold mt-3">모더레이션</h1>
          <p className="text-text-secondary text-sm mt-1">
            신고 처리 + 이의 제기 검토
          </p>
        </div>
        <Link href="/admin/applications" className="btn-ghost text-sm">
          작가 승인 →
        </Link>
      </header>

      {!me && (
        <div className="card p-6 max-w-md">
          <h2 className="text-lg font-semibold mb-3">로그인 (개발 모드)</h2>
          <input
            type="email"
            placeholder="admin@domo.example.com"
            value={loginEmail}
            onChange={(e) => setLoginEmail(e.target.value)}
            className="w-full bg-background border border-border rounded-lg px-4 py-2 text-text-primary mb-4 focus:border-primary outline-none"
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

      {me && me.role === "admin" && (
        <>
          <div className="flex gap-2 mb-6">
            <button
              onClick={() => setTab("reports")}
              className={`px-4 py-2 rounded-full text-sm transition-colors ${
                tab === "reports"
                  ? "bg-primary text-background"
                  : "bg-surface text-text-secondary"
              }`}
            >
              신고 처리 ({reports.length})
            </button>
            <button
              onClick={() => setTab("appeals")}
              className={`px-4 py-2 rounded-full text-sm transition-colors ${
                tab === "appeals"
                  ? "bg-primary text-background"
                  : "bg-surface text-text-secondary"
              }`}
            >
              이의 제기 ({appeals.length})
            </button>
          </div>

          {error && (
            <div className="card border-danger p-4 mb-6 text-danger text-sm">
              {error}
            </div>
          )}

          {loading && (
            <div className="text-text-muted text-center py-8">로딩 중...</div>
          )}

          {!loading && tab === "reports" && (
            <>
              {reports.length === 0 ? (
                <div className="card p-12 text-center text-text-muted">
                  대기 중인 신고가 없습니다.
                </div>
              ) : (
                <ul className="space-y-3">
                  {reports.map((r) => (
                    <li key={r.id} className="card p-5">
                      <div className="flex items-start justify-between mb-3">
                        <div>
                          <span className="badge-primary">{r.target_type}</span>
                          <span className="ml-2 text-text-secondary text-sm">
                            사유: {r.reason}
                          </span>
                        </div>
                        <span className="text-text-muted text-xs">
                          {new Date(r.created_at).toLocaleString("ko-KR")}
                        </span>
                      </div>

                      {r.description && (
                        <p className="text-text-secondary text-sm mb-3">
                          {r.description}
                        </p>
                      )}

                      <div className="text-xs text-text-muted mb-3">
                        대상 ID: {r.target_id.slice(0, 8)}... · 신고자:{" "}
                        {r.reporter_id.slice(0, 8)}...
                        {r.target_type === "post" && (
                          <>
                            {" · "}
                            <Link
                              href={`/posts/${r.target_id}`}
                              className="text-primary underline"
                            >
                              보기
                            </Link>
                          </>
                        )}
                      </div>

                      <textarea
                        placeholder="처리 메모 (선택)"
                        value={resolveNote[r.id] || ""}
                        onChange={(e) =>
                          setResolveNote((prev) => ({
                            ...prev,
                            [r.id]: e.target.value,
                          }))
                        }
                        className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm mb-3 focus:border-primary outline-none resize-none"
                        rows={2}
                      />

                      <div className="flex gap-2">
                        <button
                          onClick={() => handleResolve(r.id, "issue_warning")}
                          disabled={actingId === r.id}
                          className="btn-primary text-xs disabled:opacity-50"
                        >
                          ⚠ 경고 발급
                        </button>
                        <button
                          onClick={() => handleResolve(r.id, "dismiss")}
                          disabled={actingId === r.id}
                          className="btn-secondary text-xs disabled:opacity-50"
                        >
                          기각
                        </button>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </>
          )}

          {!loading && tab === "appeals" && (
            <>
              {appeals.length === 0 ? (
                <div className="card p-12 text-center text-text-muted">
                  대기 중인 이의 제기가 없습니다.
                </div>
              ) : (
                <ul className="space-y-3">
                  {appeals.map((w) => (
                    <li key={w.id} className="card p-5">
                      <div className="flex items-start justify-between mb-3">
                        <div>
                          <span className="badge-primary">이의 제기</span>
                        </div>
                        <span className="text-text-muted text-xs">
                          {new Date(w.created_at).toLocaleString("ko-KR")}
                        </span>
                      </div>

                      <div className="text-sm space-y-1 mb-3">
                        <div>
                          <span className="text-text-muted">경고 사유:</span>{" "}
                          {w.reason}
                        </div>
                        <div>
                          <span className="text-text-muted">유저 ID:</span>{" "}
                          {w.user_id.slice(0, 8)}...
                        </div>
                        {w.appeal_note && (
                          <div className="mt-2 p-2 bg-background rounded border border-border">
                            <span className="text-text-muted text-xs">
                              이의 내용:
                            </span>
                            <p className="text-text-primary mt-1">
                              {w.appeal_note}
                            </p>
                          </div>
                        )}
                      </div>

                      <div className="flex gap-2">
                        <button
                          onClick={() => handleCancelWarning(w.id)}
                          disabled={actingId === w.id}
                          className="btn-primary text-xs disabled:opacity-50"
                        >
                          ✓ 경고 취소 (이의 인정)
                        </button>
                        <button
                          onClick={() => handleRejectAppeal(w.id)}
                          disabled={actingId === w.id}
                          className="btn-secondary text-xs disabled:opacity-50"
                        >
                          이의 거절
                        </button>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </>
          )}
        </>
      )}
    </main>
  );
}
