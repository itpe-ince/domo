"use client";

/**
 * /me/settings/accessibility — Phase 9 L-E
 *
 * 접근성 설정 페이지.
 * - 포커스 모드 안내
 * - OS 고대비 모드 힌트
 */

import Link from "next/link";
import { useI18n } from "@/i18n";

export default function AccessibilitySettingsPage() {
  const { t } = useI18n();

  return (
    <main className="flex-1 min-w-0 max-w-2xl mx-auto px-6 py-8">
      <nav aria-label="breadcrumb" className="mb-6">
        <Link
          href="/me/settings"
          className="text-text-subtle text-sm hover:text-primary"
        >
          ← {t("settings.hub.title")}
        </Link>
      </nav>

      <h1 className="text-2xl font-bold mb-2">{t("accessibility.pageTitle")}</h1>
      <p className="text-text-subtle text-sm mb-8">
        {t("accessibility.contrast.highContrastHint")}
      </p>

      {/* 포커스 모드 섹션 */}
      <section
        aria-labelledby="focus-mode-heading"
        className="card p-6 space-y-3 mb-6"
      >
        <h2 id="focus-mode-heading" className="text-lg font-semibold">
          {t("accessibility.focusMode.label")}
        </h2>
        <p className="text-text-subtle text-sm">
          {t("accessibility.focusMode.description")}
        </p>
        <p className="text-xs text-text-muted">
          키보드로 탐색할 때 모든 인터랙티브 요소에 2px 포커스 링이 표시됩니다.
        </p>
      </section>

      {/* OS 고대비 힌트 */}
      <section
        aria-labelledby="contrast-hint-heading"
        className="card p-6 space-y-2"
      >
        <h2 id="contrast-hint-heading" className="text-lg font-semibold">
          색상 대비
        </h2>
        <p className="text-text-subtle text-sm">
          {t("accessibility.contrast.highContrastHint")}
        </p>
      </section>
    </main>
  );
}
