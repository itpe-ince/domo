"use client";

export const dynamic = "force-dynamic";

import { useEffect, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { verifyEmail, resendVerificationEmail, ApiClientError } from "@/lib/api";
import { useI18n } from "@/i18n";

type VerifyState = "loading" | "success" | "already_verified" | "expired" | "error";

function EmailVerifyContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { t } = useI18n();

  const [state, setState] = useState<VerifyState>("loading");
  const [resending, setResending] = useState(false);
  const [resendDone, setResendDone] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string>("");

  useEffect(() => {
    const token = searchParams.get("token");
    if (!token) {
      setState("error");
      setErrorMessage(t("auth.verify.noToken"));
      return;
    }

    verifyEmail(token)
      .then((result) => {
        if (result.already_verified) {
          setState("already_verified");
        } else {
          setState("success");
          // 3초 후 홈으로 이동
          setTimeout(() => router.push("/"), 3000);
        }
      })
      .catch((e) => {
        if (e instanceof ApiClientError && e.code === "VERIFICATION_TOKEN_EXPIRED") {
          setState("expired");
        } else {
          setState("error");
          setErrorMessage(
            e instanceof ApiClientError ? e.message : t("common.error")
          );
        }
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleResend() {
    setResending(true);
    try {
      await resendVerificationEmail();
      setResendDone(true);
    } catch (e) {
      setErrorMessage(
        e instanceof ApiClientError ? e.message : t("common.error")
      );
    } finally {
      setResending(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-background px-4">
      <div className="w-full max-w-sm bg-surface border border-border rounded-2xl shadow-xl p-8 text-center">
        {/* 로고 */}
        <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-primary/15 ring-1 ring-primary/30 mb-4">
          <span className="text-primary font-logo text-2xl">D</span>
        </div>

        {state === "loading" && (
          <>
            <h1 className="text-lg font-bold text-text-primary mb-2">
              {t("auth.verify.verifying")}
            </h1>
            <p className="text-sm text-text-muted">{t("common.loading")}</p>
          </>
        )}

        {state === "success" && (
          <>
            <div className="text-4xl mb-3">&#10003;</div>
            <h1 className="text-lg font-bold text-text-primary mb-2">
              {t("auth.verify.success")}
            </h1>
            <p className="text-sm text-text-muted">
              {t("auth.verify.redirecting")}
            </p>
          </>
        )}

        {state === "already_verified" && (
          <>
            <h1 className="text-lg font-bold text-text-primary mb-2">
              {t("auth.verify.alreadyVerified")}
            </h1>
            <button
              onClick={() => router.push("/")}
              className="mt-4 px-6 py-2 rounded-lg bg-primary text-white text-sm font-medium"
            >
              {t("auth.verify.goHome")}
            </button>
          </>
        )}

        {state === "expired" && (
          <>
            <h1 className="text-lg font-bold text-text-primary mb-2">
              {t("auth.verify.expired")}
            </h1>
            <p className="text-sm text-text-muted mb-4">
              {t("auth.verify.expiredDesc")}
            </p>
            {resendDone ? (
              <p className="text-sm text-primary">{t("auth.verify.resendSuccess")}</p>
            ) : (
              <button
                onClick={handleResend}
                disabled={resending}
                className="px-6 py-2 rounded-lg bg-primary text-white text-sm font-medium disabled:opacity-50"
              >
                {resending ? t("common.loading") : t("auth.verify.resend")}
              </button>
            )}
            {errorMessage && (
              <p className="mt-3 text-xs text-danger">{errorMessage}</p>
            )}
          </>
        )}

        {state === "error" && (
          <>
            <h1 className="text-lg font-bold text-text-primary mb-2">
              {t("auth.verify.error")}
            </h1>
            <p className="text-sm text-text-muted mb-4">{errorMessage}</p>
            <button
              onClick={() => router.push("/")}
              className="px-6 py-2 rounded-lg bg-primary text-white text-sm font-medium"
            >
              {t("auth.verify.goHome")}
            </button>
          </>
        )}
      </div>
    </div>
  );
}

export default function EmailVerifyPage() {
  return (
    <Suspense fallback={<div className="flex min-h-screen items-center justify-center"><div className="text-text-muted text-sm">Loading...</div></div>}>
      <EmailVerifyContent />
    </Suspense>
  );
}
