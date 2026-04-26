"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { QRCodeSVG } from "qrcode.react";
import {
  AdminTotpSetup,
  adminTotpEnable,
  adminTotpSetup,
  fetchMe,
  tokenStore,
} from "@/lib/api";

export default function TotpSetupPage() {
  const router = useRouter();
  const [setup, setSetup] = useState<AdminTotpSetup | null>(null);
  const [code, setCode] = useState("");
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);
  const [recoveryCodes, setRecoveryCodes] = useState<string[] | null>(null);
  const [acknowledged, setAcknowledged] = useState(false);

  useEffect(() => {
    void (async () => {
      if (!tokenStore.get()) {
        router.replace("/login");
        return;
      }
      try {
        const me = await fetchMe();
        if (me.role !== "admin") {
          router.replace("/login");
          return;
        }
      } catch {
        router.replace("/login");
        return;
      }
      try {
        const data = await adminTotpSetup();
        setSetup(data);
      } catch (e) {
        setError(e instanceof Error ? e.message : "TOTP 셋업 실패");
      } finally {
        setLoading(false);
      }
    })();
  }, [router]);

  async function handleEnable(e: React.FormEvent) {
    e.preventDefault();
    if (!/^\d{6}$/.test(code)) return;
    setSubmitting(true);
    setError(null);
    try {
      const result = await adminTotpEnable(code);
      // Show recovery codes BEFORE marking done — admin must acknowledge
      setRecoveryCodes(result.recovery_codes);
    } catch (e) {
      setError(e instanceof Error ? e.message : "코드가 올바르지 않습니다");
      setCode("");
    } finally {
      setSubmitting(false);
    }
  }

  function copyRecoveryCodes() {
    if (!recoveryCodes) return;
    const text = recoveryCodes.join("\n");
    void navigator.clipboard.writeText(text);
  }

  function downloadRecoveryCodes() {
    if (!recoveryCodes) return;
    const text =
      "Domo Admin Recovery Codes\n" +
      "=========================\n" +
      "Generated: " + new Date().toISOString() + "\n\n" +
      recoveryCodes.join("\n") + "\n\n" +
      "WARNING: Each code can be used only ONCE if you lose access to your authenticator.\n" +
      "Store these in a password manager or print and lock away.\n";
    const blob = new Blob([text], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "domo-admin-recovery-codes.txt";
    a.click();
    URL.revokeObjectURL(url);
  }

  function finishAndContinue() {
    setDone(true);
    setTimeout(() => router.replace("/dashboard"), 800);
  }

  // QR rendered locally via qrcode.react — secret never leaves the browser.

  return (
    <main className="admin-login-bg min-h-screen px-4 py-10">
      <div className="max-w-2xl mx-auto">
        <header className="mb-8 text-center">
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
              <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
              <path d="M7 11V7a5 5 0 0 1 10 0v4" />
            </svg>
          </div>
          <span className="admin-badge">Admin · 최초 1회 보안 설정</span>
          <h1 className="text-2xl font-semibold mt-3 text-admin-fg tracking-tight">
            2단계 인증 설정 (TOTP)
          </h1>
          <p className="text-admin-muted text-sm mt-1">
            Google Authenticator / Authy / 1Password 등에 등록 후 6자리 코드를 입력하세요.
          </p>
        </header>

      {loading && (
        <div className="admin-card p-8 text-center text-admin-muted text-sm">
          시크릿 생성 중...
        </div>
      )}

      {!loading && error && !setup && (
        <div className="admin-card p-6 border border-admin-danger/30">
          <div className="text-admin-danger text-sm">{error}</div>
          <p className="text-admin-muted text-xs mt-3">
            이미 TOTP가 등록된 경우 먼저 비활성화 후 다시 시도하세요.
          </p>
        </div>
      )}

      {!loading && setup && (
        <>
          {done ? (
            <div className="admin-card p-8 text-center">
              <div className="inline-flex h-12 w-12 items-center justify-center rounded-full bg-admin-success/15 ring-1 ring-admin-success/30 mb-3">
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  className="h-6 w-6 text-admin-success"
                >
                  <polyline points="20 6 9 17 4 12" />
                </svg>
              </div>
              <p className="text-admin-fg font-semibold">2FA 등록 완료</p>
              <p className="text-admin-muted text-xs mt-2">
                대시보드로 이동합니다...
              </p>
            </div>
          ) : recoveryCodes ? (
            <div className="admin-card p-6">
              <div className="flex items-start gap-3 mb-4">
                <div className="flex-shrink-0 inline-flex h-9 w-9 items-center justify-center rounded-md bg-admin-warning/15 ring-1 ring-admin-warning/30">
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    className="h-5 w-5 text-admin-warning"
                  >
                    <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
                    <line x1="12" y1="9" x2="12" y2="13" />
                    <line x1="12" y1="17" x2="12.01" y2="17" />
                  </svg>
                </div>
                <div>
                  <h2 className="text-admin-fg text-sm font-semibold uppercase tracking-wider">
                    복구 코드 (한 번만 표시됨)
                  </h2>
                  <p className="text-admin-muted text-xs mt-1">
                    Authenticator 앱에 접근할 수 없을 때 사용하는 1회용 코드입니다. 안전한 곳(비밀번호 관리자, 인쇄물)에 보관하세요. 다시는 표시되지 않습니다.
                  </p>
                </div>
              </div>

              <div className="bg-admin-bg border border-admin-border rounded-md p-4 mb-4">
                <div className="grid grid-cols-2 gap-x-6 gap-y-2 font-mono text-sm text-admin-fg">
                  {recoveryCodes.map((c, i) => (
                    <div key={c} className="flex items-baseline gap-2">
                      <span className="text-admin-muted text-[10px] w-4 text-right">
                        {i + 1}.
                      </span>
                      <span className="tracking-wider">{c}</span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="flex flex-wrap gap-2 mb-4">
                <button
                  type="button"
                  onClick={copyRecoveryCodes}
                  className="admin-btn-secondary text-xs"
                >
                  📋 복사
                </button>
                <button
                  type="button"
                  onClick={downloadRecoveryCodes}
                  className="admin-btn-secondary text-xs"
                >
                  ⬇ .txt 다운로드
                </button>
                <button
                  type="button"
                  onClick={() => window.print()}
                  className="admin-btn-secondary text-xs"
                >
                  🖨 인쇄
                </button>
              </div>

              <label className="flex items-start gap-2 mb-4 cursor-pointer">
                <input
                  type="checkbox"
                  checked={acknowledged}
                  onChange={(e) => setAcknowledged(e.target.checked)}
                  className="mt-0.5"
                />
                <span className="text-admin-fg-soft text-xs">
                  복구 코드를 안전한 곳에 저장했음을 확인합니다. 분실 시 admin 계정 복구가 어렵다는 점을 이해합니다.
                </span>
              </label>

              <button
                type="button"
                onClick={finishAndContinue}
                disabled={!acknowledged}
                className="admin-btn-primary w-full"
              >
                완료 → 대시보드
              </button>
            </div>
          ) : (
            <div className="grid md:grid-cols-2 gap-6">
              {/* Step 1: scan QR */}
              <div className="admin-card p-6">
                <h2 className="text-admin-fg text-sm font-semibold uppercase tracking-wider mb-3">
                  1. QR 스캔
                </h2>
                <div className="bg-white rounded-md p-3 mb-3 inline-block">
                  <QRCodeSVG
                    value={setup.otpauth_uri}
                    size={220}
                    level="M"
                    marginSize={2}
                  />
                </div>
                <details className="mt-2">
                  <summary className="text-admin-muted text-xs cursor-pointer hover:text-admin-fg-soft">
                    QR이 안 보이면 시크릿을 직접 입력
                  </summary>
                  <div className="mt-2 p-3 bg-admin-bg border border-admin-border rounded-md font-mono text-xs text-admin-fg-soft break-all">
                    {setup.secret}
                  </div>
                  <p className="text-admin-muted text-[10px] mt-2">
                    Issuer: {setup.issuer}
                  </p>
                </details>
              </div>

              {/* Step 2: verify */}
              <div className="admin-card p-6">
                <h2 className="text-admin-fg text-sm font-semibold uppercase tracking-wider mb-3">
                  2. 코드 확인
                </h2>
                <form onSubmit={handleEnable} className="space-y-4">
                  <div>
                    <label
                      htmlFor="totp"
                      className="block text-admin-fg text-xs font-medium mb-1.5"
                    >
                      Authenticator 6자리 코드
                    </label>
                    <input
                      id="totp"
                      type="text"
                      inputMode="numeric"
                      pattern="\d{6}"
                      maxLength={6}
                      autoComplete="one-time-code"
                      autoFocus
                      placeholder="123456"
                      value={code}
                      onChange={(e) =>
                        setCode(e.target.value.replace(/\D/g, "").slice(0, 6))
                      }
                      disabled={submitting}
                      className="admin-input w-full text-center text-lg tracking-[0.4em] font-mono"
                    />
                  </div>

                  {error && (
                    <div className="rounded-md border border-admin-danger/30 bg-admin-danger/10 px-3 py-2 text-xs text-admin-danger">
                      {error}
                    </div>
                  )}

                  <button
                    type="submit"
                    disabled={submitting || code.length !== 6}
                    className="admin-btn-primary w-full"
                  >
                    {submitting ? "확인 중..." : "활성화"}
                  </button>

                  <p className="text-admin-muted text-[11px]">
                    활성화 후 다음 로그인부터 비밀번호 + 6자리 코드가 모두
                    필요합니다.
                  </p>
                </form>
              </div>
            </div>
          )}
        </>
      )}

        <div className="mt-6 text-center">
          <button
            type="button"
            onClick={async () => {
              const { logout } = await import("@/lib/api");
              await logout();
              router.replace("/login");
            }}
            className="text-admin-muted hover:text-admin-danger text-xs transition-colors"
          >
            취소하고 로그아웃
          </button>
        </div>
      </div>
    </main>
  );
}
