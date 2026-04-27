"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { useI18n } from "@/i18n";
import { ApiClientError, loginWithGoogleIdToken } from "@/lib/api";

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
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const buttonRef = useRef<HTMLDivElement>(null);

  // Reset on close
  useEffect(() => {
    if (!open) setError(null);
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
      // Width = buttonRef container width (모달 max-w-md - p-6 = ~360px)
      // GIS personalized 모드에서는 일부 옵션 무시되지만 theme/width는 반영됨
      const containerWidth = Math.min(
        Math.floor(buttonRef.current.clientWidth || 360),
        400 // GIS max width 제한
      );
      gsi.renderButton(buttonRef.current, {
        type: "standard",
        theme: "filled_black",   // dark 모달과 일치 (logged-in 모드는 자동 흰 배경 사용)
        size: "large",
        text: "continue_with",
        shape: "rectangular",    // personalized 모드에서도 일관 (pill은 무시됨)
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
      await loginWithGoogleIdToken(resp.credential);
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
        {/* Header — centered brand + close */}
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
          <p className="text-text-muted text-xs mt-1">
            Google 계정으로 안전하게 로그인합니다.
          </p>
        </header>

        {/* Google button area */}
        <div className="px-6 py-5">
          <div
            className="flex justify-center min-h-[44px] [&>div]:!w-full"
            ref={buttonRef}
          />

          {busy && (
            <p className="text-text-muted text-xs text-center mt-3">
              {t("common.loading")}...
            </p>
          )}

          {error && (
            <div className="mt-3 rounded-lg border border-danger/30 bg-danger/10 px-3 py-2 text-xs text-danger">
              {error}
            </div>
          )}
        </div>

        {/* Footer — 약관 동의 */}
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
