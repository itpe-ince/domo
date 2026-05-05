"use client";

/**
 * /newsletter/unsubscribe?token=... — C-5 newsletter-digest
 *
 * 1-click unsubscribe landing page (email link target).
 * No authentication required — uses the token embedded in email footer.
 */

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useI18n } from "@/i18n";
import { newsletterUnsubscribe } from "@/lib/api";

type UnsubscribeState = "loading" | "success" | "already" | "error" | "missing";

export default function NewsletterUnsubscribePage() {
  const { t } = useI18n();
  const searchParams = useSearchParams();
  const token = searchParams.get("token");

  const [state, setState] = useState<UnsubscribeState>(
    token ? "loading" : "missing"
  );

  useEffect(() => {
    if (!token) {
      setState("missing");
      return;
    }

    newsletterUnsubscribe(token)
      .then((res) => {
        setState(res.unsubscribed ? "success" : "already");
      })
      .catch((e) => {
        // 404 = invalid/expired token
        if (e?.code === "INVALID_TOKEN" || e?.message?.includes("404")) {
          setState("error");
        } else {
          setState("error");
        }
      });
  }, [token]);

  const renderContent = () => {
    switch (state) {
      case "loading":
        return (
          <p className="text-gray-600">{t("newsletter.unsubscribe.loading")}</p>
        );
      case "success":
        return (
          <div>
            <div className="text-4xl mb-4">✓</div>
            <h2 className="text-xl font-semibold text-gray-800 mb-2">
              {t("newsletter.unsubscribe.success.title")}
            </h2>
            <p className="text-gray-600">
              {t("newsletter.unsubscribe.success.message")}
            </p>
          </div>
        );
      case "already":
        return (
          <div>
            <div className="text-4xl mb-4">ℹ</div>
            <h2 className="text-xl font-semibold text-gray-800 mb-2">
              {t("newsletter.unsubscribe.already.title")}
            </h2>
            <p className="text-gray-600">
              {t("newsletter.unsubscribe.already.message")}
            </p>
          </div>
        );
      case "error":
        return (
          <div>
            <div className="text-4xl mb-4">✕</div>
            <h2 className="text-xl font-semibold text-gray-800 mb-2">
              {t("newsletter.unsubscribe.error.title")}
            </h2>
            <p className="text-gray-600">
              {t("newsletter.unsubscribe.error.message")}
            </p>
          </div>
        );
      case "missing":
        return (
          <div>
            <h2 className="text-xl font-semibold text-gray-800 mb-2">
              {t("newsletter.unsubscribe.missing.title")}
            </h2>
            <p className="text-gray-600">
              {t("newsletter.unsubscribe.missing.message")}
            </p>
          </div>
        );
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="max-w-md w-full bg-white rounded-xl shadow-sm border border-gray-200 p-8 text-center">
        <p className="text-sm font-semibold text-blue-600 mb-4">Domo</p>
        {renderContent()}
        <a
          href="/"
          className="mt-8 inline-block text-sm text-gray-500 hover:text-gray-700 underline"
        >
          {t("newsletter.unsubscribe.backToHome")}
        </a>
      </div>
    </div>
  );
}
