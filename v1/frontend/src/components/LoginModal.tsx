"use client";

import { useRouter } from "next/navigation";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { useI18n } from "@/i18n";
import {
  ApiClientError,
  loginWithGoogleIdToken,
  loginWithEmailPassword,
  registerWithPassword,
  requestMagicLink,
} from "@/lib/api";
import { captureEvent, identifyUser } from "@/lib/analytics/capture";

const GOOGLE_CLIENT_ID = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID || "";

// GIS global injected by https://accounts.google.com/gsi/client (loaded in layout.tsx)
declare global {
  interface Window {
    google?: {
      accounts: {
        id: {
          initialize: (config: {
            client_id: string;
            callback: (resp: { credential: string }) => void;
            ux_mode?: "popup" | "redirect";
            auto_select?: boolean;
            cancel_on_tap_outside?: boolean;
          }) => void;
          renderButton: (
            parent: HTMLElement,
            opts: {
              type?: "standard" | "icon";
              theme?: "outline" | "filled_blue" | "filled_black";
              size?: "small" | "medium" | "large";
              text?: "signin_with" | "signup_with" | "continue_with" | "signin";
              shape?: "rectangular" | "pill" | "circle" | "square";
              logo_alignment?: "left" | "center";
              width?: number;
              locale?: string;
            }
          ) => void;
          prompt: () => void;
          disableAutoSelect: () => void;
        };
      };
    };
  }
}

// 비밀번호 강도 계산 (0~4)
function calcPasswordStrength(pw: string): number {
  if (!pw) return 0;
  let score = 0;
  if (pw.length >= 8) score++;
  if (/[A-Z]/.test(pw)) score++;
  if (/[a-z]/.test(pw)) score++;
  if (/[0-9]/.test(pw)) score++;
  if (/[^A-Za-z0-9]/.test(pw)) score++;
  return Math.min(score, 4);
}

const STRENGTH_LABELS = ["", "약함", "보통", "좋음", "강함"];
const STRENGTH_COLORS = ["", "bg-red-500", "bg-yellow-500", "bg-blue-400", "bg-green-500"];

