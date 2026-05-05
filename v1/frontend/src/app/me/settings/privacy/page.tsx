"use client";

/**
 * /me/settings/privacy — A-1 Analytics Foundation
 *
 * User-facing analytics opt-out toggle.
 * GDPR Article 7: consent is withdrawable at any time.
 *
 * Stores preference in localStorage (domo_cookie_consent_v1) and
 * immediately applies to PostHog via opt_in_capturing / opt_out_capturing.
 */

import Link from "next/link";
import { useEffect, useState } from "react";
import { useI18n } from "@/i18n";
import {
  getStoredConsent,
  type ConsentLevel,
} from "@/components/CookieConsent";

const CONSENT_KEY = "domo_cookie_consent_v1";

function saveConsent(level: ConsentLevel) {
  if (typeof window === "undefined") return;
  const record = {
    level,
    accepted_at: new Date().toISOString(),
    version: "v1",
  };
  localStorage.setItem(CONSENT_KEY, JSON.stringify(record));
}

function applyPostHogConsent(level: ConsentLevel) {
  if (typeof window === "undefined") return;
  if (!process.env.NEXT_PUBLIC_POSTHOG_KEY) return;
  import("posthog-js").then(({ default: posthog }) => {
    if (level === "all") {
      posthog.opt_in_capturing();
    } else {
      posthog.opt_out_capturing();
    }
  });
}

export default function PrivacySettingsPage() {
  const { t } = useI18n();
  const [analyticsEnabled, setAnalyticsEnabled] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    const stored = getStoredConsent();
    setAnalyticsEnabled(stored?.level === "all");
  }, []);

  function handleToggle(enabled: boolean) {
    setAnalyticsEnabled(enabled);
    const level: ConsentLevel = enabled ? "all" : "essential";
    saveConsent(level);
    applyPostHogConsent(level);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  }

  return (
    <main className="flex-1 min-w-0 max-w-2xl mx-auto px-6 py-8 space-y-6">
      <div>
        <Link
          href="/me/settings"
          className="text-text-secondary text-sm hover:text-primary"
        >
          {t("common.back")}
        </Link>
      </div>

      <div>
        <h1 className="text-2xl font-bold">{t("privacy.title")}</h1>
        <p className="text-sm text-text-secondary mt-1">{t("privacy.subtitle")}</p>
      </div>

      {/* Analytics section */}
      <section className="card p-6 space-y-4">
        <div>
          <h2 className="text-lg font-semibold">{t("privacy.analytics.title")}</h2>
          <p className="text-sm text-text-secondary mt-1">
            {t("privacy.analytics.description")}
          </p>
        </div>

        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium">
              {t("privacy.analytics.toggleLabel")}
            </p>
            <p className="text-xs text-text-secondary mt-0.5">
              {analyticsEnabled
                ? t("privacy.analytics.statusEnabled")
                : t("privacy.analytics.statusDisabled")}
            </p>
          </div>
          <button
            role="switch"
            aria-checked={analyticsEnabled}
            onClick={() => handleToggle(!analyticsEnabled)}
            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 ${
              analyticsEnabled ? "bg-primary" : "bg-border"
            }`}
          >
            <span
              className={`inline-block h-4 w-4 transform rounded-full bg-background transition-transform ${
                analyticsEnabled ? "translate-x-6" : "translate-x-1"
              }`}
            />
          </button>
        </div>

        {saved && (
          <p className="text-xs text-success" role="status">
            {t("privacy.savedConfirmation")}
          </p>
        )}
      </section>

      {/* Links */}
      <div className="text-sm text-text-secondary space-x-3">
        <Link href="/legal/privacy" className="text-primary underline">
          {t("cookie.privacyLink")}
        </Link>
        <span>&middot;</span>
        <Link href="/legal/cookies" className="text-primary underline">
          {t("cookie.policyLink")}
        </Link>
      </div>
    </main>
  );
}
