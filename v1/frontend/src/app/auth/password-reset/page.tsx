"use client";

export const dynamic = "force-dynamic";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { requestPasswordReset, ApiClientError } from "@/lib/api";
import { useI18n } from "@/i18n";

type Status = "idle" | "loading" | "sent";

export default function PasswordResetRequestPage() {
  const { t } = useI18n();
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState<Status>("idle");
  const [error, setError] = useState<string | null>(null);
  const [countdown, setCountdown] = useState<number | null>(null);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setStatus("loading");

    try {
      await requestPasswordReset(email.trim().toLowerCase());
      setStatus("sent");
    } catch (err: unknown) {
      if (err instanceof ApiClientError && err.code === "RESET_TOO_SOON") {
        const seconds =
          (err.details as { retry_after_seconds?: number })
            ?.retry_after_seconds ?? 300;
        setCountdown(seconds);
        setError(
          t("auth.password_reset.request.too_soon", { seconds })
        );
      } else {
        setError(t("auth.password_reset.request.error"));
      }
      setStatus("idle");
    }
  };

  if (status === "sent") {
    return (
      <div className="min-h-screen flex items-center justify-center bg-surface px-4">
        <div className="w-full max-w-sm bg-white dark:bg-surface-elevated rounded-xl shadow-sm border border-border p-8 text-center space-y-4">
          <div className="text-4xl">&#9993;</div>
          <h1 className="text-xl font-semibold text-text-primary">
            {t("auth.password_reset.request.sent_title")}
          </h1>
          <p className="text-sm text-text-muted">
            {t("auth.password_reset.request.sent_body")}
          </p>
          <Link
            href="/"
            className="inline-block text-sm text-primary hover:underline"
          >
            {t("auth.password_reset.request.back_to_login")}
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-surface px-4">
      <div className="w-full max-w-sm bg-white dark:bg-surface-elevated rounded-xl shadow-sm border border-border p-8 space-y-6">
        <div className="space-y-1">
          <h1 className="text-xl font-semibold text-text-primary">
            {t("auth.password_reset.request.title")}
          </h1>
          <p className="text-sm text-text-muted">
            {t("auth.password_reset.request.subtitle")}
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1">
            <label
              htmlFor="email"
              className="block text-sm font-medium text-text-primary"
            >
              {t("auth.password_reset.request.email_label")}
            </label>
            <input
              id="email"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="name@example.com"
              className="w-full px-3 py-2 text-sm rounded-lg border border-border bg-surface-hover text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-1 focus:ring-primary"
            />
          </div>

          {error && (
            <p className="text-sm text-red-500">{error}</p>
          )}

          <button
            type="submit"
            disabled={status === "loading" || !email.trim()}
            className="w-full py-2 rounded-lg bg-primary text-white text-sm font-medium disabled:opacity-50 transition-opacity"
          >
            {status === "loading"
              ? t("common.loading")
              : t("auth.password_reset.request.submit")}
          </button>
        </form>

        <div className="text-center">
          <Link
            href="/"
            className="text-sm text-text-muted hover:text-text-primary hover:underline"
          >
            {t("auth.password_reset.request.back_to_login")}
          </Link>
        </div>
      </div>
    </div>
  );
}
