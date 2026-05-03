"use client";

/**
 * PublishOptionsPanel — publish-controls PDCA #8, Task 3.4.
 *
 * 4 sub-controls in one panel (no sub-files):
 *   1. VisibilitySelector — 3 styled radio buttons
 *   2. CommentsToggle — accessible switch
 *   3. SeriesSelector — checkbox list + "새 시리즈 만들기"
 *   4. ScheduledPicker — datetime-local with min/max + timezone hint
 *
 * Props are forwarded from page.tsx via EditorWorkspace / EditorMobileWizard.
 */

import { useState, useEffect } from "react";
import { useI18n } from "@/i18n";
import type { Visibility, Series } from "@/lib/api";

export interface PublishOptionsPanelProps {
  visibility: Visibility;
  setVisibility: (v: Visibility) => void;
  commentsEnabled: boolean;
  setCommentsEnabled: (b: boolean) => void;
  seriesIds: string[];
  setSeriesIds: (ids: string[]) => void;
  scheduledAt: string;
  setScheduledAt: (v: string) => void;
  mySeries: Series[];
  seriesLoading: boolean;
  disabled?: boolean;
  onCreateSeriesClick: () => void;
}

// ─── Scheduled date helpers ───────────────────────────────────────────────

function minScheduled(): string {
  return new Date(Date.now() + 5 * 60 * 1000).toISOString().slice(0, 16);
}

function maxScheduled(): string {
  return new Date(Date.now() + 365 * 24 * 60 * 60 * 1000).toISOString().slice(0, 16);
}

function validateScheduled(value: string): "tooSoon" | "tooFar" | null {
  if (!value) return null;
  const ts = new Date(value).getTime();
  const now = Date.now();
  if (ts < now + 5 * 60 * 1000) return "tooSoon";
  if (ts > now + 365 * 24 * 60 * 60 * 1000) return "tooFar";
  return null;
}

// ─── Visibility option config ─────────────────────────────────────────────

type VisibilityOption = {
  value: Visibility;
  icon: string;
  labelKey: string;
  hintKey: string;
};

const VISIBILITY_OPTIONS: VisibilityOption[] = [
  {
    value: "public",
    icon: "🌐",
    labelKey: "post.editor.publishOptions.visibility.public",
    hintKey: "post.editor.publishOptions.visibility.publicHint",
  },
  {
    value: "followers_only",
    icon: "🔒",
    labelKey: "post.editor.publishOptions.visibility.followersOnly",
    hintKey: "post.editor.publishOptions.visibility.followersHint",
  },
  {
    value: "unlisted",
    icon: "🔗",
    labelKey: "post.editor.publishOptions.visibility.unlisted",
    hintKey: "post.editor.publishOptions.visibility.unlistedHint",
  },
];

// ─── Component ────────────────────────────────────────────────────────────

