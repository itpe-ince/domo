"use client";

import { useEffect, useState } from "react";
import { useRouter, useParams } from "next/navigation";
import { verifyMagicLink, ApiClientError } from "@/lib/api";
import { identifyUser, captureEvent } from "@/lib/analytics/capture";
import { useI18n } from "@/i18n";

type Step = "verifying" | "setup" | "done" | "error";

export default function MagicLinkPage() {
  const params = useParams() as { token: string };
  const router = useRouter();
  const { t } = useI18n();

  const [step, setStep] = useState<Step>("verifying");
  const [email, setEmail] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [errorMessage, setErrorMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [ipWarning, setIpWarning] = useState(false);

  useEffect(() => {
    handleVerify(params.token);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params.token]);

  async function handleVerify(token: string, name?: string) {
    setBusy(true);
    try {
      const res = await verifyMagicLink(token, name);

      if ("setup_required" in res && res.setup_required) {
        setEmail(res.email);
        setStep("setup");
        return;
      }

      if ("tokens" in res) {
        if (res.ip_warning) {
          setIpWarning(true);
        }
        identifyUser(res.user.id, { role: res.user.role });
        captureEvent({ type: "login", method: "magic_link" });
        setStep("done");
        setTimeout(() => router.push("/"), 2000);
      }
    } catch (e) {
      setStep("error");
      if (e instanceof ApiClientError) {
        switch (e.code) {
          case "MAGIC_LINK_EXPIRED":
            setErrorMessage(t("auth.magic_link.verify.expired"));
            break;
          case "MAGIC_LINK_USED":
            setErrorMessage(t("auth.magic_link.verify.used"));
            break;
          default:
            setErrorMessage(e.message || t("common.error"));
        }
      } else {
        setErrorMessage(t("common.error"));
      }
    } finally {
      setBusy(false);
    }
  }

  async function handleSetupSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!displayName.trim() || displayName.trim().length < 3) return;
    await handleVerify(params.token, displayName.trim());
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-background px-4">
      <div className="w-full max-w-sm bg-surface border border-border rounded-2xl shadow-lg p-8 text-center space-y-4">
        <div className="inline-flex items-center justify-center w-12 h-12 rounded-2xl bg-primary/15 ring-1 ring-primary/30 mb-2">
          <span className="text-primary font-logo text-xl">D</span>
        </div>

        {/* 검증 중 */}
        {step === "verifying" && (
          <>
            <h1 className="text-lg font-bold text-text-primary">
              {t("auth.magic_link.verify.verifying")}
            </h1>
            <div className="flex justify-center">
              <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin" />
            </div>
          </>
        )}

        {/* 신규 사용자 display_name 입력 */}
        {step === "setup" && (
          <form onSubmit={handleSetupSubmit} className="space-y-4 text-left">
            <h1 className="text-lg font-bold text-text-primary text-center">
              {t("auth.magic_link.verify.setupTitle")}
            </h1>
            {email && (
              <p className="text-xs text-text-muted text-center">{email}</p>
            )}
            <input
              type="text"
              required
              minLength={3}
              maxLength={50}
              placeholder={t("auth.magic_link.verify.setupPlaceholder")}
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              className="w-full px-3 py-2 text-sm rounded-lg border border-border bg-surface-hover text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-1 focus:ring-primary"
              autoFocus
            />
            <button
              type="submit"
              disabled={busy || displayName.trim().length < 3}
              className="w-full py-2 rounded-lg bg-primary text-white text-sm font-medium disabled:opacity-50 transition-opacity"
            >
              {busy ? t("common.loading") : t("auth.magic_link.verify.setupSubmit")}
            </button>
          </form>
        )}

        {/* 완료 */}
        {step === "done" && (
          <>
            {ipWarning && (
              <div className="rounded-lg border border-warning/30 bg-warning/10 px-3 py-2 text-xs text-warning text-left">
                {t("auth.magic_link.verify.ipWarning")}
              </div>
            )}
            <h1 className="text-lg font-bold text-text-primary">
              {t("auth.magic_link.verify.success")}
            </h1>
            <div className="flex justify-center">
              <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin" />
            </div>
          </>
        )}

        {/* 오류 */}
        {step === "error" && (
          <>
            <h1 className="text-lg font-bold text-text-primary">
              {t("auth.verify.error")}
            </h1>
            <p className="text-sm text-danger">{errorMessage}</p>
            <a
              href="/"
              className="block w-full py-2 rounded-lg border border-border text-text-secondary text-sm text-center hover:bg-surface-hover"
            >
              {t("auth.magic_link.verify.requestNew")}
            </a>
          </>
        )}
      </div>
    </div>
  );
}
