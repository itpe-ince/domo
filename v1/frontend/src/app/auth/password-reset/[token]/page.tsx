"use client";

export const dynamic = "force-dynamic";

import { FormEvent, use, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { resetPassword, ApiClientError } from "@/lib/api";
import { useI18n } from "@/i18n";

type Status = "idle" | "loading" | "success" | "error";

interface PageProps {
  params: Promise<{ token: string }>;
}

export default function PasswordResetPage({ params }: PageProps) {
  const { token } = use(params);
  const { t } = useI18n();
  const router = useRouter();

  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [status, setStatus] = useState<Status>("idle");
  const [errorCode, setErrorCode] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // 성공 후 3초 카운트다운 + 자동 리다이렉트
  useEffect(() => {
    if (status !== "success") return;
    const timer = setTimeout(() => {
      router.push("/");
    }, 3000);
    return () => clearTimeout(timer);
  }, [status, router]);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setErrorCode(null);
    setErrorMessage(null);

    if (newPassword !== confirmPassword) {
      setErrorCode("PASSWORD_MISMATCH");
      setErrorMessage(t("auth.password_reset.token.mismatch"));
      return;
    }

    setStatus("loading");

    try {
      await resetPassword(token, newPassword);
      setStatus("success");
    } catch (err: unknown) {
      setStatus("error");
      if (err instanceof ApiClientError) {
        setErrorCode(err.code ?? null);
        switch (err.code) {
          case "TOKEN_EXPIRED":
            setErrorMessage(t("auth.password_reset.token.expired"));
            break;
          case "TOKEN_ALREADY_USED":
            setErrorMessage(t("auth.password_reset.token.already_used"));
            break;
          case "INVALID_RESET_TOKEN":
            setErrorMessage(t("auth.password_reset.token.invalid"));
            break;
          case "PASSWORD_TOO_SHORT":
          case "PASSWORD_WEAK":
            setErrorMessage(err.message || t("auth.password_reset.token.invalid"));
            setStatus("idle");
            break;
          default:
            setErrorMessage(t("auth.password_reset.token.invalid"));
        }
      } else {
        setErrorMessage(t("auth.password_reset.token.invalid"));
      }
    }
  };

  // 성공 화면
  if (status === "success") {
    return (
      <div className="min-h-screen flex items-center justify-center bg-surface px-4">
        <div className="w-full max-w-sm bg-white dark:bg-surface-elevated rounded-xl shadow-sm border border-border p-8 text-center space-y-4">
          <div className="text-4xl">&#10003;</div>
          <h1 className="text-xl font-semibold text-text-primary">
            {t("auth.password_reset.success.title")}
          </h1>
          <p className="text-sm text-text-muted">
            {t("auth.password_reset.success.body")}
          </p>
        </div>
      </div>
    );
  }

  // 토큰 만료/사용됨 에러 화면 (폼 재시도 불가)
  const isTokenError =
    status === "error" &&
    (errorCode === "TOKEN_EXPIRED" ||
      errorCode === "TOKEN_ALREADY_USED" ||
      errorCode === "INVALID_RESET_TOKEN");

  if (isTokenError) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-surface px-4">
        <div className="w-full max-w-sm bg-white dark:bg-surface-elevated rounded-xl shadow-sm border border-border p-8 text-center space-y-4">
          <div className="text-4xl">&#8416;</div>
          <h1 className="text-xl font-semibold text-text-primary">
            {errorCode === "TOKEN_EXPIRED"
              ? t("auth.password_reset.token.expired")
              : errorCode === "TOKEN_ALREADY_USED"
              ? t("auth.password_reset.token.already_used")
              : t("auth.password_reset.token.invalid")}
          </h1>
          <Link
            href="/auth/password-reset"
            className="inline-block mt-2 text-sm text-primary hover:underline"
          >
            {t("auth.password_reset.token.request_again")}
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-surface px-4">
      <div className="w-full max-w-sm bg-white dark:bg-surface-elevated rounded-xl shadow-sm border border-border p-8 space-y-6">
        <h1 className="text-xl font-semibold text-text-primary">
          {t("auth.password_reset.token.title")}
        </h1>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1">
            <label
              htmlFor="new-password"
              className="block text-sm font-medium text-text-primary"
            >
              {t("auth.password_reset.token.new_password_label")}
            </label>
            <input
              id="new-password"
              type="password"
              required
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              className="w-full px-3 py-2 text-sm rounded-lg border border-border bg-surface-hover text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-1 focus:ring-primary"
            />
          </div>

          <div className="space-y-1">
            <label
              htmlFor="confirm-password"
              className="block text-sm font-medium text-text-primary"
            >
              {t("auth.password_reset.token.confirm_label")}
            </label>
            <input
              id="confirm-password"
              type="password"
              required
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              className="w-full px-3 py-2 text-sm rounded-lg border border-border bg-surface-hover text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-1 focus:ring-primary"
            />
          </div>

          {errorMessage && (
            <p className="text-sm text-red-500">{errorMessage}</p>
          )}

          <button
            type="submit"
            disabled={status === "loading" || !newPassword || !confirmPassword}
            className="w-full py-2 rounded-lg bg-primary text-white text-sm font-medium disabled:opacity-50 transition-opacity"
          >
            {status === "loading"
              ? t("common.loading")
              : t("auth.password_reset.token.submit")}
          </button>
        </form>

        <div className="text-center">
          <Link
            href="/auth/password-reset"
            className="text-sm text-text-muted hover:text-text-primary hover:underline"
          >
            {t("auth.password_reset.token.request_again")}
          </Link>
        </div>
      </div>
    </div>
  );
}
