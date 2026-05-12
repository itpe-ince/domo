"use client";

/**
 * CookieConsent.tsx — GDPR consent banner.
 *
 * A-1: Integrated PostHog opt_in / opt_out.
 * - Accept all → posthog.opt_in_capturing()
 * - Essential only → posthog.opt_out_capturing() (PostHog init default is opt_out)
 *
 * Uses i18n keys from `cookie.*` namespace (added in A-1 i18n sprint).
 */

import Link from "next/link";
import { useEffect, useState } from "react";
import { useI18n } from "@/i18n";

const CONSENT_KEY = "domo_cookie_consent_v1";

export type ConsentLevel = "essential" | "all";

export type ConsentRecord = {
  level: ConsentLevel;
  accepted_at: string;
  version: string;
};

export function getStoredConsent(): ConsentRecord | null {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem(CONSENT_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as ConsentRecord;
  } catch {
    return null;
  }
}

function applyPostHogConsent(level: ConsentLevel) {
  if (typeof window === "undefined") return;
  if (!process.env.NEXT_PUBLIC_POSTHOG_KEY) return;
  // posthog may not be on window — import dynamically to keep tree-shaking
  import("posthog-js").then(({ default: posthog }) => {
    if (level === "all") {
      posthog.opt_in_capturing();
    } else {
      posthog.opt_out_capturing();
    }
  });
}

export function CookieConsent() {
  const { t } = useI18n();
  const [shown, setShown] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined") return;
    if (!localStorage.getItem(CONSENT_KEY)) {
      setShown(true);
    }
  }, []);

  function accept(level: ConsentLevel) {
    const record: ConsentRecord = {
      level,
      accepted_at: new Date().toISOString(),
      version: "v1",
    };
    localStorage.setItem(CONSENT_KEY, JSON.stringify(record));
    applyPostHogConsent(level);
    setShown(false);
  }

  if (!shown) return null;

  return (
    <div className="fixed bottom-0 inset-x-0 z-40 bg-surface border-t border-border p-4 shadow-lg">
      <div className="max-w-4xl mx-auto flex flex-col md:flex-row md:items-center gap-3">
        <div className="flex-1 text-sm text-text-secondary">
          <p className="font-medium text-text-primary mb-1">
            {t("cookie.bannerTitle")}
          </p>
          <p>
            {t("cookie.bannerBody")}{" "}
            <Link href="/legal/cookies" className="text-primary underline">
              {t("cookie.policyLink")}
            </Link>{" "}
            &middot;{" "}
            <Link href="/legal/privacy" className="text-primary underline">
              {t("cookie.privacyLink")}
            </Link>
          </p>
        </div>
        <div className="flex gap-2 flex-shrink-0">
          <button
            onClick={() => accept("essential")}
            className="btn-secondary text-xs"
          >
            {t("cookie.essentialOnly")}
          </button>
          <button
            onClick={() => accept("all")}
            className="btn-primary text-xs"
          >
            {t("cookie.acceptAll")}
          </button>
        </div>
      </div>
    </div>
  );
}
