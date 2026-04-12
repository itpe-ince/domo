"use client";

import { useEffect, useState } from "react";
import { ApiClientError, loginWithMockEmail } from "@/lib/api";

const QUICK_ACCOUNTS = [
  { email: "admin@domo.example.com", label: "Admin" },
  { email: "maria@example.com", label: "Maria (Artist)" },
  { email: "alex@example.com", label: "Alex (Collector)" },
];

export function LoginModal({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) {
      setEmail("");
      setError(null);
    }
  }, [open]);

  async function handleLogin(target: string) {
    const value = target.trim();
    if (!value) {
      setError("이메일을 입력해주세요.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await loginWithMockEmail(value);
      onClose();
    } catch (e) {
      setError(
        e instanceof ApiClientError
          ? `${e.code}: ${e.message}`
          : e instanceof Error
            ? e.message
            : "Login failed"
      );
    } finally {
      setBusy(false);
    }
  }

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 px-4"
      onClick={onClose}
    >
      <div
        className="card w-full max-w-md p-6 space-y-4"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="flex items-center justify-between">
          <div>
            <span className="badge-primary">Dev Mode</span>
            <h2 className="text-xl font-bold mt-2">Domo 로그인</h2>
          </div>
          <button
            onClick={onClose}
            className="text-text-muted hover:text-text-primary text-xl leading-none"
            aria-label="닫기"
          >
            ×
          </button>
        </header>

        <p className="text-text-secondary text-sm">
          개발 모드에서는 이메일만 입력하면 즉시 로그인됩니다. 실제 Google OAuth는
          `GOOGLE_CLIENT_ID` 환경변수 등록 후 활성화됩니다.
        </p>

        <div>
          <label className="block text-sm text-text-secondary mb-1">
            이메일
          </label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") handleLogin(email);
            }}
            placeholder="email@example.com"
            className="w-full bg-background border border-border rounded-lg px-4 py-2 text-text-primary focus:border-primary outline-none"
            autoFocus
          />
        </div>

        {error && (
          <div className="card border-danger p-3 text-danger text-sm">
            {error}
          </div>
        )}

        <button
          onClick={() => handleLogin(email)}
          disabled={busy}
          className="btn-primary w-full disabled:opacity-50"
        >
          {busy ? "로그인 중..." : "로그인"}
        </button>

        <div>
          <p className="text-text-muted text-xs mb-2">빠른 로그인:</p>
          <div className="flex flex-wrap gap-2">
            {QUICK_ACCOUNTS.map((a) => (
              <button
                key={a.email}
                onClick={() => handleLogin(a.email)}
                disabled={busy}
                className="text-xs px-3 py-1.5 rounded-full bg-surface-hover text-text-secondary hover:text-primary disabled:opacity-50"
              >
                {a.label}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