export function LoginModal({
  open,
  onClose,
  redirectTo,
}: {
  open: boolean;
  onClose: () => void;
  redirectTo?: string;
}) {
  const router = useRouter();
  const { t } = useI18n();
  const [mode, setMode] = useState<"login" | "signup" | "magic">("login");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showEmailVerifyBanner, setShowEmailVerifyBanner] = useState(false);

  // 이메일 폼 상태
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [passwordStrength, setPasswordStrength] = useState(0);

  // 매직링크 상태
  const [magicEmail, setMagicEmail] = useState("");
  const [magicLinkSent, setMagicLinkSent] = useState(false);

  const buttonRef = useRef<HTMLDivElement>(null);

  // Reset on close
  useEffect(() => {
    if (!open) {
      setError(null);
      setShowEmailVerifyBanner(false);
      setEmail("");
      setPassword("");
      setDisplayName("");
      setPasswordStrength(0);
      setMagicEmail("");
      setMagicLinkSent(false);
      setMode("login");
    }
  }, [open]);

  // Mount Google Sign-In button when modal opens
  useEffect(() => {
    if (!open) return;
    if (!GOOGLE_CLIENT_ID) {
      setError("NEXT_PUBLIC_GOOGLE_CLIENT_ID 환경변수가 설정되지 않았습니다.");
      return;
    }

    let cancelled = false;
    const tryInit = (attempt = 0) => {
      if (cancelled) return;
      const gsi = window.google?.accounts?.id;
      // GIS script loads async — retry up to ~5 sec
      if (!gsi || !buttonRef.current) {
        if (attempt > 50) {
          setError(
            "Google 로그인 스크립트 로드 실패. 새로고침 후 다시 시도하세요."
          );
          return;
        }
        setTimeout(() => tryInit(attempt + 1), 100);
        return;
      }

      gsi.initialize({
        client_id: GOOGLE_CLIENT_ID,
        callback: handleCredential,
        ux_mode: "popup",
        cancel_on_tap_outside: false,
      });

      // Clear any previous button (re-mounts on every open)
      buttonRef.current.innerHTML = "";
      const containerWidth = Math.min(
        Math.floor(buttonRef.current.clientWidth || 360),
        400
      );
      // filled_black은 짙은 surface(#2A2018)와 톤이 겹쳐 라벨 대비가 나쁨.
      // outline은 밝은 바탕 + 어두운 글자로 모달 톤과 맞음.
      gsi.renderButton(buttonRef.current, {
        type: "standard",
        theme: "outline",
        size: "large",
        text: "continue_with",
        shape: "rectangular",
        logo_alignment: "left",
        width: containerWidth,
        locale: "ko",
      });
    };

    tryInit();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  async function handleCredential(resp: { credential: string }) {
    setBusy(true);
    setError(null);
    try {
      const user = await loginWithGoogleIdToken(resp.credential);
      identifyUser(user.id, { role: user.role });
      captureEvent({ type: "login", method: "google" });
      onClose();
      if (redirectTo) router.push(redirectTo);
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

  async function handleMagicLinkRequest(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await requestMagicLink(magicEmail);
      setMagicLinkSent(true);
    } catch (e) {
      setError(
        e instanceof ApiClientError
          ? e.message
          : e instanceof Error
            ? e.message
            : t("common.error")
      );
    } finally {
      setBusy(false);
    }
  }

  async function handleEmailLogin(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const { user, email_verified } = await loginWithEmailPassword({ email, password });
      identifyUser(user.id, { role: user.role });
      captureEvent({ type: "login", method: "email_password" });
      if (!email_verified) {
        setShowEmailVerifyBanner(true);
        // 미인증 상태에서도 로그인 허용 — 배너 표시 후 닫기
        setTimeout(() => {
          onClose();
          if (redirectTo) router.push(redirectTo);
        }, 2500);
      } else {
        onClose();
        if (redirectTo) router.push(redirectTo);
      }
    } catch (e) {
      setError(
        e instanceof ApiClientError
          ? e.message
          : e instanceof Error
            ? e.message
            : t("common.error")
      );
    } finally {
      setBusy(false);
    }
  }

  async function handleEmailSignup(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const user = await registerWithPassword({ email, password, display_name: displayName });
      identifyUser(user.id, { role: user.role });
      captureEvent({ type: "signup", method: "email_password" });
      // 가입 후 항상 인증 메일 안내 배너 표시
      setShowEmailVerifyBanner(true);
      setTimeout(() => {
        onClose();
        if (redirectTo) router.push(redirectTo);
      }, 2500);
    } catch (e) {
      setError(
        e instanceof ApiClientError
          ? e.message
          : e instanceof Error
            ? e.message
            : t("common.error")
      );
    } finally {
      setBusy(false);
    }
  }

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm px-4"
      onClick={onClose}
    >
      <div
        className="w-full max-w-sm bg-surface border border-border rounded-2xl shadow-2xl overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <header className="relative px-6 pt-6 pb-2 text-center">
          <button
            onClick={onClose}
            className="absolute top-4 right-4 w-8 h-8 rounded-full flex items-center justify-center text-text-muted hover:text-text-primary hover:bg-surface-hover transition-colors"
            aria-label="닫기"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-2xl bg-primary/15 ring-1 ring-primary/30 mb-3">
            <span className="text-primary font-logo text-xl">D</span>
          </div>
          <h2 className="text-lg font-bold text-text-primary">
            Domo {t("common.login")}
          </h2>
        </header>

        {/* 이메일 인증 안내 배너 */}
        {showEmailVerifyBanner && (
          <div className="mx-5 mt-3 rounded-lg border border-primary/30 bg-primary/10 px-3 py-2 text-xs text-primary text-center">
            {t("auth.verify.banner")}
          </div>
        )}

        {/* Google 로그인 */}
        <div className="px-5 pt-4">
          <div
            className="flex justify-center min-h-[44px] w-full rounded-lg overflow-hidden ring-1 ring-border/80 [&>div]:!w-full"
            ref={buttonRef}
          />
        </div>

        {/* 구분선 */}
        <div className="flex items-center gap-3 px-5 pt-2">
          <div className="flex-1 h-px bg-border" />
          <span className="text-xs text-text-muted">또는</span>
          <div className="flex-1 h-px bg-border" />
        </div>

        {/* 탭: 로그인 / 회원가입 / 이메일로 로그인 */}
        <div className="flex border-b border-border mx-5">
          <button
            className={`flex-1 py-2 text-xs font-medium transition-colors ${
              mode === "login"
                ? "text-primary border-b-2 border-primary"
                : "text-text-muted hover:text-text-secondary"
            }`}
            onClick={() => { setMode("login"); setError(null); }}
          >
            {t("auth.login.email.tab")}
          </button>
          <button
            className={`flex-1 py-2 text-xs font-medium transition-colors ${
              mode === "signup"
                ? "text-primary border-b-2 border-primary"
                : "text-text-muted hover:text-text-secondary"
            }`}
            onClick={() => { setMode("signup"); setError(null); }}
          >
            {t("auth.signup.tab")}
          </button>
          <button
            className={`flex-1 py-2 text-xs font-medium transition-colors ${
              mode === "magic"
                ? "text-primary border-b-2 border-primary"
                : "text-text-muted hover:text-text-secondary"
            }`}
            onClick={() => { setMode("magic"); setError(null); setMagicLinkSent(false); }}
          >
            {t("auth.magic_link.request.tab")}
          </button>
        </div>

        <div className="px-5 py-4 space-y-3">
          {/* 로그인 폼 */}
          {mode === "login" && (
            <form onSubmit={handleEmailLogin} className="space-y-3">
              <input
                type="email"
                required
                placeholder={t("auth.login.email.emailPlaceholder")}
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-3 py-2 text-sm rounded-lg border border-border bg-surface-hover text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-1 focus:ring-primary"
              />
              <input
                type="password"
                required
                placeholder={t("auth.login.email.passwordPlaceholder")}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-3 py-2 text-sm rounded-lg border border-border bg-surface-hover text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-1 focus:ring-primary"
              />
              {/* 비밀번호 찾기 — C-1 활성화 */}
              <div className="text-right">
                <Link
                  href="/auth/password-reset"
                  className="text-xs text-primary hover:underline"
                >
                  {t("auth.login.email.forgotPassword")}
                </Link>
              </div>
              <button
                type="submit"
                disabled={busy}
                className="w-full py-2 rounded-lg bg-primary text-white text-sm font-medium disabled:opacity-50 transition-opacity"
              >
                {busy ? t("common.loading") : t("auth.login.email.submit")}
              </button>
            </form>
          )}

          {/* 회원가입 폼 */}
          {mode === "signup" && (
            <form onSubmit={handleEmailSignup} className="space-y-3">
              <input
                type="text"
                required
                minLength={3}
                maxLength={50}
                placeholder={t("auth.signup.displayNamePlaceholder")}
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                className="w-full px-3 py-2 text-sm rounded-lg border border-border bg-surface-hover text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-1 focus:ring-primary"
              />
              <input
                type="email"
                required
                placeholder={t("auth.signup.emailPlaceholder")}
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-3 py-2 text-sm rounded-lg border border-border bg-surface-hover text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-1 focus:ring-primary"
              />
              <div>
                <input
                  type="password"
                  required
                  minLength={8}
                  placeholder={t("auth.signup.passwordPlaceholder")}
                  value={password}
                  onChange={(e) => {
                    setPassword(e.target.value);
                    setPasswordStrength(calcPasswordStrength(e.target.value));
                  }}
                  className="w-full px-3 py-2 text-sm rounded-lg border border-border bg-surface-hover text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-1 focus:ring-primary"
                />
                {/* 비밀번호 강도 표시 */}
                {password.length > 0 && (
                  <div className="mt-1.5 flex items-center gap-2">
                    <div className="flex gap-1 flex-1">
                      {[1, 2, 3, 4].map((i) => (
                        <div
                          key={i}
                          className={`h-1 flex-1 rounded-full transition-colors ${
                            i <= passwordStrength
                              ? STRENGTH_COLORS[passwordStrength]
                              : "bg-surface-hover"
                          }`}
                        />
                      ))}
                    </div>
                    <span className="text-xs text-text-muted">
                      {STRENGTH_LABELS[passwordStrength]}
                    </span>
                  </div>
                )}
                <p className="text-[10px] text-text-muted mt-1">
                  {t("auth.signup.passwordHint")}
                </p>
              </div>
              <button
                type="submit"
                disabled={busy || passwordStrength < 3}
                className="w-full py-2 rounded-lg bg-primary text-white text-sm font-medium disabled:opacity-50 transition-opacity"
              >
                {busy ? t("common.loading") : t("auth.signup.submit")}
              </button>
            </form>
          )}

          {/* 매직링크 폼 */}
          {mode === "magic" && (
            <div className="space-y-3">
              {magicLinkSent ? (
                <div className="text-center space-y-2 py-2">
                  <p className="text-sm text-text-primary font-medium">
                    {t("auth.magic_link.request.sent")}
                  </p>
                  <button
                    type="button"
                    onClick={() => { setMagicLinkSent(false); setError(null); }}
                    className="text-xs text-text-muted hover:text-primary underline"
                  >
                    {t("auth.magic_link.request.submit")} ({t("auth.magic_link.request.emailPlaceholder")})
                  </button>
                </div>
              ) : (
                <form onSubmit={handleMagicLinkRequest} className="space-y-3">
                  <p className="text-xs text-text-muted">
                    {t("auth.magic_link.request.description")}
                  </p>
                  <input
                    type="email"
                    required
                    placeholder={t("auth.magic_link.request.emailPlaceholder")}
                    value={magicEmail}
                    onChange={(e) => setMagicEmail(e.target.value)}
                    className="w-full px-3 py-2 text-sm rounded-lg border border-border bg-surface-hover text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-1 focus:ring-primary"
                  />
                  <button
                    type="submit"
                    disabled={busy}
                    className="w-full py-2 rounded-lg bg-primary text-white text-sm font-medium disabled:opacity-50 transition-opacity"
                  >
                    {busy ? t("common.loading") : t("auth.magic_link.request.submit")}
                  </button>
                </form>
              )}
            </div>
          )}

          {busy && !showEmailVerifyBanner && (
            <p className="text-text-muted text-xs text-center mt-3">
              {t("common.loading")}
            </p>
          )}

          {error && (
            <div className="mt-3 rounded-lg border border-danger/30 bg-danger/10 px-3 py-2 text-xs text-danger">
              {error}
            </div>
          )}
        </div>

        {/* Footer */}
        <footer className="px-6 py-3 border-t border-border bg-surface-hover/30">
          <p className="text-text-muted text-[11px] text-center leading-relaxed">
            로그인 시{" "}
            <a href="/legal/terms" className="text-text-secondary underline hover:text-primary">
              이용약관
            </a>{" "}
            및{" "}
            <a href="/legal/privacy" className="text-text-secondary underline hover:text-primary">
              개인정보처리방침
            </a>
            에 동의하게 됩니다.
          </p>
        </footer>
      </div>
    </div>
  );
}
