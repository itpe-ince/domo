"use client";

/**
 * /me/settings/accessibility — Phase 9 L-E
 *
 * 접근성 설정 페이지.
 * - 인지 단순 모드 토글 (localStorage + DB 동기화)
 * - 포커스 모드 안내
 * - OS 고대비 모드 힌트
 */

import Link from "next/link";
import { useEffect, useState } from "react";
import { useI18n } from "@/i18n";
import { ToggleSwitch } from "@/components/ToggleSwitch";
import { useCognitiveSimpleModeContext } from "@/components/CognitiveSimpleModeProvider";

export default function AccessibilitySettingsPage() {
  const { t } = useI18n();
  const { enabled, toggle } = useCognitiveSimpleModeContext();
  const [saved, setSaved] = useState(false);
  const [saving, setSaving] = useState(false);

  // saved 메시지 3초 후 자동 숨김
  useEffect(() => {
    if (!saved) return;
    const timer = setTimeout(() => setSaved(false), 3000);
    return () => clearTimeout(timer);
  }, [saved]);

  async function handleToggle(next: boolean) {
    setSaving(true);
    try {
      await toggle(next);
      setSaved(true);
    } finally {
      setSaving(false);
    }
  }

  return (
    <main id="main-content" className="flex-1 min-w-0 max-w-2xl mx-auto px-6 py-8">
      <nav aria-label="breadcrumb" className="mb-6">
        <Link
          href="/me/account"
          className="text-text-subtle text-sm hover:text-primary"
        >
          ← {t("common.settings")}
        </Link>
      </nav>

      <h1 className="text-2xl font-bold mb-2">{t("accessibility.pageTitle")}</h1>
      <p className="text-text-subtle text-sm mb-8">
        {t("accessibility.contrast.highContrastHint")}
      </p>

      {/* 저장 완료 알림 */}
      {saved && (
        <div
          role="status"
          aria-live="polite"
          aria-atomic="true"
          className="card border-primary p-3 text-primary text-sm mb-6"
        >
          {t("accessibility.settings.saved")}
        </div>
      )}

      {/* 단순 모드 섹션 */}
      <section
        aria-labelledby="simple-mode-heading"
        className="card p-6 space-y-4 mb-6"
      >
        <h2 id="simple-mode-heading" className="text-lg font-semibold">
          {t("accessibility.simpleMode.label")}
        </h2>
        <p className="text-text-subtle text-sm">
          {t("accessibility.simpleMode.description")}
        </p>

        <ToggleSwitch
          id="cognitive-simple-mode"
          checked={enabled}
          onChange={handleToggle}
          label={saving
            ? t("common.loading")
            : enabled
              ? t("accessibility.simpleMode.enabled")
              : t("accessibility.simpleMode.disabled")
          }
          disabled={saving}
        />

        {/* 단순 모드 ON 시 5가지 변경 사항 안내 */}
        <ul className="mt-3 space-y-1 text-sm text-text-subtle list-disc list-inside">
          <li>텍스트 크기 1.2배 확대</li>
          <li>줄 간격 1.8 적용</li>
          <li>애니메이션 최소화</li>
          <li>장식 요소 제거</li>
          <li>배경 블러 효과 제거</li>
        </ul>
      </section>

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
