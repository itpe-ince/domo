"use client";

/**
 * /me/settings — Settings Hub
 *
 * 6개 카테고리 카드 그리드로 설정 파편화를 통합한 허브 페이지.
 * mobile 1열 / tablet 2열 / desktop 3열
 */

import Link from "next/link";
import { useI18n } from "@/i18n";

type CategoryKey =
  | "profile"
  | "display"
  | "accessibility"
  | "notifications"
  | "privacy"
  | "account";

const CATEGORIES: {
  key: CategoryKey;
  href: string;
  icon: string;
}[] = [
  { key: "profile", href: "/me/settings/profile", icon: "👤" },
  { key: "display", href: "/me/settings/display", icon: "🌐" },
  { key: "accessibility", href: "/me/settings/accessibility", icon: "♿" },
  { key: "notifications", href: "/me/settings/notifications", icon: "🔔" },
  { key: "privacy", href: "/me/settings/privacy", icon: "🔒" },
  { key: "account", href: "/me/settings/account", icon: "⚙️" },
];

export default function SettingsHubPage() {
  const { t } = useI18n();

  return (
    <main className="flex-1 min-w-0 max-w-3xl mx-auto px-4 py-8">
      {/* Header */}
      <header className="mb-8">
        <h1 className="text-2xl font-bold text-text-primary">
          {t("settings.hub.title")}
        </h1>
        <p className="text-text-muted mt-1 text-sm">
          {t("settings.hub.subtitle")}
        </p>
      </header>

      {/* Category card grid */}
      <div
        className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4"
        role="list"
        aria-label={t("settings.hub.title")}
      >
        {CATEGORIES.map(({ key, href, icon }) => (
          <Link
            key={key}
            href={href}
            role="listitem"
            className="group flex items-start gap-4 rounded-xl border border-border bg-surface p-5 hover:bg-surface-hover transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2"
            aria-label={`${t(`settings.hub.category.${key}.title` as Parameters<typeof t>[0])} — ${t(`settings.hub.category.${key}.description` as Parameters<typeof t>[0])}`}
          >
            {/* Icon */}
            <span
              className="flex-shrink-0 text-2xl w-10 h-10 flex items-center justify-center rounded-lg bg-surface-hover group-hover:bg-background transition-colors"
              aria-hidden="true"
            >
              {icon}
            </span>

            {/* Text */}
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold text-text-primary leading-snug">
                {t(`settings.hub.category.${key}.title` as Parameters<typeof t>[0])}
              </p>
              <p className="text-xs text-text-muted mt-0.5 leading-relaxed">
                {t(`settings.hub.category.${key}.description` as Parameters<typeof t>[0])}
              </p>
            </div>

            {/* Arrow */}
            <span
              className="flex-shrink-0 text-text-muted group-hover:text-text-primary group-hover:translate-x-0.5 transition-transform mt-0.5"
              aria-hidden="true"
            >
              <svg
                width="16"
                height="16"
                viewBox="0 0 16 16"
                fill="none"
                aria-hidden="true"
              >
                <path
                  d="M6 3l5 5-5 5"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </span>
          </Link>
        ))}
      </div>
    </main>
  );
}
