"use client";

/**
 * EditorStepPublish — editor-responsive-redesign PDCA (#3, Step 4).
 *
 * Mobile wizard final step: shows scheduled-at and location badges (with
 * removal), the digital-art notice, and any submission error. Actual
 * "등록" button lives in EditorMobileWizard's footer (per OQ-D-3 = B —
 * primary submit button only on the last step).
 *
 * Pattern source: design §4.1 (EditorStepPublish).
 */

import { useI18n } from "@/i18n";

export interface EditorStepPublishProps {
  scheduledAt: string;
  onScheduledAtChange: (v: string) => void;
  locationName: string;
  onLocationNameChange: (v: string) => void;
  onLocationLatChange: (v: number | null) => void;
  onLocationLngChange: (v: number | null) => void;
  error: string | null;
}

export function EditorStepPublish({
  scheduledAt,
  onScheduledAtChange,
  locationName,
  onLocationNameChange,
  onLocationLatChange,
  onLocationLngChange,
  error,
}: EditorStepPublishProps) {
  const { t } = useI18n();
  return (
    <section className="space-y-4">
      <header className="space-y-1">
        <h2 className="text-base font-semibold">
          {t("post.editor.wizard.stepPublish.title")}
        </h2>
        <p className="text-xs text-text-muted">
          {t("post.editor.wizard.stepPublish.hint")}
        </p>
      </header>

      {/* Schedule / Location badges (read-only summary; modify via toolbar) */}
      {(scheduledAt || locationName) ? (
        <div className="flex flex-wrap gap-2">
          {scheduledAt && (
            <span className="flex items-center gap-1.5 bg-surface rounded-full px-3 py-1 text-xs text-primary">
              ⏰ {new Date(scheduledAt).toLocaleString("ko-KR")} 예약
              <button
                type="button"
                onClick={() => onScheduledAtChange("")}
                className="text-text-muted hover:text-danger"
                aria-label="예약 해제"
              >
                ✕
              </button>
            </span>
          )}
          {locationName && (
            <span className="flex items-center gap-1.5 bg-surface rounded-full px-3 py-1 text-xs text-primary">
              📍 {locationName}
              <button
                type="button"
                onClick={() => {
                  onLocationNameChange("");
                  onLocationLatChange(null);
                  onLocationLngChange(null);
                }}
                className="text-text-muted hover:text-danger"
                aria-label="위치 해제"
              >
                ✕
              </button>
            </span>
          )}
        </div>
      ) : (
        <p className="text-xs text-text-muted">
          {t("post.editor.wizard.stepPublish.empty")}
        </p>
      )}

      {/* ② artCheckNote 상시 표시 제거 — 등록 버튼 클릭 시 경고 모달로 대체 */}

      {error && (
        <div className="card border-danger p-3 text-danger text-sm">
          {error}
        </div>
      )}
    </section>
  );
}
