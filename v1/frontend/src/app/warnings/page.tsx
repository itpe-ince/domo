"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  ApiUser,
  appealWarning,
  fetchMe,
  fetchMyWarnings,
  loginWithMockEmail,
  tokenStore,
  WarningView,
} from "@/lib/api";

export default function MyWarningsPage() {
  const [me, setMe] = useState<ApiUser | null>(null);
  const [warnings, setWarnings] = useState<WarningView[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [appealNote, setAppealNote] = useState<Record<string, string>>({});
  const [acting, setActing] = useState<string | null>(null);
  const [loginEmail, setLoginEmail] = useState("");

  useEffect(() => {
    void load();
  }, []);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      if (!tokenStore.get()) return;
      const u = await fetchMe();
      setMe(u);
      setWarnings(await fetchMyWarnings());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }

  async function handleAppeal(id: string) {
    const note = appealNote[id]?.trim();
    if (!note) {
      setError("이의 내용을 입력해주세요.");
      return;
    }
    setActing(id);
    setError(null);
    try {
      const updated = await appealWarning(id, note);
      setWarnings((prev) => prev.map((w) => (w.id === id ? updated : w)));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Appeal failed");
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

  const active = warnings.filter((w) => w.is_active);
  const cancelled = warnings.filter((w) => !w.is_active);

  return (
    <main className="flex-1 min-w-0 max-w-3xl mx-auto px-6 py-8">
      <header className="flex items-center justify-between mb-8">
        <div>
          <span className="badge-primary">My Account</span>
          <h1 className="text-3xl font-bold mt-3">내 경고</h1>
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
          {me.warning_count >= 3 && me.status !== "active" && (
            <div className="card border-danger p-4 mb-6">
              <p className="text-danger font-semibold">⚠ 계정 정지</p>
              <p className="text-text-secondary text-sm mt-1">
                누적 경고 {me.warning_count}회로 계정이 정지되었습니다. 활성
                경고에 이의 제기가 가능합니다.
              </p>
            </div>
          )}

          {loading ? (
            <div className="text-text-muted text-center py-8">로딩 중...</div>
          ) : warnings.length === 0 ? (
            <div className="card p-12 text-center text-text-muted">
              경고 기록이 없습니다.
            </div>
          ) : (
            <>
              <section>
                <h2 className="text-lg font-semibold mb-3">
                  활성 경고 ({active.length})
                </h2>
                {active.length === 0 ? (
                  <p className="text-text-muted text-sm mb-6">없음</p>
                ) : (
                  <ul className="space-y-3 mb-8">
                    {active.map((w) => (
                      <li key={w.id} className="card border-warning p-5">
                        <div className="flex items-start justify-between mb-2">
                          <span className="badge-primary">활성</span>
                          <span className="text-text-muted text-xs">
                            {new Date(w.created_at).toLocaleString("ko-KR")}
                          </span>
                        </div>
                        <p className="text-text-primary mb-3">{w.reason}</p>

                        {w.appealed ? (
                          <div className="bg-background rounded p-3 border border-border">
                            <p className="text-primary text-sm mb-1">
                              ✓ 이의 제기 접수됨
                            </p>
                            {w.appeal_note && (
                              <p className="text-text-secondary text-xs">
                                {w.appeal_note}
                              </p>
                            )}
                          </div>
                        ) : (
                          <>
                            <textarea
                              placeholder="이의 내용을 작성해주세요"
                              value={appealNote[w.id] || ""}
                              onChange={(e) =>
                                setAppealNote((prev) => ({
                                  ...prev,
                                  [w.id]: e.target.value,
                                }))
                              }
                              rows={3}
                              className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm mb-2 focus:border-primary outline-none resize-none"
                            />
                            <button
                              onClick={() => handleAppeal(w.id)}
                              disabled={acting === w.id}
                              className="btn-primary text-xs disabled:opacity-50"
                            >
                              {acting === w.id ? "제출 중..." : "이의 제기"}
                            </button>
                          </>
                        )}
                      </li>
                    ))}
                  </ul>
                )}
              </section>

              {cancelled.length > 0 && (
                <section>
                  <h2 className="text-lg font-semibold mb-3 text-text-muted">
                    취소된 경고 ({cancelled.length})
                  </h2>
                  <ul className="space-y-2">
                    {cancelled.map((w) => (
                      <li key={w.id} className="card p-4 opacity-60">
                        <div className="flex items-start justify-between text-sm">
                          <p>{w.reason}</p>
                          <span className="text-text-muted text-xs">
                            취소{" "}
                            {w.cancelled_at &&
                              new Date(w.cancelled_at).toLocaleString("ko-KR")}
                          </span>
                        </div>
                      </li>
                    ))}
                  </ul>
                </section>
              )}
            </>
          )}
        </>
      )}
    </main>
  );
}
