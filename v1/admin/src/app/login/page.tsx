"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { startAuthentication } from "@simplewebauthn/browser";
import {
  adminLoginStep1,
  adminLoginVerifyRecoveryCode,
  adminLoginVerifyTotp,
  fetchMe,
  tokenStore,
  webauthnAuthenticateBegin,
  webauthnAuthenticateFinish,
} from "@/lib/api";

type Stage = "checking" | "password" | "totp";
type SecondFactorMode = "totp" | "recovery";

export default function AdminLoginPage() {
  const router = useRouter();
  const [stage, setStage] = useState<Stage>("checking");
  const [secondFactor, setSecondFactor] = useState<SecondFactorMode>("totp");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [totpCode, setTotpCode] = useState("");
  const [recoveryCode, setRecoveryCode] = useState("");
  const [challengeToken, setChallengeToken] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const totpInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    void (async () => {
      if (!tokenStore.get()) {
        setStage("password");
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
      setStage("password");
    })();
  }, [router]);

  useEffect(() => {
    if (stage === "totp") {
      // Auto-focus the TOTP input when transitioning
      setTimeout(() => totpInputRef.current?.focus(), 50);
    }
  }, [stage]);

  async function handlePasswordSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!email.trim() || !password) return;
    setSubmitting(true);
    setError(null);
    try {
      const res = await adminLoginStep1(email.trim(), password);
      if (res.totp_required === true) {
        setChallengeToken(res.challenge_token);
        setStage("totp");
      } else {
        // First-time admin: tokens already stored, redirect to TOTP setup
        if (res.totp_setup_required) {
          router.replace("/settings/totp-setup");
        } else {
          router.replace("/dashboard");
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "로그인 실패");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleTotpSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!challengeToken) return;
    setSubmitting(true);
    setError(null);
    try {
      if (secondFactor === "totp") {
        if (!/^\d{6}$/.test(totpCode)) return;
        const result = await adminLoginVerifyTotp(challengeToken, totpCode);
        // Recovery codes low warning surfaces post-login
        if (result.recovery_codes_remaining <= 2) {
          console.warn(
            `Only ${result.recovery_codes_remaining} recovery code(s) remaining`
          );
        }
        router.replace("/dashboard");
      } else {
        if (recoveryCode.replace(/[\s-]/g, "").length < 12) return;
        const result = await adminLoginVerifyRecoveryCode(
          challengeToken,
          recoveryCode
        );
        // Force redirect to settings to reissue codes if depleted
        if (result.recovery_codes_remaining <= 2) {
          router.replace("/settings/recovery-codes?low=1");
        } else {
          router.replace("/dashboard");
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "인증 코드 검증 실패");
      if (secondFactor === "totp") {
        setTotpCode("");
      } else {
        setRecoveryCode("");
      }
    } finally {
      setSubmitting(false);
    }
  }

  function switchSecondFactor(mode: SecondFactorMode) {
    setSecondFactor(mode);
    setError(null);
    setTotpCode("");
    setRecoveryCode("");
  }

  function backToPassword() {
    setStage("password");
    setChallengeToken(null);
    setTotpCode("");
    setRecoveryCode("");
    setSecondFactor("totp");
    setError(null);
  }

  async function handlePasskeyLogin() {
    if (!email.trim()) {
      setError("이메일을 먼저 입력하세요.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const begin = await webauthnAuthenticateBegin(email.trim());
      const opts = JSON.parse(begin.options);
      const assertion = await startAuthentication({ optionsJSON: opts });
      await webauthnAuthenticateFinish(begin.challenge_token, assertion);
      router.replace("/dashboard");
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Passkey 로그인 실패";
      // Browser cancel — silent
      if (/cancel|abort|NotAllowedError/i.test(msg)) {
        setError(null);
      } else {
        setError(msg);
      }
    } finally {
      setSubmitting(false);
    }
  }

  if (stage === "checking") {
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
            {stage === "password"
              ? "관리자 계정으로 로그인 (이메일 + 비밀번호)"
              : "2단계 인증 (Authenticator 앱의 6자리 코드)"}
          </p>
        </div>

        {/* Step indicator */}
        <div className="flex items-center justify-center gap-2 mb-5 text-[11px]">
          <span
            className={`flex items-center gap-1.5 ${
              stage === "password" ? "text-admin-accent" : "text-admin-muted"
            }`}
          >
            <span
              className={`inline-flex h-4 w-4 items-center justify-center rounded-full text-[10px] font-bold ${
                stage === "password"
                  ? "bg-admin-accent text-white"
                  : "bg-admin-success text-white"
              }`}
            >
              {stage === "password" ? "1" : "✓"}
            </span>
            비밀번호
          </span>
          <span className="text-admin-border">─</span>
          <span
            className={`flex items-center gap-1.5 ${
              stage === "totp" ? "text-admin-accent" : "text-admin-muted"
            }`}
          >
            <span
              className={`inline-flex h-4 w-4 items-center justify-center rounded-full text-[10px] font-bold ${
                stage === "totp"
                  ? "bg-admin-accent text-white"
                  : "bg-admin-surface-2 text-admin-muted ring-1 ring-admin-border"
              }`}
            >
              2
            </span>
            2FA 코드
          </span>
        </div>

        {stage === "password" && (
          <form onSubmit={handlePasswordSubmit} className="admin-card p-6 space-y-4">
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
                autoComplete="username"
                placeholder="admin@domo.example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                disabled={submitting}
                className="admin-input w-full"
              />
            </div>
            <div>
              <label
                htmlFor="password"
                className="block text-admin-fg text-xs font-medium mb-1.5"
              >
                비밀번호
              </label>
              <input
                id="password"
                type="password"
                autoComplete="current-password"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
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
              disabled={submitting || !email.trim() || !password}
              className="admin-btn-primary w-full"
            >
              {submitting ? "확인 중..." : "다음 →"}
            </button>

            {/* Passkey alternative — bypass password+TOTP entirely */}
            <div className="relative my-2">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-admin-border"></div>
              </div>
              <div className="relative flex justify-center">
                <span className="bg-admin-surface px-2 text-[10px] uppercase tracking-wider text-admin-muted">
                  또는
                </span>
              </div>
            </div>

            <button
              type="button"
              onClick={handlePasskeyLogin}
              disabled={submitting || !email.trim()}
              className="admin-btn-secondary w-full flex items-center justify-center gap-2"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                className="h-4 w-4"
              >
                <path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4" />
              </svg>
              Passkey로 로그인 (생체/보안키)
            </button>
            <p className="text-admin-muted text-[10px] text-center">
              이메일 입력 후 클릭 — 비밀번호 + TOTP 단계를 건너뜁니다
            </p>

            <p className="text-admin-muted text-[11px] text-center pt-2 border-t border-admin-border">
              관리자 전용 자격증명 인증 · SNS 로그인 비활성
            </p>
          </form>
        )}

        {stage === "totp" && (
          <form onSubmit={handleTotpSubmit} className="admin-card p-6 space-y-4">
            {/* Toggle: TOTP ↔ Recovery code */}
            <div className="flex rounded-md border border-admin-border bg-admin-bg p-0.5 text-[11px]">
              <button
                type="button"
                onClick={() => switchSecondFactor("totp")}
                disabled={submitting}
                className={`flex-1 py-1.5 rounded-sm transition-colors ${
                  secondFactor === "totp"
                    ? "bg-admin-accent text-white font-medium"
                    : "text-admin-muted hover:text-admin-fg"
                }`}
              >
                Authenticator 코드
              </button>
              <button
                type="button"
                onClick={() => switchSecondFactor("recovery")}
                disabled={submitting}
                className={`flex-1 py-1.5 rounded-sm transition-colors ${
                  secondFactor === "recovery"
                    ? "bg-admin-accent text-white font-medium"
                    : "text-admin-muted hover:text-admin-fg"
                }`}
              >
                복구 코드
              </button>
            </div>

            {secondFactor === "totp" ? (
              <div>
                <label
                  htmlFor="totp"
                  className="block text-admin-fg text-xs font-medium mb-1.5"
                >
                  Authenticator 6자리 코드
                </label>
                <input
                  id="totp"
                  ref={totpInputRef}
                  type="text"
                  inputMode="numeric"
                  pattern="\d{6}"
                  maxLength={6}
                  autoComplete="one-time-code"
                  placeholder="123456"
                  value={totpCode}
                  onChange={(e) =>
                    setTotpCode(e.target.value.replace(/\D/g, "").slice(0, 6))
                  }
                  disabled={submitting}
                  className="admin-input w-full text-center text-lg tracking-[0.4em] font-mono"
                />
                <p className="text-admin-muted text-[11px] mt-1.5">
                  Google Authenticator / Authy / 1Password 등의 6자리 코드
                </p>
              </div>
            ) : (
              <div>
                <label
                  htmlFor="recovery"
                  className="block text-admin-fg text-xs font-medium mb-1.5"
                >
                  복구 코드 (XXXX-XXXX-XXXX)
                </label>
                <input
                  id="recovery"
                  type="text"
                  autoComplete="off"
                  placeholder="ABCD-EFGH-JKMN"
                  value={recoveryCode}
                  onChange={(e) => setRecoveryCode(e.target.value.toUpperCase())}
                  disabled={submitting}
                  className="admin-input w-full text-center text-base tracking-[0.2em] font-mono uppercase"
                />
                <p className="text-admin-muted text-[11px] mt-1.5">
                  TOTP 등록 시 받은 1회용 백업 코드 (대시 생략 가능, 대소문자 무시)
                </p>
              </div>
            )}

            {error && (
              <div className="rounded-md border border-admin-danger/30 bg-admin-danger/10 px-3 py-2 text-xs text-admin-danger">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={
                submitting ||
                (secondFactor === "totp"
                  ? totpCode.length !== 6
                  : recoveryCode.replace(/[\s-]/g, "").length < 12)
              }
              className="admin-btn-primary w-full"
            >
              {submitting ? "검증 중..." : "로그인"}
            </button>

            <button
              type="button"
              onClick={backToPassword}
              disabled={submitting}
              className="admin-btn-ghost w-full text-xs"
            >
              ← 비밀번호 다시 입력
            </button>
          </form>
        )}

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
