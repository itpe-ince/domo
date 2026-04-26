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
      gsi.renderButton(buttonRef.current, {
        type: "standard",
        theme: "filled_black",
        size: "large",
        text: "continue_with",
        shape: "pill",
        logo_alignment: "left",
        width: 320,
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
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 px-4"
      onClick={onClose}
    >
      <div
        className="card w-full max-w-md p-6 space-y-5"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="flex items-start justify-between">
          <div>
            <h2 className="text-xl font-bold">Domo {t("common.login")}</h2>
            <p className="text-text-secondary text-sm mt-1">
              Google 계정으로 안전하게 로그인합니다.
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-text-muted hover:text-text-primary text-xl leading-none"
            aria-label="닫기"
          >
            ×
          </button>
        </header>

        {/* Google-rendered button mount point */}
        <div className="flex justify-center min-h-[44px]" ref={buttonRef} />

        {busy && (
          <p className="text-text-muted text-xs text-center">{t("common.loading")}...</p>
        )}

        {error && (
          <div className="card border-danger p-3 text-danger text-sm">
            {error}
          </div>
        )}

        <p className="text-text-muted text-[11px] text-center pt-2 border-t border-border">
          로그인 시 <a href="/legal/terms" className="underline">이용약관</a> 및{" "}
          <a href="/legal/privacy" className="underline">개인정보처리방침</a>에 동의하게 됩니다.
        </p>
      </div>
    </div>
  );
}
