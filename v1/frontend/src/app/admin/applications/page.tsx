"use client";

import { useEffect, useState } from "react";
import {
  ApiClientError,
  ApiUser,
  ArtistApplication,
  approveApplication,
  fetchMe,
  listApplications,
  logout,
  loginWithMockEmail,
  rejectApplication,
  tokenStore,
} from "@/lib/api";

export default function AdminApplicationsPage() {
  const [me, setMe] = useState<ApiUser | null>(null);
  const [applications, setApplications] = useState<ArtistApplication[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [loginEmail, setLoginEmail] = useState("");
  const [actingId, setActingId] = useState<string | null>(null);
  const [reviewNote, setReviewNote] = useState<Record<string, string>>({});

  useEffect(() => {
    void bootstrap();
  }, []);

  async function bootstrap() {
    setLoading(true);
    setError(null);
    try {
      if (tokenStore.get()) {
        const user = await fetchMe();
        setMe(user);
        if (user.role === "admin") {
          const apps = await listApplications("pending");
          setApplications(apps);
        }
      }
    } catch (e) {
      if (e instanceof ApiClientError && e.code === "UNAUTHORIZED") {
        tokenStore.clear();
        setMe(null);
      } else {
        setError(e instanceof Error ? e.message : "Unknown error");
      }
    } finally {
      setLoading(false);
    }
  }

  async function handleLogin() {
    if (!loginEmail.trim()) return;
    setError(null);
    try {
      const user = await loginWithMockEmail(loginEmail.trim());
      setMe(user);
      if (user.role === "admin") {
        const apps = await listApplications("pending");
        setApplications(apps);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Login failed");
    }
  }

  async function handleLogout() {
    await logout();
    setMe(null);
    setApplications([]);
  }

  async function handleApprove(id: string) {
    setActingId(id);
    try {
      await approveApplication(id, reviewNote[id]);
      setApplications((prev) => prev.filter((a) => a.id !== id));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Approve failed");
    } finally {
      setActingId(null);
    }
  }

  async function handleReject(id: string) {
    setActingId(id);
    try {
      await rejectApplication(id, reviewNote[id]);
      setApplications((prev) => prev.filter((a) => a.id !== id));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Reject failed");
    } finally {
      setActingId(null);
    }
  }

  return (
    <main className="min-h-screen px-6 py-12 max-w-5xl mx-auto">
      <header className="flex items-center justify-between mb-10">
        <div>
          <span className="badge-primary">Admin</span>
          <h1 className="text-3xl font-bold mt-3">작가 심사 승인</h1>
          <p className="text-text-secondary text-sm mt-1">
            Artist application review queue
          </p>
        </div>
        {me && (
          <div className="text-right">
            <div className="text-sm text-text-secondary">{me.email}</div>
            <div className="text-xs text-text-muted mb-2">role: {me.role}</div>
            <button onClick={handleLogout} className="btn-ghost text-sm">
              로그아웃
            </button>
          </div>
        )}
      </header>

      {error && (
        <div className="card border-danger p-4 mb-6 text-danger text-sm">
          {error}
        </div>
      )}

      {!me && (
        <div className="card p-6 max-w-md">
          <h2 className="text-lg font-semibold mb-4">로그인 (개발 모드)</h2>
          <p className="text-text-secondary text-sm mb-4">
            테스트용 모의 로그인입니다. 관리자 권한이 필요합니다.
          </p>
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

      {me && me.role !== "admin" && (
        <div className="card p-6">
          <h2 className="text-lg font-semibold mb-2">권한 없음</h2>
          <p className="text-text-secondary">
            관리자 권한이 필요합니다. 현재 역할: <code>{me.role}</code>
          </p>
        </div>
      )}

      {me && me.role === "admin" && (
        <section>
          <div className="text-sm text-text-secondary mb-4">
            대기 중인 심사: {applications.length}건
          </div>

          {loading && <div className="text-text-muted">로딩 중...</div>}

          {!loading && applications.length === 0 && (
            <div className="card p-8 text-center text-text-muted">
              대기 중인 심사 신청이 없습니다.
            </div>
          )}

          <div className="space-y-4">
            {applications.map((app) => (
              <div key={app.id} className="card p-6">
                <div className="flex items-start justify-between mb-4">
                  <div>
                    <div className="text-xs text-text-muted">
                      신청 ID: {app.id.slice(0, 8)}...
                    </div>
                    <div className="text-xs text-text-muted">
                      신청일:{" "}
                      {new Date(app.created_at).toLocaleString("ko-KR")}
                    </div>
                  </div>
                  <span className="badge-primary">{app.status}</span>
                </div>

                <dl className="grid grid-cols-1 gap-3 text-sm mb-4">
                  {app.school && (
                    <div>
                      <dt className="text-text-muted">학교</dt>
                      <dd>{app.school}</dd>
                    </div>
                  )}
                  {app.statement && (
                    <div>
                      <dt className="text-text-muted">자기소개</dt>
                      <dd className="whitespace-pre-wrap">{app.statement}</dd>
                    </div>
                  )}
                  {app.intro_video_url && (
                    <div>
                      <dt className="text-text-muted">소개 영상</dt>
                      <dd>
                        <a
                          href={app.intro_video_url}
                          target="_blank"
                          rel="noopener"
                          className="text-primary underline"
                        >
                          {app.intro_video_url}
                        </a>
                      </dd>
                    </div>
                  )}
                  {app.portfolio_urls && app.portfolio_urls.length > 0 && (
                    <div>
                      <dt className="text-text-muted">포트폴리오</dt>
                      <dd className="grid grid-cols-3 gap-2 mt-1">
                        {app.portfolio_urls.map((url, i) => (
                          <a
                            key={i}
                            href={url}
                            target="_blank"
                            rel="noopener"
                            className="text-primary underline text-xs truncate"
                          >
                            {url}
                          </a>
                        ))}
                      </dd>
                    </div>
                  )}
                </dl>

                <textarea
                  placeholder="심사 메모 (선택)"
                  value={reviewNote[app.id] || ""}
                  onChange={(e) =>
                    setReviewNote((prev) => ({
                      ...prev,
                      [app.id]: e.target.value,
                    }))
                  }
                  className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm text-text-primary mb-3 focus:border-primary outline-none resize-none"
                  rows={2}
                />

                <div className="flex gap-2">
                  <button
                    onClick={() => handleApprove(app.id)}
                    disabled={actingId === app.id}
                    className="btn-primary text-sm disabled:opacity-50"
                  >
                    {actingId === app.id ? "처리 중..." : "승인"}
                  </button>
                  <button
                    onClick={() => handleReject(app.id)}
                    disabled={actingId === app.id}
                    className="btn-secondary text-sm disabled:opacity-50"
                  >
                    거절
                  </button>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}
    </main>
  );
}
