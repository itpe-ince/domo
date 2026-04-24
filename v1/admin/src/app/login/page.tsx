"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { fetchMe, loginWithMockEmail, tokenStore } from "@/lib/api";

export default function AdminLoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    void (async () => {
      if (!tokenStore.get()) {
        setChecking(false);
        return;
      }
      try {
        const u = await fetchMe();
        if (u.role === "admin") {
          router.replace("/dashboard");
          return;
        }
      } catch {
        tokenStore.clear();
      }
      setChecking(false);
    })();
  }, [router]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!email.trim()) return;
    setSubmitting(true);
    setError(null);
    try {
      const u = await loginWithMockEmail(email.trim());
      if (u.role !== "admin") {
        tokenStore.clear();
        setError(`관리자 권한이 없습니다. 현재 역할: ${u.role}`);
        return;
      }
      router.replace("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "로그인 실패");
    } finally {
      setSubmitting(false);
    }
  }

  if (checking) {
    return (
      <div className="admin-login-bg flex min-h-screen items-center justify-center">
        <div className="text-admin-muted text-sm">세션 확인 중...</div>
      </div>
    );
  }

  return (
    <div className="admin-login-bg flex min-h-screen items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <div className="inline-flex h-12 w-12 items-center justify-center rounded-lg bg-admin-accent/10 ring-1 ring-admin-accent/30 mb-4">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              className="h-6 w-6 text-admin-accent"
            >
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
            </svg>
          </div>
          <h1 className="text-admin-fg text-xl font-semibold tracking-tight">
            Domo Admin Console
          </h1>
          <p className="text-admin-muted text-xs mt-1">
            관리자 전용 — 권한 있는 계정으로만 접근 가능합니다
          </p>
        </div>

        <form
          onSubmit={handleSubmit}
          className="admin-card p-6 space-y-4"
        >
          <div>
            <label
              htmlFor="email"
              className="block text-admin-fg text-xs font-medium mb-1.5"
            >
              관리자 이메일
            </label>
            <input
              id="email"
              type="email"
              autoFocus
              autoComplete="email"
              placeholder="admin@domo.example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              disabled={submitting}
              className="admin-input w-full"
            />
          </div>

          {error && (
            <div className="rounded-md border border-admin-danger/30 bg-admin-danger/10 px-3 py-2 text-xs text-admin-danger">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={submitting || !email.trim()}
            className="admin-btn-primary w-full"
          >
            {submitting ? "로그인 중..." : "로그인"}
          </button>

          <p className="text-admin-muted text-[11px] text-center pt-2 border-t border-admin-border">
            개발 모드 · Mock SSO (Google)
          </p>
        </form>

        <div className="mt-6 text-center">
          <a
            href="http://localhost:3700"
            className="text-admin-muted hover:text-admin-accent text-xs transition-colors"
          >
            ← 사용자 앱으로 돌아가기
          </a>
        </div>
      </div>
    </div>
  );
}