export function PublishOptionsPanel({
  visibility,
  setVisibility,
  commentsEnabled,
  setCommentsEnabled,
  seriesIds,
  setSeriesIds,
  scheduledAt,
  setScheduledAt,
  mySeries,
  seriesLoading,
  disabled = false,
  onCreateSeriesClick,
}: PublishOptionsPanelProps) {
  const { t } = useI18n();
  const [scheduleError, setScheduleError] = useState<string | null>(null);
  const tz = Intl.DateTimeFormat().resolvedOptions().timeZone;

  // Re-validate whenever scheduledAt changes
  useEffect(() => {
    if (!scheduledAt) {
      setScheduleError(null);
      return;
    }
    const err = validateScheduled(scheduledAt);
    if (err === "tooSoon") {
      setScheduleError(t("post.editor.publishOptions.scheduled.tooSoon"));
    } else if (err === "tooFar") {
      setScheduleError(t("post.editor.publishOptions.scheduled.tooFar"));
    } else {
      setScheduleError(null);
    }
  }, [scheduledAt, t]);

  function toggleSeries(id: string) {
    if (seriesIds.includes(id)) {
      setSeriesIds(seriesIds.filter((s) => s !== id));
    } else {
      setSeriesIds([...seriesIds, id]);
    }
  }

  return (
    <div className="flex flex-col divide-y divide-border">
      {/* Header */}
      <div className="px-4 py-3">
        <h3 className="text-sm font-semibold text-text-primary">
          {t("post.editor.publishOptions.title")}
        </h3>
      </div>

      {/* 1. Visibility */}
      <section className="px-4 py-4 space-y-2">
        <p className="text-xs font-medium text-text-secondary uppercase tracking-wide">
          {t("post.editor.publishOptions.visibility.label")}
        </p>
        <div role="radiogroup" aria-label={t("post.editor.publishOptions.visibility.label")} className="flex flex-col gap-2">
          {VISIBILITY_OPTIONS.map((opt) => {
            const isSelected = visibility === opt.value;
            return (
              <button
                key={opt.value}
                type="button"
                role="radio"
                aria-checked={isSelected}
                disabled={disabled}
                onClick={() => setVisibility(opt.value)}
                className={[
                  "flex items-start gap-3 rounded-lg border px-3 py-2.5 text-left transition-colors",
                  isSelected
                    ? "bg-surface-hover border-primary"
                    : "border-border hover:bg-surface-hover",
                  disabled ? "opacity-50 cursor-not-allowed" : "cursor-pointer",
                ].join(" ")}
              >
                <span className="text-base leading-none mt-0.5" aria-hidden>
                  {opt.icon}
                </span>
                <span className="flex flex-col gap-0.5 min-w-0">
                  <span className="text-sm font-medium text-text-primary">
                    {t(opt.labelKey)}
                  </span>
                  <span className="text-xs text-text-muted">
                    {t(opt.hintKey)}
                  </span>
                </span>
              </button>
            );
          })}
        </div>
      </section>

      {/* 2. Comments toggle */}
      <section className="px-4 py-4">
        <div className="flex items-center justify-between gap-3">
          <div className="flex flex-col gap-0.5">
            <span className="text-sm font-medium text-text-primary">
              {t("post.editor.publishOptions.comments.label")}
            </span>
            <span className="text-xs text-text-muted">
              {t("post.editor.publishOptions.comments.hint")}
            </span>
          </div>
          <button
            type="button"
            role="switch"
            aria-checked={commentsEnabled}
            disabled={disabled}
            onClick={() => setCommentsEnabled(!commentsEnabled)}
            className={[
              "relative inline-flex h-6 w-11 flex-shrink-0 rounded-full border-2 transition-colors duration-200",
              commentsEnabled ? "bg-primary border-primary" : "bg-border border-border",
              disabled ? "opacity-50 cursor-not-allowed" : "cursor-pointer",
            ].join(" ")}
          >
            <span className="sr-only">
              {commentsEnabled
                ? t("post.editor.publishOptions.comments.enabled")
                : t("post.editor.publishOptions.comments.disabled")}
            </span>
            <span
              className={[
                "pointer-events-none inline-block h-4 w-4 rounded-full bg-white shadow-sm transform transition-transform duration-200 mt-0.5",
                commentsEnabled ? "translate-x-5" : "translate-x-0.5",
              ].join(" ")}
            />
          </button>
        </div>
      </section>

      {/* 3. Series selector */}
      <section className="px-4 py-4 space-y-3">
        <p className="text-xs font-medium text-text-secondary uppercase tracking-wide">
          {t("post.editor.publishOptions.series.label")}
        </p>

        {seriesLoading ? (
          <div className="text-xs text-text-muted animate-pulse">
            {t("common.loading")}
          </div>
        ) : mySeries.length === 0 ? (
          <div className="flex flex-col gap-2">
            <p className="text-xs text-text-muted">
              {t("post.editor.publishOptions.series.none")}
            </p>
            <button
              type="button"
              disabled={disabled}
              onClick={onCreateSeriesClick}
              className="text-xs text-primary hover:underline text-left disabled:opacity-50"
            >
              {t("post.editor.publishOptions.series.createNew")}
            </button>
          </div>
        ) : (
          <div className="flex flex-col gap-1.5">
            {mySeries.map((s) => (
              <label
                key={s.id}
                className={[
                  "flex items-center gap-2.5 rounded-md px-2 py-1.5 cursor-pointer hover:bg-surface-hover transition-colors",
                  disabled ? "pointer-events-none opacity-50" : "",
                ].join(" ")}
              >
                <input
                  type="checkbox"
                  checked={seriesIds.includes(s.id)}
                  onChange={() => toggleSeries(s.id)}
                  disabled={disabled}
                  className="accent-primary h-4 w-4 flex-shrink-0"
                />
                <span className="flex items-center gap-1.5 min-w-0">
                  <span className="text-sm text-text-primary truncate">
                    {s.title}
                  </span>
                  {s.post_count != null && (
                    <span className="text-[10px] text-text-muted bg-surface rounded-full px-1.5 py-0.5 flex-shrink-0">
                      {s.post_count}
                    </span>
                  )}
                </span>
              </label>
            ))}
            <button
              type="button"
              disabled={disabled}
              onClick={onCreateSeriesClick}
              className="text-xs text-primary hover:underline text-left mt-1 disabled:opacity-50"
            >
              {t("post.editor.publishOptions.series.createNew")}
            </button>
          </div>
        )}
      </section>

      {/* 4. Scheduled picker */}
      <section className="px-4 py-4 space-y-2">
        <p className="text-xs font-medium text-text-secondary uppercase tracking-wide">
          {t("post.editor.publishOptions.scheduled.label")}
        </p>

        <div className="flex flex-col gap-1.5">
          <input
            type="datetime-local"
            value={scheduledAt}
            min={minScheduled()}
            max={maxScheduled()}
            disabled={disabled}
            onChange={(e) => setScheduledAt(e.target.value)}
            placeholder={t("post.editor.publishOptions.scheduled.placeholder")}
            className={[
              "w-full min-w-0 text-sm bg-surface border rounded-md px-3 py-2 text-text-primary outline-none focus:ring-1 focus:ring-primary transition-colors",
              scheduleError ? "border-danger focus:ring-danger" : "border-border",
              disabled ? "opacity-50 cursor-not-allowed" : "",
            ].join(" ")}
          />

          <p className="text-[11px] text-text-muted">
            {t("post.editor.publishOptions.scheduled.timezone").replace(
              "{tz}",
              tz
            )}
          </p>

          {scheduleError && (
            <p role="alert" className="text-xs text-danger">
              {scheduleError}
            </p>
          )}

          {scheduledAt && !scheduleError && (
            <button
              type="button"
              disabled={disabled}
              onClick={() => setScheduledAt("")}
              className="text-xs text-text-muted hover:text-text-primary text-left disabled:opacity-50 transition-colors"
            >
              {t("post.editor.publishOptions.scheduled.clearLabel")}
            </button>
          )}
        </div>
      </section>
    </div>
  );
}
