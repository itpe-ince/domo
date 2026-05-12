"use client";

/**
 * SkipLink — H'-1 voiceover-nvda-test-fix
 *
 * WCAG 2.4.1 Bypass Blocks (Level A) compliance.
 * Renders a visually-hidden anchor that becomes visible on keyboard focus,
 * allowing screen-reader / keyboard-only users to skip sidebar navigation
 * and jump directly to the main content landmark.
 *
 * Usage: place as the very first child of <body> (inside AppShell, before Sidebar).
 * The target element must have id="main-content".
 */

import { useI18n } from "@/i18n";

export function SkipLink() {
  const { t } = useI18n();

  return (
    <a
      href="#main-content"
      className={[
        // Hidden by default — only visible when focused via keyboard
        "sr-only focus:not-sr-only",
        // Positioning: appears at top-left corner when focused
        "focus:fixed focus:top-2 focus:left-2 focus:z-[9999]",
        // Styling
        "focus:inline-block focus:px-4 focus:py-2",
        "focus:rounded-md focus:bg-primary focus:text-background",
        "focus:text-sm focus:font-semibold focus:shadow-lg",
        "focus:outline-none focus:ring-2 focus:ring-background focus:ring-offset-2 focus:ring-offset-primary",
      ].join(" ")}
    >
      {t("a11y.skip.toMain")}
    </a>
  );
}
