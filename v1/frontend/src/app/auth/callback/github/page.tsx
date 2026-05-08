"use client";

export const dynamic = "force-dynamic";

import { useEffect, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { loginWithGitHub, ApiClientError } from "@/lib/api";
import { identifyUser, captureEvent } from "@/lib/analytics/capture";
import { useI18n } from "@/i18n";

type CallbackState = "loading" | "success" | "error";

function GitHubCallbackContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { t } = useI18n();

  const [state, setState] = useState<CallbackState>("loading");
  const [errorMessage, setErrorMessage] = useState<string>("");

  useEffect(() => {
    const code = searchParams.get("code");
    const stateParam = searchParams.get("state");

    if (!code) {
      setState("error");
      setErrorMessage("GitHub에서 인증 코드를 받지 못했습니다.");
      return;
    }

    // CSRF state 검증
    const savedState = sessionStorage.getItem("github_oauth_state");
    if (savedState && stateParam && savedState !== stateParam) {
      setState("error");
      setErrorMessage("보안 검증에 실패했습니다. 다시 로그인해주세요.");
      return;
    }
    sessionStorage.removeItem("github_oauth_state");

    const redirectUri = `${window.location.origin}/auth/callback/github`;

    loginWithGitHub(code, redirectUri)
      .then((user) => {
        identifyUser(user.id, { role: user.role });
        captureEvent({ type: "login", method: "github" });
        setState("success");
        setTimeout(() => router.push("/"), 1500);
      })
      .catch((e) => {
        setState("error");
        if (e instanceof ApiClientError) {
          if (e.code === "GITHUB_EMAIL_CONFLICT") {
            setErrorMessage(
              t("auth.github.conflict") + " " + t("auth.github.conflictHint")
            );
          } else if (e.code === "GITHUB_EMAIL_REQUIRED") {
            setErrorMessage(t("auth.github.noEmail"));
          } else {
            setErrorMessage(e.message);
          }
        } else {
          setErrorMessage(t("common.error"));
        }
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="min-h-screen flex items-center justify-center bg-background px-4">
      <div className="w-full max-w-sm bg-surface border border-border rounded-2xl shadow-lg p-8 text-center space-y-4">
        <div className="inline-flex items-center justify-center w-12 h-12 rounded-2xl bg-primary/15 ring-1 ring-primary/30 mb-2">
          <span className="text-primary font-logo text-xl">D</span>
        </div>

        {state === "loading" && (
          <>
            <h1 className="text-lg font-bold text-text-primary">{t("auth.github.connecting")}</h1>
            <div className="flex justify-center">
              <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin" />
            </div>
          </>
        )}

        {state === "success" && (
          <>
            <h1 className="text-lg font-bold text-text-primary">{t("auth.github.mergeSuccess")}</h1>
            <p className="text-sm text-text-muted">{t("auth.magic_link.verify.success")}</p>
          </>
        )}

        {state === "error" && (
          <>
            <h1 className="text-lg font-bold text-text-primary">GitHub 로그인 실패</h1>
            <p className="text-sm text-danger">{errorMessage}</p>
            <button
              onClick={() => router.push("/")}
              className="w-full py-2 rounded-lg bg-primary text-white text-sm font-medium"
            >
              홈으로 이동
            </button>
          </>
        )}
      </div>
    </div>
  );
}

export default function GitHubCallbackPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center">
        <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin" />
      </div>
    }>
      <GitHubCallbackContent />
    </Suspense>
  );
}
